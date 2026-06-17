# Xagent 迁移 Plan B：LangGraph 核心流程

> **For agentic workers:** Use superpowers-open:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 ARIZ 9 步流程从手搓状态机迁移到 LangGraph StateGraph，实现图结构流程控制、Checkpoint 持久化和条件路由。

**Architecture:** 用 LangGraph StateGraph 定义 ARIZ 流程图（9 个节点 + 条件边），用 SqliteSaver 做 Checkpoint 持久化，Flask 路由层做最小适配调用新图引擎。

**Tech Stack:** langgraph, langchain-core, langchain-openai, SQLite

---

## 文件结构总览

```
backend/
├── ariz_state.py             # [创建] ArizState TypedDict + Checkpoint 配置
├── ariz_tools.py             # [创建] ARIZ 工具定义（从 app.py 拆出）
├── ariz_nodes.py             # [创建] 9 个 Step Node 函数
├── ariz_graph.py             # [创建] LangGraph StateGraph 定义
├── app.py                    # [修改] Flask 路由适配新引擎
├── ariz_flow.py              # [保留] 旧逻辑作为 fallback
├── tests/
│   ├── test_ariz_state.py    # [创建] State 测试
│   ├── test_ariz_graph.py    # [创建] Graph 测试
│   └── test_ariz_nodes.py    # [创建] Node 测试
```

---

### Task 1: 创建 ArizState 类型定义

**Files:**
- Create: `backend/ariz_state.py`
- Create: `backend/tests/test_ariz_state.py`

- [ ] **Step 1: 创建 ariz_state.py**

```python
"""ARIZ 流程状态定义 — LangGraph StateGraph 专用"""
from typing import TypedDict, Optional
from langgraph.graph import END


class ArizState(TypedDict):
    """ARIZ 流程的全局状态"""
    current_step: str           # 当前步骤名（problem/components/...）
    step_results: dict          # 各步分析结果 {step_name: result_dict}
    messages: list              # 对话历史（LangChain message 格式）
    database_context: dict      # 组件知识库查询结果
    card_data: dict             # 当前步骤的卡片数据（供前端渲染）
    error: Optional[str]        # 错误信息（如果有）


# ARIZ 步骤定义
ARIZ_STEPS = [
    ("problem",     "问题识别"),
    ("components",  "系统组件分析"),
    ("contacts",    "接触关系分析"),
    ("function",    "功能建模"),
    ("structure",   "系统结构分析"),
    ("summary",     "功能建模问题总结"),
    ("causal",      "因果链分析"),
    ("keypoint",    "关键问题/切入点"),
    ("solution",    "生成创新方案"),
]

ARIZ_STEP_NAMES = [name for name, _ in ARIZ_STEPS]
ARIZ_STEP_LABELS = {name: label for name, label in ARIZ_STEPS}


def get_step_index(name: str) -> int:
    """获取步骤的索引位置"""
    for i, (n, _) in enumerate(ARIZ_STEPS):
        if n == name:
            return i
    return -1


def get_step_label(name: str) -> str:
    """获取步骤的中文标签"""
    return ARIZ_STEP_LABELS.get(name, name)


def get_next_step(current: str) -> Optional[str]:
    """获取下一步名称，已是最后一步返回 None"""
    idx = get_step_index(current)
    if idx < 0 or idx >= len(ARIZ_STEPS) - 1:
        return None
    return ARIZ_STEPS[idx + 1][0]


def create_initial_state() -> ArizState:
    """创建初始状态"""
    return {
        "current_step": "problem",
        "step_results": {},
        "messages": [],
        "database_context": {},
        "card_data": {},
        "error": None,
    }
```

- [ ] **Step 2: 创建 test_ariz_state.py**

```python
"""ArizState 测试"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ariz_state import (
    ARIZ_STEPS, ARIZ_STEP_NAMES, ARIZ_STEP_LABELS,
    get_step_index, get_step_label, get_next_step, create_initial_state,
)


def test_ariz_steps_count():
    """验证 ARIZ 有 9 个步骤"""
    assert len(ARIZ_STEPS) == 9


def test_ariz_step_names():
    """验证步骤名称正确"""
    assert ARIZ_STEP_NAMES == [
        "problem", "components", "contacts", "function",
        "structure", "summary", "causal", "keypoint", "solution",
    ]


def test_get_step_index():
    """验证步骤索引查找"""
    assert get_step_index("problem") == 0
    assert get_step_index("solution") == 8
    assert get_step_index("nonexistent") == -1


def test_get_step_label():
    """验证步骤标签查找"""
    assert get_step_label("problem") == "问题识别"
    assert get_step_label("solution") == "生成创新方案"
    assert get_step_label("nonexistent") == "nonexistent"


def test_get_next_step():
    """验证下一步查找"""
    assert get_next_step("problem") == "components"
    assert get_next_step("solution") is None
    assert get_next_step("nonexistent") is None


def test_create_initial_state():
    """验证初始状态创建"""
    state = create_initial_state()
    assert state["current_step"] == "problem"
    assert state["step_results"] == {}
    assert state["messages"] == []
    assert state["error"] is None
```

- [ ] **Step 3: 运行测试**

```bash
cd /Users/chenyw/PROJECT/Xagent/backend
source venv/bin/activate
python -m pytest tests/test_ariz_state.py -v
```

Expected: 6 tests PASSED。

- [ ] **Step 4: Commit**

```bash
cd /Users/chenyw/PROJECT/Xagent
git add backend/ariz_state.py backend/tests/test_ariz_state.py
git commit -m "feat: add ArizState type definitions for LangGraph"
```

---

### Task 2: 提取 ARIZ 工具定义

**Files:**
- Create: `backend/ariz_tools.py`

- [ ] **Step 1: 创建 ariz_tools.py**

从 `app.py` 中提取所有 ARIZ 工具定义，集中到独立文件。保留原文件不动，新文件供 LangGraph 使用。

```python
"""ARIZ 工具定义 — 供 LangGraph Node 使用"""
from langchain_core.tools import tool


def make_step_tool(step_num: int, name: str, label: str, fields: list) -> dict:
    """生成 ARIZ 步骤工具定义（OpenAI function calling 格式）"""
    props = {}
    required = []
    for f in fields:
        props[f["name"]] = {
            "type": f.get("type", "string"),
            "description": f.get("desc", ""),
        }
        if f.get("required"):
            required.append(f["name"])
    return {
        "type": "function",
        "function": {
            "name": f"ariz_step{step_num}_{name}",
            "description": f"ARIZ第{step_num}步：用户确认后调用此工具保存{label}结果",
            "parameters": {
                "type": "object",
                "properties": props,
                "required": required,
            },
        },
    }


# Step 1: 问题识别
STEP1_TOOL = {
    "type": "function",
    "function": {
        "name": "ariz_step1_problem",
        "description": "ARIZ第1步：用户确认后调用此工具保存问题识别结果",
        "parameters": {
            "type": "object",
            "properties": {
                "problem_object": {"type": "string", "description": "具体子系统名称"},
                "system_keywords": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "数据库检索用的系统级关键词",
                },
                "phenomenon": {"type": "string", "description": "可观测可量化的现象"},
                "constraints": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "约束条件",
                },
                "goal": {"type": "string", "description": "期望目标"},
                "contradiction_hint": {"type": "string", "description": "初步矛盾方向"},
            },
            "required": ["problem_object", "system_keywords", "phenomenon"],
        },
    },
}

# Step 2: 系统组件分析
STEP2_TOOL = {
    "type": "function",
    "function": {
        "name": "ariz_step2_components",
        "description": "ARIZ第2步：用户确认后调用此工具保存组件分析结果",
        "parameters": {
            "type": "object",
            "properties": {
                "supersystem": {"type": "string", "description": "超系统描述"},
                "supersystem_components": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "functions": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "该组件对本系统产生的功能/影响",
                            },
                        },
                        "required": ["name"],
                    },
                    "description": "超系统中与本系统有交互的外部组件",
                },
                "system_name": {"type": "string", "description": "系统名称"},
                "user_added": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "用户补充的、数据库中没有的组件列表",
                },
            },
            "required": ["supersystem", "system_name"],
        },
    },
}

# Step 3-9: 使用 make_step_tool 生成
STEP3_TOOL = make_step_tool(3, "contacts", "接触关系分析", [
    {"name": "contacts", "type": "array", "desc": "组件间接触关系列表", "required": True},
])
STEP4_TOOL = make_step_tool(4, "function", "功能建模", [
    {"name": "functions", "type": "array", "desc": "功能模型列表", "required": True},
])
STEP5_TOOL = make_step_tool(5, "structure", "系统结构分析", [
    {"name": "structure_info", "type": "object", "desc": "结构参数", "required": True},
])
STEP6_TOOL = make_step_tool(6, "summary", "问题总结", [
    {"name": "problems", "type": "object", "desc": "分类问题清单", "required": True},
])
STEP7_TOOL = make_step_tool(7, "causal", "因果链分析", [
    {"name": "causal_chains", "type": "array", "desc": "因果链列表", "required": True},
])
STEP8_TOOL = make_step_tool(8, "keypoint", "关键问题定义", [
    {"name": "contradictions", "type": "object", "desc": "矛盾定义和IFR", "required": True},
])
STEP9_TOOL = make_step_tool(9, "solution", "方案生成", [
    {"name": "solutions", "type": "array", "desc": "创新方案列表", "required": True},
])

# 所有工具列表
ALL_STEP_TOOLS = [
    STEP1_TOOL, STEP2_TOOL, STEP3_TOOL, STEP4_TOOL,
    STEP5_TOOL, STEP6_TOOL, STEP7_TOOL, STEP8_TOOL, STEP9_TOOL,
]

# 工具名 → 步骤编号映射
TOOL_STEP_MAP = {
    "ariz_step1_problem": 1,
    "ariz_step2_components": 2,
    "ariz_step3_contacts": 3,
    "ariz_step4_function": 4,
    "ariz_step5_structure": 5,
    "ariz_step6_summary": 6,
    "ariz_step7_causal": 7,
    "ariz_step8_keypoint": 8,
    "ariz_step9_solution": 9,
}

# 步骤名 → 工具映射
STEP_TOOL_MAP = {
    "problem": STEP1_TOOL,
    "components": STEP2_TOOL,
    "contacts": STEP3_TOOL,
    "function": STEP4_TOOL,
    "structure": STEP5_TOOL,
    "summary": STEP6_TOOL,
    "causal": STEP7_TOOL,
    "keypoint": STEP8_TOOL,
    "solution": STEP9_TOOL,
}


def get_tool_for_step(step_name: str) -> dict | None:
    """获取指定步骤对应的工具定义"""
    return STEP_TOOL_MAP.get(step_name)


def parse_tool_calls(response) -> dict:
    """从 LangChain response 中解析工具调用结果"""
    result = {}
    if hasattr(response, "tool_calls") and response.tool_calls:
        for tc in response.tool_calls:
            result[tc["name"]] = tc["args"]
    return result
```

- [ ] **Step 2: 验证工具定义完整性**

```bash
cd /Users/chenyw/PROJECT/Xagent/backend
source venv/bin/activate
python3 -c "
from ariz_tools import ALL_STEP_TOOLS, TOOL_STEP_MAP, STEP_TOOL_MAP, get_tool_for_step

print(f'工具总数: {len(ALL_STEP_TOOLS)}')
assert len(ALL_STEP_TOOLS) == 9

print(f'映射条目: {len(TOOL_STEP_MAP)}')
assert len(TOOL_STEP_MAP) == 9

for step in ['problem', 'components', 'contacts', 'function', 'structure', 'summary', 'causal', 'keypoint', 'solution']:
    tool = get_tool_for_step(step)
    assert tool is not None, f'{step} 无对应工具'
    print(f'  {step} → {tool[\"function\"][\"name\"]} ✓')

print('工具定义验证通过 ✓')
"
```

Expected: 9 个工具全部验证通过。

- [ ] **Step 3: Commit**

```bash
cd /Users/chenyw/PROJECT/Xagent
git add backend/ariz_tools.py
git commit -m "feat: extract ARIZ tool definitions to standalone module"
```

---

### Task 3: 创建 ARIZ Node 函数（Step 1-3）

**Files:**
- Create: `backend/ariz_nodes.py`
- Create: `backend/tests/test_ariz_nodes.py`

- [ ] **Step 1: 创建 ariz_nodes.py — 基础框架 + Step 1**

```python
"""ARIZ 流程节点函数 — 供 LangGraph StateGraph 使用"""
import json
import structlog
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from ariz_state import ArizState, get_step_label, get_step_index
from ariz_tools import get_tool_for_step, parse_tool_calls
from prompts import load_prompt
from llm import get_llm
from component_db import search_system, get_system_components

logger = structlog.get_logger()


def build_messages_for_step(state: ArizState, step_name: str) -> list:
    """为指定步骤构建消息列表"""
    system_prompt = load_prompt("system")
    # prompt 文件名格式: step1_problem, step2_components, ..., step9_solution
    step_idx = get_step_index(step_name) + 1
    step_prompt = load_prompt(f"step{step_idx}_{step_name}")

    messages = [
        SystemMessage(content=system_prompt),
        SystemMessage(content=step_prompt),
    ]

    # 注入历史上下文
    if state["step_results"]:
        history_lines = build_history_context(state["step_results"])
        if history_lines:
            messages.append(SystemMessage(content=history_lines))

    # 注入对话历史
    messages.extend(state.get("messages", []))

    return messages


def build_history_context(step_results: dict) -> str:
    """将已完成步骤的结果转为上下文摘要"""
    if not step_results:
        return ""

    lines = ["已完成的分析步骤："]
    for step_name in ["problem", "components", "contacts", "function",
                      "structure", "summary", "causal", "keypoint", "solution"]:
        if step_name in step_results:
            label = get_step_label(step_name)
            result = step_results[step_name]
            summary = summarize_step_result(step_name, result)
            lines.append(f"\n【{label}】\n{summary}")

    return "\n".join(lines)


def summarize_step_result(step_name: str, result: dict) -> str:
    """将步骤结果转为 LLM 可读的摘要"""
    if step_name == "problem":
        lines = []
        if result.get("problem_object"):
            lines.append(f"- 问题对象：{result['problem_object']}")
        if result.get("phenomenon"):
            lines.append(f"- 现象：{result['phenomenon']}")
        if result.get("goal"):
            lines.append(f"- 目标：{result['goal']}")
        if result.get("constraints"):
            lines.append(f"- 约束：{'、'.join(result['constraints'])}")
        if result.get("contradiction_hint"):
            lines.append(f"- 矛盾方向：{result['contradiction_hint']}")
        return "\n".join(lines) if lines else json.dumps(result, ensure_ascii=False)[:200]

    elif step_name == "components":
        lines = []
        if result.get("supersystem"):
            lines.append(f"- 超系统：{result['supersystem']}")
        if result.get("system_name"):
            lines.append(f"- 系统：{result['system_name']}")
        comps = result.get("all_components", [])
        if comps:
            names = [c if isinstance(c, str) else c.get("name", str(c)) for c in comps]
            lines.append(f"- 组件：{'、'.join(names)}")
        return "\n".join(lines) if lines else json.dumps(result, ensure_ascii=False)[:200]

    elif step_name == "contacts":
        contacts = result.get("contacts", [])
        lines = [f"- 共{len(contacts)}个接触关系"]
        for c in contacts[:5]:
            lines.append(f"  {c.get('component_a', '')} ↔ {c.get('component_b', '')}：{c.get('contact_type', '')}")
        return "\n".join(lines)

    elif step_name == "function":
        funcs = result.get("functions", [])
        type_map = {"useful": "有用", "insufficient": "不足", "excessive": "过度", "harmful": "有害"}
        lines = [f"- 共{len(funcs)}个功能"]
        for f in funcs[:5]:
            t = type_map.get(f.get("type", ""), f.get("type", ""))
            lines.append(f"  {f.get('source', '')} → {f.get('function', '')} → {f.get('target', '')}（{t}）")
        return "\n".join(lines)

    else:
        return json.dumps(result, ensure_ascii=False)[:300]


def query_components(system_keywords: list) -> dict:
    """查询组件知识库（复用 ariz_flow.py 的逻辑）"""
    if not system_keywords:
        return {"error": "未提供 system_keywords"}

    all_systems = []
    for kw in system_keywords:
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
        for kw in system_keywords:
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

    if not unique:
        return {"error": f"未匹配到系统", "matched_systems": []}

    primary = unique[0]
    system_data = get_system_components(primary["id"])
    return {"matched_systems": unique, "primary_system": system_data}


# ============ Step 1 Node ============

async def step1_problem_node(state: ArizState) -> dict:
    """Step 1: 问题识别"""
    logger.info("node_start", step="problem")
    llm = get_llm()
    tool = get_tool_for_step("problem")
    messages = build_messages_for_step(state, "problem")

    # 添加用户最新消息
    if state.get("messages"):
        user_msg = state["messages"][-1]
        if hasattr(user_msg, "content"):
            messages.append(user_msg)

    response = await llm.ainvoke(messages, tools=[tool] if tool else None)
    tool_results = parse_tool_calls(response)

    # 解析工具调用结果
    step_result = {}
    card_data = {}
    if "ariz_step1_problem" in tool_results:
        args = tool_results["ariz_step1_problem"]
        db_result = query_components(args.get("system_keywords", []))
        step_result = {**args, "database_query": db_result}
        card_data = {
            "step": 1,
            "title": "问题识别",
            "status": "current",
            "saved": True,
            "data": {
                "problem_object": args.get("problem_object"),
                "phenomenon": args.get("phenomenon"),
                "goal": args.get("goal"),
                "contradiction_hint": args.get("contradiction_hint"),
                "constraints": args.get("constraints", []),
                "database_query": db_result,
            },
        }

    logger.info("node_end", step="problem", has_result=bool(step_result))
    return {
        "current_step": "components",
        "step_results": {**state["step_results"], "problem": step_result} if step_result else state["step_results"],
        "card_data": card_data,
        "messages": state["messages"] + [AIMessage(content=response.content)],
    }
```

- [ ] **Step 2: 添加 Step 2 和 Step 3 Node**

在 `ariz_nodes.py` 中追加：

```python
# ============ Step 2 Node ============

async def step2_components_node(state: ArizState) -> dict:
    """Step 2: 系统组件分析"""
    logger.info("node_start", step="components")
    llm = get_llm()
    tool = get_tool_for_step("components")
    messages = build_messages_for_step(state, "components")

    if state.get("messages"):
        messages.append(state["messages"][-1])

    response = await llm.ainvoke(messages, tools=[tool] if tool else None)
    tool_results = parse_tool_calls(response)

    step_result = {}
    card_data = {}
    if "ariz_step2_components" in tool_results:
        args = tool_results["ariz_step2_components"]

        # 从 Step 1 结果获取数据库组件
        step1_data = state["step_results"].get("problem", {})
        db_result = step1_data.get("database_query", {})
        primary_system = db_result.get("primary_system", {})
        db_components = [c["name"] for c in primary_system.get("components", [])]

        # 合并用户补充的组件
        user_added = args.get("user_added", [])
        user_added_normalized = [
            {"name": c, "functions": []} if isinstance(c, str) else c
            for c in user_added
        ]

        super_raw = args.get("supersystem_components", [])
        supersystem_components = [
            {"name": c, "functions": []} if isinstance(c, str) else c
            for c in super_raw
        ]
        super_names = [c["name"] if isinstance(c, dict) else c for c in supersystem_components]

        all_components = db_components.copy()
        for c in user_added_normalized:
            name = c["name"] if isinstance(c, dict) else c
            if name not in all_components:
                all_components.append(name)
        for n in super_names:
            if n not in all_components:
                all_components.append(n)

        step_result = {
            "supersystem": args.get("supersystem", ""),
            "supersystem_components": supersystem_components,
            "system_name": args.get("system_name", primary_system.get("system", {}).get("name", "")),
            "all_components": all_components,
            "user_added": user_added_normalized,
        }
        card_data = {
            "step": 2,
            "title": "系统组件分析",
            "status": "current",
            "saved": True,
            "data": {**step_result, "database_query": db_result},
        }

    logger.info("node_end", step="components", has_result=bool(step_result))
    return {
        "current_step": "contacts",
        "step_results": {**state["step_results"], "components": step_result} if step_result else state["step_results"],
        "card_data": card_data,
        "messages": state["messages"] + [AIMessage(content=response.content)],
    }


# ============ Step 3 Node ============

async def step3_contacts_node(state: ArizState) -> dict:
    """Step 3: 接触关系分析"""
    logger.info("node_start", step="contacts")
    llm = get_llm()
    tool = get_tool_for_step("contacts")
    messages = build_messages_for_step(state, "contacts")

    if state.get("messages"):
        messages.append(state["messages"][-1])

    response = await llm.ainvoke(messages, tools=[tool] if tool else None)
    tool_results = parse_tool_calls(response)

    step_result = {}
    card_data = {}
    if "ariz_step3_contacts" in tool_results:
        contacts = tool_results["ariz_step3_contacts"].get("contacts", [])
        step_result = {"contacts": contacts}

        # 获取组件列表供前端渲染矩阵
        step2_data = state["step_results"].get("components", {})
        card_data = {
            "step": 3,
            "title": "接触关系分析",
            "status": "current",
            "saved": True,
            "data": {**step_result, "all_components": step2_data.get("all_components", [])},
        }

    # 兜底：LLM 没调工具时，从 Step 2 组件自动生成接触关系
    if not step_result:
        step2_data = state["step_results"].get("components", {})
        all_comp = step2_data.get("all_components", [])
        if len(all_comp) >= 2:
            auto_contacts = []
            for i in range(len(all_comp)):
                for j in range(i + 1, len(all_comp)):
                    auto_contacts.append({
                        "component_a": all_comp[i],
                        "component_b": all_comp[j],
                        "contact_type": "待分析",
                        "interface": "",
                    })
            step_result = {"contacts": auto_contacts}
            card_data = {
                "step": 3,
                "title": "接触关系分析",
                "status": "current",
                "saved": True,
                "data": {**step_result, "all_components": all_comp},
            }
            logger.info("step3_fallback", contact_count=len(auto_contacts))

    logger.info("node_end", step="contacts", has_result=bool(step_result))
    return {
        "current_step": "function",
        "step_results": {**state["step_results"], "contacts": step_result} if step_result else state["step_results"],
        "card_data": card_data,
        "messages": state["messages"] + [AIMessage(content=response.content)],
    }
```

- [ ] **Step 3: 创建 test_ariz_nodes.py**

```python
"""ARIZ Node 函数测试"""
import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ariz_nodes import build_messages_for_step, build_history_context, summarize_step_result
from ariz_state import create_initial_state


def test_build_messages_for_step():
    """验证消息构建"""
    state = create_initial_state()
    messages = build_messages_for_step(state, "problem")
    # 至少有 system prompt + step prompt
    assert len(messages) >= 2
    assert "动力电池" in messages[0].content


def test_build_history_context_empty():
    """验证空历史上下文"""
    result = build_history_context({})
    assert result == ""


def test_build_history_context_with_results():
    """验证有历史结果时的上下文构建"""
    step_results = {
        "problem": {
            "problem_object": "热管理系统",
            "phenomenon": "温度过高",
        }
    }
    result = build_history_context(step_results)
    assert "问题识别" in result
    assert "热管理系统" in result


def test_summarize_step_result_problem():
    """验证 Step 1 结果摘要"""
    result = {
        "problem_object": "热管理系统",
        "phenomenon": "2C放电时温度48°C",
        "goal": "温度≤40°C",
        "constraints": ["不增加重量"],
    }
    summary = summarize_step_result("problem", result)
    assert "热管理系统" in summary
    assert "48°C" in summary


def test_summarize_step_result_contacts():
    """验证 Step 3 结果摘要"""
    result = {
        "contacts": [
            {"component_a": "冷却板", "component_b": "电芯", "contact_type": "热传导"},
        ]
    }
    summary = summarize_step_result("contacts", result)
    assert "冷却板" in summary
    assert "热传导" in summary
```

- [ ] **Step 4: 运行测试**

```bash
cd /Users/chenyw/PROJECT/Xagent/backend
source venv/bin/activate
python -m pytest tests/test_ariz_nodes.py -v
```

Expected: 5 tests PASSED。

- [ ] **Step 5: Commit**

```bash
cd /Users/chenyw/PROJECT/Xagent
git add backend/ariz_nodes.py backend/tests/test_ariz_nodes.py
git commit -m "feat: add ARIZ step 1-3 LangGraph nodes"
```

---

### Task 4: 创建 ARIZ Node 函数（Step 4-9）

**Files:**
- Modify: `backend/ariz_nodes.py`

- [ ] **Step 1: 添加 Step 4-6 Node**

在 `ariz_nodes.py` 末尾追加：

```python
# ============ Step 4 Node ============

async def step4_function_node(state: ArizState) -> dict:
    """Step 4: 功能建模"""
    logger.info("node_start", step="function")
    llm = get_llm()
    tool = get_tool_for_step("function")
    messages = build_messages_for_step(state, "function")

    if state.get("messages"):
        messages.append(state["messages"][-1])

    response = await llm.ainvoke(messages, tools=[tool] if tool else None)
    tool_results = parse_tool_calls(response)

    step_result = {}
    card_data = {}
    if "ariz_step4_function" in tool_results:
        functions = tool_results["ariz_step4_function"].get("functions", [])
        step_result = {"functions": functions}
        card_data = {
            "step": 4, "title": "功能建模", "status": "current", "saved": True,
            "data": step_result,
        }

    # 兜底：从 Step 3 接触关系生成功能模型
    if not step_result:
        step3 = state["step_results"].get("contacts", {})
        contacts = step3.get("contacts", [])
        if contacts:
            contact_to_func = {
                "热传导": ("useful", "传导热量"), "对流换热": ("useful", "对流换热"),
                "换热": ("useful", "热交换"), "热传递": ("useful", "传递热量"),
                "温度监测": ("useful", "监测温度"), "接触应力": ("harmful", "产生接触应力"),
                "安装基面": ("useful", "提供安装支撑"), "流动阻力": ("harmful", "产生流动阻力"),
                "热膨胀": ("excessive", "热膨胀过大"), "驱动循环": ("useful", "驱动冷却液循环"),
                "散热": ("useful", "散发热量"), "预加热": ("useful", "预加热电池"),
            }
            auto_funcs = []
            for c in contacts:
                a, b, ctype = c.get("component_a", ""), c.get("component_b", ""), c.get("contact_type", "")
                if a and b:
                    func_type, func_desc = "useful", f"{a}对{b}产生作用"
                    for key, (ft, desc) in contact_to_func.items():
                        if key in ctype:
                            func_type, func_desc = ft, f"{a}{desc}给{b}"
                            break
                    auto_funcs.append({"source": a, "target": b, "function": func_desc, "type": func_type})
            if auto_funcs:
                step_result = {"functions": auto_funcs}
                card_data = {"step": 4, "title": "功能建模", "status": "current", "saved": True, "data": step_result}
                logger.info("step4_fallback", function_count=len(auto_funcs))

    logger.info("node_end", step="function", has_result=bool(step_result))
    return {
        "current_step": "structure",
        "step_results": {**state["step_results"], "function": step_result} if step_result else state["step_results"],
        "card_data": card_data,
        "messages": state["messages"] + [AIMessage(content=response.content)],
    }


# ============ Step 5 Node ============

async def step5_structure_node(state: ArizState) -> dict:
    """Step 5: 系统结构分析"""
    logger.info("node_start", step="structure")
    llm = get_llm()
    tool = get_tool_for_step("structure")
    messages = build_messages_for_step(state, "structure")

    if state.get("messages"):
        messages.append(state["messages"][-1])

    response = await llm.ainvoke(messages, tools=[tool] if tool else None)
    tool_results = parse_tool_calls(response)

    step_result = {}
    card_data = {}
    if "ariz_step5_structure" in tool_results:
        step_result = tool_results["ariz_step5_structure"]
        card_data = {"step": 5, "title": "系统结构分析", "status": "current", "saved": True, "data": step_result}

    logger.info("node_end", step="structure", has_result=bool(step_result))
    return {
        "current_step": "summary",
        "step_results": {**state["step_results"], "structure": step_result} if step_result else state["step_results"],
        "card_data": card_data,
        "messages": state["messages"] + [AIMessage(content=response.content)],
    }


# ============ Step 6 Node ============

async def step6_summary_node(state: ArizState) -> dict:
    """Step 6: 功能建模问题总结"""
    logger.info("node_start", step="summary")
    llm = get_llm()
    tool = get_tool_for_step("summary")
    messages = build_messages_for_step(state, "summary")

    if state.get("messages"):
        messages.append(state["messages"][-1])

    response = await llm.ainvoke(messages, tools=[tool] if tool else None)
    tool_results = parse_tool_calls(response)

    step_result = {}
    card_data = {}
    if "ariz_step6_summary" in tool_results:
        step_result = tool_results["ariz_step6_summary"]
        card_data = {"step": 6, "title": "问题总结", "status": "current", "saved": True, "data": step_result}

    logger.info("node_end", step="summary", has_result=bool(step_result))
    return {
        "current_step": "causal",
        "step_results": {**state["step_results"], "summary": step_result} if step_result else state["step_results"],
        "card_data": card_data,
        "messages": state["messages"] + [AIMessage(content=response.content)],
    }


# ============ Step 7 Node ============

async def step7_causal_node(state: ArizState) -> dict:
    """Step 7: 因果链分析"""
    logger.info("node_start", step="causal")
    llm = get_llm()
    tool = get_tool_for_step("causal")
    messages = build_messages_for_step(state, "causal")

    if state.get("messages"):
        messages.append(state["messages"][-1])

    response = await llm.ainvoke(messages, tools=[tool] if tool else None)
    tool_results = parse_tool_calls(response)

    step_result = {}
    card_data = {}
    if "ariz_step7_causal" in tool_results:
        step_result = tool_results["ariz_step7_causal"]
        card_data = {"step": 7, "title": "因果链分析", "status": "current", "saved": True, "data": step_result}

    logger.info("node_end", step="causal", has_result=bool(step_result))
    return {
        "current_step": "keypoint",
        "step_results": {**state["step_results"], "causal": step_result} if step_result else state["step_results"],
        "card_data": card_data,
        "messages": state["messages"] + [AIMessage(content=response.content)],
    }


# ============ Step 8 Node ============

async def step8_keypoint_node(state: ArizState) -> dict:
    """Step 8: 关键问题/切入点"""
    logger.info("node_start", step="keypoint")
    llm = get_llm()
    tool = get_tool_for_step("keypoint")
    messages = build_messages_for_step(state, "keypoint")

    if state.get("messages"):
        messages.append(state["messages"][-1])

    response = await llm.ainvoke(messages, tools=[tool] if tool else None)
    tool_results = parse_tool_calls(response)

    step_result = {}
    card_data = {}
    if "ariz_step8_keypoint" in tool_results:
        step_result = tool_results["ariz_step8_keypoint"]
        card_data = {"step": 8, "title": "关键问题", "status": "current", "saved": True, "data": step_result}

    logger.info("node_end", step="keypoint", has_result=bool(step_result))
    return {
        "current_step": "solution",
        "step_results": {**state["step_results"], "keypoint": step_result} if step_result else state["step_results"],
        "card_data": card_data,
        "messages": state["messages"] + [AIMessage(content=response.content)],
    }


# ============ Step 9 Node ============

async def step9_solution_node(state: ArizState) -> dict:
    """Step 9: 生成创新方案"""
    logger.info("node_start", step="solution")
    llm = get_llm()
    tool = get_tool_for_step("solution")
    messages = build_messages_for_step(state, "solution")

    if state.get("messages"):
        messages.append(state["messages"][-1])

    response = await llm.ainvoke(messages, tools=[tool] if tool else None)
    tool_results = parse_tool_calls(response)

    step_result = {}
    card_data = {}
    if "ariz_step9_solution" in tool_results:
        step_result = tool_results["ariz_step9_solution"]
        card_data = {"step": 9, "title": "创新方案", "status": "current", "saved": True, "data": step_result}

    logger.info("node_end", step="solution", has_result=bool(step_result))
    return {
        "current_step": "done",
        "step_results": {**state["step_results"], "solution": step_result} if step_result else state["step_results"],
        "card_data": card_data,
        "messages": state["messages"] + [AIMessage(content=response.content)],
    }
```

- [ ] **Step 2: 验证所有 Node 函数可导入**

```bash
cd /Users/chenyw/PROJECT/Xagent/backend
source venv/bin/activate
python3 -c "
from ariz_nodes import (
    step1_problem_node, step2_components_node, step3_contacts_node,
    step4_function_node, step5_structure_node, step6_summary_node,
    step7_causal_node, step8_keypoint_node, step9_solution_node,
)
print('9 个 Node 函数全部导入成功 ✓')
for fn in [step1_problem_node, step2_components_node, step3_contacts_node,
           step4_function_node, step5_structure_node, step6_summary_node,
           step7_causal_node, step8_keypoint_node, step9_solution_node]:
    assert callable(fn)
    print(f'  {fn.__name__} ✓')
"
```

Expected: 9 个函数全部导入成功。

- [ ] **Step 3: Commit**

```bash
cd /Users/chenyw/PROJECT/Xagent
git add backend/ariz_nodes.py
git commit -m "feat: add ARIZ step 4-9 LangGraph nodes"
```

---

### Task 5: 创建 LangGraph StateGraph

**Files:**
- Create: `backend/ariz_graph.py`
- Create: `backend/tests/test_ariz_graph.py`

- [ ] **Step 1: 创建 ariz_graph.py**

```python
"""ARIZ 流程图 — LangGraph StateGraph 定义"""
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from ariz_state import ArizState
from ariz_nodes import (
    step1_problem_node,
    step2_components_node,
    step3_contacts_node,
    step4_function_node,
    step5_structure_node,
    step6_summary_node,
    step7_causal_node,
    step8_keypoint_node,
    step9_solution_node,
)

import structlog
logger = structlog.get_logger()


def route_after_summary(state: ArizState) -> str:
    """Step 6 后的条件路由：问题少 → 跳过因果链，直接到关键问题"""
    problems = state["step_results"].get("summary", {}).get("problems", {})
    total = 0
    for v in problems.values():
        if isinstance(v, list):
            total += len(v)
        elif isinstance(v, dict):
            total += len(v)

    logger.info("route_after_summary", problem_count=total)
    if total <= 3:
        return "keypoint"
    return "causal"


def build_ariz_graph(checkpointer=None):
    """构建 ARIZ 流程图

    Args:
        checkpointer: LangGraph Checkpoint 实例（可选）

    Returns:
        编译好的 LangGraph 图
    """
    graph = StateGraph(ArizState)

    # 添加 9 个节点
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
        {"causal": "causal", "keypoint": "keypoint"},
    )

    graph.add_edge("causal", "keypoint")
    graph.add_edge("keypoint", "solution")
    graph.add_edge("solution", END)

    # 编译图
    compile_kwargs = {}
    if checkpointer:
        compile_kwargs["checkpointer"] = checkpointer

    compiled = graph.compile(**compile_kwargs)
    logger.info("ariz_graph_built", nodes=9)
    return compiled


# 全局图实例（延迟初始化）
_ariz_graph = None


def get_ariz_graph(checkpointer=None):
    """获取 ARIZ 流程图实例"""
    global _ariz_graph
    if _ariz_graph is None:
        _ariz_graph = build_ariz_graph(checkpointer)
    return _ariz_graph
```

- [ ] **Step 2: 创建 test_ariz_graph.py**

```python
"""LangGraph ARIZ 流程图测试"""
import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ariz_graph import build_ariz_graph, route_after_summary
from ariz_state import create_initial_state


def test_build_ariz_graph():
    """验证图构建成功"""
    graph = build_ariz_graph()
    assert graph is not None


def test_graph_has_all_nodes():
    """验证图包含所有 9 个节点"""
    graph = build_ariz_graph()
    node_names = list(graph.nodes)
    expected = ["problem", "components", "contacts", "function",
                "structure", "summary", "causal", "keypoint", "solution"]
    for name in expected:
        assert name in node_names, f"缺少节点: {name}"


def test_route_after_summary_few_problems():
    """验证问题少时跳过因果链"""
    state = create_initial_state()
    state["step_results"] = {
        "summary": {"problems": {"insufficient": ["问题1", "问题2"]}}
    }
    result = route_after_summary(state)
    assert result == "keypoint"


def test_route_after_summary_many_problems():
    """验证问题多时走因果链"""
    state = create_initial_state()
    state["step_results"] = {
        "summary": {"problems": {
            "insufficient": ["问题1", "问题2"],
            "harmful": ["问题3", "问题4"],
        }}
    }
    result = route_after_summary(state)
    assert result == "causal"
```

- [ ] **Step 3: 运行测试**

```bash
cd /Users/chenyw/PROJECT/Xagent/backend
source venv/bin/activate
python -m pytest tests/test_ariz_graph.py -v
```

Expected: 4 tests PASSED。

- [ ] **Step 4: Commit**

```bash
cd /Users/chenyw/PROJECT/Xagent
git add backend/ariz_graph.py backend/tests/test_ariz_graph.py
git commit -m "feat: add LangGraph StateGraph for ARIZ flow"
```

---

### Task 6: Flask 路由适配

**Files:**
- Modify: `backend/app.py`

- [ ] **Step 1: 在 app.py 顶部新增导入**

在 `app.py` 的 import 区域追加：

```python
from ariz_graph import get_ariz_graph, build_ariz_graph
from ariz_state import create_initial_state
from ariz_tools import parse_tool_calls
import asyncio
```

- [ ] **Step 2: 修改 chat() 路由支持新引擎**

在 `app.py` 的 `chat()` 函数中，将 LLM 调用逻辑替换为走 LangGraph 引擎。保留旧代码作为 fallback（用环境变量切换）。

```python
@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.json
    messages = data.get("messages", [])
    conv_id = data.get("conversation_id")

    logger.info("chat_received", message_count=len(messages), conversation_id=conv_id)

    if conv_id and messages:
        _save_user_message(conv_id, messages)

    # 判断使用新引擎还是旧引擎
    use_langgraph = os.getenv("USE_LANGGRAPH", "false").lower() == "true"

    if use_langgraph:
        return _chat_with_langgraph(data, conv_id, messages)
    else:
        return _chat_legacy(data, conv_id, messages)


def _chat_with_langgraph(data, conv_id, messages):
    """使用 LangGraph 引擎处理聊天"""
    graph = get_ariz_graph()

    def generate():
        try:
            # 构建初始状态
            state = create_initial_state()
            state["messages"] = messages

            # 使用同步方式运行图
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                result = loop.run_until_complete(
                    graph.ainvoke(state, config={"configurable": {"thread_id": conv_id or "default"}})
                )
            finally:
                loop.close()

            # 输出结果
            card_data = result.get("card_data", {})
            if card_data:
                tool_text = f"\n\n**调用工具: ariz_step{card_data['step']}**\n```json\n{json.dumps(card_data['data'], ensure_ascii=False, indent=2)}\n```\n"
                yield f'0:{json.dumps(tool_text)}\n'

            # 输出 LLM 回复
            if result.get("messages"):
                last_msg = result["messages"][-1]
                if hasattr(last_msg, "content") and last_msg.content:
                    yield f'0:{json.dumps(last_msg.content)}\n'

            # 保存助手消息
            full_response = ""
            if result.get("messages"):
                last_msg = result["messages"][-1]
                if hasattr(last_msg, "content"):
                    full_response = last_msg.content
            _save_assistant_message(conv_id, full_response)

        except Exception as e:
            logger.error("langgraph_error", error=str(e))
            error_msg = f"\n\n⚠️ AI 服务暂时不可用，请稍后重试。"
            yield f'0:{json.dumps(error_msg)}\n'

    return Response(generate(), mimetype="text/plain; charset=utf-8",
                    headers={"X-Vercel-AI-Data-Stream": "v1"})


def _chat_legacy(data, conv_id, messages):
    """旧引擎处理聊天（保持原有逻辑不变）"""
    # 原有的 chat() 函数逻辑，完整保留
    def generate():
        conv_id_for_flow = conv_id or "default"
        state = get_session_state(conv_id_for_flow)
        current_step = state["current_step"]

        system_prompt = build_system_prompt(current_step, state)
        tools = get_tools_for_step(current_step)

        tool_calls = {}
        full_response = ""

        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "system", "content": system_prompt}] + messages,
                tools=tools if tools else None,
                stream=True,
                timeout=120,
            )

            stream_start = time.time()
            last_chunk_time = time.time()
            STREAM_TIMEOUT = 300
            CHUNK_TIMEOUT = 30

            for chunk in response:
                now = time.time()
                if now - stream_start > STREAM_TIMEOUT:
                    break
                if now - last_chunk_time > CHUNK_TIMEOUT:
                    break
                last_chunk_time = now

                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta

                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        tc_index = tc.index
                        if tc_index not in tool_calls:
                            tool_calls[tc_index] = {"id": tc.id, "name": "", "arguments": ""}
                        if tc.function:
                            if tc.function.name:
                                tool_calls[tc_index]["name"] = tc.function.name
                            if tc.function.arguments:
                                tool_calls[tc_index]["arguments"] += tc.function.arguments

                if delta.content:
                    full_response += delta.content
                    yield f'0:{json.dumps(delta.content)}\n'

        except Exception as e:
            logger.error("llm_error", error=str(e), step=current_step)
            error_msg = f"\n\n⚠️ AI 服务暂时不可用，请稍后重试。"
            full_response += error_msg
            yield f'0:{json.dumps(error_msg)}\n'
            _save_assistant_message(conv_id, full_response)
            return

        for tc_info in tool_calls.values():
            func_name = tc_info["name"]
            if not func_name:
                continue
            try:
                args = json.loads(tc_info["arguments"]) if tc_info["arguments"] else {}
            except json.JSONDecodeError:
                args = {}
            result = _execute_tool(func_name, args, conv_id_for_flow)
            tool_text = f"\n\n**调用工具: {func_name}**\n```json\n{json.dumps(result, ensure_ascii=False, indent=2)}\n```\n"
            full_response += tool_text
            yield f'0:{json.dumps(tool_text)}\n'

        _save_assistant_message(conv_id, full_response)

    return Response(generate(), mimetype="text/plain; charset=utf-8",
                    headers={"X-Vercel-AI-Data-Stream": "v1"})
```

- [ ] **Step 3: 修改 ariz_status 接口**

```python
@app.route("/api/ariz/status/<conv_id>", methods=["GET"])
def ariz_status(conv_id):
    use_langgraph = os.getenv("USE_LANGGRAPH", "false").lower() == "true"
    if use_langgraph:
        try:
            graph = get_ariz_graph()
            config = {"configurable": {"thread_id": conv_id}}
            snapshot = graph.get_state(config)
            return jsonify(snapshot.values if snapshot else {"error": "no state"})
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    else:
        state = get_session_state(conv_id)
        return jsonify(state)
```

- [ ] **Step 4: 验证 Flask 启动**

```bash
cd /Users/chenyw/PROJECT/Xagent/backend
source venv/bin/activate
# 旧引擎模式启动
USE_LANGGRAPH=false timeout 5 python app.py 2>&1 || true
```

Expected: Flask 正常启动，无 import 错误。

- [ ] **Step 5: Commit**

```bash
cd /Users/chenyw/PROJECT/Xagent
git add backend/app.py
git commit -m "feat: add LangGraph engine with legacy fallback"
```

---

### Task 7: 端到端验证 — LangGraph 引擎

**Files:**
- None（纯验证）

- [ ] **Step 1: 启动 Flask（旧引擎模式）**

```bash
cd /Users/chenyw/PROJECT/Xagent/backend
source venv/bin/activate
USE_LANGGRAPH=false python app.py &
sleep 3
```

- [ ] **Step 2: 测试旧引擎正常工作**

```bash
curl -s http://localhost:8000/api/conversations | python3 -m json.tool
```

Expected: 返回对话列表 JSON，无报错。

- [ ] **Step 3: 启动 Flask（新引擎模式）**

```bash
# 停止旧进程
kill %1 2>/dev/null

cd /Users/chenyw/PROJECT/Xagent/backend
source venv/bin/activate
USE_LANGGRAPH=true python app.py &
sleep 3
```

- [ ] **Step 4: 测试新引擎 Step 1**

```bash
# 创建对话
CONV_ID=$(curl -s -X POST http://localhost:8000/api/conversations | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "对话 ID: $CONV_ID"

# 发送消息触发 Step 1
curl -s -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d "{\"conversation_id\": \"$CONV_ID\", \"messages\": [{\"role\": \"user\", \"content\": \"电池包在低温环境下续航衰减严重\"}]}" \
  2>&1 | head -20
```

Expected: 返回 SSE 流式响应，包含 ARIZ Step 1 分析内容。

- [ ] **Step 5: 检查 ARIZ 状态**

```bash
curl -s http://localhost:8000/api/ariz/status/$CONV_ID | python3 -m json.tool
```

Expected: 返回 ARIZ 状态 JSON，包含 step_results。

- [ ] **Step 6: 清理**

```bash
kill %1 2>/dev/null
```

- [ ] **Step 7: Commit（如果需要修复）**

```bash
cd /Users/chenyw/PROJECT/Xagent
git add -A
git commit -m "test: verify LangGraph engine end-to-end"
```
