"""ARIZ Step 1: 问题识别"""
import structlog

logger = structlog.get_logger()

SKILL = {
    "description": "ARIZ第1步：识别具体系统、明确问题现象、聚焦具体矛盾",
    "parameters": {
        "type": "object",
        "properties": {
            "user_description": {
                "type": "string",
                "description": "用户对问题的自由文本描述",
            },
            "supplement": {
                "type": "string",
                "description": "用户对上一轮追问的补充回答",
            },
        },
        "required": ["user_description"],
    },
    "func": None,
}


def ariz_step1_problem(user_description: str, supplement: str = "") -> dict:
    """
    问题识别：三步聚焦法

    1. 识别具体系统 —— 问题发生在哪个子系统？
       不能是"电池有问题"，必须定位到：箱体？热管理？BMS？电芯模组？电气连接？
    2. 明确问题现象 —— 可观测、可量化的症状
       不能是"散热不好"，必须是"高倍率放电时电芯最高温度超45°C，温差>8°C"
    3. 聚焦具体矛盾 —— 提炼出技术矛盾或物理矛盾
       不能是"想解决温度问题"，必须是"提高散热效率 → 增加了重量/成本"

    输出中的 system_keywords 用于 Step 2 从数据库检索组件。
    """
    logger.info("ariz_step1", desc_length=len(user_description))

    return {
        "step": "problem",
        "step_name": "问题识别",
        "focus_areas": [
            {
                "name": "具体系统定位",
                "question": "问题发生在哪个子系统？",
                "examples": [
                    "热管理（冷却/加热/温度均匀性）",
                    "箱体结构（强度/轻量化/密封）",
                    "电芯模组（成组/固定/膨胀管理）",
                    "电气连接（高压/低压/EMC）",
                    "BMS（采样/均衡/热管理策略）",
                    "机械防护（碰撞/振动/防水）",
                ],
                "requirement": "必须具体到子系统级别，不能笼统说'电池PACK有问题'",
            },
            {
                "name": "问题现象明确",
                "question": "观测到的具体现象是什么？",
                "requirement": "必须是可观测、可量化的症状，包含：什么工况下、什么参数超标、超标多少",
                "bad_example": "散热不好",
                "good_example": "2C倍率连续放电30分钟后，电芯最高温度48°C，最低温度37°C，温差11°C",
            },
            {
                "name": "聚焦具体矛盾",
                "question": "核心矛盾是什么？（改善A → 恶化B）",
                "requirement": "提炼出一个或多个明确的技术矛盾，格式：提高/改善XX → 导致/恶化YY",
                "bad_example": "想降低温度",
                "good_example": "提高冷却液流速（散热↑） → 泵功耗增加 + 管路振动噪声增大",
            },
        ],
        "output_schema": {
            "problem_object": "具体子系统名称（如：方形铝壳电池PACK液冷热管理系统）",
            "system_keywords": [
                "用于数据库检索的关键词列表",
                "例如：['热管理', '冷却'] → 匹配到热管理系统及其所有组件",
                "Agent 从用户描述中提取 1-3 个关键词"
            ],
            "phenomenon": "可观测可量化的现象描述（工况+参数+超标量）",
            "constraints": ["约束条件列表（不能动的东西）"],
            "goal": "期望目标（量化）",
            "contradiction_hint": "初步矛盾方向（用户自述或Agent提炼）",
            "clarification_needed": ["需要追问的缺失信息"],
        },
        "example_output": {
            "problem_object": "方形铝壳电池PACK液冷热管理系统",
            "system_keywords": ["热管理", "冷却"],
            "phenomenon": "2C倍率连续放电30min后，电芯最高温度48°C，最低37°C，温差11°C，超过设计指标（≤40°C，温差≤5°C）",
            "constraints": ["不增加冷却系统重量", "不增加系统功耗", "成本增幅<5%", "不改变电芯选型"],
            "goal": "最高温度≤40°C，温差≤5°C",
            "contradiction_hint": "提高散热能力 → 增加重量/成本/功耗",
            "clarification_needed": [
                "环境温度范围？（低温是否也需要考虑）",
                "现有冷却方案是什么？（液冷/风冷/相变）",
                "是否已尝试过其他方案？效果如何？",
            ],
        },
        "user_input": user_description,
        "supplement": supplement,
    }


SKILL["func"] = ariz_step1_problem
