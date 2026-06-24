"""ARIZ 流程状态定义 — LangGraph StateGraph 专用"""
from typing import TypedDict, Optional

import structlog

logger = structlog.get_logger()


class ArizState(TypedDict):
    """ARIZ 流程的全局状态"""
    current_step: str           # 当前步骤名（problem/components/...）
    step_results: dict          # 各步分析结果 {step_name: result_dict}
    messages: list              # 对话历史（LangChain message 格式）
    card_data: dict             # 当前步骤的卡片数据（供前端渲染）
    error: Optional[str]        # 错误信息（如果有）
    thread_id: str              # 会话 ID


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
        "card_data": {},
        "error": None,
        "thread_id": "default",
    }


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
