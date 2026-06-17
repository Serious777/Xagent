"""Prompt 文件加载器"""
from pathlib import Path

PROMPTS_DIR = Path(__file__).parent / "prompts"


def load_prompt(name: str) -> str:
    """加载 prompt 模板文件

    Args:
        name: prompt 名称（不含 .md 后缀），如 "system"、"step1_problem"

    Returns:
        prompt 文本内容

    Raises:
        FileNotFoundError: prompt 文件不存在
    """
    path = PROMPTS_DIR / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"Prompt file not found: {path}")
    return path.read_text(encoding="utf-8")


def list_prompts() -> list:
    """列出所有可用的 prompt 名称"""
    return [p.stem for p in PROMPTS_DIR.glob("*.md")]
