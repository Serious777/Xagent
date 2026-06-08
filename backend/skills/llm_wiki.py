"""LLM Wiki Skill - 知识库管理"""
import os
import structlog
from datetime import datetime
from pathlib import Path

logger = structlog.get_logger()

# Wiki 根目录
WIKI_ROOT = Path("/Users/chenyw/LLM-Wiki")

SKILL = {
    "description": "管理 LLM Wiki 知识库：添加资料到知识库、查询知识库、查看知识库状态",
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["ingest", "query", "status", "list"],
                "description": "操作类型：ingest=添加资料, query=查询知识, status=查看状态, list=列出文章",
            },
            "topic": {
                "type": "string",
                "description": "主题分类（ingest 时必填）",
            },
            "content": {
                "type": "string",
                "description": "要添加的内容或 URL（ingest 时必填）",
            },
            "query": {
                "type": "string",
                "description": "查询关键词（query 时必填）",
            },
        },
        "required": ["action"],
    },
    "func": None,
}

def _ensure_wiki_structure():
    """确保 Wiki 目录结构存在"""
    (WIKI_ROOT / "raw").mkdir(parents=True, exist_ok=True)
    (WIKI_ROOT / "wiki").mkdir(parents=True, exist_ok=True)

    index_file = WIKI_ROOT / "wiki" / "index.md"
    if not index_file.exists():
        index_file.write_text("# Knowledge Base Index\n")

    log_file = WIKI_ROOT / "wiki" / "log.md"
    if not log_file.exists():
        log_file.write_text("# Wiki Log\n")

def _get_status() -> dict:
    """获取 Wiki 状态"""
    raw_dir = WIKI_ROOT / "raw"
    wiki_dir = WIKI_ROOT / "wiki"

    raw_count = len(list(raw_dir.rglob("*.md"))) if raw_dir.exists() else 0
    wiki_count = len(list(wiki_dir.rglob("*.md"))) if wiki_dir.exists() else 0

    topics = []
    if raw_dir.exists():
        topics = [d.name for d in raw_dir.iterdir() if d.is_dir()]

    return {
        "wiki_root": str(WIKI_ROOT),
        "raw_articles": raw_count,
        "wiki_articles": wiki_count,
        "topics": topics,
    }

def _list_articles() -> list:
    """列出所有 Wiki 文章"""
    wiki_dir = WIKI_ROOT / "wiki"
    articles = []
    if wiki_dir.exists():
        for topic_dir in wiki_dir.iterdir():
            if topic_dir.is_dir():
                for article in topic_dir.glob("*.md"):
                    articles.append({
                        "topic": topic_dir.name,
                        "title": article.stem,
                        "path": str(article.relative_to(WIKI_ROOT)),
                    })
    return articles

def _ingest(topic: str, content: str) -> dict:
    """添加资料到 Wiki"""
    _ensure_wiki_structure()

    raw_dir = WIKI_ROOT / "raw" / topic
    raw_dir.mkdir(parents=True, exist_ok=True)

    # 生成文件名
    today = datetime.now().strftime("%Y-%m-%d")
    slug = content[:50].replace(" ", "-").replace("/", "-").lower()
    filename = f"{today}-{slug}.md"

    # 写入 raw 文件
    raw_file = raw_dir / filename
    raw_content = f"""---
source: manual
collected: {today}
published: Unknown
---

{content}
"""
    raw_file.write_text(raw_content)

    logger.info("wiki_ingested", topic=topic, file=filename)

    # 记录日志
    log_file = WIKI_ROOT / "wiki" / "log.md"
    with open(log_file, "a") as f:
        f.write(f"\n- [{today}] Ingested into `{topic}`: {filename}")

    return {
        "status": "success",
        "topic": topic,
        "file": filename,
        "message": f"资料已保存到 raw/{topic}/{filename}",
    }

def _query_wiki(query: str) -> dict:
    """查询 Wiki 知识库"""
    wiki_dir = WIKI_ROOT / "wiki"
    if not wiki_dir.exists():
        return {"error": "Wiki 不存在，请先 ingest 资料"}

    results = []
    query_lower = query.lower()

    for md_file in wiki_dir.rglob("*.md"):
        if md_file.name in ("index.md", "log.md"):
            continue
        content = md_file.read_text()
        if query_lower in content.lower():
            results.append({
                "file": str(md_file.relative_to(WIKI_ROOT)),
                "snippet": content[:200],
            })

    return {"query": query, "results": results, "count": len(results)}

def llm_wiki(action: str, topic: str = "", content: str = "", query: str = "") -> dict:
    """Wiki 操作入口"""
    logger.info("wiki_action", action=action, topic=topic)

    if action == "status":
        return _get_status()
    elif action == "list":
        return {"articles": _list_articles()}
    elif action == "ingest":
        if not topic or not content:
            return {"error": "ingest 需要 topic 和 content 参数"}
        return _ingest(topic, content)
    elif action == "query":
        if not query:
            return {"error": "query 需要 query 参数"}
        return _query_wiki(query)
    else:
        return {"error": f"未知操作: {action}"}

SKILL["func"] = llm_wiki
