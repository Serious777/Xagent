"""ARIZ 流程图 — LangGraph StateGraph 定义"""
import structlog
from langgraph.graph import StateGraph, END

from ariz_state import ArizState, route_after_summary
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

logger = structlog.get_logger()


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
