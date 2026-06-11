"""ARIZ Step 9: 生成创新方案"""
import structlog
logger = structlog.get_logger()

SKILL = {
    "description": "ARIZ第9步：基于矛盾和发明原理，生成具体创新方案",
    "parameters": {
        "type": "object",
        "properties": {
            "keypoint_result": {
                "type": "string",
                "description": "第8步关键问题定义结果",
            },
            "context": {
                "type": "string",
                "description": "前面各步的上下文摘要（组件/接触/功能/结构）",
            },
            "supplement": {
                "type": "string",
                "description": "用户对方案的反馈/补充约束",
            },
        },
        "required": ["keypoint_result"],
    },
    "func": None,
}

def ariz_step9_solution(keypoint_result: str, context: str = "", supplement: str = "") -> dict:
    logger.info("ariz_step9")
    return {
        "step": "solution",
        "step_name": "生成创新方案",
        "instruction": (
            "基于矛盾定义，生成方案卡片：\n"
            "每个方案包含：\n"
            "1. title — 方案名称\n"
            "2. principle — 应用的发明原理\n"
            "3. description — 具体描述\n"
            "4. pros / cons — 优缺点\n"
            "5. feasibility — 可行性评估\n"
            "6. estimated_effect — 预期效果"
        ),
        "example_output": {
            "solutions": [
                {
                    "title": "相变材料辅助散热",
                    "principle": "参数变化（#35）",
                    "description": "在电芯与冷却板之间嵌入PCM层，利用相变潜热吸收峰值热量",
                    "pros": ["不增加泵功耗", "温度均匀性好"],
                    "cons": ["PCM成本较高", "长期稳定性待验证"],
                    "feasibility": "medium",
                    "estimated_effect": "峰值温度降低5-8°C",
                }
            ]
        },
        "user_input": keypoint_result[:100],
        "supplement": supplement,
    }

SKILL["func"] = ariz_step9_solution
