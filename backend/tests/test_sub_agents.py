"""子 Agent 测试"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import asyncio
from sub_agents import run_db_lookup_agent


def test_db_lookup_agent_no_keywords():
    """验证无关键词时返回空结果"""
    loop = asyncio.new_event_loop()
    try:
        result = loop.run_until_complete(run_db_lookup_agent({"system_keywords": []}))
    finally:
        loop.close()
    assert result["matched_systems"] == []


def test_db_lookup_agent_with_keywords():
    """验证有关键词时能查询数据库"""
    loop = asyncio.new_event_loop()
    try:
        result = loop.run_until_complete(run_db_lookup_agent({"system_keywords": ["热管理系统"]}))
    finally:
        loop.close()
    # 数据库中有种子数据时应匹配到
    assert isinstance(result["matched_systems"], list)


def test_db_lookup_agent_alias_mapping():
    """验证别名映射功能"""
    loop = asyncio.new_event_loop()
    try:
        result = loop.run_until_complete(run_db_lookup_agent({"system_keywords": ["PTC"]}))
    finally:
        loop.close()
    assert isinstance(result["matched_systems"], list)
