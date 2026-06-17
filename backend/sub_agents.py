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
