# EduScan 技术学习指南 (Technology Study Guide)

## 项目概述

EduScan 是一个 AI 驱动的 K12 学生作业助手，包含三个主要部分：
- **Backend**: Python FastAPI + LangGraph + 多模型 AI (Claude/GPT/Gemini)
- **Frontend**: Next.js 16 + React 19 + Tailwind CSS v4
- **Mobile**: React Native (Expo 50) + TypeScript

---

## 第一部分：后端技术栈与架构

### 1.1 核心框架：FastAPI

**什么是 FastAPI？**
FastAPI 是一个现代、高性能的 Python Web 框架，基于类型提示（Type Hints）自动生成 API 文档。

**关键学习点：**
- **异步编程 (async/await)**: FastAPI 原生支持异步，所有路由和数据库操作都使用 `async def`
- **依赖注入 (Dependency Injection)**: 通过 `Depends()` 注入数据库会话、当前用户等
- **Pydantic 模型**: 请求和响应自动验证和序列化
- **生命周期管理 (Lifespan)**: 应用启动时初始化 Redis、修复数据库序列

**项目中的实际应用：**
```python
# 依赖注入示例
@router.post("/solve")
async def solve(
    file: UploadFile,
    db: AsyncSession = Depends(get_db),        # 数据库会话
    user: User = Depends(get_current_user),     # JWT 认证
):
    scan_service = ScanService(db)
    return await scan_service.scan_and_solve(file, user)
```

### 1.2 数据库：SQLAlchemy 2.0 + PostgreSQL + pgvector

**SQLAlchemy 2.0 异步模式：**
- `AsyncSession` 替代传统同步 Session
- `asyncpg` 驱动实现真正的异步数据库访问
- ORM 映射使用 `Mapped[]` 类型注解

**pgvector 向量搜索：**
- 在 PostgreSQL 中存储 1536 维向量嵌入
- 支持余弦相似度 (cosine similarity) 搜索
- 用于语义缓存和相似题目查找

**关键模型设计（13个模型）：**
- `User` - 用户，关联 Clerk 认证，支持订阅等级
- `ScanRecord` - 扫描记录，包含 OCR 文本和向量嵌入
- `Solution` - AI 解答，含步骤(JSONB)、验证状态、质量评分
- `Formula` - 公式库，支持 GIN 索引的关键词搜索
- `MistakeBook` - 错题本，支持间隔重复(spaced repetition)
- `SemanticCache` - 语义缓存，存储向量和框架
- `DailyUsage` / `GuestUsage` - 使用配额追踪
- `SubscriptionTier` - 订阅等级配置
- `ConversationMessage` - 对话历史

**数据库迁移 (Alembic):**
- 18 个迁移文件，从初始表结构到向量搜索
- 大量种子数据：1200+ 公式 (Cambridge + NCEA)，1000+ 题目

### 1.3 AI 管道：LangGraph 状态机

**什么是 LangGraph？**
LangGraph 是 LangChain 的图编排工具，用于构建有状态的 AI 工作流。

**解题管道流程：**
```
OCR → CHECK_CACHE → [缓存命中] → 直接返回
                  → [缓存未命中] → ANALYZE → RETRIEVE → SOLVE → QUICK_VERIFY → ENRICH → 返回
```

**7 个管道节点：**
1. **OCR 节点** - Gemini Vision 多模态 OCR，识别手写和数学公式
2. **CHECK_CACHE 节点** - 4 层语义缓存检查
3. **ANALYZE 节点** - 检测学科、难度、题型
4. **RETRIEVE 节点** - RAG 检索相关公式和知识库
5. **SOLVE 节点** - LLM 生成分步解答 (Sonnet 或 Haiku+框架)
6. **QUICK_VERIFY 节点** - Gemini 独立验证答案 (5秒超时)
7. **ENRICH 节点** - 最终清理和格式化

**条件路由 (Conditional Edges)：**
- 缓存命中时跳过分析和求解步骤
- Layer 3 命中时使用 Haiku + 框架（成本降低 90%）
- 验证超时时优雅跳过

### 1.4 四层语义缓存策略

这是项目的核心创新之一：

| 层级 | 技术 | 匹配条件 | 成本 |
|------|------|----------|------|
| L1 | Redis 精确匹配 | SHA256 哈希完全一致 | 极低 |
| L2 | pgvector 余弦相似度 > 0.95 | 几乎相同的题目 | 低 |
| L3 | pgvector 余弦 0.80-0.95 | 相似题型，复用框架 | 中（Haiku） |
| L4 | 完整 LLM 求解 | 全新题目 | 高（Sonnet） |

**Layer 3 框架复用机制：**
- Sonnet 求解后，Haiku 提取可复用的"解题框架"
- 框架包含：推理链、关键原则、常见错误
- 下次遇到相似题目，Haiku + 框架即可完成求解
- 成本节约约 90%

### 1.5 多模型 AI 集成

**支持的 AI 提供商：**
- **Claude (Anthropic)**: claude-sonnet-4 (强模型), claude-haiku-4-5 (快速模型)
- **GPT (OpenAI)**: gpt-4o (强模型), gpt-4o-mini (快速模型)
- **Gemini (Google)**: gemini-2.5-flash (强模型), gemini-2.5-flash-lite (快速模型)

**模型选择策略：**
- OCR: Gemini Vision（多模态能力强，免费额度高）
- 求解: Claude Sonnet（推理能力强）或 Haiku+框架（性价比高）
- 验证: Gemini Flash（快速、便宜）
- 框架提取: Claude Haiku（快速、结构化输出好）
- 嵌入: Gemini Embedding（768维，免费）

### 1.6 认证系统：Clerk + JWT

**Clerk 集成流程：**
1. 前端使用 Clerk SDK 完成登录（Google/Email 等）
2. Clerk 签发 JWT Token
3. 后端通过 JWKS URL 验证 JWT 签名
4. 首次登录自动创建本地 User 记录
5. 根据邮箱列表自动分配管理员角色

**依赖函数层次：**
- `get_current_user()` - 必须认证
- `get_optional_user()` - 可选认证
- `get_current_or_guest_user()` - 认证或游客

### 1.7 速率限制与配额

**双层保护：**
1. **Redis 滑动窗口** (per-minute): 防止突发请求
   - 求解: 6 req/min
   - 认证: 10 req/min
   - 全局: 60 req/min
2. **数据库日配额** (per-day): 基于订阅等级或 IP
   - 游客: 50 题/天
   - 注册用户: 按等级

**优雅降级：**
- Redis 不可用时放行（fail-open）
- 返回 429 + Retry-After 头

### 1.8 存储服务

**双后端设计：**
- **Cloudflare R2**: 主要存储（S3 兼容 API）
- **本地文件系统**: 开发环境回退
- UUID 命名防冲突

### 1.9 Prompt 工程

**结构化 JSON 输出：**
- 要求 AI 返回严格 JSON 格式
- 包含：题型、知识点、步骤(带公式和计算)、最终答案、提示

**数学格式规范：**
- `formula` 字段：纯 LaTeX（无 $ 分隔符）
- `description` 字段：内联 `$...$`，独立 `$$...$$`
- 使用 `\frac{}{}`、`\sqrt{}`、`x^{2}` 等标准 LaTeX

**验证提示 (Quick Verify)：**
- 独立重新计算答案
- 返回：独立答案、是否正确、错误描述、置信度

**深度评估提示 (Deep Evaluate)：**
- 6 维质量评分：正确性、完整性、清晰度、教学法、格式、总体
- 附带改进建议

### 1.10 后端关键设计模式

1. **依赖注入 (FastAPI Depends)**: 路由级别注入 DB/用户
2. **服务定位器模式**: ScanService(db) 在路由中创建
3. **LangGraph 状态机**: 有向图管理 AI 工作流
4. **Provider 模式 (OCR)**: 抽象基类 + 多个实现 + 回退
5. **异步优先**: asyncpg + httpx + asyncio.create_task()
6. **后台任务**: 深度评估、缓存写入、框架生成异步执行
7. **ORM Mode (Pydantic)**: from_attributes=True 自动转换

---

## 第二部分：前端技术栈与架构

### 2.1 核心框架：Next.js 16 + React 19

**Next.js App Router：**
- 基于文件系统的路由 (`src/app/` 目录)
- 支持动态路由 (`[scanId]/page.tsx`)
- 中间件路由保护 (`middleware.ts`)
- 布局嵌套 (`layout.tsx` 层层嵌套)

**React 19 新特性：**
- JSX Transform（无需手动 import React）
- 改进的并发渲染

**页面结构：**
| 路由 | 功能 | 认证 |
|------|------|------|
| `/` | 首页上传与解题 / 营销落地页 | 登录后显示主功能 |
| `/history` | 扫描历史（分页+筛选） | 需要 |
| `/history/[scanId]` | 单条扫描详情 | 需要 |
| `/mistakes` | 错题本（掌握度切换） | 需要 |
| `/formulas` | 公式库搜索 | 需要 |
| `/admin/*` | 管理后台 | 管理员 |
| `/sign-in`, `/sign-up` | Clerk 认证页 | 不需要 |

### 2.2 Tailwind CSS v4

**新版本特点：**
- PostCSS 集成 (`@tailwindcss/postcss`)
- CSS 变量配置（替代传统 tailwind.config.js）
- 更快的构建速度

**设计系统颜色：**
- Primary: Indigo (#6366F1) — 按钮、活跃导航
- Success: Emerald (#10B981) — 已验证、已掌握
- Sidebar: Gray-900 — 深色侧边栏
- 学科颜色：数学(Indigo)、物理(Blue)、化学(Emerald)、生物(Orange)

### 2.3 数学渲染

**KaTeX (渲染引擎)：**
- 将 LaTeX 渲染为 HTML（比 MathJax 更快）
- 支持内联 `$...$` 和独立 `$$...$$`
- 错误回退：渲染失败时显示原始 LaTeX

**MathLive (输入编辑器)：**
- Web Component `<math-field>`
- 可视化数学表达式输入
- LaTeX 输入/输出

**自定义渲染工具：**
- `renderMathText()` - 解析文本中的数学公式
- `renderRichText()` - 支持 **粗体**、列表、换行
- HTML 转义防止 XSS

### 2.4 组件架构

**核心组件：**
- **AppShell** - 条件布局（登录用户显示侧边栏，游客全宽）
- **Sidebar** - 深色侧边栏 + 移动端汉堡菜单 + 响应式
- **UploadZone** - 拖放上传 + 移动端拍照/相册 + 剪贴板粘贴
- **SolutionDisplay** - 分步解答 + KaTeX 公式 + 验证状态 + 相关公式
- **ConversationThread** - 聊天气泡式追问界面
- **MathInput** - MathLive 数学编辑器封装
- **Pagination** - 可复用分页（滑动窗口）

### 2.5 API 客户端

**Axios 配置：**
- 基础 URL 从环境变量读取
- 60 秒超时
- 请求拦截器自动添加 Bearer Token
- SSE (Server-Sent Events) 支持实时解题进度

**API 函数分类：**
- 图片/文本求解：`solveImage()`, `solveText()`, `solveTextStream()`
- 历史：`getHistory()`, `deleteHistoryItem()`
- 错题：`getMistakes()`, `addToMistakes()`, `updateMistake()`
- 公式：`getFormulas()`, `saveFormula()`
- 对话：`getConversation()`, `sendFollowUp()`
- 管理：独立的 `admin-api.ts`

### 2.6 前端关键设计模式

1. **客户端组件 ("use client")**: 所有交互页面标记为客户端组件
2. **本地状态管理**: 使用 React Hooks，无 Redux/Zustand
3. **SSE 流式传输**: 实时显示解题进度
4. **Clerk 中间件保护**: 路由级别认证 + 角色控制
5. **动态导入 (next/dynamic)**: MathLive 禁用 SSR（Web Component）
6. **响应式设计**: 移动优先，Tailwind 断点适配

---

## 第三部分：移动端技术栈与架构

### 3.1 核心框架：Expo 50 + React Native

**Expo 优势：**
- 统一的开发环境（iOS/Android/Web）
- 丰富的原生模块（Camera、ImagePicker、SecureStore）
- OTA 更新支持
- 支持 `npm run web` 浏览器开发（无需 Xcode）

**文件路由 (Expo Router v3)：**
```
/auth/login      → 登录页
/auth/register   → 注册页
/main/home       → 首页仪表盘
/main/scan       → 扫描标签（触发模态框）
/main/saved      → 收藏/错题
/main/profile    → 个人资料
/scan/           → 相机拍照
/scan/result     → 解答展示
```

### 3.2 状态管理：Zustand + React Query

**Zustand Stores（3 个状态仓库）：**

**authStore (认证状态)：**
- 用户信息、Token、认证状态
- 持久化：native 用 expo-secure-store (加密)，web 用 localStorage
- 操作：login, register, logout, loadUser, setTokens

**scanStore (扫描状态)：**
- 扫描/处理状态、当前结果、错误
- 临时状态，不持久化
- 操作：solve, clearScan, setError

**settingsStore (设置状态)：**
- AI 提供商选择、年级、暗色模式、通知
- 持久化：native 用 react-native-mmkv (快速 KV)，web 用 localStorage
- 操作：setDefaultAIProvider, setGradeLevel, setDarkMode

**React Query (服务端状态)：**
- 5 分钟缓存 (staleTime)
- 失败重试 2 次
- 用于 API 数据获取和缓存

### 3.3 主题系统

**设计令牌 (Design Tokens)：**
- **Colors**: 主色 Indigo、辅色 Emerald、语义色、学科色、深浅模式
- **Typography**: 系统字体，8 级字号 (12-36px)，预设样式 (h1-caption)
- **Spacing**: 4px 网格，12 级间距 (0-96px)
- **Shadows**: 4 级阴影（iOS shadow + Android elevation）
- **Border Radius**: 7 级圆角 (0-9999px)

### 3.4 API 层与拦截器

**请求拦截器：**
- 自动添加 Bearer Token
- 动态加载 authStore（避免循环依赖）

**响应拦截器：**
- 捕获 401 错误
- 自动刷新 Token
- 刷新成功后重试原请求
- 刷新失败则登出
- 防止无限重试 (`_retry` 标记)

### 3.5 移动端关键设计模式

1. **文件路由 (Expo Router)**: 目录即路由
2. **Platform-specific 代码**: `Platform.OS === 'web'` 条件适配
3. **安全存储分层**: 敏感数据用 SecureStore，设置用 MMKV
4. **循环依赖规避**: API 拦截器动态 require authStore
5. **Tab + Modal 混合导航**: Tab 导航器 + 全屏模态框
6. **渐变效果 (LinearGradient)**: 首页头部和扫描按钮

---

## 第四部分：全栈关键学习主题

### 4.1 TypeScript 全栈类型系统

**前后端类型一致性：**
- 后端 Pydantic Schema → 前端 TypeScript Interface
- 核心类型：SolutionStep, ScanResponse, Formula, PaginatedResponse
- API 响应类型化，IDE 自动补全

### 4.2 认证架构 (Clerk)

**完整认证流程：**
```
用户 → Clerk SDK (前端/移动端) → Google/Email 登录
     → Clerk 签发 JWT
     → 后端 JWKS 验证 JWT
     → 自动创建/关联本地用户
     → 返回用户数据 + 配额信息
```

### 4.3 实时通信：SSE (Server-Sent Events)

**前端实现：**
- 使用 `fetch` + `ReadableStream` 读取 SSE
- 解析 `event:` 和 `data:` 行
- 事件类型：stage（阶段进度）、ocr_result、complete、error

**后端实现：**
- FastAPI `StreamingResponse` + `astream()`
- LangGraph `stream_mode="updates"` 逐节点推送

### 4.4 RAG (检索增强生成)

**项目中的 RAG 实现：**
1. 公式库检索 — 基于关键词和学科匹配相关公式
2. 知识库检索 — 向量搜索相关知识点
3. 语义缓存 — pgvector 相似度搜索复用历史解答

### 4.5 数据库设计要点

**JSONB 列的使用场景：**
- `Solution.steps` - 灵活的步骤数组
- `Solution.deep_evaluation` - 6 维评分
- `MistakeBook.tags` - 标签数组
- `SubscriptionTier.features` - 功能配置

**索引策略：**
- GIN 索引用于 JSONB 和 ARRAY 列（公式关键词搜索）
- B-Tree 索引用于外键和时间戳
- pgvector HNSW 索引用于向量搜索

**间隔重复 (Spaced Repetition)：**
- MistakeBook 包含 `mastery_level`, `review_count`, `next_review_at`
- 支持错题的渐进复习

### 4.6 多层缓存架构

```
请求 → Redis L1 (精确匹配, ~1ms)
     → pgvector L2 (高相似度 >0.95, ~10ms)
     → pgvector L3 (中相似度 0.80-0.95, 用框架+Haiku, ~2s)
     → LLM L4 (完整求解, Claude Sonnet, ~10s)
```

### 4.7 错误处理与降级策略

**后端降级链：**
- OCR：Gemini → 配置的 Provider → 回退到 Gemini
- 验证：Gemini 验证 → 超时跳过 → 返回 "未验证"
- 缓存：Redis → pgvector → 跳过直接求解
- 速率限制：Redis → fail-open（放行）

### 4.8 Docker 部署架构

```yaml
services:
  backend:    # FastAPI 应用
  postgres:   # PostgreSQL + pgvector 扩展
  redis:      # 缓存和速率限制
  frontend:   # Next.js 应用
```

---

## 第五部分：技术栈总览

### 后端技术

| 技术 | 用途 | 版本 |
|------|------|------|
| Python | 编程语言 | 3.11+ |
| FastAPI | Web 框架 | >= 0.109 |
| SQLAlchemy | ORM | >= 2.0.25 |
| PostgreSQL + pgvector | 数据库 + 向量搜索 | 16+ |
| Redis | 缓存 + 速率限制 | >= 5.0 |
| LangGraph | AI 工作流编排 | >= 1.0 |
| LangChain | LLM 抽象层 | >= 0.3 |
| Alembic | 数据库迁移 | >= 1.13 |
| Clerk | 认证服务 | - |
| Cloudflare R2 | 对象存储 | - |
| Pydantic | 数据验证 | >= 2.5 |
| pytest | 测试框架 | 7.4 |

### 前端技术

| 技术 | 用途 | 版本 |
|------|------|------|
| TypeScript | 编程语言 | 5 |
| Next.js | React 框架 | 16.1 |
| React | UI 库 | 19.2 |
| Tailwind CSS | 样式框架 | 4 |
| Clerk | 认证 SDK | 6.39 |
| Axios | HTTP 客户端 | 1.13 |
| KaTeX | LaTeX 渲染 | 0.16 |
| MathLive | 数学输入 | 0.108 |

### 移动端技术

| 技术 | 用途 | 版本 |
|------|------|------|
| TypeScript | 编程语言 | 5.3+ |
| React Native | 移动框架 | 0.73 |
| Expo | 开发平台 | 50 |
| Expo Router | 文件路由 | 3.4 |
| Zustand | 状态管理 | 4.4 |
| React Query | 服务端状态 | 5.17 |
| Axios | HTTP 客户端 | 1.6 |
| expo-camera | 相机 | 14.1 |
| expo-image-picker | 图片选择 | 14.7 |
| expo-secure-store | 安全存储 | 12.8 |
| react-native-mmkv | 快速 KV | 2.11 |
| react-native-math-view | 数学渲染 | 3.9 |

---

## 第六部分：API 端点参考

| 方法 | 端点 | 功能 | 认证 |
|------|------|------|------|
| GET | /api/v1/auth/me | 获取用户信息+配额 | 需要 |
| POST | /api/v1/scan/solve | 上传图片求解 | 需要 |
| POST | /api/v1/scan/solve-guest | 游客模式求解 | 不需要 |
| POST | /api/v1/scan/solve-guest-stream | SSE 流式求解 | 不需要 |
| GET | /api/v1/scan/{id} | 获取扫描结果 | 需要 |
| POST | /api/v1/scan/{id}/followup | 追问 | 需要 |
| GET | /api/v1/scan/{id}/conversation | 对话历史 | 需要 |
| POST | /api/v1/scan/extract-text | 仅 OCR | 需要 |
| GET | /api/v1/history | 扫描历史（分页） | 需要 |
| DELETE | /api/v1/history/{id} | 删除历史 | 需要 |
| GET | /api/v1/mistakes | 错题列表 | 需要 |
| POST | /api/v1/mistakes | 添加错题 | 需要 |
| PATCH | /api/v1/mistakes/{id} | 更新错题 | 需要 |
| DELETE | /api/v1/mistakes/{id} | 删除错题 | 需要 |
| GET | /api/v1/formulas | 搜索公式 | 需要 |
| POST | /api/v1/formulas | 保存公式 | 需要 |
| GET | /api/v1/formulas/{id} | 公式详情 | 需要 |

---

## 第七部分：数据流全景图

```
1. 用户上传图片/文本
   ↓
2. 前端/移动端 → POST /scan/solve
   ↓
3. 配额检查 (DailyUsage/GuestUsage)
   ↓
4. 图片上传到 R2/本地存储
   ↓
5. LangGraph 管道执行：
   OCR → 缓存检查 → 分析 → 检索公式 → AI 求解 → 验证 → 丰富
   ↓
6. 持久化：ScanRecord + Solution + ConversationMessage
   ↓
7. 异步后台任务：
   - 深度评估 (6维质量评分)
   - 缓存写入 (Redis L1 + pgvector L2/L3)
   - 框架生成 (Haiku 提取可复用推理链)
   - 向量嵌入 (相似度搜索索引)
   ↓
8. 返回 ScanResponse (scan_id, ocr_text, solution, formulas)
   ↓
9. 前端渲染：KaTeX 公式 + 分步解答 + 相关公式
   ↓
10. 用户追问 → POST /scan/{id}/followup → 对话延续
```

---

## 第八部分：推荐学习路径

### 初级学习路径
1. Python 异步编程 (async/await, asyncio)
2. FastAPI 基础 (路由、依赖注入、Pydantic)
3. SQLAlchemy 2.0 ORM 基础
4. Next.js App Router 基础
5. React Hooks (useState, useEffect, useCallback)
6. TypeScript 类型系统
7. Tailwind CSS 实用类

### 中级学习路径
1. PostgreSQL 高级 (JSONB, GIN 索引, 数组类型)
2. JWT 认证与 Clerk 集成
3. Axios 拦截器与 Token 刷新
4. SSE (Server-Sent Events) 实时通信
5. React Native + Expo Router
6. Zustand 状态管理
7. KaTeX/MathLive 数学渲染

### 高级学习路径
1. LangGraph 有状态 AI 工作流
2. pgvector 向量搜索与语义缓存
3. 多模型 AI 编排 (Claude/GPT/Gemini)
4. Prompt 工程 (结构化 JSON 输出, 验证, 评估)
5. RAG (检索增强生成) 实现
6. Redis 滑动窗口速率限制
7. Alembic 数据库迁移策略
8. Docker 微服务部署
