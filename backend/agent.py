"""Deep Agents Agent 封装 — 单步执行模式 + SQLite 持久化"""
import json
import os
import sqlite3
import structlog
from contextlib import contextmanager
from datetime import datetime
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from llm import get_llm
from prompts import load_prompt
from ariz_state import ArizState, create_initial_state, get_step_label, ARIZ_STEP_NAMES, get_next_step
from context_manager import compress_messages
from observability import TraceContext
from ariz_nodes import (
    step1_problem_node, step2_components_node, step3_contacts_node,
    step4_function_node, step5_structure_node, step6_summary_node,
    step7_causal_node, step8_keypoint_node, step9_solution_node,
)

logger = structlog.get_logger()

# 步骤名 → Node 函数映射
STEP_NODES = {
    "problem": step1_problem_node,
    "components": step2_components_node,
    "contacts": step3_contacts_node,
    "function": step4_function_node,
    "structure": step5_structure_node,
    "summary": step6_summary_node,
    "causal": step7_causal_node,
    "keypoint": step8_keypoint_node,
    "solution": step9_solution_node,
}

# SQLite 数据库路径
DB_PATH = os.path.join(os.path.dirname(__file__), "xagent.db")


# ============ 数据库连接管理 ============

@contextmanager
def _get_db():
    """数据库连接上下文管理器，自动提交/关闭/回滚"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _init_agent_table():
    """初始化 Agent 状态表"""
    with _get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS agent_states (
                thread_id TEXT PRIMARY KEY,
                current_step TEXT NOT NULL DEFAULT 'problem',
                step_results TEXT NOT NULL DEFAULT '{}',
                messages_json TEXT NOT NULL DEFAULT '[]',
                card_data TEXT NOT NULL DEFAULT '{}',
                updated_at TEXT NOT NULL
            );
        """)


_init_agent_table()


# ============ 消息序列化 ============

def _serialize_messages(messages: list) -> list:
    """将 LangChain messages 序列化为 JSON 可存储格式"""
    return [
        {"role": "system", "content": msg.content} if isinstance(msg, SystemMessage)
        else {"role": "user", "content": msg.content} if isinstance(msg, HumanMessage)
        else {"role": "assistant", "content": msg.content}
        for msg in messages
        if isinstance(msg, (SystemMessage, HumanMessage, AIMessage))
    ]


def _deserialize_messages(messages_json: list) -> list:
    """将 JSON 格式反序列化为 LangChain messages"""
    role_map = {"system": SystemMessage, "user": HumanMessage, "assistant": AIMessage}
    return [
        role_map[msg["role"]](content=msg["content"])
        for msg in messages_json
        if msg.get("role") in role_map
    ]


# ============ Agent ============

class XagentAgent:
    """Xagent 核心 Agent — 单步执行模式 + SQLite 持久化"""

    def __init__(self):
        self.llm = get_llm()
        self.system_prompt = load_prompt("system")
        logger.info("xagent_agent_initialized")

    async def run(self, user_message: str, state: ArizState = None,
                  thread_id: str = "default") -> dict:
        """运行当前步骤（单步执行）"""
        if state is None:
            state = self._load_state(thread_id)

        # 创建新 state，避免修改调用方的原始 dict（不可变模式）
        user_msg = HumanMessage(content=user_message)
        state = {
            **state,
            "messages": state.get("messages", []) + [user_msg],
            "thread_id": thread_id,
        }

        # 上下文压缩
        state["messages"] = await compress_messages(
            state["messages"], state["current_step"]
        )

        # 追踪
        trace_ctx = TraceContext(thread_id, state["current_step"])

        try:
            current_step = state["current_step"]
            node_fn = STEP_NODES.get(current_step)

            if node_fn is None:
                return {
                    "response": "ARIZ 流程已完成！",
                    "card_data": {},
                    "state": state,
                    "trace": trace_ctx.finish(),
                }

            logger.info("agent_run_step", step=current_step, thread_id=thread_id)
            result = await node_fn(state)

            # 持久化到 SQLite
            self._save_state(thread_id, result)

            # 提取回复
            response_text = ""
            if result.get("messages"):
                last_msg = result["messages"][-1]
                if hasattr(last_msg, "content"):
                    response_text = last_msg.content

            return {
                "response": response_text,
                "card_data": result.get("card_data", {}),
                "state": result,
                "trace": trace_ctx.finish(),
            }

        except Exception as e:
            trace_ctx.record_error(str(e))
            logger.error("agent_run_failed", error=str(e), thread_id=thread_id)
            # 异常时也保存状态，避免用户消息丢失
            try:
                self._save_state(thread_id, state)
            except Exception as save_err:
                logger.error("state_save_on_error_failed", error=str(save_err))
            return {
                "response": f"⚠️ AI 服务暂时不可用：{str(e)}",
                "card_data": {},
                "state": state,
                "trace": trace_ctx.finish(),
            }

    def confirm_step(self, thread_id: str) -> dict:
        """用户确认当前步骤（步骤已由节点函数推进，此方法仅返回当前状态）"""
        state = self._load_state(thread_id)
        current_step = state["current_step"]

        if current_step == "done":
            return {
                "ok": True,
                "current_step": None,
                "message": "ARIZ 全部流程已完成！",
            }

        current_label = get_step_label(current_step)
        logger.info("step_confirmed", thread_id=thread_id, step=current_step)

        return {
            "ok": True,
            "current_step": current_step,
            "message": f"已确认，进入{current_label}",
        }

    def get_state(self, thread_id: str) -> ArizState:
        """获取会话状态"""
        return self._load_state(thread_id)

    def _load_state(self, thread_id: str) -> ArizState:
        """从 SQLite 加载状态（返回新 dict，不修改外部状态）"""
        with _get_db() as conn:
            row = conn.execute(
                "SELECT current_step, step_results, messages_json, card_data "
                "FROM agent_states WHERE thread_id = ?",
                (thread_id,),
            ).fetchone()

        if row:
            return {
                "current_step": row["current_step"],
                "step_results": json.loads(row["step_results"]),
                "messages": _deserialize_messages(json.loads(row["messages_json"])),
                "card_data": json.loads(row["card_data"]),
                "error": None,
                "thread_id": thread_id,
            }

        return create_initial_state() | {"thread_id": thread_id}

    def _save_state(self, thread_id: str, state: ArizState):
        """保存状态到 SQLite"""
        messages_json = json.dumps(
            _serialize_messages(state.get("messages", [])), ensure_ascii=False
        )
        step_results = json.dumps(state.get("step_results", {}), ensure_ascii=False)
        card_data = json.dumps(state.get("card_data", {}), ensure_ascii=False)
        now = datetime.now().isoformat()

        with _get_db() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO agent_states
                   (thread_id, current_step, step_results, messages_json, card_data, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (thread_id, state.get("current_step", "problem"), step_results,
                 messages_json, card_data, now),
            )
        logger.info("state_saved", thread_id=thread_id, step=state.get("current_step"))


# 全局 Agent 实例（延迟初始化）
_agent = None


def get_agent() -> XagentAgent:
    """获取 Agent 单例"""
    global _agent
    if _agent is None:
        _agent = XagentAgent()
    return _agent
