# -*- coding: utf-8 -*-
"""
知识图谱API路由
提供知识点层级图谱数据
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any, Optional
import json
import os
from pathlib import Path

router = APIRouter(prefix="/api/v1/knowledge-graph", tags=["知识图谱"])


def load_knowledge_points() -> List[Dict[str, Any]]:
    """加载知识点数据"""
    data_path = Path(__file__).parent.parent / "data" / "knowledge_points.json"

    if not data_path.exists():
        raise FileNotFoundError(f"知识点数据文件不存在: {data_path}")

    with open(data_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def build_hierarchical_graph(knowledge_points: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    构建层级图谱数据

    层级结构：书 -> 章 -> 节 -> 部（知识点）
    节点大小：书(60) > 章(45) > 节(35) > 部(25)
    """
    nodes = []
    edges = []
    node_ids = set()

    # 用于存储已创建的节点，避免重复
    books = {}
    chapters = {}
    sections = {}

    for kp in knowledge_points:
        book_id = kp.get('book_id')
        book_name = kp.get('book_name')
        chapter_id = kp.get('chapter_id')
        chapter_name = kp.get('chapter')
        section_id = kp.get('section_id')
        section_name = kp.get('section')
        part_name = kp.get('part')
        kp_name = kp.get('name')

        # 创建书节点
        if book_id and book_id not in books:
            books[book_id] = {
                "id": book_id,
                "label": book_name,
                "type": "book",
                "size": 60,
                "level": 1
            }
            nodes.append(books[book_id])
            node_ids.add(book_id)

        # 创建章节点
        if chapter_id and chapter_id not in chapters:
            chapters[chapter_id] = {
                "id": chapter_id,
                "label": chapter_name,
                "type": "chapter",
                "size": 45,
                "level": 2,
                "book_id": book_id
            }
            nodes.append(chapters[chapter_id])
            node_ids.add(chapter_id)

            # 创建书->章的边
            if book_id:
                edges.append({
                    "id": f"{book_id}-{chapter_id}",
                    "source": book_id,
                    "target": chapter_id,
                    "type": "contains"
                })

        # 创建节节点
        if section_id and section_id not in sections:
            sections[section_id] = {
                "id": section_id,
                "label": section_name,
                "type": "section",
                "size": 35,
                "level": 3,
                "chapter_id": chapter_id
            }
            nodes.append(sections[section_id])
            node_ids.add(section_id)

            # 创建章->节的边
            if chapter_id:
                edges.append({
                    "id": f"{chapter_id}-{section_id}",
                    "source": chapter_id,
                    "target": section_id,
                    "type": "contains"
                })

        # 创建知识点节点
        kp_id = f"kp_{len(nodes)}"
        kp_node = {
            "id": kp_id,
            "label": kp_name,
            "type": "knowledge_point",
            "size": 25,
            "level": 4,
            "section_id": section_id,
            "data": {
                "name": kp_name,
                "part": part_name,
                "theory_description": kp.get('theory_description', ''),
                "application_scenarios": kp.get('application_scenarios', ''),
                "typical_keywords": kp.get('typical_keywords', '')
            }
        }
        nodes.append(kp_node)
        node_ids.add(kp_id)

        # 创建节->知识点的边
        if section_id:
            edges.append({
                "id": f"{section_id}-{kp_id}",
                "source": section_id,
                "target": kp_id,
                "type": "contains"
            })

    return {
        "nodes": nodes,
        "edges": edges
    }


@router.get("/books")
def get_book_list():
    """
    获取所有书籍列表

    Returns:
        书籍列表，包含book_id和book_name
    """
    try:
        knowledge_points = load_knowledge_points()

        # 统计每本书的信息
        books = {}
        for kp in knowledge_points:
            book_id = kp.get('book_id')
            if book_id and book_id not in books:
                books[book_id] = {
                    'book_id': book_id,
                    'book_name': kp.get('book_name'),
                    'chapter_count': 0,
                    'section_count': 0,
                    'kp_count': 0
                }

        # 统计每本书的章节和知识点数量
        for kp in knowledge_points:
            book_id = kp.get('book_id')
            if book_id in books:
                books[book_id]['kp_count'] += 1

        # 统计章节数
        for book_id in books:
            book_kps = [kp for kp in knowledge_points if kp.get('book_id') == book_id]
            chapters = set(kp.get('chapter_id') for kp in book_kps if kp.get('chapter_id'))
            sections = set(kp.get('section_id') for kp in book_kps if kp.get('section_id'))
            books[book_id]['chapter_count'] = len(chapters)
            books[book_id]['section_count'] = len(sections)

        return {
            "code": 200,
            "message": "success",
            "data": list(books.values())
        }
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取书籍列表失败: {str(e)}")


@router.get("/data")
def get_knowledge_graph_data(book_id: Optional[str] = Query(None, description="书籍ID筛选")):
    """
    获取知识图谱数据

    返回层级结构的图谱数据：书 -> 章 -> 节 -> 知识点

    Args:
        book_id: 可选的书籍ID，如果提供则只返回该书的图谱数据
    """
    try:
        knowledge_points = load_knowledge_points()

        # 如果指定了book_id，只保留该书的知识点
        if book_id:
            knowledge_points = [kp for kp in knowledge_points if kp.get('book_id') == book_id]

        graph_data = build_hierarchical_graph(knowledge_points)

        return {
            "code": 200,
            "message": "success",
            "data": graph_data
        }
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成图谱数据失败: {str(e)}")


@router.get("/knowledge-point/{kp_id}")
def get_knowledge_point_detail(kp_id: str):
    """
    获取知识点详情

    Args:
        kp_id: 知识点ID

    Returns:
        知识点详细信息
    """
    try:
        knowledge_points = load_knowledge_points()

        # 从kp_id中提取索引
        if kp_id.startswith("kp_"):
            index = int(kp_id.split("_")[1])
            if 0 <= index < len(knowledge_points):
                kp = knowledge_points[index]
                return {
                    "code": 200,
                    "message": "success",
                    "data": {
                        "name": kp.get('name'),
                        "book_name": kp.get('book_name'),
                        "chapter": kp.get('chapter'),
                        "section": kp.get('section'),
                        "part": kp.get('part'),
                        "theory_description": kp.get('theory_description', ''),
                        "application_scenarios": kp.get('application_scenarios', ''),
                        "typical_keywords": kp.get('typical_keywords', '')
                    }
                }

        raise HTTPException(status_code=404, detail="知识点不存在")
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的知识点ID")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取知识点详情失败: {str(e)}")
