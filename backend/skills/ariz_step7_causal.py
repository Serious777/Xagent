"""ARIZ Step 7: 因果链分析"""
import structlog
logger = structlog.get_logger()

SKILL = {
    "description": "ARIZ第7步：从表层问题逐步追问根因，建立因果链",
    "parameters": {
        "type": "object",
        "properties": {
            "summary_result": {
                "type": "string",
                "description": "第6步问题总结结果",
            },
            "selected_problem": {
                "type": "string",
                "description": "用户选择要深入分析的问题",
            },
            "supplement": {
                "type": "string",
                "description": "用户对因果链的补充/修正",
            },
        },
        "required": ["summary_result"],
    },
    "func": None,
}

def ariz_step7_causal(summary_result: str, selected_problem: str = "", supplement: str = "") -> dict:
    logger.info("ariz_step7")
    return {
        "step": "causal",
        "step_name": "因果链分析",
        "instruction": (
            "对选中的问题建立因果链：\n"
            "1. 从表层问题开始，逐层追问'为什么'\n"
            "2. 识别系统级约束（不可改动的）\n"
            "3. 找到根本原因\n"
            "4. 识别潜在切入点（可行的改进方向）"
        ),
        "example_output": {
            "problem": "冷却板散热能力不足",
            "chain": [
                {"level": 1, "cause": "冷却液流速不够", "type": "direct"},
                {"level": 2, "cause": "水泵功率受限", "type": "intermediate"},
                {"level": 3, "cause": "系统功耗预算限制", "type": "root_cause"},
            ],
            "entry_points": [
                {"point": "流道设计优化", "feasibility": "high"},
                {"point": "导热材料升级", "feasibility": "medium"},
            ],
        },
        "user_input": summary_result[:100],
        "supplement": supplement,
    }

SKILL["func"] = ariz_step7_causal
