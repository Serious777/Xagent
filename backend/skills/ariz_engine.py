"""ARIZ 流程引擎 — 总控调度"""
import structlog

logger = structlog.get_logger()

# ARIZ 流程步骤定义
ARIZ_STEPS = [
    ("problem",     "问题识别",       "ariz_step1_problem"),
    ("components",  "系统组件分析",   "ariz_step2_components"),
    ("contacts",    "接触关系分析",   "ariz_step3_contacts"),
    ("function",    "功能建模",       "ariz_step4_function"),
    ("structure",   "系统结构分析",   "ariz_step5_structure"),
    ("summary",     "功能建模问题总结", "ariz_step6_summary"),
    ("causal",      "因果链分析",     "ariz_step7_causal"),
    ("keypoint",    "关键问题/切入点", "ariz_step8_keypoint"),
    ("solution",    "生成创新方案",   "ariz_step9_solution"),
]

SKILL = {
    "description": "ARIZ 流程引擎：管理9步创新分析流程的调度与状态控制",
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["start", "next", "goto", "status", "report"],
                "description": (
                    "start=开始ARIZ流程, next=进入下一步, "
                    "goto=跳转到指定步骤, status=查看当前状态, "
                    "report=生成完整报告"
                ),
            },
            "step": {
                "type": "string",
                "description": "goto 时指定目标步骤名称（如 problem, components 等）",
            },
            "context": {
                "type": "string",
                "description": "用户输入的问题描述或补充信息",
            },
        },
        "required": ["action"],
    },
    "func": None,
}


def _get_step_index(step_name: str) -> int:
    """获取步骤索引，不存在返回 -1"""
    for i, (name, _, _) in enumerate(ARIZ_STEPS):
        if name == step_name:
            return i
    return -1


def _format_steps_status(current_index: int) -> str:
    """格式化步骤状态"""
    lines = ["ARIZ 流程状态："]
    for i, (name, label, _) in enumerate(ARIZ_STEPS):
        if i < current_index:
            lines.append(f"  ✅ {i+1}. {label}")
        elif i == current_index:
            lines.append(f"  👉 {i+1}. {label}（当前）")
        else:
            lines.append(f"  ⬜ {i+1}. {label}")
    return "\n".join(lines)


def ariz_engine(action: str, step: str = "", context: str = "") -> dict:
    """
    ARIZ 流程引擎入口。

    注意：当前版本不维护持久状态，状态通过对话上下文传递。
    返回的 JSON 中包含 _next_step 和 _prompt 告诉引擎下一步做什么。
    """
    logger.info("ariz_engine_action", action=action, step=step)

    if action == "status":
        return {
            "status": "ready",
            "steps": [(name, label) for name, label, _ in ARIZ_STEPS],
            "message": "请提供初始问题描述，开始 ARIZ 分析流程。",
        }

    elif action == "start":
        return {
            "_next_step": "problem",
            "_prompt": "请描述你要分析的初始问题（现象、对象、约束、期望目标）。",
            "message": "ARIZ 流程已启动，进入第1步：问题识别。",
        }

    elif action == "next":
        # 由引擎判断下一步（这里简化处理，实际由对话流程控制）
        return {
            "message": "请确认当前步骤结果，确认后进入下一步。",
        }

    elif action == "goto":
        idx = _get_step_index(step)
        if idx < 0:
            return {"error": f"未知步骤: {step}，可用步骤: {[s[0] for s in ARIZ_STEPS]}"}
        return {
            "_next_step": step,
            "message": f"跳转到第{idx+1}步：{ARIZ_STEPS[idx][1]}",
        }

    elif action == "report":
        return {
            "message": "请提供各步骤的分析结果，我将生成完整报告。",
        }

    else:
        return {"error": f"未知操作: {action}"}


SKILL["func"] = ariz_engine
