"""
图谱查询路由
处理图谱数据查询和可视化
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from app.models.schemas import GraphData, RenameRequest
from app.services.graphrag_service import GraphRAGService
from app.services.progress_manager import progress_manager
import httpx
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/graph", tags=["graph"])

# 全局 GraphRAG 服务实例
graphrag_service = GraphRAGService()

print("[INFO] graph.py 模块已加载，DELETE 端点应该已注册")


@router.get("/files")
async def get_file_list():
    """获取所有已上传文件的列表"""
    try:
        if graphrag_service.storage is None:
            from app.config import settings
            await graphrag_service.initialize(settings.GRAPHRAG_CONFIG_PATH)

        query = """
        MATCH (m:Message)
        OPTIONAL MATCH (m)-[:MENTIONS]->(e:Entity)
        WITH m.source_id as file_id, m.name as name, count(DISTINCT e) as entity_count
        RETURN file_id, name, entity_count
        ORDER BY file_id DESC
        """

        results = await graphrag_service.storage.execute_read_async(query, {})

        files = []
        for record in results:
            file_id = record.get('file_id')
            if file_id and file_id != 'None':
                files.append({
                    "file_id": file_id,
                    "name": record.get('name'),
                    "entity_count": record.get('entity_count', 0)
                })

        return {"files": files}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取文件列表失败: {str(e)}")


@router.delete("/test-delete")
async def test_delete():
    """测试 DELETE 端点是否工作"""
    print("🧪 测试 DELETE 端点被调用")
    return {"message": "DELETE 端点工作正常"}


@router.delete("/files/{file_id}")
async def delete_file(file_id: str):
    """删除文件及其关联的所有数据"""
    try:
        if graphrag_service.storage is None:
            from app.config import settings
            await graphrag_service.initialize(settings.GRAPHRAG_CONFIG_PATH)

        # 查找匹配的 Message 节点
        find_query = """
        MATCH (m:Message)
        WHERE m.source_id = $file_id
        RETURN m.id as message_id
        """

        print(f"🔍 删除文件: file_id={file_id}")
        print(f"🔍 查询语句: {find_query}")
        print(f"🔍 查询参数: {{'file_id': file_id}}")

        results = await graphrag_service.storage.execute_read_async(find_query, {"file_id": file_id})

        print(f"🔍 查询结果: {results}")
        print(f"🔍 结果类型: {type(results)}")
        print(f"🔍 结果长度: {len(results) if results else 0}")

        if not results:
            logger.warning(f"❌ 未找到匹配的 Message 节点，返回 404")
            raise HTTPException(status_code=404, detail="文件不存在")

        # 删除找到的所有匹配节点及其关联数据
        message_ids = [record['message_id'] for record in results]
        print(f"🗑️ 准备删除 {len(message_ids)} 个 Message 节点: {message_ids}")

        # 第一步：删除 Message 节点及其所有关系
        delete_messages_query = """
        MATCH (m:Message)
        WHERE m.id IN $message_ids
        DETACH DELETE m
        """

        print(f"🗑️ 步骤1: 删除 Message 节点")
        await graphrag_service.storage.execute_write_async(delete_messages_query, {"message_ids": message_ids})
        print(f"✅ 步骤1完成: Message 节点已删除")

        # 第二步：清理没有任何 MENTIONS 关系的孤立实体
        cleanup_entities_query = """
        MATCH (e:Entity)
        WHERE NOT (e)<-[:MENTIONS]-()
        DETACH DELETE e
        """

        print(f"🗑️ 步骤2: 清理孤立实体")
        await graphrag_service.storage.execute_write_async(cleanup_entities_query, {})
        print(f"✅ 步骤2完成: 孤立实体已清理")

        return {"message": f"文件删除成功，共删除 {len(message_ids)} 个消息节点"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除文件失败: {str(e)}")


@router.put("/files/{file_id}")
async def rename_file(file_id: str, request: RenameRequest):
    """重命名文件"""
    try:
        if graphrag_service.storage is None:
            from app.config import settings
            await graphrag_service.initialize(settings.GRAPHRAG_CONFIG_PATH)

        query = """
        MATCH (m:Message {id: $file_id})
        SET m.name = $new_name
        RETURN m.id as file_id
        """

        result = await graphrag_service.storage.execute_write_async(query, {"file_id": file_id, "new_name": request.new_name})
        if not result:
            raise HTTPException(status_code=404, detail="文件不存在")

        return {"message": "文件重命名成功", "file_id": file_id, "new_name": request.new_name}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"重命名文件失败: {str(e)}")


@router.get("/visualize/{file_id}", response_model=GraphData)
async def get_graph_visualization(
    file_id: str,
    page_range: Optional[str] = Query(None, description="页面范围，如 '1-20'")
):
    """
    获取图谱可视化数据

    Args:
        file_id: 文件 ID
        page_range: 页面范围（可选）

    Returns:
        ECharts 格式的图谱数据
    """
    try:
        # 确保服务已初始化
        if graphrag_service.storage is None:
            from app.config import settings
            await graphrag_service.initialize(settings.GRAPHRAG_CONFIG_PATH)

        graph_data = await graphrag_service.get_graph_data(file_id, page_range)
        return GraphData(**graph_data)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取图谱数据失败: {str(e)}")


@router.get("/cosma/{file_id}")
async def get_cosma_data(file_id: str):
    """获取 Cosma 格式的图谱数据"""
    try:
        if graphrag_service.storage is None:
            from app.config import settings
            await graphrag_service.initialize(settings.GRAPHRAG_CONFIG_PATH)

        cosma_data = await graphrag_service.get_cosma_data(file_id)
        return cosma_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取 Cosma 数据失败: {str(e)}")


@router.get("/search/baike")
async def search_baike(keyword: str = Query(..., description="搜索关键词")):
    """搜索百科（维基百科 fallback + 超星图书）"""
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            # 先尝试百度百科
            url = f"https://baike.baidu.com/item/{keyword}"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9",
                "Referer": "https://www.baidu.com/"
            }
            response = await client.get(url, headers=headers)

            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                title_elem = soup.select_one('.lemmaWgt-lemmaTitle-title h1')

                if title_elem:
                    summary_elem = soup.select_one('.lemma-summary')
                    summary = summary_elem.get_text(strip=True) if summary_elem else ""

                    info = {}
                    info_box = soup.select_one('.basic-info')
                    if info_box:
                        items = info_box.select('.basicInfo-item')
                        for item in items[:5]:
                            name = item.select_one('.name')
                            value = item.select_one('.value')
                            if name and value:
                                info[name.text.strip()] = value.get_text(strip=True)

                    return {
                        "success": True,
                        "title": title_elem.text.strip(),
                        "summary": summary[:500] if summary else "暂无摘要",
                        "info": info,
                        "url": url
                    }

            # Fallback 到维基百科
            wiki_url = f"https://zh.wikipedia.org/api/rest_v1/page/summary/{keyword}"
            wiki_headers = {"User-Agent": "GraphRAG/1.0", "Accept": "application/json"}
            wiki_response = await client.get(wiki_url, headers=wiki_headers)

            if wiki_response.status_code == 200:
                data = wiki_response.json()
                return {
                    "success": True,
                    "title": data.get("title", keyword),
                    "summary": data.get("extract", "暂无摘要"),
                    "info": {},
                    "url": data.get("content_urls", {}).get("desktop", {}).get("page", f"https://zh.wikipedia.org/wiki/{keyword}")
                }

            return {"success": False, "message": "未找到相关词条"}

    except Exception as e:
        return {"success": False, "message": f"搜索失败: {str(e)}"}


@router.get("/search/books")
async def search_books(keyword: str = Query(..., description="搜索关键词")):
    """搜索超星图书馆书籍（优先从 Neo4j 读取，没有则爬取）"""
    try:
        # 初始化服务
        if graphrag_service.storage is None:
            from app.config import settings
            await graphrag_service.initialize(settings.GRAPHRAG_CONFIG_PATH)

        # 先从 Neo4j 读取
        cached_books = await graphrag_service.get_books_from_neo4j(keyword)
        if cached_books:
            return {
                "success": True,
                "books": cached_books[:10],
                "total": len(cached_books),
                "from_cache": True
            }

        # 没有缓存，调用爬虫
        import subprocess
        import json
        from pathlib import Path

        scripts_dir = Path(__file__).parent.parent.parent.parent.parent / "scripts"
        crawler_script = scripts_dir / "search_libsp.py"

        if not crawler_script.exists():
            return {"success": False, "message": "爬虫脚本不存在"}

        result = subprocess.run(
            ["python", str(crawler_script), keyword],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(scripts_dir)
        )

        if result.returncode != 0:
            return {"success": False, "message": f"爬虫执行失败: {result.stderr}"}

        try:
            lines = result.stdout.strip().split('\n')
            json_line = lines[-1]
            books = json.loads(json_line)

            if books:
                # 保存到 Neo4j
                await graphrag_service.save_books_to_neo4j(keyword, books)

                return {
                    "success": True,
                    "books": books[:10],
                    "total": len(books),
                    "from_cache": False
                }
            else:
                return {"success": False, "message": "未找到相关书籍"}

        except (json.JSONDecodeError, IndexError) as e:
            return {"success": False, "message": f"解析搜索结果失败: {str(e)}"}

    except subprocess.TimeoutExpired:
        return {"success": False, "message": "搜索超时，请稍后重试"}
    except Exception as e:
        return {"success": False, "message": f"搜索失败: {str(e)}"}

@router.get("/progress/{file_id}")
async def get_file_progress(file_id: str):
    """获取文件处理进度"""
    try:
        progress = await progress_manager.get_progress(file_id)
        
        if progress is None:
            # 如果没有进度信息,检查文件是否已完成
            if graphrag_service.storage is None:
                from app.config import settings
                await graphrag_service.initialize(settings.GRAPHRAG_CONFIG_PATH)
            
            # 检查文件是否存在于数据库
            query = """
            MATCH (m:Message)
            WHERE m.id STARTS WITH $file_id
            RETURN count(m) as count
            """
            results = await graphrag_service.storage.execute_read_async(query, {"file_id": file_id})
            
            if results and results[0]['count'] > 0:
                # 文件已完成处理
                return {
                    "file_id": file_id,
                    "status": "completed",
                    "progress": 100,
                    "message": "处理完成"
                }
            else:
                # 文件不存在
                raise HTTPException(status_code=404, detail="文件不存在或尚未开始处理")
        
        return progress
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取进度失败: {str(e)}")
