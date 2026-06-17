"""Xagent - 动力电池PACK创新智能体（LangGraph + Deep Agents）"""
import json
import os
import sqlite3
import uuid
import asyncio
from contextlib import contextmanager
from datetime import datetime
import structlog
from flask import Flask, request, Response, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

from skills import SKILLS
from agent import get_agent
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
logger.info("xagent_started")


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
    logger.info("conversation_created", id=conv_id)
    return jsonify({"id": conv_id, "title": "新对话", "created_at": now, "updated_at": now})


@app.route("/api/conversations/<conv_id>", methods=["DELETE"])
def delete_conversation(conv_id):
    with get_db() as conn:
        conn.execute("DELETE FROM messages WHERE conversation_id = ?", (conv_id,))
        conn.execute("DELETE FROM conversations WHERE id = ?", (conv_id,))
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


# ============ 聊天接口 ============

@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.json
    messages = data.get("messages", [])
    conv_id = data.get("conversation_id")

    logger.info("chat_received", message_count=len(messages), conversation_id=conv_id)

    if conv_id and messages:
        _save_user_message(conv_id, messages)

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

            # 运行 Agent（单步执行）
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
            logger.error("agent_error", error=str(e))
            error_msg = "\n\n⚠️ AI 服务暂时不可用，请稍后重试。"
            yield f'0:{json.dumps(error_msg)}\n'

    return Response(generate(), mimetype="text/plain; charset=utf-8",
                    headers={"X-Vercel-AI-Data-Stream": "v1"})


# ============ ARIZ 流程接口 ============

@app.route("/api/ariz/status/<conv_id>", methods=["GET"])
def ariz_status(conv_id):
    agent = get_agent()
    state = agent.get_state(conv_id)
    serializable_state = {
        "current_step": state.get("current_step"),
        "step_results": state.get("step_results", {}),
        "card_data": state.get("card_data", {}),
        "error": state.get("error"),
        "message_count": len(state.get("messages", [])),
    }
    return jsonify(serializable_state)


@app.route("/api/ariz/reset/<conv_id>", methods=["POST"])
def ariz_reset(conv_id):
    """重置 ARIZ 流程"""
    with get_db() as conn:
        try:
            conn.execute("DELETE FROM agent_states WHERE thread_id = ?", (conv_id,))
        except Exception:
            pass  # 表可能不存在
    return jsonify({"ok": True, "message": "流程已重置"})


@app.route("/api/ariz/confirm/<conv_id>", methods=["POST"])
def ariz_confirm(conv_id):
    """用户确认当前步骤"""
    agent = get_agent()
    result = agent.confirm_step(conv_id)
    if result.get("ok"):
        return jsonify({**result, "card_status": "done"})
    else:
        return jsonify(result), 400


# ============ Skill 列表 ============

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
