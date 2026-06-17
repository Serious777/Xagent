"""Deep Agents Agent 封装 — 统一入口（单步执行模式）"""
import os
import structlog
from langchain_core.messages import HumanMessage, AIMessage

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


class XagentAgent:
    """Xagent 核心 Agent — 单步执行模式

    每次调用只执行当前步骤的 Node，不自动推进到下一步。
    用户确认后，由 confirm_step() 推进到下一步。
    """

    def __init__(self):
        self.llm = get_llm()
        self.system_prompt = load_prompt("system")
        # 会话状态存储（内存 + SQLite 持久化）
        self._states: dict[str, ArizState] = {}
        logger.info("xagent_agent_initialized")

    async def run(self, user_message: str, state: ArizState = None,
                  thread_id: str = "default") -> dict:
        """运行当前步骤（单步执行）

        Args:
            user_message: 用户消息
            state: 当前状态（None 则从存储中获取或创建）
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
            state = self._get_or_create_state(thread_id)

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
            # 获取当前步骤的 Node 函数
            current_step = state["current_step"]
            node_fn = STEP_NODES.get(current_step)

            if node_fn is None:
                return {
                    "response": "ARIZ 流程已完成！",
                    "card_data": {},
                    "state": state,
                    "trace": trace_ctx.finish(),
                }

            # 执行当前步骤的 Node
            logger.info("agent_run_step", step=current_step, thread_id=thread_id)
            result = await node_fn(state)

            # 保存状态
            self._states[thread_id] = result

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
        """用户确认当前步骤，推进到下一步

        注意：当前步骤的 Node 已经执行完毕并保存了结果，
        current_step 已经被 Node 更新为下一步了。
        所以 confirm 只需要返回当前状态即可。

        Returns:
            {
                "ok": bool,
                "current_step": str,        # 新的当前步骤
                "message": str,             # 确认消息
            }
        """
        state = self._states.get(thread_id)
        if state is None:
            return {"ok": False, "error": "会话不存在"}

        current_step = state["current_step"]

        # 检查是否已完成
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
        return self._get_or_create_state(thread_id)

    def _get_or_create_state(self, thread_id: str) -> ArizState:
        """获取或创建会话状态"""
        if thread_id not in self._states:
            self._states[thread_id] = create_initial_state()
        return self._states[thread_id]


# 全局 Agent 实例（延迟初始化）
_agent = None


def get_agent() -> XagentAgent:
    """获取 Agent 单例"""
    global _agent
    if _agent is None:
        _agent = XagentAgent()
    return _agent
