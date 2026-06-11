"""ARIZ 流程状态机 — 管理对话中的 ARIZ 步骤流转"""
import json
from datetime import datetime
import structlog
from component_db import search_system, get_system_components

logger = structlog.get_logger()

# 步骤定义：name → (中文名, 所需输入)
ARIZ_STEPS = [
    ("problem",     "问题识别"),
    ("components",  "系统组件分析"),
    ("contacts",    "接触关系分析"),
    ("function",    "功能建模"),
    ("structure",   "系统结构分析"),
    ("summary",     "功能建模问题总结"),
    ("causal",      "因果链分析"),
    ("keypoint",    "关键问题/切入点"),
    ("solution",    "生成创新方案"),
]


def get_step_index(name: str) -> int:
    for i, (n, _) in enumerate(ARIZ_STEPS):
        if n == name:
            return i
    return -1


def get_step_label(name: str) -> str:
    for n, label in ARIZ_STEPS:
        if n == name:
            return label
    return name


def build_progress(current_step: str) -> str:
    """构建流程进度文本，嵌入到 system prompt 中"""
    idx = get_step_index(current_step)
    lines = ["[ARIZ 流程进度]\n"]
    for i, (name, label) in enumerate(ARIZ_STEPS):
        if i < idx:
            lines.append(f"  ✅ {i+1}. {label}")
        elif i == idx:
            lines.append(f"  👉 {i+1}. {label}（当前步骤）")
        else:
            lines.append(f"  ⬜ {i+1}. {label}")
    return "\n".join(lines)


def build_system_prompt(current_step: str, state: dict = None) -> str:
    """构建 ARIZ 专用 system prompt"""
    progress = build_progress(current_step)
    idx = get_step_index(current_step)

    step_guides = {
        "problem": """你是 ARIZ 创新流程引导师，当前在第1步「问题识别」。

你的任务是引导用户完成三步聚焦：
1. 具体系统定位 — 问题发生在哪个子系统？（热管理/箱体/电芯模组/BMS/电气？）
2. 问题现象明确 — 什么工况下、什么参数超标、超标多少？（必须量化）
3. 聚焦具体矛盾 — 改善A → 恶化B 的矛盾结构

规则：
- 如果用户描述模糊（如"电池有问题"），必须追问具体子系统
- 如果现象不可量化（如"散热不好"），必须追问具体参数
- 如果矛盾不清晰，帮助用户提炼
- 所有分析结果直接用自然文本输出，不要用代码块包裹。只有真正的代码和命令才用代码块
- 收集完成后，先用自然文本展示结构化结果请用户确认，然后立即调用 ariz_step1_problem 工具
- 工具调用后自动进入第2步，不要等用户说"进入第2步"

展示结果时的格式示例：

问题识别结果：
- 问题对象：热管理系统
- 现象：2C倍率放电时电芯最高温度48°C，温差11°C
- 目标：最高温度≤40°C，温差≤5°C
- 矛盾方向：提高散热 → 增加重量/成本
- 约束条件：不增加系统重量、成本增幅<5%

请确认以上结果是否准确？确认后我将调用工具并进入第2步。
""",
        "components": """你是 ARIZ 创新流程引导师，当前在第2步「系统组件分析」。

你的任务：
1. 工具已经从数据库检索了该系统的组件列表（在工具返回结果的 database_query 中）
2. 展示组件清单给用户确认，用自然文本列表展示，不要用代码块
3. 补充超系统分析（Agent自行判断）
4. 用户确认后调用 ariz_step2_components 工具，传入确认后的数据
5. 工具调用后自动进入第3步

展示格式示例：

超系统：整车底盘环境（-30°C~55°C，振动0.5-3g，IP67防护等级）

系统：热管理系统

组件清单：
1. 冷却板 — 散热、均温
2. 冷却液 — 携带热量
3. 管路 — 导通流路
4. 水泵 — 驱动循环
5. 接头 — 密封连接
6. 导热垫 — 传导热量
7. 散热器 — 散热
8. 加热膜/PTC — 加热

请确认以上组件是否完整？有无需要补充的？
""",

        "contacts": """你正在引导第3步「接触关系分析」。

基于第2步的组件列表，分析组件间的接触/交互关系。

规则：
- 用自然文本展示接触关系，不要用代码块
- 用户确认后调用 ariz_step3_contacts 工具，然后自动进入第4步

展示格式示例：

接触关系分析：
1. 冷却板 ↔ 导热垫：热传导，面接触
2. 导热垫 ↔ 电芯模组：热传导，导热界面
3. 冷却液 ↔ 冷却板：对流换热，流道内壁
4. 水泵 ↔ 冷却液：驱动，泵进出口
5. 管路 ↔ 冷却液：导通，管路内壁

请确认以上接触关系是否正确？
""",

        "function": """你正在引导第4步「功能建模」。

基于组件和接触关系，建立功能模型。标注功能类型：有用(useful)/不足(insufficient)/过度(excessive)/有害(harmful)/缺失(missing)。

规则：
- 用自然文本列表展示功能模型，不要用代码块
- 用户确认后调用 ariz_step4_function 工具，然后自动进入第5步

展示格式示例：

功能模型：
✅ 电芯模组 → 产生热量 → 环境（有用功能）
✅ 电芯模组 → 提供电能 → 高压输出端（有用功能）
⚠️ 冷却板 → 散热 → 电芯模组（不足功能：高倍率工况下散热能力不够）
⚠️ 导热垫 → 传导热量 → 冷却板（不足功能：导热系数偏低）
❌ 冷却液 → 低温流动性差 → 管路（有害功能）

请确认以上功能模型是否准确？
""",

        "structure": """你正在引导第5步「系统结构分析」。

分析系统空间结构，追问布局参数（尺寸/排列/冷却位置/流道走向），识别结构约束和瓶颈。

规则：
- 用自然文本展示结构分析，不要用代码块
- 用户确认后调用 ariz_step5_structure 工具，然后自动进入第6步
""",

        "summary": """你正在引导第6步「功能建模问题总结」。

从功能模型中提取所有问题，分类为：不足功能/有害功能/过度功能/缺失功能。给出优先级建议。

规则：
- 用自然文本展示问题清单，不要用代码块
- 用户确认后调用 ariz_step6_summary 工具，然后自动进入第7步
""",

        "causal": """你正在引导第7步「因果链分析」。

从用户选择的问题开始，逐层追问'为什么'，建立因果链。识别系统级约束和根本原因。找到潜在切入点。

规则：
- 用自然文本展示因果链（树状结构），不要用代码块
- 用户确认后调用 ariz_step7_causal 工具，然后自动进入第8步
""",

        "keypoint": """你正在引导第8步「关键问题/切入点」。

定义技术矛盾（改善A→恶化B）、物理矛盾（同一参数既要大又要小）、理想最终状态（IFR）。

规则：
- 用自然文本展示矛盾定义和IFR，不要用代码块
- 用户确认后调用 ariz_step8_keypoint 工具，然后自动进入第9步
""",

        "solution": """你正在引导第9步「生成创新方案」。

基于矛盾和发明原理，生成具体方案卡片。每个方案包含：名称、原理、描述、优缺点、可行性、预期效果。

规则：
- 用自然文本展示方案卡片，不要用代码块
- 用户确认后调用 ariz_step9_solution 工具
- 生成完整ARIZ分析报告
""",
    }

    step_guide = step_guides.get(current_step, "")

    # 历史结果注入
    history = inject_history(state.get("step_results", {})) if state else ""

    return f"""你是一个专注于动力电池 PACK 创新的 AI Agent，基于 TRIZ ARIZ 方法论引导工程师完成系统化创新分析。

{progress}

{step_guide}

{history}

重要规则：
- 每步完成后，向用户展示结果并请求确认
- 用户确认后立即调用对应工具记录结果，然后自动进入下一步
- 不要等用户说"进入下一步"，确认即推进
- 用户可以随时要求修改某个步骤
- 所有展示给用户的结果用自然文本，不要用代码块。只有真正的代码、命令才用代码块
- 工具调用的参数用 JSON，但不要把分析结果输出为 JSON 代码块
- 语言：中文
- 语气：专业但自然，像经验丰富的工程师同事在对话，不要过于机械
- 步骤卡片由系统自动渲染，你不需要在消息中重复展示步骤卡片内容"""


# ========== 流程状态管理（基于会话内存） ==========

# 会话状态：{ conversation_id: { "current_step": str, "step_results": dict, "step_history": list } }
_session_states = {}


def get_session_state(conv_id: str) -> dict:
    """获取会话的 ARIZ 状态，不存在则初始化"""
    if conv_id not in _session_states:
        _session_states[conv_id] = {
            "current_step": "problem",
            "step_results": {},
            "step_history": [],
        }
    return _session_states[conv_id]


def set_session_step(conv_id: str, step: str):
    """设置当前步骤"""
    state = get_session_state(conv_id)
    state["current_step"] = step
    logger.info("ariz_step_changed", conv_id=conv_id, step=step)


def save_step_result(conv_id: str, step: str, result: dict):
    """保存某步的分析结果"""
    state = get_session_state(conv_id)
    state["step_results"][step] = result


def get_step_result(conv_id: str, step: str) -> dict:
    """获取某步的分析结果"""
    state = get_session_state(conv_id)
    return state["step_results"].get(step, {})


def advance_step(conv_id: str) -> str:
    """前进到下一步，返回新步骤名。已是最后一步则返回 None"""
    state = get_session_state(conv_id)
    idx = get_step_index(state["current_step"])
    if idx < len(ARIZ_STEPS) - 1:
        # 记录当前步骤确认时间
        state["step_history"].append({
            "step": state["current_step"],
            "confirmed_at": datetime.now().isoformat(),
        })
        next_step = ARIZ_STEPS[idx + 1][0]
        state["current_step"] = next_step
        return next_step
    return None


def rollback_to_step(conv_id: str, target_step: str) -> dict:
    """回退到指定步骤，清空后续结果"""
    state = get_session_state(conv_id)
    target_idx = get_step_index(target_step)
    if target_idx < 0:
        return {"error": f"未知步骤: {target_step}"}

    # 删除目标步骤及之后的所有结果
    for step_name, _ in ARIZ_STEPS[target_idx:]:
        state["step_results"].pop(step_name, None)

    # 清空目标步骤之后的历史
    state["step_history"] = [
        h for h in state["step_history"]
        if get_step_index(h["step"]) < target_idx
    ]

    state["current_step"] = target_step
    logger.info("ariz_rolled_back", conv_id=conv_id, target=target_step)
    return {"rolled_back_to": target_step, "message": f"已回退到：{get_step_label(target_step)}"}


def reset_flow(conv_id: str):
    """重置流程"""
    _session_states[conv_id] = {
        "current_step": "problem",
        "step_results": {},
        "step_history": [],
    }


# ========== 历史结果注入 ==========


def _summarize_step_result(step_name: str, result: dict) -> str:
    """将步骤结果转为 LLM 可读的摘要文本"""
    if step_name == "problem":
        d = result.get("step1_result", result)
        lines = []
        if d.get("problem_object"): lines.append(f"- 问题对象：{d['problem_object']}")
        if d.get("phenomenon"): lines.append(f"- 现象：{d['phenomenon']}")
        if d.get("goal"): lines.append(f"- 目标：{d['goal']}")
        if d.get("constraints"): lines.append(f"- 约束：{'、'.join(d['constraints'])}")
        if d.get("contradiction_hint"): lines.append(f"- 矛盾方向：{d['contradiction_hint']}")
        return "\n".join(lines)

    elif step_name == "components":
        d = result.get("step2_result", result)
        lines = []
        if d.get("supersystem"): lines.append(f"- 超系统：{d['supersystem']}")
        if d.get("system_name"): lines.append(f"- 系统：{d['system_name']}")
        comps = d.get("all_components", [])
        if comps:
            comp_names = [c if isinstance(c, str) else c.get("name", str(c)) for c in comps]
            lines.append(f"- 组件：{'、'.join(comp_names)}")
        return "\n".join(lines)

    elif step_name == "contacts":
        contacts = result.get("contacts", [])
        lines = [f"- 共{len(contacts)}个接触关系"]
        for c in contacts[:5]:
            lines.append(f"  {c.get('component_a','')} ↔ {c.get('component_b','')}：{c.get('contact_type','')}")
        return "\n".join(lines)

    elif step_name == "function":
        funcs = result.get("functions", [])
        type_map = {"useful": "有用", "insufficient": "不足", "excessive": "过度", "harmful": "有害", "missing": "缺失"}
        lines = [f"- 共{len(funcs)}个功能"]
        for f in funcs[:5]:
            t = type_map.get(f.get("type", ""), f.get("type", ""))
            lines.append(f"  {f.get('source','')} → {f.get('function','')} → {f.get('target','')}（{t}）")
        return "\n".join(lines)

    else:
        return json.dumps(result, ensure_ascii=False)[:300]


def inject_history(step_results: dict) -> str:
    """将已完成步骤的结果注入为历史上下文"""
    if not step_results:
        return ""

    lines = ["已完成的分析步骤："]
    for step_name, _ in ARIZ_STEPS:
        if step_name in step_results:
            label = get_step_label(step_name)
            summary = _summarize_step_result(step_name, step_results[step_name])
            lines.append(f"\n【{label}】\n{summary}")

    return "\n".join(lines)


# ========== Step 2 数据库查询 ==========

def query_components_for_step2(step1_result: dict) -> dict:
    """
    根据 Step 1 的 system_keywords 查询数据库，返回组件信息。
    供 Step 2 使用。
    """
    keywords = step1_result.get("system_keywords", [])
    if not keywords:
        return {"error": "未提供 system_keywords，无法查询数据库"}

    all_systems = []
    for kw in keywords:
        systems = search_system(kw)
        all_systems.extend(systems)

    # 去重
    seen_ids = set()
    unique_systems = []
    for s in all_systems:
        if s["id"] not in seen_ids:
            seen_ids.add(s["id"])
            unique_systems.append(s)

    if not unique_systems:
        return {"error": f"关键词 {keywords} 未匹配到任何系统", "matched_systems": []}

    # 取第一个匹配的系统（通常是最相关的）
    primary_system = unique_systems[0]
    system_data = get_system_components(primary_system["id"])

    return {
        "matched_systems": unique_systems,
        "primary_system": system_data,
    }
