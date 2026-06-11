"""ARIZ Step 5: 系统结构分析"""
import structlog
logger = structlog.get_logger()

SKILL = {
    "description": "ARIZ第5步：分析系统空间结构，识别布局约束和结构瓶颈",
    "parameters": {
        "type": "object",
        "properties": {
            "components_result": {
                "type": "string",
                "description": "第2步组件结果",
            },
            "user_supplement": {
                "type": "string",
                "description": "用户提供的结构参数（尺寸/排列/布局等）",
            },
        },
        "required": ["components_result", "user_supplement"],
    },
    "func": None,
}

def ariz_step5_structure(components_result: str, user_supplement: str = "") -> dict:
    logger.info("ariz_step5")
    return {
        "step": "structure",
        "step_name": "系统结构分析",
        "instruction": (
            "分析系统空间结构：\n"
            "1. dimensions — 外形尺寸\n"
            "2. layout — 布局方式\n"
            "3. layout_constraints — 布局约束\n"
            "4. structural_bottlenecks — 结构瓶颈\n"
            "需要向用户追问：尺寸、排列方式、冷却位置、流道走向等"
        ),
        "example_output": {
            "dimensions": "4300x1500x120mm",
            "layout": "96S4P, 底置冷却板, 蛇形流道",
            "layout_constraints": ["底部空间受底盘离地间隙限制", "电芯间距受膨胀预留限制"],
            "structural_bottlenecks": ["蛇形流道造成末端电芯温度偏高"],
        },
        "user_input": components_result[:100],
        "supplement": user_supplement,
    }

SKILL["func"] = ariz_step5_structure
