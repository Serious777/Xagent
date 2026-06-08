"""Xagent Skills 注册表"""
from skills.web_search import SKILL as web_search_skill
from skills.llm_wiki import SKILL as llm_wiki_skill

SKILLS = {
    "web_search": web_search_skill,
    "llm_wiki": llm_wiki_skill,
}
