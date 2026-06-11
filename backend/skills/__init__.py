"""Xagent Skills 注册表"""
from skills.llm_wiki import SKILL as llm_wiki_skill
from skills.ariz_engine import SKILL as ariz_engine_skill
from skills.ariz_step1_problem import SKILL as ariz_step1_skill
from skills.ariz_step2_components import SKILL as ariz_step2_skill
from skills.ariz_step3_contacts import SKILL as ariz_step3_skill
from skills.ariz_step4_function import SKILL as ariz_step4_skill
from skills.ariz_step5_structure import SKILL as ariz_step5_skill
from skills.ariz_step6_summary import SKILL as ariz_step6_skill
from skills.ariz_step7_causal import SKILL as ariz_step7_skill
from skills.ariz_step8_keypoint import SKILL as ariz_step8_skill
from skills.ariz_step9_solution import SKILL as ariz_step9_skill

SKILLS = {
    # ARIZ 流程
    "ariz_engine": ariz_engine_skill,
    "ariz_step1_problem": ariz_step1_skill,
    "ariz_step2_components": ariz_step2_skill,
    "ariz_step3_contacts": ariz_step3_skill,
    "ariz_step4_function": ariz_step4_skill,
    "ariz_step5_structure": ariz_step5_skill,
    "ariz_step6_summary": ariz_step6_skill,
    "ariz_step7_causal": ariz_step7_skill,
    "ariz_step8_keypoint": ariz_step8_skill,
    "ariz_step9_solution": ariz_step9_skill,
    # 原有技能
    "llm_wiki": llm_wiki_skill,
}
