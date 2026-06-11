"""ARIZ Step 8: 关键问题/切入点定义"""
import structlog
logger = structlog.get_logger()

SKILL = {
    "description": "ARIZ第8步：定义技术矛盾、物理矛盾和理想最终状态（IFR）",
    "parameters": {
        "type": "object",
        "properties": {
            "causal_result": {
                "type": "string",
                "description": "第7步因果链分析结果",
            },
            "supplement": {
                "type": "string",
                "description": "用户对矛盾定义的确认/修正",
            },
        },
        "required": ["causal_result"],
    },
    "func": None,
}

def ariz_step8_keypoint(causal_result: str, supplement: str = "") -> dict:
    logger.info("ariz_step8")
    return {
        "step": "keypoint",
        "step_name": "关键问题/切入点",
        "instruction": (
            "基于因果链，定义核心矛盾：\n"
            "1. technical_contradictions — 技术矛盾列表（改善A → 恶化B）\n"
            "2. physical_contradictions — 物理矛盾列表（同一参数既要大又要小）\n"
            "3. ifr — 理想最终状态\n"
            "4. selected_focus — 建议优先解决的矛盾"
        ),
        "example_output": {
            "technical_contradictions": [
                {"improve": "散热效率", "worsen": "重量/成本"},
                {"improve": "流道尺寸缩小", "worsen": "流阻增加"},
            ],
            "physical_contradictions": [
                {"parameter": "冷却液流量", "want_large": "散热好", "want_small": "能耗低"},
            ],
            "ifr": "冷却系统自身不增加重量/体积/成本，却能完美散热",
            "selected_focus": "TC1: 散热效率 vs 重量/成本",
        },
        "user_input": causal_result[:100],
        "supplement": supplement,
    }

SKILL["func"] = ariz_step8_keypoint
