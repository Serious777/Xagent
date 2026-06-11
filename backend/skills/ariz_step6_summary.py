"""ARIZ Step 6: 功能建模问题总结"""
import structlog
logger = structlog.get_logger()

SKILL = {
    "description": "ARIZ第6步：从功能模型中提取并分类所有问题（不足/有害/过度/缺失）",
    "parameters": {
        "type": "object",
        "properties": {
            "function_result": {
                "type": "string",
                "description": "第4步功能建模结果",
            },
            "structure_result": {
                "type": "string",
                "description": "第5步结构分析结果",
            },
            "supplement": {
                "type": "string",
                "description": "用户对问题清单的确认/补充",
            },
        },
        "required": ["function_result", "structure_result"],
    },
    "func": None,
}

def ariz_step6_summary(function_result: str, structure_result: str, supplement: str = "") -> dict:
    logger.info("ariz_step6")
    return {
        "step": "summary",
        "step_name": "功能建模问题总结",
        "instruction": (
            "从功能模型中提取问题并分类：\n"
            "1. insufficient_functions — 不足功能\n"
            "2. harmful_functions — 有害功能\n"
            "3. excessive_functions — 过度功能\n"
            "4. missing_functions — 缺失功能\n"
            "5. 给出优先级建议"
        ),
        "example_output": {
            "insufficient_functions": ["冷却板散热能力不足", "导热垫导热系数偏低"],
            "harmful_functions": ["冷却液腐蚀铝制冷却板"],
            "excessive_functions": ["电芯快充时产热过多"],
            "missing_functions": [],
            "total_count": 3,
            "priority_hint": "建议优先解决：散热不足、导热系数偏低",
        },
        "user_input": f"function: {function_result[:100]}..., structure: {structure_result[:100]}...",
        "supplement": supplement,
    }

SKILL["func"] = ariz_step6_summary
