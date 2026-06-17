"""Deep Agents Agent 封装 — 统一入口"""
import os
import structlog
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from llm import get_llm
from prompts import load_prompt
from ariz_state import ArizState, create_initial_state, get_step_label
from ariz_graph import build_ariz_graph
from context_manager import compress_messages
from observability import TraceContext

logger = structlog.get_logger()


class XagentAgent:
    """Xagent 核心 Agent — 基于 LangGraph + 上下文管理"""

    def __init__(self):
        self.llm = get_llm()
        self.system_prompt = load_prompt("system")
        self.graph = build_ariz_graph()
        logger.info("xagent_agent_initialized")

    async def run(self, user_message: str, state: ArizState = None,
                  thread_id: str = "default") -> dict:
        """运行一次 Agent 交互

        Args:
            user_message: 用户消息
            state: 当前状态（None 则创建初始状态）
            thread_id: 会话 ID

        Returns:
            {
                "response": str,           # 助手回复文本
                "card_data": dict,          # 步骤卡片数据
                "state": ArizState,         # 更新后的状态
                "trace": dict,              # 追踪摘要
            }
        """
        if state is None:
            state = create_initial_state()

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
            # 运行 LangGraph
            result = await self.graph.ainvoke(
                state,
                config={"configurable": {"thread_id": thread_id}},
            )

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

    def get_state(self, thread_id: str) -> dict:
        """获取会话状态"""
        try:
            snapshot = self.graph.get_state(
                config={"configurable": {"thread_id": thread_id}}
            )
            return snapshot.values if snapshot else create_initial_state()
        except Exception:
            return create_initial_state()


# 全局 Agent 实例（延迟初始化）
_agent = None


def get_agent() -> XagentAgent:
    """获取 Agent 单例"""
    global _agent
    if _agent is None:
        _agent = XagentAgent()
    return _agent
