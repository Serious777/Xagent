"""Xagent - Agent 项目主入口"""
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

# ---- 数据库 ----
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
    logger.info("db_initialized", path=DB_PATH)

init_db()

# ---- LLM 客户端（Xiaomi MiMo） ----
client = OpenAI(
    api_key=os.getenv("XIAOMI_API_KEY"),
    base_url=os.getenv("XIAOMI_BASE_URL"),
)
MODEL = os.getenv("XIAOMI_MODEL", "mimo-v2.5")

logger.info("xagent_started", model=MODEL, skills=list(SKILLS.keys()))

# ---- 构建工具定义 ----
def build_tools():
    tools = []
    for name, skill_info in SKILLS.items():
        tools.append({
            "type": "function",
            "function": {
                "name": name,
                "description": skill_info["description"],
                "parameters": skill_info["parameters"],
            }
        })
    return tools

# ============ 对话 API ============

# 列出所有对话
@app.route("/api/conversations", methods=["GET"])
def list_conversations():
    conn = get_db()
    rows = conn.execute(
        "SELECT id, title, created_at, updated_at FROM conversations ORDER BY updated_at DESC"
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

# 新建对话
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
    logger.info("conversation_created", id=conv_id)
    return jsonify({"id": conv_id, "title": "新对话", "created_at": now, "updated_at": now})

# 删除对话
@app.route("/api/conversations/<conv_id>", methods=["DELETE"])
def delete_conversation(conv_id):
    conn = get_db()
    conn.execute("DELETE FROM messages WHERE conversation_id = ?", (conv_id,))
    conn.execute("DELETE FROM conversations WHERE id = ?", (conv_id,))
    conn.commit()
    conn.close()
    logger.info("conversation_deleted", id=conv_id)
    return jsonify({"ok": True})

# 更新对话标题
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

# 获取对话历史消息
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
            # 确保对话存在
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
            # 自动用第一条消息作为标题
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
        tools = build_tools()
        tool_calls = {}
        full_response = ""

        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "system", "content": "你是一个智能助手，可以根据需要调用工具完成任务。"}] + messages,
            tools=tools if tools else None,
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

        for tc_info in tool_calls.values():
            func_name = tc_info["name"]
            if func_name and func_name in SKILLS:
                try:
                    args = json.loads(tc_info["arguments"]) if tc_info["arguments"] else {}
                except json.JSONDecodeError:
                    args = {}
                logger.info("tool_called", tool=func_name, args=list(args.keys()))
                try:
                    result = SKILLS[func_name]["func"](**args)
                    logger.info("tool_completed", tool=func_name)
                except Exception as e:
                    result = {"error": str(e)}
                    logger.error("tool_failed", tool=func_name, error=str(e))
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
