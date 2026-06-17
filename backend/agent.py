"""Deep Agents Agent 封装 — 单步执行模式 + SQLite 持久化"""
import json
import os
import sqlite3
import structlog
from datetime import datetime
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from llm import get_llm
from prompts import load_prompt
from ariz_state import ArizState, create_initial_state, get_step_label, ARIZ_STEP_NAMES
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


def _init_agent_table():
    """初始化 Agent 状态表"""
    conn = sqlite3.connect(DB_PATH)
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
    conn.commit()
    conn.close()


_init_agent_table()


def _serialize_messages(messages: list) -> list:
    """将 LangChain messages 序列化为 JSON 可存储格式"""
    result = []
    for msg in messages:
        if isinstance(msg, SystemMessage):
            result.append({"role": "system", "content": msg.content})
        elif isinstance(msg, HumanMessage):
            result.append({"role": "user", "content": msg.content})
        elif isinstance(msg, AIMessage):
            result.append({"role": "assistant", "content": msg.content})
    return result


def _deserialize_messages(messages_json: list) -> list:
    """将 JSON 格式反序列化为 LangChain messages"""
    result = []
    for msg in messages_json:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if role == "system":
            result.append(SystemMessage(content=content))
        elif role == "user":
            result.append(HumanMessage(content=content))
        elif role == "assistant":
            result.append(AIMessage(content=content))
    return result


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

        # 添加用户消息
        user_msg = HumanMessage(content=user_message)
        state["messages"] = state.get("messages", []) + [user_msg]
        state["thread_id"] = thread_id

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
            trace_ctx.finish()
            logger.error("agent_run_failed", error=str(e), thread_id=thread_id)
            return {
                "response": f"⚠️ AI 服务暂时不可用：{str(e)}",
                "card_data": {},
                "state": state,
                "trace": trace_ctx.finish(),
            }

    def confirm_step(self, thread_id: str) -> dict:
        """用户确认当前步骤，推进到下一步"""
        state = self._load_state(thread_id)
        current_step = state["current_step"]

        if current_step == "done":
            return {
                "ok": True,
                "current_step": None,
                "message": "ARIZ 全部流程已完成！",
            }

        current_label = get_step_label(current_step)
        logger.info("step_confirmed", thread_id=thread_id, to_step=current_step)

        return {
            "ok": True,
            "current_step": current_step,
            "message": f"已确认，进入{current_label}",
        }

    def get_state(self, thread_id: str) -> ArizState:
        """获取会话状态"""
        return self._load_state(thread_id)

    def _load_state(self, thread_id: str) -> ArizState:
        """从 SQLite 加载状态"""
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT current_step, step_results, messages_json, card_data FROM agent_states WHERE thread_id = ?",
            (thread_id,),
        ).fetchone()
        conn.close()

        if row:
            state = create_initial_state()
            state["current_step"] = row["current_step"]
            state["step_results"] = json.loads(row["step_results"])
            state["messages"] = _deserialize_messages(json.loads(row["messages_json"]))
            state["card_data"] = json.loads(row["card_data"])
            state["thread_id"] = thread_id
            return state
        else:
            state = create_initial_state()
            state["thread_id"] = thread_id
            return state

    def _save_state(self, thread_id: str, state: ArizState):
        """保存状态到 SQLite"""
        messages_json = json.dumps(_serialize_messages(state.get("messages", [])), ensure_ascii=False)
        step_results = json.dumps(state.get("step_results", {}), ensure_ascii=False)
        card_data = json.dumps(state.get("card_data", {}), ensure_ascii=False)
        now = datetime.now().isoformat()

        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            """INSERT OR REPLACE INTO agent_states
               (thread_id, current_step, step_results, messages_json, card_data, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (thread_id, state.get("current_step", "problem"), step_results,
             messages_json, card_data, now),
        )
        conn.commit()
        conn.close()
        logger.info("state_saved", thread_id=thread_id, step=state.get("current_step"))


# 全局 Agent 实例（延迟初始化）
_agent = None


def get_agent() -> XagentAgent:
    """获取 Agent 单例"""
    global _agent
    if _agent is None:
        _agent = XagentAgent()
    return _agent
