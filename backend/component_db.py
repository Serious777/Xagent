"""组件知识库 — 数据库读写层（上下文管理器）"""
import os
import sqlite3
from contextlib import contextmanager
import structlog

logger = structlog.get_logger()

DB_PATH = os.path.join(os.path.dirname(__file__), "components.db")
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "db_schema.sql")


@contextmanager
def get_db():
    """数据库连接上下文管理器，自动提交/关闭/回滚"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """初始化数据库表"""
    with get_db() as conn:
        with open(SCHEMA_PATH) as f:
            conn.executescript(f.read())
    logger.info("component_db_initialized", path=DB_PATH)


def search_system(keyword: str) -> list:
    """根据关键词搜索系统"""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, name, description FROM systems WHERE name LIKE ? OR description LIKE ?",
            (f"%{keyword}%", f"%{keyword}%"),
        ).fetchall()
    return [dict(r) for r in rows]


def get_system_components(system_id: int) -> dict:
    """获取某个系统下的所有组件及其功能"""
    with get_db() as conn:
        system = conn.execute(
            "SELECT id, name, description FROM systems WHERE id = ?", (system_id,)
        ).fetchone()
        if not system:
            return {"error": f"系统ID {system_id} 不存在"}

        system_dict = dict(system)

        components = conn.execute(
            "SELECT id, name, description, is_core FROM components WHERE system_id = ?",
            (system_id,),
        ).fetchall()

        component_list = []
        for comp in components:
            comp_dict = dict(comp)
            functions = conn.execute(
                "SELECT function_name, function_type, description, target "
                "FROM component_functions WHERE component_id = ?",
                (comp["id"],),
            ).fetchall()
            comp_dict["functions"] = [dict(f) for f in functions]
            component_list.append(comp_dict)

        relations = conn.execute(
            """
            SELECT ca.name as component_a, cb.name as component_b,
                   r.relation_type, r.interface_desc
            FROM component_relations r
            JOIN components ca ON r.component_a_id = ca.id
            JOIN components cb ON r.component_b_id = cb.id
            WHERE ca.system_id = ? AND cb.system_id = ?
            """,
            (system_id, system_id),
        ).fetchall()

    return {
        "system": system_dict,
        "components": component_list,
        "relations": [dict(r) for r in relations],
    }


def get_all_systems() -> list:
    """列出所有已录入的系统"""
    with get_db() as conn:
        rows = conn.execute("SELECT id, name, description FROM systems ORDER BY id").fetchall()
    return [dict(r) for r in rows]


def add_system(name: str, description: str = "") -> int:
    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO systems (name, description) VALUES (?, ?)",
            (name, description),
        )
    return cursor.lastrowid


def add_component(system_id: int, name: str, description: str = "", is_core: int = 0) -> int:
    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO components (system_id, name, description, is_core) VALUES (?, ?, ?, ?)",
            (system_id, name, description, is_core),
        )
    return cursor.lastrowid


def add_function(component_id: int, function_name: str, description: str = "",
                 function_type: str = "useful", target: str = "") -> int:
    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO component_functions (component_id, function_name, function_type, description, target) "
            "VALUES (?, ?, ?, ?, ?)",
            (component_id, function_name, function_type, description, target),
        )
    return cursor.lastrowid


def add_relation(component_a_id: int, component_b_id: int,
                 relation_type: str, interface_desc: str = "") -> int:
    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO component_relations (component_a_id, component_b_id, relation_type, interface_desc) "
            "VALUES (?, ?, ?, ?)",
            (component_a_id, component_b_id, relation_type, interface_desc),
        )
    return cursor.lastrowid
