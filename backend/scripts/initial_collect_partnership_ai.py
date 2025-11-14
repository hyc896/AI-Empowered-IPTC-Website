# -*- coding: utf-8 -*-

"""
Partnership on AI 首次采集脚本
用于首次全量采集所有历史文章（支持无限滚动加载）
"""

import re
import sys
import uuid
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from playwright.async_api import async_playwright, Browser, Page, Playwright
from sqlalchemy.exc import IntegrityError

from backend.database.entities import PartnershipAIMessage
from backend.database.connection import create_session
from backend.storage import get_chromadb_storage
from backend.llm import get_embedding_client

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PartnershipAIInitialCollector:
    """Partnership on AI首次全量采集器"""

    def __init__(
        self,
        source_id: str,
        chroma_collection: str,
        url: str = "https://partnershiponai.org/blog/",
        region: str = "US",
        language: str = "en"
    ):
        self.source_id = source_id
        self.chroma_collection = chroma_collection
        self.url = url
        self.region = region
        self.language = language

        self.chroma_storage = get_chromadb_storage()
        self.embedding_client = get_embedding_client()

        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None

    async def initialize(self) -> bool:
        """初始化浏览器"""
        try:
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=False,  # 首次采集显示浏览器，方便观察
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                    '--disable-dev-shm-usage'
                ]
            )

            self.chroma_storage.create_collection(
                collection_name=self.chroma_collection
            )

            logger.info(f"【Partnership AI】首次采集器初始化成功")
            return True
        except Exception as e:
            logger.error(f"【Partnership AI】初始化失败: {e}")
            return False

    async def collect_all(self) -> List[Dict[str, Any]]:
        """
        采集所有历史文章（无限滚动）

        Returns:
            所有文章列表
        """
        if not await self.initialize():
            logger.error("初始化失败")
            return []

        try:
            articles = await self._scrape_all_articles()
            logger.info(f"【Partnership AI】共爬取到 {len(articles)} 篇文章")

            if articles:
                await self._store_items(articles)
                logger.info(f"【Partnership AI】首次采集完成，成功存储 {len(articles)} 篇文章")

            return articles
        finally:
            await self._close_browser()

    async def _scrape_all_articles(self) -> List[Dict[str, Any]]:
        """
        爬取所有文章（无限滚动加载）

        Returns:
            文章列表
        """
        page: Optional[Page] = None
        try:
            page = await self._browser.new_page()

            await page.set_extra_http_headers({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
            })

            logger.info(f"正在访问: {self.url}")
            await page.goto(self.url, wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(3)

            # 关闭Cookie弹窗（如果存在）
            try:
                allow_all_button = await page.query_selector("button:has-text('Allow all')")
                if allow_all_button:
                    await allow_all_button.click()
                    logger.info("已关闭Cookie弹窗")
                    await asyncio.sleep(1)
            except Exception as e:
                logger.debug(f"未找到Cookie弹窗或关闭失败: {e}")

            articles_selector = "a.post-card"
            await page.wait_for_selector(articles_selector, timeout=15000)

            # 无限滚动加载所有文章
            previous_count = 0
            no_change_count = 0
            max_no_change = 3  # 连续3次没有新增内容则停止

            while no_change_count < max_no_change:
                try:
                    current_count = await page.locator(articles_selector).count()
                    logger.info(f"当前已加载 {current_count} 篇文章")

                    if current_count == previous_count:
                        no_change_count += 1
                        logger.info(f"无新内容加载 (第{no_change_count}/{max_no_change}次)")
                    else:
                        no_change_count = 0
                        previous_count = current_count

                    # 滚动到页面底部
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await asyncio.sleep(2)

                    # 检查是否有"加载更多"按钮
                    try:
                        load_more_button = await page.query_selector("button.load-more, a.load-more, .load-more-button")
                        if load_more_button:
                            logger.info("点击'加载更多'按钮")
                            await load_more_button.click()
                            await asyncio.sleep(3)
                    except Exception as btn_error:
                        logger.debug(f"检查加载更多按钮失败: {btn_error}")

                except Exception as e:
                    logger.warning(f"滚动循环中发生错误: {e}，停止滚动")
                    break

            logger.info(f"滚动完成，最终加载了 {previous_count} 篇文章")

            # 提取所有文章数据（列表页信息）
            article_elements = await page.query_selector_all(articles_selector)
            articles_list = []

            for idx, article_elem in enumerate(article_elements, 1):
                article_data = await self._extract_article_from_element(article_elem)
                if article_data:
                    articles_list.append(article_data)
                    logger.info(f"[{idx}/{len(article_elements)}] 列表页提取: {article_data['title'][:50]}...")
                else:
                    logger.warning(f"[{idx}/{len(article_elements)}] 列表页提取失败")

            logger.info(f"\n=== 开始访问详情页获取完整内容 ===\n")

            # 逐个访问详情页，获取完整content
            for idx, article_data in enumerate(articles_list, 1):
                article_url = article_data['url']
                logger.info(f"[{idx}/{len(articles_list)}] 访问详情页: {article_url}")

                try:
                    full_content = await self._fetch_article_content(article_url)
                    if full_content:
                        article_data['content'] = full_content
                        logger.info(f"[{idx}/{len(articles_list)}] ✓ 获取到完整内容 ({len(full_content)} 字符)")
                    else:
                        logger.warning(f"[{idx}/{len(articles_list)}] ⚠ 详情页内容为空，保持使用摘要")
                except Exception as e:
                    logger.error(f"[{idx}/{len(articles_list)}] ✗ 详情页访问失败: {e}")
                    # 保持使用列表页的excerpt作为content

            return articles_list

        except Exception as e:
            logger.error(f"爬取失败: {e}", exc_info=True)
            return []
        finally:
            if page:
                await page.close()

    async def _fetch_article_content(self, article_url: str) -> Optional[str]:
        """
        访问文章详情页，获取完整内容

        Args:
            article_url: 文章URL

        Returns:
            完整的文章内容
        """
        detail_page: Optional[Page] = None
        try:
            detail_page = await self._browser.new_page()

            await detail_page.set_extra_http_headers({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            })

            await detail_page.goto(article_url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(2)

            # 提取文章正文内容（使用article或.entry-content选择器）
            content_elem = await detail_page.query_selector('article .entry-content, .entry-content, article')
            if not content_elem:
                logger.warning(f"未找到文章内容元素: {article_url}")
                return None

            # 获取所有段落文本
            paragraphs = await detail_page.query_selector_all('article p, .entry-content p')
            content_parts = []

            for para in paragraphs:
                para_text = (await para.inner_text()).strip()
                # 过滤掉非正文内容（如"Share"、空段落等）
                if para_text and para_text not in ['Share', '']:
                    # 排除作者信息行（通常很短且包含日期）
                    if len(para_text) > 30 or ',' not in para_text:
                        content_parts.append(para_text)

            full_content = '\n\n'.join(content_parts)
            return full_content if full_content else None

        except Exception as e:
            logger.error(f"获取文章详情失败 {article_url}: {e}")
            return None
        finally:
            if detail_page:
                await detail_page.close()

    async def _extract_article_from_element(self, article_elem) -> Optional[Dict[str, Any]]:
        """从post-card元素中提取文章数据"""
        try:
            url = await article_elem.get_attribute("href")
            if not url:
                return None

            title_elem = await article_elem.query_selector(".content_block")
            if not title_elem:
                return None

            title_text = (await title_elem.inner_text()).strip()
            title_lines = [line.strip() for line in title_text.split('\n') if line.strip()]

            if len(title_lines) > 1:
                title = title_lines[-1]
            else:
                title = title_text

            if not title:
                return None

            excerpt_elem = await article_elem.query_selector(".post_excerpt")
            excerpt = ""
            if excerpt_elem:
                excerpt = (await excerpt_elem.inner_text()).strip()

            if not excerpt:
                excerpt = title

            author_info_elem = await article_elem.query_selector(".author_info")
            author = ""
            published_at = None

            if author_info_elem:
                author_info_text = (await author_info_elem.inner_text()).strip()
                author_info_lines = [line.strip() for line in author_info_text.split('\n') if line.strip()]

                if len(author_info_lines) >= 2:
                    author = author_info_lines[0]
                    date_text = author_info_lines[1]
                    published_at = self._parse_date_text(date_text)
                elif len(author_info_lines) == 1:
                    if ',' in author_info_lines[0] or len(author_info_lines[0]) < 20:
                        author = author_info_lines[0]
                    else:
                        date_text = author_info_lines[0]
                        published_at = self._parse_date_text(date_text)

            if not published_at:
                published_at = datetime.now()

            external_id = self._extract_id_from_url(url)

            return {
                "external_id": external_id,
                "title": title,
                "content": excerpt if excerpt else title,
                "summary": excerpt if excerpt else None,
                "provider": author if author else None,
                "published_at": published_at or datetime.now(),
                "url": url,
                "region": self.region,
                "category": "AI Governance",
                "language": self.language
            }
        except Exception as e:
            logger.error(f"提取文章数据失败: {e}")
            return None

    def _extract_id_from_url(self, url: str) -> Optional[str]:
        """从URL提取文章ID（slug）"""
        try:
            match = re.search(r'/([^/]+)/?$', url)
            return match.group(1) if match else None
        except Exception:
            return None

    def _parse_date_text(self, date_text: str) -> datetime:
        """解析日期文本（格式：Oct 31, 2025）"""
        try:
            return datetime.strptime(date_text.strip(), '%b %d, %Y')
        except Exception as e:
            logger.error(f"日期解析失败 '{date_text}': {e}")
            return datetime.now()

    async def _store_items(self, items: List[Dict[str, Any]]) -> None:
        """并发存储到MySQL和ChromaDB"""
        mysql_task = self._store_to_mysql(items)
        chroma_task = self._store_to_chroma(items)
        await asyncio.gather(mysql_task, chroma_task, return_exceptions=True)

    async def _store_to_mysql(self, items: List[Dict[str, Any]]) -> None:
        """存储到MySQL"""
        success_count = 0
        duplicate_count = 0
        error_count = 0

        try:
            with create_session() as db:
                for item in items:
                    summary = self._generate_summary(item.get('summary'), item.get('content', ''))

                    message = PartnershipAIMessage(
                        id=str(uuid.uuid4()),
                        source_id=self.source_id,
                        external_id=item.get('external_id'),
                        title=item['title'],
                        content=item['content'],
                        summary=summary,
                        provider=item.get('provider'),
                        published_at=item.get('published_at'),
                        crawled_at=datetime.now(),
                        url=item['url'],
                        region=item.get('region'),
                        category=item.get('category'),
                        language=item.get('language')
                    )

                    try:
                        db.add(message)
                        db.commit()
                        success_count += 1
                        logger.info(f"✅ MySQL插入成功: {item.get('url')}")
                    except IntegrityError as e:
                        db.rollback()
                        if "Duplicate entry" in str(e):
                            duplicate_count += 1
                            logger.warning(f"⚠️ 重复URL: {item['url']}")
                        else:
                            error_count += 1
                            logger.error(f"❌ MySQL插入错误: {e}")
        except Exception as e:
            logger.error(f"MySQL存储失败: {e}")

        logger.info(f"【MySQL统计】成功: {success_count}, 重复: {duplicate_count}, 错误: {error_count}")

    async def _store_to_chroma(self, items: List[Dict[str, Any]]) -> None:
        """存储到ChromaDB"""
        success_count = 0
        error_count = 0

        try:
            for item in items:
                try:
                    summary = self._generate_summary(item.get('summary'), item.get('content', ''))
                    document_text = f"{item['title']} {summary}"

                    embedding = self.embedding_client.generate_embedding(document_text)

                    chroma_id = item.get('url') or str(uuid.uuid4())

                    self.chroma_storage.upsert(
                        collection_name=self.chroma_collection,
                        ids=[chroma_id],
                        documents=[document_text],
                        metadatas=[{
                            "source_id": self.source_id,
                            "external_id": item.get('external_id', ''),
                            "published_at": item['published_at'].isoformat() if item.get('published_at') else '',
                            "url": item.get('url', ''),
                            "title": item['title'],
                            "provider": item.get('provider', ''),
                            "region": item.get('region', ''),
                            "category": item.get('category', ''),
                            "language": item.get('language', '')
                        }],
                        embeddings=[embedding]
                    )
                    success_count += 1
                    logger.info(f"✅ ChromaDB插入成功: {item.get('url')}")
                except Exception as e:
                    error_count += 1
                    logger.error(f"❌ ChromaDB插入失败: {e}")
        except Exception as e:
            logger.error(f"ChromaDB存储失败: {e}")

        logger.info(f"【ChromaDB统计】成功: {success_count}, 错误: {error_count}")

    def _generate_summary(self, summary: Optional[str], content: str) -> str:
        """生成摘要"""
        if summary and len(summary.strip()) > 0:
            return summary.strip()

        if len(content) <= 1000:
            return content

        return content[:1000] + "..."

    async def _close_browser(self) -> None:
        """关闭浏览器"""
        try:
            if self._browser:
                await self._browser.close()
            if self._playwright:
                await self._playwright.stop()
        except Exception as e:
            logger.error(f"关闭浏览器失败: {e}")


async def main():
    """主函数"""
    # 1. 初始化ChromaDB
    logger.info("【1/3】初始化ChromaDB...")
    from backend.storage import initialize_chromadb
    from backend.config.config_manager import ConfigManager

    config_path = project_root / 'config.yaml'
    config_manager = ConfigManager()
    config_manager.load_config(str(config_path))
    config_data = config_manager.get_config()

    chromadb_config = config_data.get("database", {}).get("chromadb", {})
    if not initialize_chromadb(chromadb_config):
        logger.error("ChromaDB初始化失败")
        return

    logger.info("✓ ChromaDB初始化成功")

    # 2. 初始化LLM客户端
    logger.info("【2/3】初始化LLM客户端...")
    from backend.llm.global_llm_manager import GlobalLLMManager

    llm_config = config_data.get("llm", {})
    embedding_config = llm_config.get("embedding", {})
    fast_config = llm_config.get("fast", {})

    llm_manager = GlobalLLMManager.get_instance()
    llm_manager.initialize(
        chat_config=None,
        embedding_config=embedding_config,
        fast_config=fast_config
    )

    logger.info("✓ LLM客户端初始化成功")

    # 3. 从数据库获取Partnership AI消息源配置
    logger.info("【3/3】读取消息源配置...")
    from backend.database.entities import MessageSource

    with create_session() as db:
        source = db.query(MessageSource).filter(
            MessageSource.name.like('%Partnership%')
        ).first()

        if not source:
            logger.error("未找到Partnership AI消息源配置")
            return

        logger.info(f"找到消息源: {source.name} (ID: {source.id})")
        chroma_collection = source.config.get('chroma_collection', 'partnership_ai_blog')

    # 4. 开始采集
    logger.info("\n=== 开始首次全量采集 ===\n")
    collector = PartnershipAIInitialCollector(
        source_id=source.id,
        chroma_collection=chroma_collection
    )

    articles = await collector.collect_all()
    logger.info(f"\n=== 首次采集完成！共采集 {len(articles)} 篇文章 ===")


if __name__ == "__main__":
    asyncio.run(main())
