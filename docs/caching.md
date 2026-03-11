# 09 — 缓存与 LLM 调用优化

## 1. 设计目标

- 最小化 LLM API 调用次数和成本
- 用户获得解题帮助的响应时间 < 2 秒（大多数情况）
- 随着题库增长，边际成本趋近于零

核心原则：**LLM 只做一次，结果永久复用。**

---

## 2. 用户输入的三种情况

### 情况一：完全相同的输入

两个用户输入了一模一样的题目文字。

**方案：精确匹配缓存（Exact Cache）**

以输入文字的 SHA256 哈希作为 key，存入 Redis。命中直接返回，不调用任何 API。

```
用户输入
    │
    ▼
SHA256(input_text) → 查 Redis
    │
    ├── 命中 → 直接返回（$0，< 5ms）
    │
    └── 未命中 → 进入下一层
```

### 情况二：表述略有不同，本质相同

同一道题，不同学生用不同方式输入：
- "求 x² + 2x + 1 = 0 的根"
- "解方程 x² + 2x + 1 = 0"
- "x squared plus 2x plus 1 equals zero, find x"

**方案：向量语义缓存（Semantic Cache）**

对输入文字生成 Embedding，在 `semantic_cache` 表中做向量相似搜索。相似度超过阈值则复用已有答案。

```
用户输入
    │
    ▼
生成 Embedding（$0.0001）
    │
    ▼
pgvector 相似搜索
    │
    ├── 相似度 > 0.95 → 复用答案（< 50ms）
    │                   标注"类似问题的解答"
    │
    └── 相似度 < 0.95 → 进入下一层
```

### 情况三：原理完全相同，具体内容不同

两道题用同一套解题思路，但题目数据、场景、表述都不同：

> 题 A：一个 2kg 物体受 5N 合力，从静止运动 3 秒，求末速度。
> 题 B：一个 500g 物体受 2N 合力，初速度 1m/s，运动 4 秒，求位移。

两题都是"牛顿第二定律 + 运动学公式"，但无法用精确匹配或语义相似直接复用答案。

**方案：解题框架复用（Template Reuse）**

不复用答案，复用**解题过程的抽象结构**。识别到相同模板后，用轻量模型（Haiku）按已有框架执行，而非让重量模型（Sonnet）从零分析。

```
用户输入
    │
    ▼
向量匹配找到相似题（0.80–0.95 相似度区间）
    │
    ▼
取出该题的 solution_framework
    │
    ▼
Haiku + 框架 → 针对新题执行（$0.001，< 2s）
    │
    ▼
结果存入 semantic_cache
```

---

## 3. solution_framework：存什么

`solution_framework` 是每道题在入库时由 Sonnet 一次性生成并存储的**解题过程抽象结构**，不是答案本身。

存的是 LLM 解题时的**思考过程**，让后续的轻量模型不需要重新"想方法"，只需要按框架执行。

### 3.1 理科计算题（物理、化学、数学）

存推理链：解题步骤的逻辑顺序和每步用到的原理。

```json
{
  "topic": "Newton's Second Law + Kinematics",
  "reasoning_chain": [
    "识别已知量：列出题目给出的所有数值和单位",
    "确认初始条件：初速度是否为零，方向如何",
    "用牛顿第二定律求加速度：F_net = ma → a = F/m",
    "用运动学公式求目标量：v = u + at 或 s = ut + ½at²",
    "检查单位一致性，给出最终答案"
  ],
  "key_principles": [
    "牛顿第二定律（F = ma）",
    "匀加速直线运动公式"
  ],
  "what_to_identify": [
    "题目给的是合力还是某个分力",
    "初速度是否明确给出或隐含为零",
    "是否需要考虑方向（矢量）"
  ],
  "common_mistakes": [
    "将重力误用为合力",
    "忘记初速度不为零的情况",
    "混淆位移和路程"
  ],
  "achievement_level_guide": {
    "achieved": "正确代入公式得到数值答案",
    "merit": "过程完整，单位正确，说明每步依据",
    "excellence": "分析受力情况，讨论方向，验证结果合理性"
  }
}
```

### 3.2 数学证明题

存证明策略：选择哪种证明方法，以及证明的骨架结构。

```json
{
  "topic": "Proof by Contradiction",
  "proof_strategy": "反证法",
  "structure": [
    "假设结论不成立（写出否命题）",
    "基于假设进行逻辑推导",
    "推导出与已知条件矛盾的结果",
    "因此假设不成立，原结论成立"
  ],
  "key_lemmas": [
    "需要用到的中间定理或引理"
  ],
  "what_to_identify": [
    "结论的否命题如何表述",
    "推导中需要用到哪些已知定理"
  ],
  "common_mistakes": [
    "否命题表述不准确",
    "推导步骤跳跃，缺少依据"
  ]
}
```

### 3.3 文科分析题（历史、经济、地理）

存答题结构：回答框架和各评分等级的关注点。

```json
{
  "topic": "Economic Policy Analysis",
  "answer_structure": "PEEL",
  "components": [
    "Point：明确论点，直接回应题目要求",
    "Evidence：引用具体数据、史实或案例",
    "Explain：解释证据如何支持论点",
    "Link：联系回题目核心问题"
  ],
  "what_to_identify": [
    "题目要求分析、评价还是解释",
    "需要覆盖几个论点（看分值）",
    "是否需要讨论正反两面"
  ],
  "achievement_level_guide": {
    "achieved": "能识别相关概念并作基本解释",
    "merit": "论点清晰，有具体证据支持",
    "excellence": "深度分析，讨论多角度影响，有自己的判断"
  },
  "common_mistakes": [
    "只描述现象，没有分析原因",
    "论据与论点脱节",
    "没有联系具体情境"
  ]
}
```

### 3.4 生物分析题

存分析路径：生物题通常需要联系结构与功能，存分析的切入点。

```json
{
  "topic": "Enzyme Activity Analysis",
  "analysis_path": [
    "识别实验变量：自变量、因变量、控制变量",
    "描述图表趋势（如有）",
    "用酶的结构或特性解释趋势原因",
    "联系到生物体的实际意义"
  ],
  "key_concepts": [
    "酶的活性位点与底物专一性",
    "温度/pH 对酶构象的影响",
    "活化能的概念"
  ],
  "what_to_identify": [
    "是描述题还是解释题（关键词：describe/explain/discuss）",
    "是否需要提及具体的生化机制"
  ]
}
```

---

## 4. solution_framework 的生成时机

在 **Parse Pipeline（03-parser.md）** 的 Step 5 写入数据库之后，作为额外的 Celery 任务触发：

```
parse_paper 任务完成
        │
        ▼
generate_frameworks(paper_id)   ← 新增 Celery 任务
        │
  对每道新题调用 Sonnet
  生成 solution_framework
        │
        ▼
写入 questions.solution_framework
        │
        ▼
写入 questions.solution_steps     ← 同时生成完整解题过程
写入 questions.key_concepts       ← 知识点解释
写入 questions.common_mistakes    ← 常见错误
写入 questions.hint_level_1       ← 轻提示
写入 questions.hint_level_2       ← 中提示
```

**一道题调用 Sonnet 一次，生成所有预计算内容，此后永不再为这道题调用 Sonnet。**

---

## 5. 数据库变更

### 5.1 `questions` 表新增字段

在 `04-database.md` 的 questions 表基础上新增：

```sql
-- 预计算内容（离线生成，在线直接读取）
solution_steps          text,         -- 完整分步解题过程
solution_framework      jsonb,        -- 解题框架（见第3节）
key_concepts            text,         -- 本题涉及知识点解释
common_mistakes         text,         -- 常见错误提示
hint_level_1            text,         -- 轻提示（不透露答案）
hint_level_2            text,         -- 中提示
framework_generated_at  timestamptz,  -- 框架生成时间

-- 索引：快速找到未生成框架的题目
CREATE INDEX idx_questions_no_framework
  ON questions (id)
  WHERE solution_framework IS NULL;
```

### 5.2 新增 `semantic_cache` 表

```sql
CREATE TABLE semantic_cache (
    id              uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    input_hash      varchar(64) UNIQUE,  -- SHA256，精确匹配用
    input_text      text NOT NULL,
    embedding       vector(1536),        -- 语义匹配用
    response        jsonb NOT NULL,      -- 存储的完整响应
    model_used      varchar(30),         -- 生成此响应用的模型
    template_id     uuid,                -- 如果是框架复用，记录来源题目
    hit_count       int DEFAULT 0,       -- 被命中次数（用于分析）
    created_at      timestamptz DEFAULT now(),
    last_hit_at     timestamptz
);

-- 向量索引
CREATE INDEX idx_semantic_cache_embedding
  ON semantic_cache
  USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 50);

-- 精确匹配索引
CREATE UNIQUE INDEX idx_semantic_cache_hash
  ON semantic_cache (input_hash);
```

---

## 6. 完整处理流程

```
用户提交题目
      │
      ▼
┌─────────────────────────────────────────┐
│ Layer 1：精确匹配                        │
│ SHA256(input) → Redis                   │
│ 命中 → 返回（$0，< 5ms）                │
└──────────────────┬──────────────────────┘
                   │ 未命中
                   ▼
┌─────────────────────────────────────────┐
│ Layer 2：语义缓存                        │
│ Embedding → semantic_cache 向量搜索     │
│ 相似度 > 0.95 → 返回（$0.0001，< 50ms）│
└──────────────────┬──────────────────────┘
                   │ 未命中
                   ▼
┌─────────────────────────────────────────┐
│ Layer 3：框架复用                        │
│ 相似度 0.80–0.95 区间                   │
│ 取出匹配题的 solution_framework         │
│ Haiku + 框架 → 执行（$0.001，< 2s）    │
│ 结果存入 semantic_cache                 │
└──────────────────┬──────────────────────┘
                   │ 未命中（真正新题）
                   ▼
┌─────────────────────────────────────────┐
│ Layer 4：Sonnet 完整分析                 │
│ 从零分析，生成答案 + framework          │
│ （$0.01，< 8s）                         │
│ 结果存入 semantic_cache                 │
│ framework 写入 questions 表             │
└─────────────────────────────────────────┘
```

---

## 7. 模型选择策略

| 场景 | 模型 | 原因 |
|------|------|------|
| 离线预计算框架（一次性） | claude-sonnet-4-6 | 需要深度理解，质量优先 |
| Layer 3 框架复用执行 | claude-haiku-4-5 | 框架已给，执行为主，速度和成本优先 |
| Layer 4 真正新题 | claude-sonnet-4-6 | 需要从零推理 |
| 学生答案针对性点评 | claude-haiku-4-5 | 参考答案已有，对比执行为主 |
| Embedding 生成 | text-embedding-3-large | 语义质量高，成本极低 |

---

## 8. 学生提交答案的特殊处理

学生输入自己的答案请求点评，这是唯一无法完全预计算的场景（答案是动态的）。但可以通过规则匹配减少 LLM 调用：

```
学生提交答案
      │
      ▼
规则匹配（关键词、数值、结构）
      │
      ├── 匹配度高（> 80%）
      │   → 返回预设的 common_mistakes 反馈
      │   → 不调用 LLM（$0）
      │
      └── 匹配度低
          → Haiku + 标准答案 + 学生答案
          → 针对性点评（$0.001）
```

---

## 9. 成本估算

### 一次性离线预计算（全量 30K 题）

| 项目 | 数量 | 单价 | 合计 |
|------|------|------|------|
| Sonnet 生成框架 | 30,000 题 | $0.001/题 | $30 |
| Embedding 生成 | 30,000 题 | $0.0001/题 | $3 |
| **合计** | | | **$33** |

### 每日运营成本（1,000 用户/天，每人平均 5 次查询）

| 层级 | 预估命中率 | 调用次数 | 日成本 |
|------|-----------|---------|--------|
| Layer 1 精确缓存 | 30% | 0 | $0 |
| Layer 2 语义缓存 | 40% | 1,500 次 Embedding | $0.15 |
| Layer 3 框架复用 | 20% | 1,000 次 Haiku | $1.00 |
| Layer 4 新题 | 10% | 500 次 Sonnet | $5.00 |
| **合计** | | | **~$6/天** |

随着用户增多，缓存命中率持续上升，Layer 4 触发比例持续下降，边际成本趋近于零。

---

## 10. 缓存失效策略

| 缓存类型 | 失效策略 | 原因 |
|---------|---------|------|
| Redis 精确缓存 | 永不过期 | 题目答案不会变 |
| semantic_cache | 永不删除，只追加 | 复用价值持续存在 |
| questions.solution_framework | 手动触发更新 | 只在模型升级时重新生成 |
| 预计算解析内容 | 手动触发更新 | 人工审核修正后重新生成 |