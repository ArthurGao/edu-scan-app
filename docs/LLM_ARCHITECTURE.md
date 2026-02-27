# EduScan LLM 调用架构详解

## 目录

- [整体架构](#整体架构)
- [LLM Registry — 模型注册中心](#llm-registry--模型注册中心)
- [完整调用链路](#完整调用链路)
  - [阶段 1: OCR 图片文字提取](#阶段-1-ocr-图片文字提取)
  - [阶段 2: Analyze 题目分类](#阶段-2-analyze-题目分类)
  - [阶段 3: Retrieve RAG 检索](#阶段-3-retrieve-rag-检索)
  - [阶段 4: Solve 核心解题](#阶段-4-solve-核心解题)
  - [阶段 5: Quick Verify 快速验算](#阶段-5-quick-verify-快速验算)
  - [阶段 6: Enrich 结果丰富](#阶段-6-enrich-结果丰富)
  - [阶段 7: Deep Evaluate 深度评估（异步）](#阶段-7-deep-evaluate-深度评估异步)
  - [阶段 8: Embedding 向量化存储](#阶段-8-embedding-向量化存储)
- [Follow-up 追问对话](#follow-up-追问对话)
- [重试与容错机制](#重试与容错机制)
- [模型选择策略](#模型选择策略)
- [Prompt 设计规范](#prompt-设计规范)
- [调用汇总表](#调用汇总表)
- [关键文件索引](#关键文件索引)

---

## 整体架构

EduScan 后端通过 **LangGraph** 构建了一条有向状态图 (StateGraph) pipeline。用户上传图片或文字后，经过 OCR → 分析 → 检索 → 解题 → 验证 → 丰富 的完整链路，期间调用多个不同的 LLM。

```
用户上传图片/文字
        │
        ▼
┌──────────────────────────────────────────────────────────┐
│  API Layer: POST /api/v1/scan/solve                      │
│  → ScanService.scan_and_solve()                          │
└───────────────────────┬──────────────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────────────────┐
│              LangGraph solve_graph                        │
│                                                          │
│  ┌─────┐   ┌─────────┐   ┌──────────┐   ┌───────┐      │
│  │ OCR │──▶│ ANALYZE  │──▶│ RETRIEVE │──▶│ SOLVE │      │
│  │LLM1 │   │  LLM2   │   │ (向量DB) │   │ LLM3  │      │
│  └─────┘   └─────────┘   └──────────┘   └───┬───┘      │
│                                               │          │
│                                               ▼          │
│                                        ┌────────────┐    │
│                                        │QUICK VERIFY│    │
│                                        │   LLM4     │    │
│                                        └─────┬──────┘    │
│                                              │           │
│                              ┌───────────────┼────────┐  │
│                              │               │        │  │
│                              ▼               ▼        ▼  │
│                          通过验证       验证失败    超时  │
│                          confidence    attempt<2   跳过  │
│                           ≥0.8       ┌──▶SOLVE     │     │
│                              │       │  (换模型)   │     │
│                              ▼       │             ▼     │
│                         ┌────────┐   │       ┌────────┐  │
│                         │ ENRICH │◀──┘       │ ENRICH │  │
│                         │        │           │(caution)│  │
│                         └───┬────┘           └───┬────┘  │
│                             │                    │       │
│                             ▼                    ▼       │
│                            END                  END      │
└──────────────────────────────┬───────────────────────────┘
                               │
                    ┌──────────┼──────────┐
                    ▼                     ▼
          ┌──────────────┐      ┌──────────────┐
          │DEEP EVALUATE │      │  EMBEDDING   │
          │  LLM5 (异步) │      │ OpenAI (异步) │
          └──────────────┘      └──────────────┘
```

---

## LLM Registry — 模型注册中心

> 文件: `app/llm/registry.py`

所有 LLM 调用通过统一的 Registry 获取模型实例。底层使用 LangChain 的 Chat Model 抽象。

### 支持的 Provider

| Provider | LangChain Class | API Key 配置 |
|----------|----------------|-------------|
| `claude` | `ChatAnthropic` (langchain_anthropic) | `ANTHROPIC_API_KEY` |
| `openai` | `ChatOpenAI` (langchain_openai) | `OPENAI_API_KEY` |
| `gemini` | `ChatGoogleGenerativeAI` (langchain_google_genai) | `GOOGLE_API_KEY` |

### 模型分档 (Tier)

每个 Provider 有不同档次的模型，用于不同任务：

| Provider | strong (核心解题) | fast (轻量任务) | verify | evaluate |
|----------|-----------------|----------------|--------|----------|
| claude | claude-sonnet-4-20250514 | claude-haiku-4-5-20251001 | — | — |
| openai | gpt-4o | gpt-4o-mini | — | — |
| gemini | gemini-2.5-flash | gemini-2.5-flash-lite | gemini-2.5-flash-lite | gemini-2.5-flash |

### 两个核心函数

**`get_llm(tier, provider)`** — 按档次和厂商获取模型：

```python
# 获取默认 provider 的 fast 模型
llm = get_llm("fast")

# 获取 Gemini 的 verify 模型
llm = get_llm("verify", "gemini")
```

所有模型统一 `temperature=0.1`。API Key 从 `.env` 通过 pydantic-settings 加载。

**`select_llm(preferred, subject, attempt)`** — 智能选模型（用于 Solve 阶段）：

```python
# 首次解题：按学科选 provider
llm = select_llm(preferred=None, subject="math", attempt=0)
# → 数学用 claude-sonnet-4

# 重试：自动轮换到下一个 provider
llm = select_llm(preferred=None, subject="math", attempt=1)
# → 轮换到 openai gpt-4o
```

学科与 Provider 的映射关系：

| 学科 | 默认 Provider |
|------|-------------|
| math (数学) | claude |
| physics (物理) | claude |
| chinese (语文) | claude |
| chemistry (化学) | openai |
| biology (生物) | openai |
| english (英语) | openai |

---

## 完整调用链路

### 阶段 1: OCR 图片文字提取

> 文件: `app/services/ocr_service.py` → `GeminiVisionOCRProvider`
> Graph 节点: `app/graph/nodes/ocr.py`

**模型**: Gemini 2.5 Flash Lite (固定)
**调用方式**: 多模态 — 图片 base64 + 文字指令

```python
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash-lite",
    temperature=0.0,  # OCR 不需要创造性
)

message = HumanMessage(content=[
    {"type": "text", "text": "Extract ALL text from this image..."},
    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_image}"}},
])

result = await llm.ainvoke([message])
```

**Prompt 要点**:
- 检测图片方向（手机拍照可能旋转）
- 数学表达式用 LaTeX `$...$` 格式输出
- 保留原始排版，多道题自动编号
- 只输出提取的文字，不做其他解释

**预处理**: 调用前先用 Pillow 的 `ImageOps.exif_transpose()` 修正 EXIF 旋转方向。

**容错**: 如果配置的 OCR provider 未实现，自动 fallback 到 Gemini Vision。

**跳过条件**: 如果用户直接输入文字（非图片），跳过 OCR，直接使用 input_text。

---

### 阶段 2: Analyze 题目分类

> 文件: `app/graph/nodes/analyze.py`
> Prompt: `app/llm/prompts/analysis.py`

**模型**: 当前默认 provider 的 **fast** 档（如 claude-haiku-4-5）
**目的**: 识别学科、题型、难度、知识点

```python
llm = get_llm("fast")
messages = build_analysis_messages(ocr_text, grade_level)
result = await llm.ainvoke(messages)
parsed = json.loads(result.content)
```

**System Prompt**:
```
You are an expert education AI that classifies student homework problems.
Analyze the given problem text and identify:
1. Subject (math, physics, chemistry, biology, english, chinese)
2. Problem type (equation, geometry, word_problem, proof, multiple_choice, fill_in_blank)
3. Difficulty (easy, medium, hard)
4. Key knowledge points

Respond ONLY in JSON.
```

**输出示例**:
```json
{
  "subject": "math",
  "problem_type": "equation",
  "difficulty": "medium",
  "knowledge_points": ["algebra", "linear_equations"]
}
```

**容错**: LLM 调用失败时，使用关键词匹配的 fallback 函数 `_detect_subject_fallback()`，扫描文本中的学科关键词（如 "equation"→math, "force"→physics）。

---

### 阶段 3: Retrieve RAG 检索

> 文件: `app/graph/nodes/retrieve.py`

**当前状态**: Placeholder，返回空结果。待接入 pgvector 向量搜索。

**设计目标**: 根据题目文本，从知识库中检索：
- `related_formulas` — 相关公式
- `similar_problems` — 相似的历史题目

检索结果会作为上下文注入 Solve 阶段的 prompt。

---

### 阶段 4: Solve 核心解题

> 文件: `app/graph/nodes/solve.py`
> Prompt: `app/llm/prompts/solve.py`

**模型**: `select_llm()` 智能选择 — 按学科选 provider 的 **strong** 档
**这是整个链路中最核心的 LLM 调用。**

```python
llm = select_llm(
    preferred=state.get("preferred_provider"),
    subject=state.get("detected_subject", "math"),
    attempt=state.get("attempt_count", 0),
)

# 构建 RAG 上下文
context = _build_context(related_formulas, similar_problems)

messages = build_solve_messages(
    ocr_text=ocr_text,
    subject=subject,
    grade_level=grade_level,
    context=context,  # RAG 检索结果注入
)

result = await llm.ainvoke(messages)
```

**System Prompt**:
```
You are an experienced {subject} teacher helping a {grade_level} student.
Your goal is to provide clear, educational explanations that help the student
understand the solution process.

IMPORTANT: Respond ONLY in valid JSON format.
```

**User Prompt 结构**:
```
请分步解题...

数学格式规范：
- formula 字段：纯 LaTeX，不带 $ 符号
- description/calculation 字段：用 $ 和 $$ 包裹数学表达式
- 使用 \frac{}{}, x^{}, \sqrt{} 等 LaTeX 语法

## Reference Context (如果有 RAG 结果)
- 相关公式...
- 相似题目...

## Problem
{ocr_text}

Respond in JSON format:
{
  "question_type": "...",
  "knowledge_points": [...],
  "steps": [{"step": 1, "description": "...", "formula": "...", "calculation": "..."}],
  "final_answer": "...",
  "explanation": "...",
  "tips": "..."
}
```

**JSON 解析容错**:
1. 首先尝试 `json.loads(result.content)`
2. 如果失败，尝试从文本中提取第一个 `{...}` 块
3. 都失败则构造一个兜底结构，把原始回复放入 `final_answer`

**重试机制**: 如果后续 Quick Verify 失败，`attempt_count + 1`，重新进入 Solve 节点，`select_llm` 会自动轮换到不同 provider（如从 Claude → OpenAI → Gemini）。

---

### 阶段 5: Quick Verify 快速验算

> 文件: `app/graph/nodes/quick_verify.py`
> Prompt: `app/llm/prompts/verify.py`

**模型**: Gemini 2.5 Flash Lite (固定)
**目的**: 用不同的模型独立验算答案是否正确
**超时**: 硬限制 **5 秒**

```python
llm = get_llm("verify", "gemini")
messages = build_verify_messages(problem_text, final_answer, steps_summary, subject)

result = await asyncio.wait_for(
    llm.ainvoke(messages),
    timeout=5.0,  # 超时则跳过验证
)
```

**System Prompt** (中文):
```
你是一个数学/理科验算助手。请独立验算以下题目的答案是否正确。

要求：
1. 自己独立计算出正确答案
2. 对比给出的答案
3. 检查关键步骤是否有逻辑错误

仅返回 JSON：
{
  "independent_answer": "你算出的答案",
  "is_correct": true或false,
  "error_description": "如果错误，说明哪步出错",
  "confidence": 0.0到1.0
}
```

**决策逻辑** (`app/graph/edges.py`):

| 条件 | 走向 | 说明 |
|------|------|------|
| `is_correct=true && confidence≥0.8` | → ENRICH | 验证通过 |
| `verify_passed=None` (超时/异常/低置信度) | → ENRICH | 无法验证，跳过 |
| `is_correct=false && attempt<2` | → SOLVE (重试) | 换模型重新解题 |
| `is_correct=false && attempt≥2` | → ENRICH (caution) | 最大重试次数，标记警告 |

**容错**: 超时和异常都返回 `verify_passed=None`，不阻塞主流程。

---

### 阶段 6: Enrich 结果丰富

> 文件: `app/graph/nodes/enrich.py`

**不调用 LLM**。纯数据组装：把解题结果 + 相关公式 + 难度 + 质量分打包成 `final_solution`。

---

### 阶段 7: Deep Evaluate 深度评估（异步）

> 文件: `app/graph/nodes/deep_evaluate.py`
> Prompt: `app/llm/prompts/deep_evaluate.py`

**模型**: Gemini 2.5 Flash (固定)
**执行方式**: `asyncio.create_task()` — 用户已拿到结果后异步执行

```python
# scan_service.py 中触发
asyncio.create_task(self._run_deep_evaluate_background(...))
```

```python
llm = get_llm("evaluate", "gemini")
messages = build_deep_evaluate_messages(
    problem_text, solution_raw, final_answer, steps, subject, grade_level
)
result = await llm.ainvoke(messages)
```

**System Prompt** (中文):
```
你是一位资深教师，正在全面评估一份 K12 学生作业的 AI 解答质量。

评分维度（0.0-1.0）：
- correctness: 答案和每一步计算是否正确
- completeness: 是否覆盖所有考点，有无遗漏步骤
- clarity: 对该年级学生是否易懂
- pedagogy: 是否引导学生思考，而非直接给答案
- format: LaTeX 公式格式、步骤编号、排版是否规范
- overall: 以上五项的加权平均
```

**输出示例**:
```json
{
  "correctness": 0.95,
  "completeness": 0.9,
  "clarity": 0.85,
  "pedagogy": 0.8,
  "format": 0.9,
  "overall": 0.88,
  "improvement_suggestions": "第三步可以补充更多中间推导过程",
  "better_approach": null
}
```

**结果持久化**: 写入 `Solution.deep_evaluation` (JSONB) 和 `Solution.quality_score`。

---

### 阶段 8: Embedding 向量化存储

> 文件: `app/llm/embeddings.py`

**模型**: OpenAI `text-embedding-3-small` (1536 维)
**执行方式**: best-effort，失败不影响主流程

```python
_embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
vector = await _embeddings.aembed_query(text)
```

用于将题目文本嵌入向量，存入 pgvector，为 Retrieve 阶段的"相似题目检索"提供数据基础。

---

## Follow-up 追问对话

> 文件: `app/graph/followup_graph.py`
> Prompt: `app/llm/prompts/followup.py`
> API: `POST /api/v1/scan/{scan_id}/followup`

独立的 LangGraph，用于用户对某道题的追问。

```
START → build_context → generate_reply → END
```

```python
llm = get_llm("strong")  # 默认 provider 的 strong 模型
messages = build_followup_messages(
    conversation_history,  # 完整对话历史
    user_message,
    subject, grade_level,
)
result = await llm.ainvoke(messages)
```

**System Prompt**:
```
You are a patient {subject} teacher having a conversation with a {grade_level} student.
You previously helped them solve a problem. Now they have a follow-up question.
Be encouraging, clear, and educational. Use LaTeX for any formulas.
```

**对话历史格式**: 使用 LangChain 的 `SystemMessage` / `HumanMessage` / `AIMessage` 交替排列，保持完整上下文。

**持久化**: 每轮对话保存到 `conversation_messages` 表，通过 `ConversationService` 管理。

---

## 重试与容错机制

### Solve 重试 (Provider 轮换)

```
第 1 次 (attempt=0): 按学科选 provider → 如 Claude Sonnet
        │
        ▼ Quick Verify 失败
        │
第 2 次 (attempt=1): 轮换到下一个 provider → 如 OpenAI GPT-4o
        │
        ▼ Quick Verify 再次失败
        │
第 3 次 (attempt=2): 轮换到下一个 provider → 如 Gemini Flash
        │
        ▼ 仍然失败
        │
标记 verification_status = "caution"，返回最后一次结果
```

### 各阶段容错

| 阶段 | 失败处理 |
|------|---------|
| OCR | 如果 provider 未实现，fallback 到 Gemini Vision |
| Analyze | LLM 失败时用关键词匹配 fallback |
| Solve | JSON 解析失败时尝试提取 `{...}` 子串 |
| Quick Verify | 5 秒超时或异常 → 跳过验证，不阻塞 |
| Deep Evaluate | 异常 → 记录日志，不影响已返回的结果 |
| Embedding | 异常 → 静默忽略 |

---

## 模型选择策略

### 按任务分配模型的设计思路

| 任务类型 | 需求 | 选择策略 |
|---------|------|---------|
| OCR | 多模态、免费额度 | Gemini Flash Lite (固定) |
| 分类 | 速度快、成本低 | 默认 provider 的 fast 档 |
| 解题 | 推理能力强 | 按学科选 provider 的 strong 档 |
| 验算 | 独立第二意见、速度快 | Gemini Flash Lite (固定，不同于解题模型) |
| 深度评估 | 全面分析能力 | Gemini Flash (异步，不影响响应时间) |
| 追问 | 对话能力强 | 默认 provider 的 strong 档 |
| 向量化 | 高质量嵌入 | OpenAI text-embedding-3-small (固定) |

### 为什么验算固定用 Gemini?

- **模型独立性**: 解题用 Claude/OpenAI，验算用 Gemini，避免"用同一个模型检查自己"
- **成本控制**: Gemini Flash Lite 有大量免费额度
- **速度**: 5 秒超时限制下需要快速响应的模型

---

## Prompt 设计规范

### 所有 Prompt 的共同原则

1. **强制 JSON 输出**: 所有 prompt 都要求 `Respond ONLY in JSON`
2. **角色设定**: 面向 K12 学生，语言清晰、有教育价值
3. **LaTeX 规范**:
   - `formula` 字段：纯 LaTeX，如 `\frac{-b \pm \sqrt{b^2-4ac}}{2a}`
   - 文本字段：`$...$` 行内公式，`$$...$$` 独立公式
4. **双语**: 解题 prompt 英文（面向多语种），验证/评估 prompt 中文（面向中国 K12）

### Prompt 文件对应关系

| Prompt 文件 | 使用阶段 | 语言 |
|------------|---------|------|
| `prompts/analysis.py` | Analyze | 英文 |
| `prompts/solve.py` | Solve | 英文 |
| `prompts/verify.py` | Quick Verify | 中文 |
| `prompts/evaluate.py` | (预留) | 英文 |
| `prompts/deep_evaluate.py` | Deep Evaluate | 中文 |
| `prompts/followup.py` | Follow-up | 英文 |

---

## 调用汇总表

一次完整的解题请求，LLM 调用情况：

| # | 阶段 | 模型 | 调用方式 | 同步/异步 | 必须 |
|---|------|------|---------|----------|------|
| 1 | OCR | Gemini 2.5 Flash Lite | 多模态 (base64 图片) | 同步 | 有图片时 |
| 2 | Analyze | fast 档 (如 Haiku) | 纯文字 → JSON | 同步 | 是 |
| 3 | Solve | strong 档 (如 Sonnet 4) | 纯文字 → JSON | 同步 | 是 |
| 4 | Quick Verify | Gemini 2.5 Flash Lite | 纯文字 → JSON, 5s 超时 | 同步 | 是 (可跳过) |
| 5 | Deep Evaluate | Gemini 2.5 Flash | 纯文字 → JSON | 后台异步 | 否 |
| 6 | Embedding | OpenAI embedding-3-small | Embedding API | 同步 (best-effort) | 否 |
| 7 | Follow-up | strong 档 | 多轮对话 | 同步 | 仅追问时 |

**最少调用**: 3 次 (文字输入，无图片: Analyze + Solve + Verify)
**典型调用**: 5 次 (图片输入: OCR + Analyze + Solve + Verify + Deep Evaluate)
**最多调用**: 9 次 (图片 + Solve 重试 3 轮: OCR + Analyze + 3×Solve + 3×Verify + Deep Evaluate)

---

## 关键文件索引

```
backend/app/
├── llm/
│   ├── __init__.py              # 导出 get_llm, select_llm
│   ├── registry.py              # 模型注册中心，Provider/Tier/学科映射
│   ├── embeddings.py            # OpenAI Embedding 封装
│   └── prompts/
│       ├── __init__.py          # 导出所有 prompt 构建函数
│       ├── analysis.py          # Analyze 阶段 prompt
│       ├── solve.py             # Solve 阶段 prompt
│       ├── verify.py            # Quick Verify 阶段 prompt
│       ├── evaluate.py          # Evaluate prompt (预留)
│       ├── deep_evaluate.py     # Deep Evaluate 阶段 prompt
│       └── followup.py          # Follow-up 对话 prompt
├── graph/
│   ├── state.py                 # SolveState / FollowUpState 类型定义
│   ├── solve_graph.py           # 主解题 LangGraph 定义
│   ├── followup_graph.py        # 追问对话 LangGraph 定义
│   ├── edges.py                 # 条件边：重试决策逻辑
│   └── nodes/
│       ├── ocr.py               # OCR 节点
│       ├── analyze.py           # 题目分析节点 (调用 LLM)
│       ├── retrieve.py          # RAG 检索节点 (待实现)
│       ├── solve.py             # 解题节点 (调用 LLM)
│       ├── quick_verify.py      # 快速验算节点 (调用 LLM)
│       ├── enrich.py            # 结果丰富节点 (纯逻辑)
│       └── deep_evaluate.py     # 深度评估 (调用 LLM)
├── services/
│   ├── scan_service.py          # 编排整个流程的 Service 层
│   ├── ocr_service.py           # OCR Provider 策略模式
│   ├── embedding_service.py     # 向量嵌入服务
│   └── conversation_service.py  # 对话历史管理
├── config.py                    # 环境变量配置 (API keys, 模型名称)
└── api/v1/scan.py               # HTTP 路由入口
```

---

## LangGraph State 数据流

`SolveState` (TypedDict) 在各节点间传递，每个节点读取需要的字段、写入新字段：

```
OCR 写入:
  → ocr_text, ocr_confidence

ANALYZE 读取 ocr_text, 写入:
  → detected_subject, problem_type, difficulty, knowledge_points

RETRIEVE 读取 ocr_text, detected_subject, 写入:
  → related_formulas, similar_problems

SOLVE 读取 ocr_text, detected_subject, grade_level, related_formulas, similar_problems, 写入:
  → solution_raw, solution_parsed, llm_provider, llm_model, prompt_tokens, completion_tokens

QUICK VERIFY 读取 ocr_text, solution_parsed, detected_subject, 写入:
  → verify_passed, verify_confidence, independent_answer, verify_error

ENRICH 读取 solution_parsed, related_formulas, difficulty, quality_score, 写入:
  → final_solution, related_formula_ids
```
