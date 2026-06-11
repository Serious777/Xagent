"""ARIZ Step 4: 功能建模"""
import structlog
logger = structlog.get_logger()

SKILL = {
    "description": "ARIZ第4步：建立系统功能模型，标注功能类型（有用/不足/过度/有害/缺失）",
    "parameters": {
        "type": "object",
        "properties": {
            "components_result": {
                "type": "string",
                "description": "第2步组件结果",
            },
            "contacts_result": {
                "type": "string",
                "description": "第3步接触关系结果",
            },
            "supplement": {
                "type": "string",
                "description": "用户对功能模型的补充/修正",
            },
        },
        "required": ["components_result", "contacts_result"],
    },
    "func": None,
}

def ariz_step4_function(components_result: str, contacts_result: str, supplement: str = "") -> dict:
    logger.info("ariz_step4")
    return {
        "step": "function",
        "step_name": "功能建模",
        "instruction": (
            "基于组件和接触关系，建立功能模型：\n"
            "功能类型：useful(有用) / insufficient(不足) / excessive(过度) / harmful(有害) / missing(缺失)\n"
            "每个功能标注：source → function → target, type, description"
        ),
        "example_output": {
            "functions": [
                {"source": "电芯模组", "target": "环境", "function": "产生热量", "type": "useful", "description": "电芯工作时产生焦耳热"},
                {"source": "冷却板", "target": "电芯模组", "function": "散热", "type": "insufficient", "description": "液冷散热能力不足"},
            ]
        },
        "user_input": f"components: {components_result[:100]}..., contacts: {contacts_result[:100]}...",
        "supplement": supplement,
    }

SKILL["func"] = ariz_step4_function
