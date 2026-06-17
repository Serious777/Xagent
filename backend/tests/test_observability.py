"""可观测性模块测试"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from observability import TraceContext


def test_trace_context_init():
    """验证追踪上下文初始化"""
    ctx = TraceContext("test-123", "problem")
    assert ctx.thread_id == "test-123"
    assert ctx.step == "problem"
    assert ctx.llm_calls == []
    assert ctx.tool_calls == []
    assert ctx.tokens_used == {"input": 0, "output": 0, "total": 0}


def test_trace_context_record_llm_call():
    """验证 LLM 调用记录"""
    ctx = TraceContext("test-123", "problem")
    ctx.record_llm_call("mimo-v2.5", 1500.0, input_tokens=100, output_tokens=50)
    ctx.record_llm_call("mimo-v2.5", 2000.0, input_tokens=200, output_tokens=80)

    assert len(ctx.llm_calls) == 2
    assert ctx.tokens_used["input"] == 300
    assert ctx.tokens_used["output"] == 130
    assert ctx.tokens_used["total"] == 430


def test_trace_context_record_tool_call():
    """验证工具调用记录"""
    ctx = TraceContext("test-123", "problem")
    ctx.record_tool_call("ariz_step1_problem", 500.0, success=True)
    ctx.record_tool_call("ariz_step2_components", 300.0, success=False)

    assert len(ctx.tool_calls) == 2
    assert ctx.tool_calls[0]["success"] is True
    assert ctx.tool_calls[1]["success"] is False


def test_trace_context_finish():
    """验证追踪完成"""
    ctx = TraceContext("test-123", "problem")
    ctx.record_llm_call("mimo-v2.5", 1500.0, input_tokens=100, output_tokens=50)
    summary = ctx.finish()

    assert summary["thread_id"] == "test-123"
    assert summary["step"] == "problem"
    assert summary["llm_calls"] == 1
    assert summary["total_ms"] >= 0


def test_trace_context_errors():
    """验证错误记录"""
    ctx = TraceContext("test-123", "problem")
    ctx.record_error("test error 1")
    ctx.record_error("test error 2")

    assert len(ctx.errors) == 2
    summary = ctx.finish()
    assert summary["errors"] == 2
