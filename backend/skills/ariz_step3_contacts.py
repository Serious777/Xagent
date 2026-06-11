"""ARIZ Step 3: 接触关系分析"""
import structlog
logger = structlog.get_logger()

SKILL = {
    "description": "ARIZ第3步：分析各组件间的接触/交互关系类型",
    "parameters": {
        "type": "object",
        "properties": {
            "components_result": {
                "type": "string",
                "description": "第2步的组件分析结果（JSON）",
            },
            "supplement": {
                "type": "string",
                "description": "用户对接触关系的补充/修正",
            },
        },
        "required": ["components_result"],
    },
    "func": None,
}

def ariz_step3_contacts(components_result: str, supplement: str = "") -> dict:
    logger.info("ariz_step3")
    return {
        "step": "contacts",
        "step_name": "接触关系分析",
        "instruction": (
            "分析组件间的接触关系：\n"
            "1. component_a / component_b — 接触的两个组件\n"
            "2. contact_type — 接触类型（热传导/对流/辐射/机械/电气/化学）\n"
            "3. interface — 界面描述\n"
            "4. confirmed — 是否经用户确认"
        ),
        "example_output": {
            "contacts": [
                {"component_a": "电芯模组", "component_b": "冷却板", "contact_type": "热传导", "interface": "导热垫", "confirmed": True},
                {"component_a": "冷却板", "component_b": "冷却液", "contact_type": "对流换热", "interface": "流道内壁面", "confirmed": True},
            ]
        },
        "user_input": components_result,
        "supplement": supplement,
    }

SKILL["func"] = ariz_step3_contacts
