"""自建可观测性模块 — 替代 LangSmith"""
import time
import functools
import structlog
from typing import Optional

logger = structlog.get_logger()


class TraceContext:
    """追踪上下文，记录单次 Agent 调用的全链路信息"""

    def __init__(self, thread_id: str, step: str):
        self.thread_id = thread_id
        self.step = step
        self.start_time = time.time()
        self.llm_calls: list = []
        self.tool_calls: list = []
        self.tokens_used: dict = {"input": 0, "output": 0, "total": 0}
        self.errors: list = []

    def record_llm_call(self, model: str, latency_ms: float,
                        input_tokens: int = 0, output_tokens: int = 0):
        """记录一次 LLM 调用"""
        self.llm_calls.append({
            "model": model,
            "latency_ms": round(latency_ms),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        })
        self.tokens_used["input"] += input_tokens
        self.tokens_used["output"] += output_tokens
        self.tokens_used["total"] += input_tokens + output_tokens

    def record_tool_call(self, tool_name: str, latency_ms: float, success: bool):
        """记录一次工具调用"""
        self.tool_calls.append({
            "tool": tool_name,
            "latency_ms": round(latency_ms),
            "success": success,
        })

    def record_error(self, error: str):
        """记录错误"""
        self.errors.append(error)

    def finish(self) -> dict:
        """完成追踪，返回摘要"""
        total_ms = round((time.time() - self.start_time) * 1000)
        summary = {
            "thread_id": self.thread_id,
            "step": self.step,
            "total_ms": total_ms,
            "llm_calls": len(self.llm_calls),
            "tool_calls": len(self.tool_calls),
            "tokens": self.tokens_used,
            "errors": len(self.errors),
        }
        logger.info("trace_summary", **summary)
        return summary


def trace_step(step: str):
    """装饰器：追踪 ARIZ 步骤执行"""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(state, *args, **kwargs):
            thread_id = state.get("thread_id", "unknown")
            ctx = TraceContext(thread_id, step)
            try:
                result = await func(state, *args, **kwargs, trace_ctx=ctx)
                ctx.finish()
                return result
            except Exception as e:
                ctx.record_error(str(e))
                ctx.finish()
                raise
        return wrapper
    return decorator


def trace_llm_call(model: str):
    """装饰器：追踪单次 LLM 调用"""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = await func(*args, **kwargs)
                latency_ms = (time.time() - start) * 1000
                usage = getattr(result, "usage_metadata", None) or {}
                logger.info("llm_call",
                    model=model,
                    latency_ms=round(latency_ms),
                    input_tokens=usage.get("input_tokens", 0),
                    output_tokens=usage.get("output_tokens", 0),
                )
                return result
            except Exception as e:
                latency_ms = (time.time() - start) * 1000
                logger.error("llm_call_failed",
                    model=model,
                    latency_ms=round(latency_ms),
                    error=str(e),
                )
                raise
        return wrapper
    return decorator
