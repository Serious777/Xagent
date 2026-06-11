"""ARIZ Step 2: 系统组件分析"""
import json
import structlog

logger = structlog.get_logger()

SKILL = {
    "description": "ARIZ第2步：从数据库提取系统组件，Agent补充超系统分析，组成完整系统组件分析",
    "parameters": {
        "type": "object",
        "properties": {
            "problem_result": {
                "type": "string",
                "description": "第1步的问题识别结果（JSON）",
            },
            "supplement": {
                "type": "string",
                "description": "用户对组件列表的补充/修正",
            },
        },
        "required": ["problem_result"],
    },
    "func": None,
}


def ariz_step2_components(problem_result: str, supplement: str = "") -> dict:
    """
    系统组件分析：两步组合

    1. 数据库检索：根据 Step 1 输出的 system_keywords，从组件数据库中
       拉取该系统的稳定组件列表和功能描述。
    2. Agent 补充：Agent 基于用户问题中的环境信息，自行判断并补充超系统分析。

    输出 = 数据库组件 + Agent 超系统 + 用户补充
    """
    logger.info("ariz_step2")

    # 尝试解析 Step 1 结果获取关键词
    try:
        step1 = json.loads(problem_result) if isinstance(problem_result, str) else problem_result
        keywords = step1.get("system_keywords", [])
    except (json.JSONDecodeError, AttributeError):
        keywords = []

    return {
        "step": "components",
        "step_name": "系统组件分析",
        "data_source": "database + agent",
        "workflow": [
            {
                "phase": "database_lookup",
                "action": "根据 system_keywords 从数据库检索系统组件",
                "keywords": keywords,
                "note": "返回该系统下所有组件名称、功能描述、组件间关系",
            },
            {
                "phase": "agent_supersystem",
                "action": "Agent 根据用户问题自行分析超系统",
                "note": "超系统包括：工作环境（温度/振动/海拔）、整车接口、法规标准等",
            },
            {
                "phase": "user_supplement",
                "action": "向用户确认并收集补充组件",
                "note": "展示数据库组件 + 超系统，让用户确认或补充遗漏",
            },
        ],
        "output_schema": {
            "supersystem": "Agent 自行分析的超系统描述",
            "system_name": "从数据库匹配的系统名称",
            "database_components": "从数据库提取的组件列表（含功能描述）",
            "user_added_components": "用户补充的组件",
            "all_components": "合并后的完整组件列表",
        },
        "example_output": {
            "supersystem": "整车底盘环境（-30°C~55°C，振动0.5-3g，IP67防护等级）",
            "system_name": "热管理系统",
            "database_components": [
                {"name": "冷却板", "description": "液冷系统核心散热部件", "functions": ["散热", "均温"]},
                {"name": "冷却液", "description": "乙二醇水溶液", "functions": ["携带热量"]},
                {"name": "管路", "description": "连接冷却板和散热器", "functions": ["导通流路"]},
                {"name": "水泵", "description": "驱动冷却液循环", "functions": ["驱动循环"]},
                {"name": "接头", "description": "管路密封连接", "functions": ["密封连接"]},
                {"name": "导热垫", "description": "电芯与冷却板间的TIM", "functions": ["传导热量"]},
                {"name": "散热器", "description": "风冷/水冷换热", "functions": ["散热"]},
            ],
            "user_added_components": [],
            "all_components": [
                {"name": "冷却板", "source": "database"},
                {"name": "冷却液", "source": "database"},
                {"name": "管路", "source": "database"},
                {"name": "水泵", "source": "database"},
                {"name": "接头", "source": "database"},
                {"name": "导热垫", "source": "database"},
                {"name": "散热器", "source": "database"},
                {"name": "液冷板流道", "source": "user_added"},
            ],
        },
        "user_input": problem_result[:200] if len(problem_result) > 200 else problem_result,
        "supplement": supplement,
    }


SKILL["func"] = ariz_step2_components
