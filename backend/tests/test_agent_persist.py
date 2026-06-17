"""Agent 持久化测试"""
import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agent import _serialize_messages, _deserialize_messages, XagentAgent
from ariz_state import create_initial_state
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage


def test_serialize_messages():
    """验证消息序列化"""
    messages = [
        SystemMessage(content="系统提示"),
        HumanMessage(content="用户消息"),
        AIMessage(content="助手回复"),
    ]
    serialized = _serialize_messages(messages)
    assert len(serialized) == 3
    assert serialized[0] == {"role": "system", "content": "系统提示"}
    assert serialized[1] == {"role": "user", "content": "用户消息"}
    assert serialized[2] == {"role": "assistant", "content": "助手回复"}


def test_deserialize_messages():
    """验证消息反序列化"""
    data = [
        {"role": "system", "content": "系统提示"},
        {"role": "user", "content": "用户消息"},
        {"role": "assistant", "content": "助手回复"},
    ]
    messages = _deserialize_messages(data)
    assert len(messages) == 3
    assert isinstance(messages[0], SystemMessage)
    assert isinstance(messages[1], HumanMessage)
    assert isinstance(messages[2], AIMessage)


def test_serialize_deserialize_roundtrip():
    """验证序列化/反序列化往返"""
    original = [
        SystemMessage(content="你好"),
        HumanMessage(content="测试"),
        AIMessage(content="回复"),
    ]
    serialized = _serialize_messages(original)
    restored = _deserialize_messages(serialized)

    assert len(restored) == len(original)
    for orig, rest in zip(original, restored):
        assert type(orig) == type(rest)
        assert orig.content == rest.content


def test_agent_save_load_state():
    """验证 Agent 状态持久化"""
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

    agent = XagentAgent()

    # 创建一个测试状态
    state = create_initial_state()
    state["thread_id"] = "test_persist_001"
    state["step_results"] = {"problem": {"problem_object": "热管理系统"}}
    state["messages"] = [
        HumanMessage(content="测试消息"),
        AIMessage(content="测试回复"),
    ]
    state["card_data"] = {"step": 1, "title": "问题识别"}

    # 保存
    agent._save_state("test_persist_001", state)

    # 加载
    loaded = agent._load_state("test_persist_001")

    assert loaded["current_step"] == "problem"
    assert loaded["step_results"]["problem"]["problem_object"] == "热管理系统"
    assert len(loaded["messages"]) == 2
    assert loaded["card_data"]["step"] == 1
    assert loaded["thread_id"] == "test_persist_001"

    # 清理
    import sqlite3
    conn = sqlite3.connect(os.path.join(os.path.dirname(__file__), "..", "xagent.db"))
    conn.execute("DELETE FROM agent_states WHERE thread_id = 'test_persist_001'")
    conn.commit()
    conn.close()
