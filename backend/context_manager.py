"""上下文压缩中间件 — 管理长对话的 token 预算"""
import structlog
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from llm import get_llm_no_stream

logger = structlog.get_logger()

# 每个步骤的上下文策略
CONTEXT_RULES = {
    "problem":     {"max_messages": 20, "summarize_threshold": 15},
    "components":  {"max_messages": 25, "summarize_threshold": 20},
    "contacts":    {"max_messages": 25, "summarize_threshold": 20},
    "function":    {"max_messages": 30, "summarize_threshold": 25},
    "structure":   {"max_messages": 30, "summarize_threshold": 25},
    "summary":     {"max_messages": 35, "summarize_threshold": 30},
    "causal":      {"max_messages": 35, "summarize_threshold": 30},
    "keypoint":    {"max_messages": 40, "summarize_threshold": 35},
    "solution":    {"max_messages": 50, "summarize_threshold": 45},
}


def estimate_tokens(text: str) -> int:
    """粗略估算 token 数（中文约 1.5 字/token）"""
    return max(1, len(text) // 2)


def estimate_messages_tokens(messages: list) -> int:
    """估算消息列表的总 token 数"""
    total = 0
    for msg in messages:
        if hasattr(msg, "content"):
            total += estimate_tokens(msg.content)
    return total


async def compress_messages(messages: list, current_step: str) -> list:
    """压缩消息列表，保持在 token 预算内

    策略：
    1. 保留 system prompt（第一条）
    2. 保留最近 N 条消息（N 由 CONTEXT_RULES 决定）
    3. 中间的消息压缩为摘要
    """
    if not messages:
        return messages

    rules = CONTEXT_RULES.get(current_step, {"max_messages": 30, "summarize_threshold": 25})
    max_msgs = rules["max_messages"]

    if len(messages) <= max_msgs:
        return messages

    # 分离 system prompt 和对话消息
    system_msgs = []
    conversation_msgs = []
    for msg in messages:
        if isinstance(msg, SystemMessage):
            system_msgs.append(msg)
        else:
            conversation_msgs.append(msg)

    if len(conversation_msgs) <= max_msgs:
        return messages

    # 需要压缩：保留最近的 max_msgs 条，压缩前面的
    keep_recent = max_msgs - 2  # 留 2 个位置给摘要
    old_messages = conversation_msgs[:-keep_recent]
    recent_messages = conversation_msgs[-keep_recent:]

    # 生成摘要
    summary = await summarize_messages(old_messages)

    # 重组消息列表
    compressed = system_msgs + [
        SystemMessage(content=f"[历史对话摘要]\n{summary}"),
    ] + recent_messages

    logger.info("context_compressed",
        original_count=len(messages),
        compressed_count=len(compressed),
        summarized_count=len(old_messages),
        step=current_step,
    )

    return compressed


async def summarize_messages(messages: list) -> str:
    """用 LLM 将消息压缩为摘要"""
    if not messages:
        return ""

    # 提取文本内容
    texts = []
    for msg in messages:
        if hasattr(msg, "content") and msg.content:
            role = "用户" if isinstance(msg, HumanMessage) else "助手"
            texts.append(f"{role}: {msg.content[:200]}")

    if not texts:
        return ""

    combined = "\n".join(texts)

    # 用 LLM 做摘要
    try:
        llm = get_llm_no_stream()
        result = await llm.ainvoke([
            SystemMessage(content="请将以下对话历史压缩为简洁的摘要，保留关键信息（问题识别、分析结论、用户偏好）。不超过 300 字。"),
            HumanMessage(content=combined),
        ])
        return result.content
    except Exception as e:
        logger.error("summarize_failed", error=str(e))
        # 摘要失败时，直接截断
        return f"[对话历史过长，已截断。共 {len(messages)} 条消息。]"
