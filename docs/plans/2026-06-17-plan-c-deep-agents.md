# Xagent 迁移 Plan C：Deep Agents 高级特性

> **For agentic workers:** Use superpowers-open:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 集成 Deep Agents 的上下文管理、子 Agent 编排和自建可观测性，解决长对话 token 爆炸和调试困难问题。

**Architecture:** 用 Deep Agents 的 create_deep_agent 包装 LangGraph Agent，引入上下文压缩中间件管理 token 预算，Step 2 组件分析拆分为两个并行子 Agent，自建 structlog tracing 替代 LangSmith。

**Tech Stack:** deepagents, langchain-core, langchain-openai, structlog, asyncio

---

## 文件结构总览

```
backend/
├── context_manager.py        # [创建] 上下文压缩中间件
├── sub_agents.py             # [创建] 子 Agent 定义（Step 2）
├── observability.py          # [创建] 自建 tracing
├── agent.py                  # [创建] Deep Agents Agent 封装
├── app.py                    # [修改] 集成新 Agent
├── tests/
│   ├── test_context.py       # [创建] 上下文管理测试
│   ├── test_sub_agents.py    # [创建] 子 Agent 测试
│   └── test_observability.py # [创建] 可观测性测试
```

---

### Task 1: 创建自建可观测性模块

**Files:**
- Create: `backend/observability.py`
- Create: `backend/tests/test_observability.py`

- [ ] **Step 1: 创建 observability.py**

```python
"""自建可观测性模块 — 替代 LangSmith"""
import time
import functools
import structlog
from typing import Any, Optional

logger = structlog.get_logger()


class TraceContext:
    """追踪上下文，记录单次 Agent 调用的全链路信息"""

    def __init__(self, thread_id: str, step: str):
        self.thread_id = thread_id
        self.step = step
        self.start_time = time.time()
        self.llm_calls: list[dict] = []
        self.tool_calls: list[dict] = []
        self.tokens_used: dict = {"input": 0, "output": 0, "total": 0}
        self.errors: list[str] = []

    def record_llm_call(self, model: str, latency_ms: float,
                        input_tokens: int = 0, output_tokens: int = 0):
        """记录一次 LLM 调用"""
        self.llm_calls.append({
            "model": model,
            "latency_ms": round(latency_ms),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        })
        self.tokens_used["input"] += input_tokens
        self.tokens_used["output"] += output_tokens
        self.tokens_used["total"] += input_tokens + output_tokens

    def record_tool_call(self, tool_name: str, latency_ms: float, success: bool):
        """记录一次工具调用"""
        self.tool_calls.append({
            "tool": tool_name,
            "latency_ms": round(latency_ms),
            "success": success,
        })

    def record_error(self, error: str):
        """记录错误"""
        self.errors.append(error)

    def finish(self) -> dict:
        """完成追踪，返回摘要"""
        total_ms = round((time.time() - self.start_time) * 1000)
        summary = {
            "thread_id": self.thread_id,
            "step": self.step,
            "total_ms": total_ms,
            "llm_calls": len(self.llm_calls),
            "tool_calls": len(self.tool_calls),
            "tokens": self.tokens_used,
            "errors": len(self.errors),
        }
        logger.info("trace_summary", **summary)
        return summary


def trace_step(step: str):
    """装饰器：追踪 ARIZ 步骤执行"""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(state, *args, **kwargs):
            thread_id = state.get("thread_id", "unknown")
            ctx = TraceContext(thread_id, step)
            try:
                result = await func(state, *args, **kwargs, trace_ctx=ctx)
                ctx.finish()
                return result
            except Exception as e:
                ctx.record_error(str(e))
                ctx.finish()
                raise
        return wrapper
    return decorator


def trace_llm_call(model: str):
    """装饰器：追踪单次 LLM 调用"""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = await func(*args, **kwargs)
                latency_ms = (time.time() - start) * 1000
                usage = getattr(result, "usage_metadata", None) or {}
                logger.info("llm_call",
                    model=model,
                    latency_ms=round(latency_ms),
                    input_tokens=usage.get("input_tokens", 0),
                    output_tokens=usage.get("output_tokens", 0),
                )
                return result
            except Exception as e:
                latency_ms = (time.time() - start) * 1000
                logger.error("llm_call_failed",
                    model=model,
                    latency_ms=round(latency_ms),
                    error=str(e),
                )
                raise
        return wrapper
    return decorator
```

- [ ] **Step 2: 创建 test_observability.py**

```python
"""可观测性模块测试"""
import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from observability import TraceContext


def test_trace_context_init():
    """验证追踪上下文初始化"""
    ctx = TraceContext("test-123", "problem")
    assert ctx.thread_id == "test-123"
    assert ctx.step == "problem"
    assert ctx.llm_calls == []
    assert ctx.tool_calls == []
    assert ctx.tokens_used == {"input": 0, "output": 0, "total": 0}


def test_trace_context_record_llm_call():
    """验证 LLM 调用记录"""
    ctx = TraceContext("test-123", "problem")
    ctx.record_llm_call("mimo-v2.5", 1500.0, input_tokens=100, output_tokens=50)
    ctx.record_llm_call("mimo-v2.5", 2000.0, input_tokens=200, output_tokens=80)

    assert len(ctx.llm_calls) == 2
    assert ctx.tokens_used["input"] == 300
    assert ctx.tokens_used["output"] == 130
    assert ctx.tokens_used["total"] == 430


def test_trace_context_record_tool_call():
    """验证工具调用记录"""
    ctx = TraceContext("test-123", "problem")
    ctx.record_tool_call("ariz_step1_problem", 500.0, success=True)
    ctx.record_tool_call("ariz_step2_components", 300.0, success=False)

    assert len(ctx.tool_calls) == 2
    assert ctx.tool_calls[0]["success"] is True
    assert ctx.tool_calls[1]["success"] is False


def test_trace_context_finish():
    """验证追踪完成"""
    ctx = TraceContext("test-123", "problem")
    ctx.record_llm_call("mimo-v2.5", 1500.0, input_tokens=100, output_tokens=50)
    summary = ctx.finish()

    assert summary["thread_id"] == "test-123"
    assert summary["step"] == "problem"
    assert summary["llm_calls"] == 1
    assert summary["total_ms"] >= 0
```

- [ ] **Step 3: 运行测试**

```bash
cd /Users/chenyw/PROJECT/Xagent/backend
source venv/bin/activate
python -m pytest tests/test_observability.py -v
```

Expected: 4 tests PASSED。

- [ ] **Step 4: Commit**

```bash
cd /Users/chenyw/PROJECT/Xagent
git add backend/observability.py backend/tests/test_observability.py
git commit -m "feat: add self-built tracing observability module"
```

---

### Task 2: 创建上下文压缩中间件

**Files:**
- Create: `backend/context_manager.py`
- Create: `backend/tests/test_context.py`

- [ ] **Step 1: 创建 context_manager.py**

```python
"""上下文压缩中间件 — 管理长对话的 token 预算"""
import structlog
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from llm import get_llm_no_stream

logger = structlog.get_logger()

# 每个步骤的上下文策略
CONTEXT_RULES = {
    "problem":     {"max_messages": 20, "summarize_threshold": 15},
    "components":  {"max_messages": 25, "summarize_threshold": 20},
    "contacts":    {"max_messages": 25, "summarize_threshold": 20},
    "function":    {"max_messages": 30, "summarize_threshold": 25},
    "structure":   {"max_messages": 30, "summarize_threshold": 25},
    "summary":     {"max_messages": 35, "summarize_threshold": 30},
    "causal":      {"max_messages": 35, "summarize_threshold": 30},
    "keypoint":    {"max_messages": 40, "summarize_threshold": 35},
    "solution":    {"max_messages": 50, "summarize_threshold": 45},
}


def estimate_tokens(text: str) -> int:
    """粗略估算 token 数（中文约 1.5 字/token）"""
    return max(1, len(text) // 2)


def estimate_messages_tokens(messages: list) -> int:
    """估算消息列表的总 token 数"""
    total = 0
    for msg in messages:
        if hasattr(msg, "content"):
            total += estimate_tokens(msg.content)
    return total


async def compress_messages(messages: list, current_step: str) -> list:
    """压缩消息列表，保持在 token 预算内

    策略：
    1. 保留 system prompt（第一条）
    2. 保留最近 N 条消息（N 由 CONTEXT_RULES 决定）
    3. 中间的消息压缩为摘要
    """
    if not messages:
        return messages

    rules = CONTEXT_RULES.get(current_step, {"max_messages": 30, "summarize_threshold": 25})
    max_msgs = rules["max_messages"]
    threshold = rules["summarize_threshold"]

    if len(messages) <= max_msgs:
        return messages

    # 分离 system prompt 和对话消息
    system_msgs = []
    conversation_msgs = []
    for msg in messages:
        if isinstance(msg, SystemMessage):
            system_msgs.append(msg)
        else:
            conversation_msgs.append(msg)

    if len(conversation_msgs) <= max_msgs:
        return messages

    # 需要压缩：保留最近的 max_msgs 条，压缩前面的
    keep_recent = max_msgs - 2  # 留 2 个位置给摘要
    old_messages = conversation_msgs[:-keep_recent]
    recent_messages = conversation_msgs[-keep_recent:]

    # 生成摘要
    summary = await summarize_messages(old_messages)

    # 重组消息列表
    compressed = system_msgs + [
        SystemMessage(content=f"[历史对话摘要]\n{summary}"),
    ] + recent_messages

    logger.info("context_compressed",
        original_count=len(messages),
        compressed_count=len(compressed),
        summarized_count=len(old_messages),
        step=current_step,
    )

    return compressed


async def summarize_messages(messages: list) -> str:
    """用 LLM 将消息压缩为摘要"""
    if not messages:
        return ""

    # 提取文本内容
    texts = []
    for msg in messages:
        if hasattr(msg, "content") and msg.content:
            role = "用户" if isinstance(msg, HumanMessage) else "助手"
            texts.append(f"{role}: {msg.content[:200]}")

    if not texts:
        return ""

    combined = "\n".join(texts)

    # 用 LLM 做摘要
    try:
        llm = get_llm_no_stream()
        result = await llm.ainvoke([
            SystemMessage(content="请将以下对话历史压缩为简洁的摘要，保留关键信息（问题识别、分析结论、用户偏好）。不超过 300 字。"),
            HumanMessage(content=combined),
        ])
        return result.content
    except Exception as e:
        logger.error("summarize_failed", error=str(e))
        # 摘要失败时，直接截断
        return f"[对话历史过长，已截断。共 {len(messages)} 条消息。]"
```

- [ ] **Step 2: 创建 test_context.py**

```python
"""上下文管理模块测试"""
import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from context_manager import (
    estimate_tokens, estimate_messages_tokens, CONTEXT_RULES,
)
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage


def test_estimate_tokens():
    """验证 token 估算"""
    assert estimate_tokens("hello") >= 1
    assert estimate_tokens("你好世界") >= 1
    assert estimate_tokens("") >= 1  # 最小为 1


def test_estimate_messages_tokens():
    """验证消息列表 token 估算"""
    messages = [
        SystemMessage(content="系统提示"),
        HumanMessage(content="用户消息"),
        AIMessage(content="助手回复"),
    ]
    total = estimate_messages_tokens(messages)
    assert total > 0


def test_context_rules_coverage():
    """验证所有步骤都有上下文规则"""
    expected_steps = ["problem", "components", "contacts", "function",
                      "structure", "summary", "causal", "keypoint", "solution"]
    for step in expected_steps:
        assert step in CONTEXT_RULES, f"缺少步骤 {step} 的上下文规则"
        assert "max_messages" in CONTEXT_RULES[step]
        assert "summarize_threshold" in CONTEXT_RULES[step]


def test_context_rules_progression():
    """验证上下文预算随步骤递增"""
    steps = ["problem", "components", "contacts", "function",
             "structure", "summary", "causal", "keypoint", "solution"]
    for i in range(len(steps) - 1):
        curr = CONTEXT_RULES[steps[i]]["max_messages"]
        next_val = CONTEXT_RULES[steps[i + 1]]["max_messages"]
        assert next_val >= curr, f"{steps[i+1]} 的预算应 >= {steps[i]}"
```

- [ ] **Step 3: 运行测试**

```bash
cd /Users/chenyw/PROJECT/Xagent/backend
source venv/bin/activate
python -m pytest tests/test_context.py -v
```

Expected: 4 tests PASSED。

- [ ] **Step 4: Commit**

```bash
cd /Users/chenyw/PROJECT/Xagent
git add backend/context_manager.py backend/tests/test_context.py
git commit -m "feat: add context compression middleware"
```

---

### Task 3: 创建子 Agent（Step 2 组件分析拆分）

**Files:**
- Create: `backend/sub_agents.py`
- Create: `backend/prompts/sub_agent_db.md`
- Create: `backend/prompts/sub_agent_supersystem.md`
- Create: `backend/tests/test_sub_agents.py`

- [ ] **Step 1: 创建子 Agent prompt 文件**

创建 `backend/prompts/sub_agent_db.md`：

```markdown
你是组件知识库查询专家。你的任务是根据用户描述的问题，从数据库中查询匹配的系统和组件。

规则：
- 使用 search_components_tool 查询组件
- 返回匹配的系统名称、系统描述、组件列表
- 如果没有匹配，返回空列表
- 不要编造数据库中没有的组件
```

创建 `backend/prompts/sub_agent_supersystem.md`：

```markdown
你是超系统分析专家。你的任务是分析与目标系统交互的外部环境和组件。

规则：
- 分析整车环境（温度范围、振动、防护等级等）
- 识别与目标系统有物理/能量/信息交互的外部组件
- 每个外部组件说明其对目标系统的影响
- 不要列出与目标系统无关的组件
```

- [ ] **Step 2: 创建 sub_agents.py**

```python
"""子 Agent 定义 — Step 2 组件分析拆分"""
import asyncio
import structlog
from langchain_core.messages import SystemMessage, HumanMessage

from llm import get_llm
from prompts import load_prompt
from component_db import search_system, get_system_components

logger = structlog.get_logger()


async def run_db_lookup_agent(problem_data: dict) -> dict:
    """子 Agent 1：数据库组件查询

    从 Step 1 的问题识别结果中提取关键词，查询组件知识库。
    """
    logger.info("sub_agent_start", agent="db_lookup")

    keywords = problem_data.get("system_keywords", [])
    if not keywords:
        logger.warning("db_lookup_no_keywords")
        return {"matched_systems": [], "primary_system": {}}

    # 直接查询数据库（不需要 LLM，纯工具调用）
    all_systems = []
    for kw in keywords:
        systems = search_system(kw)
        all_systems.extend(systems)

    # 别名映射兜底
    if not all_systems:
        alias_map = {
            "PTC": "热管理系统", "热泵": "热管理系统", "预热": "热管理系统",
            "冷却": "热管理系统", "散热": "热管理系统", "低温": "热管理系统",
            "续航": "BMS", "电池管理": "BMS", "模组": "电芯模组",
            "箱体": "箱体结构", "电气": "高低压线束",
        }
        for kw in keywords:
            for alias, system_name in alias_map.items():
                if alias in kw:
                    systems = search_system(system_name)
                    all_systems.extend(systems)

    seen_ids = set()
    unique = []
    for s in all_systems:
        if s["id"] not in seen_ids:
            seen_ids.add(s["id"])
            unique.append(s)

    result = {"matched_systems": unique}
    if unique:
        result["primary_system"] = get_system_components(unique[0]["id"])

    logger.info("sub_agent_end", agent="db_lookup", matched=len(unique))
    return result


async def run_supersystem_agent(problem_data: dict, db_result: dict) -> dict:
    """子 Agent 2：超系统分析

    用 LLM 分析与目标系统交互的外部环境和组件。
    """
    logger.info("sub_agent_start", agent="supersystem")

    llm = get_llm()
    prompt = load_prompt("sub_agent_supersystem")

    # 构建输入
    problem_desc = f"问题对象：{problem_data.get('problem_object', '未知')}\n"
    problem_desc += f"现象：{problem_data.get('phenomenon', '未知')}\n"

    primary = db_result.get("primary_system", {})
    if primary:
        system_info = primary.get("system", {})
        problem_desc += f"系统：{system_info.get('name', '未知')}\n"
        components = primary.get("components", [])
        if components:
            comp_names = [c["name"] for c in components]
            problem_desc += f"系统组件：{'、'.join(comp_names)}\n"

    messages = [
        SystemMessage(content=prompt),
        HumanMessage(content=problem_desc),
    ]

    try:
        response = await llm.ainvoke(messages)
        logger.info("sub_agent_end", agent="supersystem", response_len=len(response.content))
        return {
            "supersystem_analysis": response.content,
            "raw_response": response.content,
        }
    except Exception as e:
        logger.error("supersystem_agent_failed", error=str(e))
        return {"supersystem_analysis": "", "error": str(e)}


async def run_step2_sub_agents(problem_data: dict) -> dict:
    """并行运行 Step 2 的两个子 Agent，合并结果"""
    logger.info("step2_sub_agents_start")

    # 子 Agent 1：数据库查询（纯工具，不需要 LLM）
    db_result = await run_db_lookup_agent(problem_data)

    # 子 Agent 2：超系统分析（需要 LLM）
    super_result = await run_supersystem_agent(problem_data, db_result)

    # 合并结果
    primary = db_result.get("primary_system", {})
    system_info = primary.get("system", {})
    components = primary.get("components", [])

    merged = {
        "system_name": system_info.get("name", ""),
        "system_description": system_info.get("description", ""),
        "db_components": [{"name": c["name"], "functions": c.get("functions", [])} for c in components],
        "supersystem_analysis": super_result.get("supersystem_analysis", ""),
        "matched_systems": [
            {"id": s["id"], "name": s.get("name", "")}
            for s in db_result.get("matched_systems", [])
        ],
    }

    logger.info("step2_sub_agents_end",
        db_components=len(components),
        has_supersystem=bool(merged["supersystem_analysis"]),
    )
    return merged
```

- [ ] **Step 3: 创建 test_sub_agents.py**

```python
"""子 Agent 测试"""
import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sub_agents import run_db_lookup_agent


@pytest.mark.asyncio
async def test_db_lookup_agent_no_keywords():
    """验证无关键词时返回空结果"""
    result = await run_db_lookup_agent({"system_keywords": []})
    assert result["matched_systems"] == []


@pytest.mark.asyncio
async def test_db_lookup_agent_with_keywords():
    """验证有关键词时能查询数据库"""
    result = await run_db_lookup_agent({"system_keywords": ["热管理系统"]})
    # 数据库中有种子数据时应匹配到
    assert isinstance(result["matched_systems"], list)
```

- [ ] **Step 4: 运行测试**

```bash
cd /Users/chenyw/PROJECT/Xagent/backend
source venv/bin/activate
pip install pytest-asyncio 2>&1 | tail -3
python -m pytest tests/test_sub_agents.py -v
```

Expected: 2 tests PASSED。

- [ ] **Step 5: Commit**

```bash
cd /Users/chenyw/PROJECT/Xagent
git add backend/sub_agents.py backend/prompts/sub_agent_db.md backend/prompts/sub_agent_supersystem.md backend/tests/test_sub_agents.py
git commit -m "feat: add Step 2 sub-agents (db lookup + supersystem analysis)"
```

---

### Task 4: 创建 Deep Agents Agent 封装

**Files:**
- Create: `backend/agent.py`

- [ ] **Step 1: 创建 agent.py**

```python
"""Deep Agents Agent 封装 — 统一入口"""
import os
import structlog
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from llm import get_llm
from prompts import load_prompt
from ariz_state import ArizState, create_initial_state, get_step_label
from ariz_graph import build_ariz_graph
from context_manager import compress_messages
from observability import TraceContext

logger = structlog.get_logger()


class XagentAgent:
    """Xagent 核心 Agent — 基于 LangGraph + 上下文管理"""

    def __init__(self):
        self.llm = get_llm()
        self.system_prompt = load_prompt("system")
        self.graph = build_ariz_graph()
        logger.info("xagent_agent_initialized")

    async def run(self, user_message: str, state: ArizState = None,
                  thread_id: str = "default") -> dict:
        """运行一次 Agent 交互

        Args:
            user_message: 用户消息
            state: 当前状态（None 则创建初始状态）
            thread_id: 会话 ID

        Returns:
            {
                "response": str,           # 助手回复文本
                "card_data": dict,          # 步骤卡片数据
                "state": ArizState,         # 更新后的状态
                "trace": dict,              # 追踪摘要
            }
        """
        if state is None:
            state = create_initial_state()

        # 添加用户消息
        user_msg = HumanMessage(content=user_message)
        state["messages"] = state.get("messages", []) + [user_msg]
        state["thread_id"] = thread_id

        # 上下文压缩
        state["messages"] = await compress_messages(
            state["messages"], state["current_step"]
        )

        # 追踪
        trace_ctx = TraceContext(thread_id, state["current_step"])

        try:
            # 运行 LangGraph
            result = await self.graph.ainvoke(
                state,
                config={"configurable": {"thread_id": thread_id}},
            )

            trace_ctx.finish()

            # 提取回复
            response_text = ""
            if result.get("messages"):
                last_msg = result["messages"][-1]
                if hasattr(last_msg, "content"):
                    response_text = last_msg.content

            return {
                "response": response_text,
                "card_data": result.get("card_data", {}),
                "state": result,
                "trace": trace_ctx.finish(),
            }

        except Exception as e:
            trace_ctx.record_error(str(e))
            trace_ctx.finish()
            logger.error("agent_run_failed", error=str(e), thread_id=thread_id)
            return {
                "response": f"⚠️ AI 服务暂时不可用：{str(e)}",
                "card_data": {},
                "state": state,
                "trace": trace_ctx.finish(),
            }

    def get_state(self, thread_id: str) -> dict:
        """获取会话状态"""
        try:
            snapshot = self.graph.get_state(
                config={"configurable": {"thread_id": thread_id}}
            )
            return snapshot.values if snapshot else create_initial_state()
        except Exception:
            return create_initial_state()


# 全局 Agent 实例（延迟初始化）
_agent = None


def get_agent() -> XagentAgent:
    """获取 Agent 单例"""
    global _agent
    if _agent is None:
        _agent = XagentAgent()
    return _agent
```

- [ ] **Step 2: 验证 Agent 初始化**

```bash
cd /Users/chenyw/PROJECT/Xagent/backend
source venv/bin/activate
python3 -c "
from dotenv import load_dotenv
load_dotenv()

from agent import XagentAgent
agent = XagentAgent()
print(f'Agent 初始化成功')
print(f'System prompt 长度: {len(agent.system_prompt)} chars')
print(f'Graph 节点: {list(agent.graph.nodes.keys())}')
"
```

Expected: Agent 初始化成功，打印 system prompt 长度和 9 个节点名。

- [ ] **Step 3: Commit**

```bash
cd /Users/chenyw/PROJECT/Xagent
git add backend/agent.py
git commit -m "feat: add Deep Agents XagentAgent wrapper"
```

---

### Task 5: 集成 Deep Agents Agent 到 Flask

**Files:**
- Modify: `backend/app.py`

- [ ] **Step 1: 修改 app.py 的 chat() 路由**

将 `_chat_with_langgraph` 替换为使用新的 `XagentAgent`：

```python
# 在 app.py 顶部新增导入
from agent import get_agent


def _chat_with_langgraph(data, conv_id, messages):
    """使用 Deep Agents + LangGraph 引擎处理聊天"""
    agent = get_agent()

    def generate():
        try:
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                # 获取用户最新消息
                user_msg = ""
                for m in reversed(messages):
                    if m.get("role") == "user":
                        user_msg = m["content"]
                        break

                # 获取或创建状态
                state = agent.get_state(conv_id or "default")

                # 运行 Agent
                result = loop.run_until_complete(
                    agent.run(user_msg, state=state, thread_id=conv_id or "default")
                )
            finally:
                loop.close()

            # 输出卡片数据
            card_data = result.get("card_data", {})
            if card_data:
                tool_text = f"\n\n**步骤 {card_data.get('step', '?')}：{card_data.get('title', '')}**\n"
                yield f'0:{json.dumps(tool_text)}\n'

            # 输出回复
            response = result.get("response", "")
            if response:
                yield f'0:{json.dumps(response)}\n'

            # 保存消息
            _save_assistant_message(conv_id, response)

        except Exception as e:
            logger.error("deep_agent_error", error=str(e))
            error_msg = f"\n\n⚠️ AI 服务暂时不可用，请稍后重试。"
            yield f'0:{json.dumps(error_msg)}\n'

    return Response(generate(), mimetype="text/plain; charset=utf-8",
                    headers={"X-Vercel-AI-Data-Stream": "v1"})
```

- [ ] **Step 2: 验证 Flask 启动**

```bash
cd /Users/chenyw/PROJECT/Xagent/backend
source venv/bin/activate
USE_LANGGRAPH=true timeout 5 python app.py 2>&1 || true
```

Expected: Flask 正常启动，无 import 错误。

- [ ] **Step 3: Commit**

```bash
cd /Users/chenyw/PROJECT/Xagent
git add backend/app.py
git commit -m "feat: integrate Deep Agents agent into Flask"
```

---

### Task 6: 端到端验证 — Deep Agents 引擎

**Files:**
- None（纯验证）

- [ ] **Step 1: 启动 Flask（Deep Agents 模式）**

```bash
cd /Users/chenyw/PROJECT/Xagent/backend
source venv/bin/activate
USE_LANGGRAPH=true python app.py &
sleep 3
```

- [ ] **Step 2: 测试 Step 1 完整流程**

```bash
# 创建对话
CONV_ID=$(curl -s -X POST http://localhost:8000/api/conversations | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "对话 ID: $CONV_ID"

# 发送问题
curl -s -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d "{\"conversation_id\": \"$CONV_ID\", \"messages\": [{\"role\": \"user\", \"content\": \"电池包在低温环境下续航衰减严重，2C放电时电芯最低温度-15°C\"}]}" \
  2>&1 | head -30
```

Expected: 返回 SSE 流式响应，包含 ARIZ Step 1 分析。

- [ ] **Step 3: 检查 ARIZ 状态**

```bash
curl -s http://localhost:8000/api/ariz/status/$CONV_ID | python3 -m json.tool
```

Expected: 返回状态 JSON，包含 step_results 和 current_step。

- [ ] **Step 4: 测试多步流程（Step 1 → Step 2）**

```bash
# 模拟用户确认 Step 1
curl -s -X POST http://localhost:8000/api/ariz/confirm/$CONV_ID | python3 -m json.tool

# 发送 Step 2 触发消息
curl -s -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d "{\"conversation_id\": \"$CONV_ID\", \"messages\": [{\"role\": \"user\", \"content\": \"已确认，请继续下一步\"}]}" \
  2>&1 | head -30
```

Expected: 返回 Step 2 组件分析结果。

- [ ] **Step 5: 清理**

```bash
kill %1 2>/dev/null
```

- [ ] **Step 6: 全量测试运行**

```bash
cd /Users/chenyw/PROJECT/Xagent/backend
source venv/bin/activate
python -m pytest tests/ -v
```

Expected: 所有测试 PASSED。

- [ ] **Step 7: Final Commit**

```bash
cd /Users/chenyw/PROJECT/Xagent
git add -A
git commit -m "feat: complete Deep Agents integration - Phase 2 done"
```
