# Xagent LangGraph + Deep Agents 迁移设计

> **目标：** 将 Xagent 从手搓状态机迁移到 LangGraph + Deep Agents 体系，实现企业级流程可控性、上下文管理和可观测性。

## 1. 背景与痛点

当前 Xagent 使用 Flask + OpenAI SDK + SQLite 构建，ARIZ 9 步流程通过手搓状态机管理。存在以下核心问题：

- **流程控制脆弱**：线性 index+1，分支/回退困难
- **上下文管理原始**：全量注入历史结果，长对话 token 爆炸
- **兜底逻辑耦合**：防御性代码散落在 SSE 流式输出循环中
- **无可观测性**：LLM 调用耗时、token 用量无法追踪
- **Prompt 硬编码**：200+ 行 prompt 字符串嵌入 Python 代码

## 2. 技术选型

| 组件 | 选择 | 理由 |
|------|------|------|
| 流程编排 | LangGraph | 图结构状态机，支持条件路由、Checkpoint |
| Agent Harness | Deep Agents | 上下文压缩、子 Agent 编排 |
| LLM Wrapper | LangChain ChatOpenAI | MiMo OpenAI 兼容，已验证通过 |
| 数据库 | SQLite（保持） | 单用户开发阶段，零迁移成本 |
| 可观测性 | 自建 structlog tracing | 不用 LangSmith，轻量可控 |
| Prompt 管理 | 独立 Markdown 文件 | 职责分离，版本可控 |
| 前端 | 小改 | 适配 LangGraph stream 格式 |

## 3. 架构设计

### 3.1 整体架构

```
┌─────────────────────────────────────────────────┐
│              Frontend (Next.js)                  │
│  小改：SSE 解析适配 LangGraph stream 格式        │
└──────────────────┬──────────────────────────────┘
                   │ HTTP / SSE
┌──────────────────▼──────────────────────────────┐
│              Flask (路由层保持)                    │
│  /api/chat → Deep Agents Agent                   │
│  /api/conversations → SQLite                     │
│  /api/ariz/* → LangGraph Checkpoint              │
└──────────────────┬──────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────┐
│         Deep Agents Agent Harness                │
│  - create_deep_agent(model, tools, prompt)       │
│  - 上下文压缩中间件                               │
│  - 子 Agent 生成（Step 2 组件分析）               │
└──────────────────┬──────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────┐
│       LangGraph StateGraph (ARIZ 流程)           │
│  StateGraph(ArizState)                           │
│  9 nodes + conditional edges                     │
│  Checkpoint: SqliteSaver                         │
└──────────────────┬──────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────┐
│              SQLite (保持不变)                    │
│  xagent.db: conversations / messages /           │
│             ariz_sessions / components           │
└─────────────────────────────────────────────────┘
```

### 3.2 文件结构

```
backend/
├── app.py                    # Flask 路由（微调接口适配）
├── llm.py                    # [新] LLM 客户端封装
├── ariz_graph.py             # [新] LangGraph StateGraph 定义
├── ariz_state.py             # [新] ArizState TypedDict + Checkpoint
├── ariz_nodes.py             # [新] 每步 Node 函数
├── ariz_tools.py             # [新] ARIZ 工具定义
├── context_manager.py        # [新] Deep Agents 上下文压缩
├── sub_agents.py             # [新] 子 Agent（Step 2 组件分析）
├── observability.py          # [新] 自建 tracing
├── prompts/                  # [新] Prompt 文件目录
│   ├── system.md             # 全局 system prompt
│   ├── step1_problem.md
│   ├── step2_components.md
│   ├── step3_contacts.md
│   ├── step4_function.md
│   ├── step5_structure.md
│   ├── step6_summary.md
│   ├── step7_causal.md
│   ├── step8_keypoint.md
│   └── step9_solution.md
├── ariz_flow.py              # 保留（旧逻辑 fallback）
├── component_db.py           # 保留不变
├── seed_components.py        # 保留不变
├── requirements.txt          # 更新依赖
└── tests/
```

## 4. 核心组件设计

### 4.1 LLM 客户端（llm.py）

```python
from langchain_openai import ChatOpenAI
import os

def create_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=os.getenv("XIAOMI_MODEL", "mimo-v2.5"),
        base_url=os.getenv("XIAOMI_BASE_URL"),
        api_key=os.getenv("XIAOMI_API_KEY"),
        streaming=True,
        timeout=120,
    )
```

### 4.2 LangGraph State（ariz_state.py）

```python
from typing import TypedDict, Optional
from langgraph.graph import END

class ArizState(TypedDict):
    current_step: str
    step_results: dict
    messages: list
    database_context: dict
    context_budget: int
```

### 4.3 LangGraph StateGraph（ariz_graph.py）

```python
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver

graph = StateGraph(ArizState)

# 9 个节点
graph.add_node("problem", step1_problem_node)
graph.add_node("components", step2_components_node)
graph.add_node("contacts", step3_contacts_node)
graph.add_node("function", step4_function_node)
graph.add_node("structure", step5_structure_node)
graph.add_node("summary", step6_summary_node)
graph.add_node("causal", step7_causal_node)
graph.add_node("keypoint", step8_keypoint_node)
graph.add_node("solution", step9_solution_node)

# 线性主流程
graph.set_entry_point("problem")
graph.add_edge("problem", "components")
graph.add_edge("components", "contacts")
graph.add_edge("contacts", "function")
graph.add_edge("function", "structure")
graph.add_edge("structure", "summary")

# Step 6 → 条件路由
graph.add_conditional_edges(
    "summary",
    route_after_summary,
    {"causal": "causal", "keypoint": "keypoint"}
)

graph.add_edge("causal", "keypoint")
graph.add_edge("keypoint", "solution")
graph.add_edge("solution", END)

# Checkpoint
checkpointer = SqliteSaver.from_conn_string("xagent.db")
```

### 4.4 Node 函数（ariz_nodes.py）

每个 Node 对应 ARIZ 一步，职责：
1. 从 State 读取输入
2. 调用 LLM（带当前步骤的 prompt + tools）
3. 解析 LLM 输出（text + tool_calls）
4. 更新 State

```python
async def step1_problem_node(state: ArizState) -> dict:
    """Step 1: 问题识别"""
    prompt = load_prompt("step1_problem")
    llm = create_llm()
    tools = [ariz_step1_tool]

    # 调用 LLM
    response = await llm.ainvoke(
        build_messages(state, prompt),
        tools=tools,
    )

    # 解析工具调用
    result = parse_tool_calls(response)

    # 更新 state
    return {
        "step_results": {**state["step_results"], "problem": result},
        "current_step": "components",
    }
```

### 4.5 条件路由（ariz_graph.py）

```python
def route_after_summary(state: ArizState) -> str:
    """Step 6 后的条件路由：问题少 → 跳过因果链"""
    problems = state["step_results"].get("summary", {}).get("problems", {})
    total = sum(len(v) for v in problems.values() if isinstance(v, list))
    if total <= 3:
        return "keypoint"  # 问题少，直接跳到关键问题
    return "causal"        # 问题多，走因果链分析
```

### 4.6 子 Agent（sub_agents.py）

Step 2 组件分析拆分为两个子 Agent：

```python
from deepagents import create_sub_agent

# 子 Agent 1：数据库组件查询
db_agent = create_sub_agent(
    name="component_lookup",
    model=create_llm(),
    tools=[search_components_tool, get_system_info_tool],
    system_prompt=load_prompt("sub_agent_db"),
)

# 子 Agent 2：超系统分析
super_agent = create_sub_agent(
    name="supersystem_analysis",
    model=create_llm(),
    tools=[],
    system_prompt=load_prompt("sub_agent_supersystem"),
)

# Step 2 Node 并行调度两个子 Agent
async def step2_components_node(state: ArizState) -> dict:
    # 并行执行
    db_result, super_result = await asyncio.gather(
        db_agent.ainvoke({"input": state["database_context"]}),
        super_agent.ainvoke({"input": state["messages"]}),
    )
    # 合并结果
    merged = merge_component_results(db_result, super_result)
    return {"step_results": {**state["step_results"], "components": merged}}
```

### 4.7 上下文管理（context_manager.py）

```python
from deepagents.context import ContextCompressor

# 上下文压缩策略
CONTEXT_RULES = {
    "problem":     {"max_history": 5,   "summarize_before": 0},
    "components":  {"max_history": 10,  "summarize_before": 0},
    "contacts":    {"max_history": 10,  "summarize_before": 0},
    "function":    {"max_history": 15,  "summarize_before": 5},
    "structure":   {"max_history": 15,  "summarize_before": 5},
    "summary":     {"max_history": 20,  "summarize_before": 10},
    "causal":      {"max_history": 20,  "summarize_before": 10},
    "keypoint":    {"max_history": 25,  "summarize_before": 15},
    "solution":    {"max_history": 30,  "summarize_before": 20},
}

compressor = ContextCompressor(
    rules=CONTEXT_RULES,
    summarizer=create_llm(),  # 用 MiMo 做摘要
)
```

### 4.8 可观测性（observability.py）

```python
import structlog
import time
import functools

logger = structlog.get_logger()

def trace(step: str):
    """装饰器：追踪函数执行"""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = await func(*args, **kwargs)
                elapsed = time.time() - start
                logger.info("step_completed",
                    step=step,
                    latency_ms=round(elapsed * 1000),
                    status="success")
                return result
            except Exception as e:
                elapsed = time.time() - start
                logger.error("step_failed",
                    step=step,
                    latency_ms=round(elapsed * 1000),
                    error=str(e))
                raise
        return wrapper
    return decorator
```

### 4.9 Prompt 管理（prompts/）

```
prompts/
├── system.md                 # 全局规则（中文、语气、核心约束）
├── step1_problem.md          # Step 1 专属指令
├── step2_components.md       # Step 2 专属指令（含子 Agent 调度说明）
├── sub_agent_db.md           # 子 Agent: 数据库查询
├── sub_agent_supersystem.md  # 子 Agent: 超系统分析
├── step3_contacts.md
├── step4_function.md
├── step5_structure.md
├── step6_summary.md
├── step7_causal.md
├── step8_keypoint.md
└── step9_solution.md
```

加载方式：

```python
from pathlib import Path

PROMPTS_DIR = Path(__file__).parent / "prompts"

def load_prompt(name: str) -> str:
    return (PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8")
```

## 5. Flask 适配层

### 5.1 聊天接口适配

```python
@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.json
    conv_id = data.get("conversation_id")

    def generate():
        for event in agent.stream(
            {"messages": data["messages"]},
            config={"configurable": {"thread_id": conv_id}},
        ):
            # 转换为 SSE 格式
            yield format_sse(event)

    return Response(generate(), mimetype="text/plain; charset=utf-8",
                    headers={"X-Vercel-AI-Data-Stream": "v1"})
```

### 5.2 ARIZ 状态查询适配

```python
@app.route("/api/ariz/status/<conv_id>", methods=["GET"])
def ariz_status(conv_id):
    # 从 LangGraph Checkpoint 读取状态
    config = {"configurable": {"thread_id": conv_id}}
    state = graph.get_state(config)
    return jsonify(state.values)
```

## 6. 前端改动点

| 文件 | 改动 |
|------|------|
| `app/page.tsx` | SSE 解析逻辑适配 LangGraph stream event 格式 |
| `components/Message.tsx` | 消息渲染适配新格式 |
| 其他组件 | 不动 |

## 7. 依赖变更

```txt
# requirements.txt 新增
langchain-core>=1.4.0
langchain-openai>=1.3.0
langgraph>=0.2.0
deepagents>=0.1.0

# 保持不变
flask
flask-cors
openai              # 保留，备用
python-dotenv
structlog
requests
```

## 8. 迁移策略

### Phase 0: 评估验证（1 周）
- [x] MiMo + LangChain 兼容性验证 ✅
- [ ] Deep Agents 安装与基础测试
- [ ] LangGraph StateGraph PoC（Step 1→2 流转）

### Phase 1: 核心迁移（2-3 周）
- [ ] 创建 ariz_state.py、ariz_graph.py
- [ ] 迁移 9 个 Step Node
- [ ] Prompt 外置为 Markdown 文件
- [ ] Flask 适配层
- [ ] Checkpoint 持久化

### Phase 2: 上下文优化（2 周）
- [ ] Deep Agents 上下文压缩集成
- [ ] 自建 tracing 实现
- [ ] 子 Agent 拆分（Step 2）

### Phase 3: 企业级增强（2-3 周）
- [ ] 评估体系（LangSmith Eval 替代方案）
- [ ] 多租户支持（可选）
- [ ] 部署架构优化

## 9. 风险与对策

| 风险 | 影响 | 对策 |
|------|------|------|
| Deep Agents API 演进 | 中 | 锁定版本，关注 changelog |
| LangGraph 学习曲线 | 中 | PoC 先跑通最小图 |
| 前端接口变动 | 低 | Flask 适配层隔离变化 |
| MiMo streaming 兼容 | 低 | 已验证通过 |

## 10. 验收标准

- [ ] ARIZ 9 步流程在 LangGraph 中完整跑通
- [ ] Checkpoint 支持中断恢复和回退
- [ ] 长对话（50+ 轮）token 消耗降低 50%+
- [ ] LLM 调用延迟和 token 用量可观测
- [ ] 前端交互体验无退化
- [ ] 现有功能全部保持（对话管理、组件知识库）
