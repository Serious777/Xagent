"""Xagent - 动力电池PACK创新智能体"""
import json
import os
import sqlite3
import uuid
import time
from contextlib import contextmanager
from datetime import datetime
import structlog
from flask import Flask, request, Response, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from openai import OpenAI

from skills import SKILLS
from ariz_flow import (
    build_system_prompt, get_session_state, set_session_step,
    save_step_result, get_step_result, advance_step, reset_flow,
    query_components_for_step2, ARIZ_STEPS, get_step_index, get_step_label,
)
from component_db import init_db as init_component_db

# LangGraph + Deep Agents 新引擎（USE_LANGGRAPH=true 时启用）
try:
    from ariz_graph import get_ariz_graph
    from ariz_state import create_initial_state
    from ariz_tools import parse_tool_calls
    from agent import get_agent
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False

import asyncio

load_dotenv()

# ---- 结构化日志 ----
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.dev.ConsoleRenderer(),
    ],
)
logger = structlog.get_logger()

# ---- Flask 初始化 ----
app = Flask(__name__)
CORS(app)


# ============ 数据库连接管理 ============

DB_PATH = os.path.join(os.path.dirname(__file__), "xagent.db")


@contextmanager
def get_db():
    """数据库连接上下文管理器，自动提交/关闭/回滚"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL DEFAULT '新对话',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
            );
        """)


init_db()
init_component_db()

# ---- LLM 客户端 ----
client = OpenAI(
    api_key=os.getenv("XIAOMI_API_KEY"),
    base_url=os.getenv("XIAOMI_BASE_URL"),
)
MODEL = os.getenv("XIAOMI_MODEL", "mimo-v2.5")

logger.info("xagent_started", model=MODEL)


# ============ 全局错误处理 ============

@app.errorhandler(400)
def bad_request(e):
    return jsonify({"error": "请求参数错误", "detail": str(e)}), 400


@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "资源不存在"}), 404


@app.errorhandler(500)
def internal_error(e):
    logger.error("internal_error", error=str(e))
    return jsonify({"error": "服务器内部错误"}), 500


@app.errorhandler(Exception)
def handle_exception(e):
    logger.error("unhandled_exception", error=str(e), type=type(e).__name__)
    return jsonify({"error": "服务器内部错误", "detail": str(e)}), 500


# ============ 工具定义（ARIZ 步骤 + wiki） ============

ARIZ_STEP1_TOOL = {
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
                    "description": "数据库检索用的系统级关键词（必须是系统名称如'热管理系统'、'箱体结构'、'BMS'，不要用现象描述如'低温续航衰减'）"
                },
                "phenomenon": {"type": "string", "description": "可观测可量化的现象"},
                "constraints": {"type": "array", "items": {"type": "string"}, "description": "约束条件"},
                "goal": {"type": "string", "description": "期望目标"},
                "contradiction_hint": {"type": "string", "description": "初步矛盾方向"},
            },
            "required": ["problem_object", "system_keywords", "phenomenon"],
        },
    },
}

ARIZ_STEP2_TOOL = {
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
                                "description": "该组件对本系统产生的功能/影响"
                            }
                        },
                        "required": ["name"]
                    },
                    "description": "超系统中与本系统有交互的外部组件（含功能描述）"
                },
                "system_name": {"type": "string", "description": "系统名称"},
                "user_added": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "用户补充的、数据库中没有的组件列表"
                },
            },
            "required": ["supersystem", "system_name"],
        },
    },
}


def make_step_tool(step_num: int, name: str, label: str, fields: list) -> dict:
    props = {}
    required = []
    for f in fields:
        props[f["name"]] = {"type": f.get("type", "string"), "description": f.get("desc", "")}
        if f.get("required"):
            required.append(f["name"])
    return {
        "type": "function",
        "function": {
            "name": f"ariz_step{step_num}_{name}",
            "description": f"ARIZ第{step_num}步：用户确认后调用此工具保存{label}结果",
            "parameters": {"type": "object", "properties": props, "required": required},
        },
    }


ARIZ_STEP3_TOOL = make_step_tool(3, "contacts", "接触关系分析", [
    {"name": "contacts", "type": "array", "desc": "组件间接触关系列表", "required": True},
])
ARIZ_STEP4_TOOL = make_step_tool(4, "function", "功能建模", [
    {"name": "functions", "type": "array", "desc": "功能模型列表，每项含 source(作用者)、target(作用对象)、function(功能)、type(功能类型: useful/insufficient/excessive/harmful)", "required": True},
])
ARIZ_STEP5_TOOL = make_step_tool(5, "structure", "系统结构分析", [
    {"name": "structure_info", "type": "object", "desc": "结构参数", "required": True},
])
ARIZ_STEP6_TOOL = make_step_tool(6, "summary", "问题总结", [
    {"name": "problems", "type": "object", "desc": "分类问题清单", "required": True},
])
ARIZ_STEP7_TOOL = make_step_tool(7, "causal", "因果链分析", [
    {"name": "causal_chains", "type": "array", "desc": "因果链列表", "required": True},
])
ARIZ_STEP8_TOOL = make_step_tool(8, "keypoint", "关键问题定义", [
    {"name": "contradictions", "type": "object", "desc": "矛盾定义和IFR", "required": True},
])
ARIZ_STEP9_TOOL = make_step_tool(9, "solution", "方案生成", [
    {"name": "solutions", "type": "array", "desc": "创新方案列表", "required": True},
])

ARIZ_TOOLS = [
    ARIZ_STEP1_TOOL, ARIZ_STEP2_TOOL, ARIZ_STEP3_TOOL, ARIZ_STEP4_TOOL,
    ARIZ_STEP5_TOOL, ARIZ_STEP6_TOOL, ARIZ_STEP7_TOOL, ARIZ_STEP8_TOOL,
    ARIZ_STEP9_TOOL,
]

ARIZ_TOOL_MAP = {
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


def get_tools_for_step(step: str) -> list:
    tools = []
    step_tool_map = {
        "problem": 0, "components": 1, "contacts": 2, "function": 3,
        "structure": 4, "summary": 5, "causal": 6, "keypoint": 7, "solution": 8,
    }
    idx = step_tool_map.get(step)
    if idx is not None:
        tools.append(ARIZ_TOOLS[idx])
    return tools


# ============ 工具调用处理 ============

def handle_ariz_tool_call(conv_id: str, tool_name: str, args: dict) -> dict:
    """处理 ARIZ 工具调用，返回结构化结果（含 card_data 供前端渲染卡片）"""
    step_num = ARIZ_TOOL_MAP.get(tool_name)
    if not step_num:
        return {"error": f"未知工具: {tool_name}"}

    step_name = ARIZ_STEPS[step_num - 1][0]

    if step_num == 1:
        db_result = query_components_for_step2(args)
        step_data = {**args, "database_query": db_result}
        save_step_result(conv_id, "problem", step_data)

        card = {
            "step": 1,
            "title": "问题识别",
            "status": "current",
            "saved": True,
            "data": {
                "problem_object": args.get("problem_object"),
                "phenomenon": args.get("phenomenon"),
                "goal": args.get("goal"),
                "contradiction_hint": args.get("contradiction_hint"),
                "constraints": args.get("constraints", []),
                "database_query": db_result,
            },
        }
        return {"status": "saved", "message": "问题识别结果已保存，请确认", "card_data": card}

    elif step_num == 2:
        # 从 Step 1 的保存结果中读取数据库查询结果（已在 step_results["problem"] 中）
        step1_data = get_step_result(conv_id, "problem")
        db_result = step1_data.get("database_query", {})
        primary_system = db_result.get("primary_system", {})
        db_components = primary_system.get("components", [])
        db_comp_names = [c["name"] for c in db_components]

        user_added = args.get("user_added", [])
        # 归一化 user_added：字符串 → {name, functions: []}
        user_added_normalized = [
            {"name": c, "functions": []} if isinstance(c, str) else c
            for c in user_added
        ]
        # 归一化 supersystem_components：字符串 → {name, functions: []}
        super_raw = args.get("supersystem_components", [])
        supersystem_components = [
            {"name": c, "functions": []} if isinstance(c, str) else c
            for c in super_raw
        ]
        super_names = [c["name"] if isinstance(c, dict) else c for c in supersystem_components]

        all_components = db_comp_names + [
            c["name"] if isinstance(c, dict) else c
            for c in user_added_normalized
            if (c["name"] if isinstance(c, dict) else c) not in db_comp_names
        ]
        # 加入超组件
        for n in super_names:
            if n not in all_components:
                all_components.append(n)

        merged_args = {
            "supersystem": args.get("supersystem", ""),
            "supersystem_components": supersystem_components,
            "system_name": args.get("system_name", primary_system.get("system", {}).get("name", "")),
            "all_components": all_components,
            "user_added": user_added_normalized,
        }
        save_step_result(conv_id, "components", merged_args)

        card = {
            "step": 2,
            "title": "系统组件分析",
            "status": "current",
            "saved": True,
            "data": {**merged_args, "database_query": db_result},
        }
        return {"status": "saved", "message": "系统组件分析结果已保存，请确认", "card_data": card}

    else:
        save_step_result(conv_id, step_name, args)
        card_data = {**args}
        # Step 3 需要 Step 2 的组件列表来渲染矩阵
        if step_num == 3:
            step2_data = get_step_result(conv_id, "components")
            card_data["all_components"] = step2_data.get("all_components", [])
        card = {
            "step": step_num,
            "title": get_step_label(step_name),
            "status": "current",
            "saved": True,
            "data": card_data,
        }
        return {"status": "saved", "message": f"{get_step_label(step_name)}结果已保存，请确认", "card_data": card}


# ============ 对话 API ============

@app.route("/api/conversations", methods=["GET"])
def list_conversations():
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, title, created_at, updated_at FROM conversations ORDER BY updated_at DESC"
        ).fetchall()
    return jsonify([dict(r) for r in rows])


@app.route("/api/conversations", methods=["POST"])
def create_conversation():
    conv_id = str(uuid.uuid4())[:8]
    now = datetime.now().isoformat()
    with get_db() as conn:
        conn.execute(
            "INSERT INTO conversations (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (conv_id, "新对话", now, now),
        )
    reset_flow(conv_id)
    logger.info("conversation_created", id=conv_id)
    return jsonify({"id": conv_id, "title": "新对话", "created_at": now, "updated_at": now})


@app.route("/api/conversations/<conv_id>", methods=["DELETE"])
def delete_conversation(conv_id):
    with get_db() as conn:
        conn.execute("DELETE FROM messages WHERE conversation_id = ?", (conv_id,))
        conn.execute("DELETE FROM conversations WHERE id = ?", (conv_id,))
    reset_flow(conv_id)
    logger.info("conversation_deleted", id=conv_id)
    return jsonify({"ok": True})


@app.route("/api/conversations/<conv_id>", methods=["PATCH"])
def update_conversation(conv_id):
    data = request.json
    title = data.get("title", "")
    with get_db() as conn:
        conn.execute(
            "UPDATE conversations SET title = ?, updated_at = ? WHERE id = ?",
            (title, datetime.now().isoformat(), conv_id),
        )
    return jsonify({"ok": True})


@app.route("/api/conversations/<conv_id>/messages", methods=["GET"])
def get_messages(conv_id):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT role, content FROM messages WHERE conversation_id = ? ORDER BY id",
            (conv_id,),
        ).fetchall()
    return jsonify([dict(r) for r in rows])


# ============ 聊天辅助函数 ============

def _save_user_message(conv_id: str, messages: list):
    """保存用户消息到数据库，自动创建对话并设置标题"""
    last_user_msg = None
    for m in reversed(messages):
        if m.get("role") == "user":
            last_user_msg = m
            break
    if not last_user_msg:
        return

    with get_db() as conn:
        exists = conn.execute(
            "SELECT id FROM conversations WHERE id = ?", (conv_id,)
        ).fetchone()
        if not exists:
            now = datetime.now().isoformat()
            conn.execute(
                "INSERT INTO conversations (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (conv_id, "新对话", now, now),
            )

        conn.execute(
            "INSERT INTO messages (conversation_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (conv_id, "user", last_user_msg["content"], datetime.now().isoformat()),
        )

        msg_count = conn.execute(
            "SELECT COUNT(*) FROM messages WHERE conversation_id = ? AND role = 'user'",
            (conv_id,),
        ).fetchone()[0]
        if msg_count == 1:
            title = last_user_msg["content"][:30]
            conn.execute(
                "UPDATE conversations SET title = ?, updated_at = ? WHERE id = ?",
                (title, datetime.now().isoformat(), conv_id),
            )

        conn.execute(
            "UPDATE conversations SET updated_at = ? WHERE id = ?",
            (datetime.now().isoformat(), conv_id),
        )


def _save_assistant_message(conv_id: str, content: str):
    """保存助手回复到数据库"""
    if not conv_id or not content:
        return
    with get_db() as conn:
        conn.execute(
            "INSERT INTO messages (conversation_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (conv_id, "assistant", content, datetime.now().isoformat()),
        )


def _execute_tool(func_name: str, args: dict, conv_id: str) -> dict:
    """执行工具调用并返回结果"""
    if func_name in ARIZ_TOOL_MAP:
        return handle_ariz_tool_call(conv_id, func_name, args)
    return {"error": f"未知工具: {func_name}"}


# ============ 聊天接口 ============

def _build_fallback_args(conv_id: str, step: str, llm_text: str = "") -> dict:
    """当 LLM 没有调用工具时，从文本回复中提取数据作为兜底"""
    if step == "components":
        step1 = get_step_result(conv_id, "problem")
        if not step1:
            return {}
        db = step1.get("database_query", {}).get("primary_system", {})
        db_comps = [c["name"] for c in db.get("components", [])]
        return {
            "supersystem": step1.get("constraints", [""])[0] if step1.get("constraints") else "",
            "supersystem_components": [],
            "system_name": db.get("system", {}).get("name", step1.get("problem_object", "")),
            "all_components": db_comps,
            "user_added": [],
        }
    elif step == "contacts":
        step2 = get_step_result(conv_id, "components")
        if not step2:
            return {}
        all_comp = step2.get("all_components", [])
        contacts = []
        for i, a in enumerate(all_comp):
            for b in all_comp[i+1:]:
                contacts.append({"component_a": a, "component_b": b, "contact_type": "待分析", "interface": ""})
        return {"contacts": contacts}
    elif step == "function":
        # 从 Step 3 接触关系一一对应生成功能模型
        step3 = get_step_result(conv_id, "contacts")
        contacts = step3.get("contacts", [])
        functions = []
        for c in contacts:
            a = c.get("component_a", "")
            b = c.get("component_b", "")
            ctype = c.get("contact_type", "")
            if a and b:
                func_desc = f"{a}对{b}产生{ctype}作用" if ctype else f"{a}对{b}产生作用"
                functions.append({"source": a, "target": b, "function": func_desc, "type": "useful"})
        if not functions:
            functions = _extract_functions_from_text(llm_text)
        return {"functions": functions}
    elif step == "structure":
        return {"structure_info": {}}
    elif step == "summary":
        return {"problems": {}}
    elif step == "causal":
        return {"causal_chains": []}
    elif step == "keypoint":
        return {"contradictions": {}}
    elif step == "solution":
        return {"solutions": []}
    return {}


def _extract_functions_from_text(text: str) -> list:
    """从 LLM 文本回复中提取功能关系"""
    import re
    functions = []
    # 匹配格式: "A → B：功能描述" 或 "A 对 B 的功能描述"
    patterns = [
        r'([\u4e00-\u9fa5a-zA-Z0-9_]+)\s*[→\-\->]+\s*([\u4e00-\u9fa5a-zA-Z0-9_]+)[:：]\s*(.+)',
        r'([\u4e00-\u9fa5a-zA-Z0-9_]+)\s*对\s*([\u4e00-\u9fa5a-zA-Z0-9_]+)[:：]\s*(.+)',
        r'([\u4e00-\u9fa5a-zA-Z0-9_]+)\s*→\s*([\u4e00-\u9fa5a-zA-Z0-9_]+)[:：]\s*(.+)',
    ]
    for line in text.split('\n'):
        line = line.strip()
        if not line:
            continue
        for pat in patterns:
            m = re.search(pat, line)
            if m:
                src, tgt, func = m.group(1).strip(), m.group(2).strip(), m.group(3).strip()
                # 简单判断类型
                ftype = "useful"
                if any(w in func for w in ["不足", "不够", "需要增强", "偏弱"]):
                    ftype = "insufficient"
                elif any(w in func for w in ["过度", "过大", "过高", "超出"]):
                    ftype = "excessive"
                elif any(w in func for w in ["有害", "干扰", "损伤", "破坏"]):
                    ftype = "harmful"
                functions.append({"source": src, "target": tgt, "function": func, "type": ftype})
                break
    return functions


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.json
    messages = data.get("messages", [])
    conv_id = data.get("conversation_id")

    logger.info("chat_received", message_count=len(messages), conversation_id=conv_id)

    if conv_id and messages:
        _save_user_message(conv_id, messages)

    # 判断使用新引擎还是旧引擎
    use_langgraph = os.getenv("USE_LANGGRAPH", "false").lower() == "true"

    if use_langgraph and LANGGRAPH_AVAILABLE:
        return _chat_with_langgraph(data, conv_id, messages)
    else:
        return _chat_legacy(data, conv_id, messages)


def _chat_with_langgraph(data, conv_id, messages):
    """使用 Deep Agents + LangGraph 引擎处理聊天"""
    agent = get_agent()

    def generate():
        try:
            # 获取用户最新消息
            user_msg = ""
            for m in reversed(messages):
                if m.get("role") == "user":
                    user_msg = m["content"]
                    break

            # 获取或创建状态
            state = agent.get_state(conv_id or "default")

            # 运行 Agent
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                result = loop.run_until_complete(
                    agent.run(user_msg, state=state, thread_id=conv_id or "default")
                )
            finally:
                loop.close()

            # 输出卡片数据（匹配前端 parseArizSteps 正则格式）
            card_data = result.get("card_data", {})
            if card_data and card_data.get("step"):
                step_num = card_data["step"]
                step_name = ["", "problem", "components", "contacts", "function",
                             "structure", "summary", "causal", "keypoint", "solution"][step_num]
                # 包装成前端期望的格式
                tool_result = {
                    "card_data": {
                        "step": card_data["step"],
                        "title": card_data.get("title", ""),
                        "data": card_data.get("data", {}),
                        "saved": card_data.get("saved", True),
                        "status": card_data.get("status", "current"),
                    },
                    "status": "saved",
                }
                tool_text = f"\n\n**调用工具: ariz_step{step_num}_{step_name}**\n```json\n{json.dumps(tool_result, ensure_ascii=False, indent=2)}\n```\n"
                yield f'0:{json.dumps(tool_text)}\n'

            # 输出回复
            response = result.get("response", "")
            if response:
                yield f'0:{json.dumps(response)}\n'

            # 保存消息
            _save_assistant_message(conv_id, response)

        except Exception as e:
            logger.error("deep_agent_error", error=str(e))
            error_msg = f"\n\n⚠️ AI 服务暂时不可用，请稍后重试。"
            yield f'0:{json.dumps(error_msg)}\n'

    return Response(generate(), mimetype="text/plain; charset=utf-8",
                    headers={"X-Vercel-AI-Data-Stream": "v1"})


def _chat_legacy(data, conv_id, messages):
    """旧引擎处理聊天（保持原有逻辑不变）"""

    def generate():
        conv_id_for_flow = conv_id or "default"
        state = get_session_state(conv_id_for_flow)
        current_step = state["current_step"]

        system_prompt = build_system_prompt(current_step, state)
        tools = get_tools_for_step(current_step)

        tool_calls = {}
        full_response = ""

        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "system", "content": system_prompt}] + messages,
                tools=tools if tools else None,
                stream=True,
                timeout=120,
            )

            stream_start = time.time()
            last_chunk_time = time.time()
            STREAM_TIMEOUT = 300  # 整个流最大持续时间
            CHUNK_TIMEOUT = 30    # 两个 chunk 之间的最大间隔

            for chunk in response:
                now = time.time()
                if now - stream_start > STREAM_TIMEOUT:
                    logger.warning("stream_timeout", step=current_step, elapsed=now - stream_start)
                    break
                if now - last_chunk_time > CHUNK_TIMEOUT:
                    logger.warning("chunk_timeout", step=current_step, gap=now - last_chunk_time)
                    break
                last_chunk_time = now

                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta

                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        tc_index = tc.index
                        if tc_index not in tool_calls:
                            tool_calls[tc_index] = {"id": tc.id, "name": "", "arguments": ""}
                        if tc.function:
                            if tc.function.name:
                                tool_calls[tc_index]["name"] = tc.function.name
                            if tc.function.arguments:
                                tool_calls[tc_index]["arguments"] += tc.function.arguments

                if delta.content:
                    full_response += delta.content
                    yield f'0:{json.dumps(delta.content)}\n'

        except Exception as e:
            logger.error("llm_error", error=str(e), step=current_step)
            error_msg = f"\n\n⚠️ AI 服务暂时不可用，请稍后重试。"
            full_response += error_msg
            yield f'0:{json.dumps(error_msg)}\n'
            _save_assistant_message(conv_id, full_response)
            return

        # 处理工具调用
        for tc_info in tool_calls.values():
            func_name = tc_info["name"]
            if not func_name:
                continue

            try:
                args = json.loads(tc_info["arguments"]) if tc_info["arguments"] else {}
            except json.JSONDecodeError:
                args = {}

            logger.info("tool_called", tool=func_name, args=list(args.keys()))
            result = _execute_tool(func_name, args, conv_id_for_flow)

            tool_text = f"\n\n**调用工具: {func_name}**\n```json\n{json.dumps(result, ensure_ascii=False, indent=2)}\n```\n"
            full_response += tool_text
            yield f'0:{json.dumps(tool_text)}\n'

        # === Step 3 后检查：LLM 调用了工具但 contacts 为空时，自动补充 ===
        if current_step == "contacts" and current_step in [ARIZ_TOOL_MAP.get(tc["name"]) for tc in tool_calls.values() if tc["name"]]:
            state_check = get_session_state(conv_id_for_flow)
            saved_contacts = state_check["step_results"].get("contacts", {}).get("contacts", [])
            if not saved_contacts:
                step2_data = get_step_result(conv_id_for_flow, "components")
                all_comp = step2_data.get("all_components", [])
                if len(all_comp) >= 2:
                    auto_contacts = []
                    for i in range(len(all_comp)):
                        for j in range(i + 1, len(all_comp)):
                            auto_contacts.append({"component_a": all_comp[i], "component_b": all_comp[j], "contact_type": "待分析", "interface": ""})
                    result = _execute_tool("ariz_step3_contacts", {"contacts": auto_contacts}, conv_id_for_flow)
                    tool_text = f"\n\n**自动补充接触关系: {len(auto_contacts)}组**\n"
                    full_response += tool_text
                    yield f'0:{json.dumps(tool_text)}\n'
                    logger.info("step3_auto_contacts", count=len(auto_contacts))

        # === Step 4 后检查：LLM 调用了工具但 functions 为空时，从 Step 3 接触关系一一对应生成 ===
        if current_step == "function":
            state_check = get_session_state(conv_id_for_flow)
            saved_funcs = state_check["step_results"].get("function", {}).get("functions", [])
            if not saved_funcs:
                step3 = get_step_result(conv_id_for_flow, "contacts")
                contacts = step3.get("contacts", [])
                if contacts:
                    # 接触类型 → 功能类型 + 功能描述的映射
                    contact_to_func = {
                        "热传导": ("useful", "传导热量"),
                        "对流换热": ("useful", "对流换热"),
                        "换热": ("useful", "热交换"),
                        "热传递": ("useful", "传递热量"),
                        "温度传导": ("useful", "传导温度"),
                        "温度监测": ("useful", "监测温度"),
                        "接触应力": ("harmful", "产生接触应力"),
                        "安装基面": ("useful", "提供安装支撑"),
                        "流体压力": ("useful", "承受流体压力"),
                        "负载反馈": ("insufficient", "负载反馈不足"),
                        "流动阻力": ("harmful", "产生流动阻力"),
                        "容积变化": ("useful", "补偿容积变化"),
                        "流向控制": ("useful", "控制流向"),
                        "密封连接": ("useful", "密封连接"),
                        "热膨胀": ("excessive", "热膨胀过大"),
                        "驱动循环": ("useful", "驱动冷却液循环"),
                        "换热介质": ("useful", "作为换热介质"),
                        "容量补偿": ("useful", "补偿容量变化"),
                        "散热": ("useful", "散发热量"),
                        "预加热": ("useful", "预加热电池"),
                        "温度检测": ("useful", "检测温度"),
                        "传导热量": ("useful", "传导热量"),
                    }
                    auto_funcs = []
                    for c in contacts:
                        a = c.get("component_a", "")
                        b = c.get("component_b", "")
                        ctype = c.get("contact_type", "")
                        if a and b:
                            # 根据接触类型匹配功能描述
                            func_type = "useful"
                            func_desc = f"{a}对{b}产生作用"
                            for key, (ft, desc) in contact_to_func.items():
                                if key in ctype:
                                    func_type = ft
                                    func_desc = f"{a}{desc}给{b}"
                                    break
                            auto_funcs.append({"source": a, "target": b, "function": func_desc, "type": func_type})
                    if auto_funcs:
                        result = _execute_tool("ariz_step4_function", {"functions": auto_funcs}, conv_id_for_flow)
                        tool_text = f"\n\n**基于{len(auto_funcs)}组接触关系自动生成功能模型**\n"
                        full_response += tool_text
                        yield f'0:{json.dumps(tool_text)}\n'
                        logger.info("step4_auto_functions", count=len(auto_funcs))

        # 兜底：LLM 没有调用工具时，自动推进流程
        has_tool_call = any(tc["name"] for tc in tool_calls.values())
        if not has_tool_call and tools:
            logger.warning("no_tool_call", step=current_step)
            # 自动调用当前步骤的工具，用已有数据保存
            step_tool_name = tools[0]["function"]["name"]
            step_num = ARIZ_TOOL_MAP.get(step_tool_name)
            if step_num:
                # 从上一步结果推导数据
                fallback_args = _build_fallback_args(conv_id_for_flow, current_step, full_response)
                if fallback_args:
                    logger.info("fallback_tool_call", tool=step_tool_name, args=list(fallback_args.keys()))
                    result = _execute_tool(step_tool_name, fallback_args, conv_id_for_flow)
                    tool_text = f"\n\n**调用工具: {step_tool_name}**\n```json\n{json.dumps(result, ensure_ascii=False, indent=2)}\n```\n"
                    full_response += tool_text
                    yield f'0:{json.dumps(tool_text)}\n'

        _save_assistant_message(conv_id, full_response)

    return Response(generate(), mimetype="text/plain; charset=utf-8",
                    headers={"X-Vercel-AI-Data-Stream": "v1"})


# ---- ARIZ 流程状态查询 ----

@app.route("/api/ariz/status/<conv_id>", methods=["GET"])
def ariz_status(conv_id):
    use_langgraph = os.getenv("USE_LANGGRAPH", "false").lower() == "true"
    if use_langgraph and LANGGRAPH_AVAILABLE:
        agent = get_agent()
        state = agent.get_state(conv_id)
        # 转换 LangChain messages 为可序列化格式
        serializable_state = {
            "current_step": state.get("current_step"),
            "step_results": state.get("step_results", {}),
            "card_data": state.get("card_data", {}),
            "error": state.get("error"),
            "message_count": len(state.get("messages", [])),
        }
        return jsonify(serializable_state)
    else:
        state = get_session_state(conv_id)
        return jsonify(state)


@app.route("/api/ariz/reset/<conv_id>", methods=["POST"])
def ariz_reset(conv_id):
    reset_flow(conv_id)
    return jsonify({"ok": True, "message": "流程已重置"})


@app.route("/api/ariz/confirm/<conv_id>", methods=["POST"])
def ariz_confirm(conv_id):
    """用户确认当前步骤，推进到下一步"""
    use_langgraph = os.getenv("USE_LANGGRAPH", "false").lower() == "true"

    if use_langgraph and LANGGRAPH_AVAILABLE:
        agent = get_agent()
        result = agent.confirm_step(conv_id)
        if result.get("ok"):
            return jsonify({**result, "card_status": "done"})
        else:
            return jsonify(result), 400
    else:
        state = get_session_state(conv_id)
        current_step = state["current_step"]
        current_label = get_step_label(current_step)

        step_result = get_step_result(conv_id, current_step)
        if not step_result:
            return jsonify({"ok": False, "error": f"{current_label}尚未保存结果"}), 400

        next_step = advance_step(conv_id)

        if next_step:
            next_label = get_step_label(next_step)
            return jsonify({
                "ok": True,
                "current_step": next_step,
                "current_step_index": get_step_index(next_step) + 1,
                "message": f"{current_label}已确认，进入{next_label}",
                "card_status": "done",
            })
        else:
            return jsonify({
                "ok": True,
                "current_step": None,
                "message": "ARIZ 全部流程已完成！",
                "card_status": "done",
                "all_results": {k: v for k, v in state["step_results"].items()},
            })


# ---- Skill 列表 ----

@app.route("/api/skills", methods=["GET"])
def list_skills():
    return jsonify([
        {"name": name, "description": info["description"]}
        for name, info in SKILLS.items()
    ])


if __name__ == "__main__":
    port = int(os.getenv("FLASK_PORT", 8000))
    debug = os.getenv("FLASK_DEBUG", "true").lower() == "true"
    logger.info("server_starting", port=port, debug=debug)
    app.run(port=port, debug=debug)
