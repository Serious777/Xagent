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
    step_idx = get_step_index(step_name) + 1
    step_prompt = load_prompt(f"step{step_idx}_{step_name}")

    messages = [
        SystemMessage(content=system_prompt),
        SystemMessage(content=step_prompt),
    ]

    # 注入历史上下文
    if state.get("step_results"):
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
    """查询组件知识库"""
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

    response = await llm.ainvoke(messages, tools=[tool] if tool else None)
    tool_results = parse_tool_calls(response)

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
    # 只有保存了结果才推进到下一步
    new_step = "components" if step_result else "problem"
    return {
        "current_step": new_step,
        "step_results": {**state["step_results"], "problem": step_result} if step_result else state["step_results"],
        "card_data": card_data,
        "messages": state["messages"] + [AIMessage(content=response.content)],
    }


# ============ Step 2 Node ============

async def step2_components_node(state: ArizState) -> dict:
    """Step 2: 系统组件分析"""
    logger.info("node_start", step="components")
    llm = get_llm()
    tool = get_tool_for_step("components")
    messages = build_messages_for_step(state, "components")

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
    new_step = "contacts" if step_result else "components"
    return {
        "current_step": new_step,
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

    response = await llm.ainvoke(messages, tools=[tool] if tool else None)
    tool_results = parse_tool_calls(response)

    step_result = {}
    card_data = {}
    if "ariz_step3_contacts" in tool_results:
        contacts = tool_results["ariz_step3_contacts"].get("contacts", [])
        step_result = {"contacts": contacts}

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
    new_step = "function" if step_result else "contacts"
    return {
        "current_step": new_step,
        "step_results": {**state["step_results"], "contacts": step_result} if step_result else state["step_results"],
        "card_data": card_data,
        "messages": state["messages"] + [AIMessage(content=response.content)],
    }


# ============ Step 4 Node ============

async def step4_function_node(state: ArizState) -> dict:
    """Step 4: 功能建模"""
    logger.info("node_start", step="function")
    llm = get_llm()
    tool = get_tool_for_step("function")
    messages = build_messages_for_step(state, "function")

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
    new_step = "structure" if step_result else "function"
    return {
        "current_step": new_step,
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

    response = await llm.ainvoke(messages, tools=[tool] if tool else None)
    tool_results = parse_tool_calls(response)

    step_result = {}
    card_data = {}
    if "ariz_step5_structure" in tool_results:
        step_result = tool_results["ariz_step5_structure"]
        card_data = {"step": 5, "title": "系统结构分析", "status": "current", "saved": True, "data": step_result}

    logger.info("node_end", step="structure", has_result=bool(step_result))
    new_step = "summary" if step_result else "structure"
    return {
        "current_step": new_step,
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

    response = await llm.ainvoke(messages, tools=[tool] if tool else None)
    tool_results = parse_tool_calls(response)

    step_result = {}
    card_data = {}
    if "ariz_step6_summary" in tool_results:
        step_result = tool_results["ariz_step6_summary"]
        card_data = {"step": 6, "title": "问题总结", "status": "current", "saved": True, "data": step_result}

    logger.info("node_end", step="summary", has_result=bool(step_result))
    new_step = "causal" if step_result else "summary"
    return {
        "current_step": new_step,
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

    response = await llm.ainvoke(messages, tools=[tool] if tool else None)
    tool_results = parse_tool_calls(response)

    step_result = {}
    card_data = {}
    if "ariz_step7_causal" in tool_results:
        step_result = tool_results["ariz_step7_causal"]
        card_data = {"step": 7, "title": "因果链分析", "status": "current", "saved": True, "data": step_result}

    logger.info("node_end", step="causal", has_result=bool(step_result))
    new_step = "keypoint" if step_result else "causal"
    return {
        "current_step": new_step,
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

    response = await llm.ainvoke(messages, tools=[tool] if tool else None)
    tool_results = parse_tool_calls(response)

    step_result = {}
    card_data = {}
    if "ariz_step8_keypoint" in tool_results:
        step_result = tool_results["ariz_step8_keypoint"]
        card_data = {"step": 8, "title": "关键问题", "status": "current", "saved": True, "data": step_result}

    logger.info("node_end", step="keypoint", has_result=bool(step_result))
    new_step = "solution" if step_result else "keypoint"
    return {
        "current_step": new_step,
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

    response = await llm.ainvoke(messages, tools=[tool] if tool else None)
    tool_results = parse_tool_calls(response)

    step_result = {}
    card_data = {}
    if "ariz_step9_solution" in tool_results:
        step_result = tool_results["ariz_step9_solution"]
        card_data = {"step": 9, "title": "创新方案", "status": "current", "saved": True, "data": step_result}

    logger.info("node_end", step="solution", has_result=bool(step_result))
    new_step = "done" if step_result else "solution"
    return {
        "current_step": new_step,
        "step_results": {**state["step_results"], "solution": step_result} if step_result else state["step_results"],
        "card_data": card_data,
        "messages": state["messages"] + [AIMessage(content=response.content)],
    }
