# -*- coding: utf-8 -*-
"""
知识图谱API路由
提供知识点层级图谱数据
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any, Optional
import json
from pathlib import Path

router = APIRouter(prefix="/api/v1/knowledge-graph", tags=["知识图谱"])

MARX_BOOK_IDS = {"marx_principles_2023", "marx_basic_principles_2023"}
MARX_BOOK_ID = "marx_basic_principles_2023"
MARX_BOOK_NAME = "马克思主义基本原理（2023年版）"


def load_knowledge_points() -> List[Dict[str, Any]]:
    """加载知识点数据。"""
    data_path = Path(__file__).parent.parent / "data" / "knowledge_points.json"

    if not data_path.exists():
        raise FileNotFoundError(f"知识点数据文件不存在: {data_path}")

    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict):
        data = data.get("knowledge_points") or data.get("data") or data.get("items") or []
    return data if isinstance(data, list) else []


def _safe_id(value: Any, fallback: str) -> str:
    text = str(value or "").strip()
    if not text:
        text = fallback
    return "".join(ch if ch.isalnum() else "_" for ch in text).strip("_") or fallback


def _text(kp: Dict[str, Any], *keys: str, default: str = "") -> str:
    for key in keys:
        value = kp.get(key)
        if value not in (None, ""):
            return str(value)
    return default


def _normalize_book(raw_book_id: str, raw_book_name: str) -> tuple[str, str]:
    if raw_book_id in MARX_BOOK_IDS or raw_book_name == MARX_BOOK_NAME:
        return MARX_BOOK_ID, MARX_BOOK_NAME
    book_name = raw_book_name or "思政知识点"
    book_id = raw_book_id or f"book_{_safe_id(book_name, 'unknown')}"
    return book_id, book_name


def normalize_knowledge_points() -> List[Dict[str, Any]]:
    """把不同形态的知识点文件规整为稳定的书→章→节→知识点结构。"""
    normalized = []
    for index, item in enumerate(load_knowledge_points()):
        if not isinstance(item, dict):
            item = {"name": str(item)}

        name = _text(item, "name", "knowledge_point_name", "title")
        if not name:
            continue

        raw_book_id = _text(item, "book_id")
        raw_book_name = _text(item, "book_name", "book")
        book_id, book_name = _normalize_book(raw_book_id, raw_book_name)

        chapter_label = _text(item, "chapter", "chapter_name", "chapter_title", default="全部知识点")
        raw_chapter_id = _text(item, "chapter_id")
        chapter_id = f"{book_id}__chapter__{_safe_id(raw_chapter_id or chapter_label, str(index))}"

        section_label = _text(item, "section", "section_name", "section_title", default="未分组知识点")
        raw_section_id = _text(item, "section_id")
        section_id = f"{chapter_id}__section__{_safe_id(raw_section_id or section_label, str(index))}"

        normalized.append({
            **item,
            "_index": index,
            "_graph_kp_id": f"kp_{index}",
            "_book_id": book_id,
            "_book_name": book_name,
            "_chapter_id": chapter_id,
            "_chapter_label": chapter_label,
            "_section_id": section_id,
            "_section_label": section_label,
            "_name": name,
        })
    return normalized


def build_hierarchical_graph(knowledge_points: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    构建层级图谱数据。

    层级结构：书 -> 章 -> 节 -> 知识点。
    所有章、节节点 ID 均包含 book_id，避免三本书之间的章节编号互相覆盖。
    """
    nodes = []
    edges = []
    node_ids = set()
    edge_ids = set()

    def add_node(node: Dict[str, Any]):
        if node["id"] in node_ids:
            return
        nodes.append(node)
        node_ids.add(node["id"])

    def add_edge(source: str, target: str, edge_type: str = "contains"):
        if source not in node_ids or target not in node_ids:
            return
        edge_id = f"{source}-{target}"
        if edge_id in edge_ids:
            return
        edges.append({
            "id": edge_id,
            "source": source,
            "target": target,
            "type": edge_type,
        })
        edge_ids.add(edge_id)

    for kp in knowledge_points:
        book_id = kp["_book_id"]
        chapter_id = kp["_chapter_id"]
        section_id = kp["_section_id"]
        kp_id = kp["_graph_kp_id"]

        add_node({
            "id": book_id,
            "label": kp["_book_name"],
            "type": "book",
            "size": 64,
            "level": 1,
        })

        add_node({
            "id": chapter_id,
            "label": kp["_chapter_label"],
            "type": "chapter",
            "size": 46,
            "level": 2,
            "book_id": book_id,
        })
        add_edge(book_id, chapter_id)

        add_node({
            "id": section_id,
            "label": kp["_section_label"],
            "type": "section",
            "size": 34,
            "level": 3,
            "chapter_id": chapter_id,
            "book_id": book_id,
        })
        add_edge(chapter_id, section_id)

        add_node({
            "id": kp_id,
            "label": kp["_name"],
            "type": "knowledge_point",
            "size": 20,
            "level": 4,
            "section_id": section_id,
            "chapter_id": chapter_id,
            "book_id": book_id,
            "data": {
                "name": kp["_name"],
                "book_name": kp["_book_name"],
                "chapter": kp["_chapter_label"],
                "section": kp["_section_label"],
                "part": kp.get("part", ""),
                "theory_description": kp.get("theory_description", ""),
                "application_scenarios": kp.get("application_scenarios", ""),
                "typical_keywords": kp.get("typical_keywords", ""),
            },
        })
        add_edge(section_id, kp_id)

    return {"nodes": nodes, "edges": edges}


@router.get("/books")
def get_book_list():
    """获取所有书籍列表，合并历史上拆开的马克思主义基本原理 book_id。"""
    try:
        knowledge_points = normalize_knowledge_points()
        books: Dict[str, Dict[str, Any]] = {}

        for kp in knowledge_points:
            book_id = kp["_book_id"]
            if book_id not in books:
                books[book_id] = {
                    "book_id": book_id,
                    "book_name": kp["_book_name"],
                    "chapter_count": 0,
                    "section_count": 0,
                    "kp_count": 0,
                    "_chapters": set(),
                    "_sections": set(),
                }

            books[book_id]["kp_count"] += 1
            books[book_id]["_chapters"].add(kp["_chapter_id"])
            books[book_id]["_sections"].add(kp["_section_id"])

        result = []
        for book in books.values():
            result.append({
                "book_id": book["book_id"],
                "book_name": book["book_name"],
                "chapter_count": len(book["_chapters"]),
                "section_count": len(book["_sections"]),
                "kp_count": book["kp_count"],
            })

        return {"code": 200, "message": "success", "data": result}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取书籍列表失败: {str(e)}")


@router.get("/data")
def get_knowledge_graph_data(book_id: Optional[str] = Query(None, description="书籍ID筛选")):
    """
    获取知识图谱数据。

    Args:
        book_id: 可选的书籍ID，如果提供则只返回该书的图谱数据。
    """
    try:
        knowledge_points = normalize_knowledge_points()
        if book_id:
            normalized_book_id, _ = _normalize_book(book_id, "")
            knowledge_points = [kp for kp in knowledge_points if kp["_book_id"] == normalized_book_id]

        graph_data = build_hierarchical_graph(knowledge_points)
        return {"code": 200, "message": "success", "data": graph_data}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成图谱数据失败: {str(e)}")


@router.get("/knowledge-point/{kp_id}")
def get_knowledge_point_detail(kp_id: str):
    """获取知识点详情。"""
    try:
        knowledge_points = normalize_knowledge_points()
        for kp in knowledge_points:
            if kp["_graph_kp_id"] == kp_id or str(kp.get("id", "")) == kp_id:
                return {
                    "code": 200,
                    "message": "success",
                    "data": {
                        "name": kp["_name"],
                        "book_name": kp["_book_name"],
                        "chapter": kp["_chapter_label"],
                        "section": kp["_section_label"],
                        "part": kp.get("part", ""),
                        "theory_description": kp.get("theory_description", ""),
                        "application_scenarios": kp.get("application_scenarios", ""),
                        "typical_keywords": kp.get("typical_keywords", ""),
                    },
                }

        raise HTTPException(status_code=404, detail="知识点不存在")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取知识点详情失败: {str(e)}")
