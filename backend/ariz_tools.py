"""ARIZ 工具定义 — 供 LangGraph Node 使用"""


def make_step_tool(step_num: int, name: str, label: str, fields: list) -> dict:
    """生成 ARIZ 步骤工具定义（OpenAI function calling 格式）"""
    props = {}
    required = []
    for f in fields:
        props[f["name"]] = {
            "type": f.get("type", "string"),
            "description": f.get("desc", ""),
        }
        if f.get("required"):
            required.append(f["name"])
    return {
        "type": "function",
        "function": {
            "name": f"ariz_step{step_num}_{name}",
            "description": f"ARIZ第{step_num}步：用户确认后调用此工具保存{label}结果",
            "parameters": {
                "type": "object",
                "properties": props,
                "required": required,
            },
        },
    }


# Step 1: 问题识别
STEP1_TOOL = {
    "type": "function",
    "function": {
        "name": "ariz_step1_problem",
        "description": "ARIZ第1步：用户确认后调用此工具保存问题识别结果",
        "parameters": {
            "type": "object",
            "properties": {
                "problem_object": {"type": "string", "description": "具体子系统名称"},
                "system_keywords": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "数据库检索用的系统级关键词",
                },
                "phenomenon": {"type": "string", "description": "可观测可量化的现象"},
                "constraints": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "约束条件",
                },
                "goal": {"type": "string", "description": "期望目标"},
                "contradiction_hint": {"type": "string", "description": "初步矛盾方向"},
            },
            "required": ["problem_object", "system_keywords", "phenomenon"],
        },
    },
}

# Step 2: 系统组件分析
STEP2_TOOL = {
    "type": "function",
    "function": {
        "name": "ariz_step2_components",
        "description": "ARIZ第2步：用户确认后调用此工具保存组件分析结果",
        "parameters": {
            "type": "object",
            "properties": {
                "supersystem": {"type": "string", "description": "超系统描述"},
                "supersystem_components": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "functions": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "该组件对本系统产生的功能/影响",
                            },
                        },
                        "required": ["name"],
                    },
                    "description": "超系统中与本系统有交互的外部组件",
                },
                "system_name": {"type": "string", "description": "系统名称"},
                "user_added": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "用户补充的、数据库中没有的组件列表",
                },
            },
            "required": ["supersystem", "system_name"],
        },
    },
}

# Step 3-9: 使用 make_step_tool 生成
STEP3_TOOL = make_step_tool(3, "contacts", "接触关系分析", [
    {"name": "contacts", "type": "array", "desc": "组件间接触关系列表", "required": True},
])
STEP4_TOOL = make_step_tool(4, "function", "功能建模", [
    {"name": "functions", "type": "array", "desc": "功能模型列表", "required": True},
])
STEP5_TOOL = make_step_tool(5, "structure", "系统结构分析", [
    {"name": "structure_info", "type": "object", "desc": "结构参数", "required": True},
])
STEP6_TOOL = make_step_tool(6, "summary", "问题总结", [
    {"name": "problems", "type": "object", "desc": "分类问题清单", "required": True},
])
STEP7_TOOL = make_step_tool(7, "causal", "因果链分析", [
    {"name": "causal_chains", "type": "array", "desc": "因果链列表", "required": True},
])
STEP8_TOOL = make_step_tool(8, "keypoint", "关键问题定义", [
    {"name": "contradictions", "type": "object", "desc": "矛盾定义和IFR", "required": True},
])
STEP9_TOOL = make_step_tool(9, "solution", "方案生成", [
    {"name": "solutions", "type": "array", "desc": "创新方案列表", "required": True},
])

# 所有工具列表
ALL_STEP_TOOLS = [
    STEP1_TOOL, STEP2_TOOL, STEP3_TOOL, STEP4_TOOL,
    STEP5_TOOL, STEP6_TOOL, STEP7_TOOL, STEP8_TOOL, STEP9_TOOL,
]

# 工具名 → 步骤编号映射
TOOL_STEP_MAP = {
    "ariz_step1_problem": 1,
    "ariz_step2_components": 2,
    "ariz_step3_contacts": 3,
    "ariz_step4_function": 4,
    "ariz_step5_structure": 5,
    "ariz_step6_summary": 6,
    "ariz_step7_causal": 7,
    "ariz_step8_keypoint": 8,
    "ariz_step9_solution": 9,
}

# 步骤名 → 工具映射
STEP_TOOL_MAP = {
    "problem": STEP1_TOOL,
    "components": STEP2_TOOL,
    "contacts": STEP3_TOOL,
    "function": STEP4_TOOL,
    "structure": STEP5_TOOL,
    "summary": STEP6_TOOL,
    "causal": STEP7_TOOL,
    "keypoint": STEP8_TOOL,
    "solution": STEP9_TOOL,
}


def get_tool_for_step(step_name: str) -> dict | None:
    """获取指定步骤对应的工具定义"""
    return STEP_TOOL_MAP.get(step_name)


def parse_tool_calls(response) -> dict:
    """从 LangChain response 中解析工具调用结果"""
    result = {}
    if hasattr(response, "tool_calls") and response.tool_calls:
        for tc in response.tool_calls:
            result[tc["name"]] = tc["args"]
    return result
