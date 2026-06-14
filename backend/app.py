"""Xagent - 动力电池PACK创新智能体"""
import json
import os
import sqlite3
import uuid
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

# ---- 对话数据库 ----
DB_PATH = os.path.join(os.path.dirname(__file__), "xagent.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
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
    conn.commit()
    conn.close()


init_db()
init_component_db()

# ---- LLM 客户端 ----
client = OpenAI(
    api_key=os.getenv("XIAOMI_API_KEY"),
    base_url=os.getenv("XIAOMI_BASE_URL"),
)
MODEL = os.getenv("XIAOMI_MODEL", "mimo-v2.5")

logger.info("xagent_started", model=MODEL)


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
                    "description": "用于数据库检索的关键词"
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
                    "items": {"type": "string"},
                    "description": "超系统中与本系统有交互的外部组件"
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
    {"name": "functions", "type": "array", "desc": "功能模型列表", "required": True},
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

WIKI_TOOL = {
    "type": "function",
    "function": {
        "name": "llm_wiki",
        "description": SKILLS["llm_wiki"]["description"],
        "parameters": SKILLS["llm_wiki"]["parameters"],
    },
}


def get_tools_for_step(step: str) -> list:
    tools = [WIKI_TOOL]
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

    # ---- Step 1 ----
    if step_num == 1:
        db_result = query_components_for_step2(args)
        step_data = {**args, "database_query": db_result}
        save_step_result(conv_id, "problem", step_data)
        state = get_session_state(conv_id)
        state["database_query"] = db_result

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
        return {
            "status": "saved",
            "message": "问题识别结果已保存，请确认",
            "card_data": card,
        }

    # ---- Step 2 ----
    elif step_num == 2:
        state = get_session_state(conv_id)
        db_result = state.get("database_query", {})
        primary_system = db_result.get("primary_system", {})
        db_components = primary_system.get("components", [])
        db_comp_names = [c["name"] for c in db_components]

        user_added = args.get("user_added", [])
        all_components = db_comp_names + [c for c in user_added if c not in db_comp_names]
        supersystem_components = args.get("supersystem_components", [])

        merged_args = {
            "supersystem": args.get("supersystem", ""),
            "supersystem_components": supersystem_components,
            "system_name": args.get("system_name", primary_system.get("system", {}).get("name", "")),
            "all_components": all_components,
            "user_added": user_added,
        }
        save_step_result(conv_id, "components", merged_args)

        card = {
            "step": 2,
            "title": "系统组件分析",
            "status": "current",
            "saved": True,
            "data": {
                **merged_args,
                "database_query": db_result,
            },
        }
        return {
            "status": "saved",
            "message": "系统组件分析结果已保存，请确认",
            "card_data": card,
        }

    # ---- Step 3-9 ----
    else:
        save_step_result(conv_id, step_name, args)

        card = {
            "step": step_num,
            "title": get_step_label(step_name),
            "status": "current",
            "saved": True,
            "data": args,
        }
        return {
            "status": "saved",
            "message": f"{get_step_label(step_name)}结果已保存，请确认",
            "card_data": card,
        }


# ============ 对话 API ============

@app.route("/api/conversations", methods=["GET"])
def list_conversations():
    conn = get_db()
    rows = conn.execute(
        "SELECT id, title, created_at, updated_at FROM conversations ORDER BY updated_at DESC"
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/api/conversations", methods=["POST"])
def create_conversation():
    conv_id = str(uuid.uuid4())[:8]
    now = datetime.now().isoformat()
    conn = get_db()
    conn.execute(
        "INSERT INTO conversations (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
        (conv_id, "新对话", now, now),
    )
    conn.commit()
    conn.close()
    reset_flow(conv_id)
    logger.info("conversation_created", id=conv_id)
    return jsonify({"id": conv_id, "title": "新对话", "created_at": now, "updated_at": now})


@app.route("/api/conversations/<conv_id>", methods=["DELETE"])
def delete_conversation(conv_id):
    conn = get_db()
    conn.execute("DELETE FROM messages WHERE conversation_id = ?", (conv_id,))
    conn.execute("DELETE FROM conversations WHERE id = ?", (conv_id,))
    conn.commit()
    conn.close()
    reset_flow(conv_id)
    logger.info("conversation_deleted", id=conv_id)
    return jsonify({"ok": True})


@app.route("/api/conversations/<conv_id>", methods=["PATCH"])
def update_conversation(conv_id):
    data = request.json
    title = data.get("title", "")
    conn = get_db()
    conn.execute(
        "UPDATE conversations SET title = ?, updated_at = ? WHERE id = ?",
        (title, datetime.now().isoformat(), conv_id),
    )
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


@app.route("/api/conversations/<conv_id>/messages", methods=["GET"])
def get_messages(conv_id):
    conn = get_db()
    rows = conn.execute(
        "SELECT role, content FROM messages WHERE conversation_id = ? ORDER BY id",
        (conv_id,),
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


# ============ 聊天接口 ============

@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.json
    messages = data.get("messages", [])
    conv_id = data.get("conversation_id")

    logger.info("chat_received", message_count=len(messages), conversation_id=conv_id)

    # 保存用户消息
    if conv_id and messages:
        last_user_msg = None
        for m in reversed(messages):
            if m.get("role") == "user":
                last_user_msg = m
                break
        if last_user_msg:
            conn = get_db()
            exists = conn.execute("SELECT id FROM conversations WHERE id = ?", (conv_id,)).fetchone()
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
            conn.commit()
            conn.close()

    def generate():
        conv_id_for_flow = conv_id or "default"
        state = get_session_state(conv_id_for_flow)
        current_step = state["current_step"]

        system_prompt = build_system_prompt(current_step, state)
        tools = get_tools_for_step(current_step)

        tool_calls = {}
        full_response = ""

        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "system", "content": system_prompt}] + messages,
            tools=tools,
            stream=True,
        )

        for chunk in response:
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

            if func_name in ARIZ_TOOL_MAP:
                result = handle_ariz_tool_call(conv_id_for_flow, func_name, args)
            elif func_name == "llm_wiki" and "llm_wiki" in SKILLS:
                try:
                    result = SKILLS["llm_wiki"]["func"](**args)
                except Exception as e:
                    result = {"error": str(e)}
            else:
                result = {"error": f"未知工具: {func_name}"}

            # 输出工具结果（含 card_data 供前端渲染卡片）
            tool_text = f"\n\n**调用工具: {func_name}**\n```json\n{json.dumps(result, ensure_ascii=False, indent=2)}\n```\n"
            full_response += tool_text
            yield f'0:{json.dumps(tool_text)}\n'

        # 保存助手回复
        if conv_id and full_response:
            conn = get_db()
            conn.execute(
                "INSERT INTO messages (conversation_id, role, content, created_at) VALUES (?, ?, ?, ?)",
                (conv_id, "assistant", full_response, datetime.now().isoformat()),
            )
            conn.commit()
            conn.close()

    return Response(generate(), mimetype="text/plain; charset=utf-8",
                    headers={"X-Vercel-AI-Data-Stream": "v1"})


# ---- ARIZ 流程状态查询 ----
@app.route("/api/ariz/status/<conv_id>", methods=["GET"])
def ariz_status(conv_id):
    state = get_session_state(conv_id)
    return jsonify(state)


@app.route("/api/ariz/reset/<conv_id>", methods=["POST"])
def ariz_reset(conv_id):
    reset_flow(conv_id)
    return jsonify({"ok": True, "message": "流程已重置"})


@app.route("/api/ariz/confirm/<conv_id>", methods=["POST"])
def ariz_confirm(conv_id):
    """用户确认当前步骤，推进到下一步"""
    state = get_session_state(conv_id)
    current_step = state["current_step"]
    current_idx = get_step_index(current_step)
    current_label = get_step_label(current_step)

    # 检查是否有保存的结果
    step_result = get_step_result(conv_id, current_step)
    if not step_result:
        return jsonify({"ok": False, "error": f"{current_label}尚未保存结果"}), 400

    # 推进到下一步
    next_step = advance_step(conv_id)

    if next_step:
        next_label = get_step_label(next_step)
        return jsonify({
            "ok": True,
            "current_step": next_step,
            "current_step_index": get_step_index(next_step) + 1,
            "message": f"{current_label}已确认，进入{next_label}",
            "card_status": "done",  # 前端用这个把卡片状态从 current 改为 done
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
