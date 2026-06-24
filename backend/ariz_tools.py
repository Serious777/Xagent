"""ARIZ 工具定义 — 供 LangGraph Node 使用"""


def make_step_tool(step_num: int, name: str, label: str, fields: list) -> dict:
    """生成 ARIZ 步骤工具定义（OpenAI function calling 格式）

    fields 格式: [{"name": "x", "type": "array", "desc": "...", "required": True, "items": {...}}]
    """
    props = {}
    required = []
    for f in fields:
        prop = {
            "type": f.get("type", "string"),
            "description": f.get("desc", ""),
        }
        if "items" in f:
            prop["items"] = f["items"]
        if "properties" in f:
            prop["properties"] = f["properties"]
        if f.get("required"):
            required.append(f["name"])
        props[f["name"]] = prop
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

# Step 3: 接触关系分析（手动定义 items schema）
STEP3_TOOL = {
    "type": "function",
    "function": {
        "name": "ariz_step3_contacts",
        "description": "ARIZ第3步：用户确认后调用此工具保存接触关系分析结果",
        "parameters": {
            "type": "object",
            "properties": {
                "contacts": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "component_a": {"type": "string", "description": "组件A名称"},
                            "component_b": {"type": "string", "description": "组件B名称"},
                            "contact_type": {"type": "string", "description": "接触类型：热传导/对流换热/机械固定/电气连接/待分析"},
                            "interface": {"type": "string", "description": "接触界面描述"},
                        },
                        "required": ["component_a", "component_b", "contact_type"],
                    },
                    "description": "组件间接触关系列表",
                },
            },
            "required": ["contacts"],
        },
    },
}

# Step 4: 功能建模（手动定义 items schema）
STEP4_TOOL = {
    "type": "function",
    "function": {
        "name": "ariz_step4_function",
        "description": "ARIZ第4步：用户确认后调用此工具保存功能建模结果",
        "parameters": {
            "type": "object",
            "properties": {
                "functions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "source": {"type": "string", "description": "功能作用者（组件名称）"},
                            "target": {"type": "string", "description": "功能作用对象（组件名称）"},
                            "function": {"type": "string", "description": "功能描述"},
                            "type": {"type": "string", "description": "功能类型：useful/insufficient/excessive/harmful"},
                        },
                        "required": ["source", "target", "function", "type"],
                    },
                    "description": "功能模型列表",
                },
            },
            "required": ["functions"],
        },
    },
}
# Step 5: 系统结构分析（基于 Step 4 功能模型，识别关键问题节点）
STEP5_TOOL = {
    "type": "function",
    "function": {
        "name": "ariz_step5_structure",
        "description": "ARIZ第5步：基于功能模型分析系统结构，识别关键问题节点",
        "parameters": {
            "type": "object",
            "properties": {
                "functions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "source": {"type": "string", "description": "功能作用者（组件名称）"},
                            "target": {"type": "string", "description": "功能作用对象（组件名称）"},
                            "function": {"type": "string", "description": "功能描述"},
                            "type": {"type": "string", "description": "功能类型：useful/insufficient/excessive/harmful"},
                        },
                        "required": ["source", "target", "function", "type"],
                    },
                    "description": "系统功能模型列表（复用 Step 4 数据）",
                },
                "key_problems": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "node": {"type": "string", "description": "问题组件名称"},
                            "problem": {"type": "string", "description": "问题描述"},
                            "severity": {"type": "string", "description": "严重程度：high/medium/low"},
                        },
                        "required": ["node", "problem", "severity"],
                    },
                    "description": "关键问题节点列表",
                },
            },
            "required": ["functions", "key_problems"],
        },
    },
}
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
