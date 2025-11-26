# -*- coding: utf-8 -*-

"""
Centre for the Governance of AI Collector
人工智能治理中心研究论文采集器
"""

import re
import uuid
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from playwright.async_api import Browser, Page
from sqlalchemy.exc import IntegrityError

from backend.database.entities import GovAIMessage
from backend.database.connection import create_session
from backend.collectors.base import PlaywrightCollectorBase
try:
    from backend.storage import get_chromadb_storage
    _chroma_available = True
except ImportError:
    _chroma_available = False

try:
    from backend.llm import get_embedding_client, get_translator
    _llm_available = True
except ImportError:
    _llm_available = False

logger = logging.getLogger(__name__)


class GovAICollector(PlaywrightCollectorBase):
    """Centre for the Governance of AI研究论文采集器"""

    def __init__(self, config: Dict[str, Any]):
        """
        初始化采集器

        Args:
            config: 配置字典，包含：
                - interval: 采集间隔（秒）
                - mysql_table: MySQL表名
                - chroma_collection: ChromaDB collection名称
                - url: GovAI research页面URL
                - source_id: 消息源ID（关联message_sources表）
                - region: 地区（GLOBAL）
                - language: 语言（en）
        """
        super().__init__(config)
        self.mysql_table = config['mysql_table']
        self.chroma_collection = config['chroma_collection']
        self.url = config['config'].get('url', 'https://www.governance.ai/research')
        self.region = config['config'].get('region', 'GLOBAL')
        self.language = config['config'].get('language', 'en')

        if _chroma_available:
            self.chroma_storage = get_chromadb_storage()
        else:
            self.chroma_storage = None
            logger.warning("【GovAI】ChromaDB不可用，将只存储到MySQL")

        if _llm_available:
            self.embedding_client = get_embedding_client()
            self.translator = get_translator()
        else:
            self.embedding_client = None
            self.translator = None
            logger.warning("【GovAI】LLM服务不可用，将跳过向量化和翻译")
    async def _on_initialize(self) -> bool:
        """
        子类初始化钩子：创建ChromaDB collection

        Returns:
            是否初始化成功
        """
        try:

            if self.chroma_storage:
                self.chroma_storage.create_collection(
                    collection_name=self.chroma_collection
                )

            logger.info(f"【GovAI】采集器初始化成功: {self.url}")
            return True
        except Exception as e:
            logger.error(f"【GovAI】采集器初始化失败: {e}")
            return False



    async def _collect_once(self) -> None:
        """
        单次采集

        流程：
        1. 获取MySQL中最新论文URL
        2. Playwright爬取研究列表页
        3. 过滤已存在URL
        4. 翻译英文摘要为中文
        5. 并发存储到MySQL + ChromaDB
        """
        try:
            latest_url = await self._get_latest_stored_url()
            logger.debug(f"Latest stored URL: {latest_url}")

            papers_list = await self._scrape_papers_list(latest_url)

            if not papers_list:
                logger.debug("No new items to collect")
                return

            new_items = self._filter_new_items(papers_list, latest_url)

            if new_items:
                await self._store_items(new_items)
                logger.info(f"【GovAI】采集到 {len(new_items)} 篇新论文")
            else:
                logger.debug("【GovAI】所有论文已存在，无新数据")

        except Exception as e:
            logger.error(f"【GovAI】采集错误: {e}", exc_info=True)

    async def _get_latest_stored_url(self) -> Optional[str]:
        """
        获取MySQL中最新论文的URL（使用ORM）

        Returns:
            最新URL，如果没有返回None
        """
        try:
            with create_session() as db:
                latest = db.query(GovAIMessage).filter(
                    GovAIMessage.source_id == self.source_id,
                    GovAIMessage.url.isnot(None)
                ).order_by(
                    GovAIMessage.published_at.desc()
                ).first()

                if latest and latest.url:
                    return str(latest.url)
                return None
        except Exception as e:
            logger.error(f"Failed to get latest URL: {e}")
            return None

    async def _scrape_papers_list(self, latest_url: Optional[str]) -> List[Dict[str, Any]]:
        """
        Playwright爬取研究列表页，提取论文列表

        Args:
            latest_url: 最新已存储的URL，遇到此URL立即停止

        Returns:
            论文列表
        """
        page: Optional[Page] = None
        max_retries = 3
        retry_delay = 5

        for attempt in range(max_retries):
            try:
                page = await self._browser.new_page()

                await page.set_extra_http_headers({
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.9',
                })

                await page.goto(self.url, wait_until="domcontentloaded", timeout=60000)
                await asyncio.sleep(5)
                break

            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"【GovAI】第 {attempt + 1} 次尝试失败: {e}，{retry_delay}秒后重试...")
                    if page:
                        await page.close()
                        page = None
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error(f"【GovAI】所有重试均失败: {e}", exc_info=True)
                    if page:
                        await page.close()
                    return []

        if not page:
            return []

        try:
            # GovAI网站的研究论文可能在各种容器中，尝试提取所有包含research-paper链接的元素
            # 由于网站动态加载，我们使用JavaScript提取
            papers_data = await page.evaluate("""
                () => {
                    const papers = [];
                    const allLinks = document.querySelectorAll('a[href*="/research-paper/"]');

                    allLinks.forEach(link => {
                        // 找到包含完整信息的父容器
                        let container = link.closest('div[class*="box"], div[class*="card"], article');
                        if (!container) container = link.parentElement;

                        const href = link.href;
                        const titleElem = container.querySelector('h1, h2, h3, h4, [class*="title"]') || link;
                        const title = titleElem.textContent.trim();

                        // 提取日期
                        const dateRegex = /(January|February|March|April|May|June|July|August|September|October|November|December)\\s+(\\d{4})/i;
                        const containerText = container.textContent;
                        const dateMatch = containerText.match(dateRegex);
                        const dateStr = dateMatch ? dateMatch[0] : '';

                        // 提取作者（通常在日期之后）
                        let authors = '';
                        const textLines = containerText.split('\\n').map(l => l.trim()).filter(l => l);
                        for (let i = 0; i < textLines.length; i++) {
                            if (textLines[i].match(dateRegex)) {
                                // 找到日期后面的行可能是作者
                                if (i + 1 < textLines.length) {
                                    const nextLine = textLines[i + 1];
                                    if (nextLine.length > 10 && nextLine.length < 300) {
                                        authors = nextLine;
                                    }
                                }
                                break;
                            }
                        }

                        // 提取分类标签
                        const categoryElem = container.querySelector('[class*="category"], [class*="tag"], [class*="type"]');
                        const category = categoryElem ? categoryElem.textContent.trim() : '';

                        // 提取描述
                        const descElems = container.querySelectorAll('p, [class*="excerpt"], [class*="description"]');
                        let description = '';
                        for (const elem of descElems) {
                            const text = elem.textContent.trim();
                            if (text.length > 50 && text.length < 1000 && !text.match(dateRegex)) {
                                description = text;
                                break;
                            }
                        }

                        if (title && href) {
                            papers.push({
                                title: title,
                                url: href,
                                date: dateStr,
                                authors: authors,
                                category: category,
                                description: description
                            });
                        }
                    });

                    return papers;
                }
            """)

            logger.debug(f"Found {len(papers_data)} research paper elements")

            papers_list = []
            for paper_data in papers_data:
                article_data = self._extract_paper_from_data(paper_data)

                if not article_data:
                    continue

                article_url = article_data.get('url')
                if not article_url:
                    continue

                if latest_url and article_url == latest_url:
                    logger.debug(f"Reached latest stored URL ({latest_url}), stopping")
                    break

                papers_list.append(article_data)

            return papers_list

        except Exception as e:
            logger.error(f"Failed to scrape papers list: {e}", exc_info=True)
            return []
        finally:
            if page:
                await page.close()

    def _extract_paper_from_data(self, paper_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        从JavaScript提取的数据中构建论文字典

        Args:
            paper_data: JavaScript提取的论文数据

        Returns:
            论文数据字典
        """
        try:
            title = paper_data.get('title', '').strip()
            url = paper_data.get('url', '').strip()

            if not title or not url:
                return None

            # 解析日期
            date_str = paper_data.get('date', '').strip()
            published_at = self._parse_date_text(date_str) if date_str else datetime.now()

            # 提取作者
            authors = paper_data.get('authors', '').strip()

            # 提取分类
            category = paper_data.get('category', '').strip()

            # 提取描述（作为content）
            description = paper_data.get('description', '').strip()
            if not description:
                description = title

            # 从URL提取external_id
            external_id = self._extract_id_from_url(url)

            return {
                "external_id": external_id,
                "title": title,
                "content": description,
                "summary": None,  # 将在后续翻译
                "provider": authors if authors else None,
                "published_at": published_at,
                "url": url,
                "region": self.region,
                "category": category if category else None,
                "language": self.language
            }
        except Exception as e:
            logger.error(f"Failed to extract paper from data: {e}")
            return None

    def _extract_id_from_url(self, url: str) -> Optional[str]:
        """
        从URL提取论文ID

        Args:
            url: 论文URL，如 https://www.governance.ai/research-paper/what-does-the-public-think-about-ai

        Returns:
            论文路径slug作为ID
        """
        try:
            match = re.search(r'/research-paper/([^/?]+)', url)
            return match.group(1) if match else None
        except Exception:
            return None

    def _parse_date_text(self, date_text: str) -> datetime:
        """
        解析日期文本

        Args:
            date_text: 日期文本，如 "January 2025"

        Returns:
            datetime对象
        """
        try:
            # 尝试解析 "January 2025" 格式
            return datetime.strptime(date_text.strip(), '%B %Y')
        except Exception:
            try:
                # 尝试解析 "Jan 2025" 格式
                return datetime.strptime(date_text.strip(), '%b %Y')
            except Exception as e:
                logger.error(f"Failed to parse date text '{date_text}': {e}")
                return datetime.now()

    def _filter_new_items(
        self,
        papers_list: List[Dict[str, Any]],
        latest_url: Optional[str]
    ) -> List[Dict[str, Any]]:
        """
        过滤已存在的论文

        Args:
            papers_list: 论文列表
            latest_url: 最新已存储URL

        Returns:
            新论文列表
        """
        if not latest_url:
            return papers_list

        new_items = []
        for item in papers_list:
            if item.get('url') == latest_url:
                break
            new_items.append(item)

        return new_items

    async def _store_items(self, items: List[Dict[str, Any]]) -> None:
        """
        串行存储到MySQL和ChromaDB

        注意：在Celery solo pool + nest_asyncio环境下，asyncio.gather会导致任务上下文冲突
        改为串行执行以保证稳定性

        Args:
            items: 论文列表
        """
        await self._store_to_mysql(items)
        await self._store_to_chroma(items)

    async def _store_to_mysql(self, items: List[Dict[str, Any]]) -> None:
        """
        存储到MySQL

        Args:
            items: 论文列表
        """
        try:
            # 步骤1：预先翻译所有summary（在session外，避免长时间占用连接）
            summaries = {}
            for item in items:
                summaries[item['url']] = await self._generate_summary(
                    item.get('summary'),
                    item.get('content', '')
                )

            # 步骤2：批量入库（在session内）
            with create_session() as db:
                for item in items:
                    message = GovAIMessage(
                        id=str(uuid.uuid4()),
                        source_id=self.source_id,
                        external_id=item.get('external_id'),
                        title=item['title'],
                        content=item['content'],
                        summary=summaries[item['url']],
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
                        logger.debug(f"Inserted to MySQL: url={item.get('url')}")
                    except IntegrityError as e:
                        db.rollback()
                        if "Duplicate entry" in str(e):
                            logger.debug(f"Duplicate URL: {item['url']}")
                        else:
                            logger.error(f"MySQL insert error: {e}")
        except Exception as e:
            logger.error(f"Failed to store to MySQL: {e}")

    async def _store_to_chroma(self, items: List[Dict[str, Any]]) -> None:
        """
        存储到ChromaDB

        Args:
            items: 论文列表
        """
        if not self.chroma_storage or not self.embedding_client:
            return

        try:
            for item in items:
                summary = await self._generate_summary(item.get('summary'), item.get('content', ''))
                document_text = f"{item['title']} {summary}"

                embedding = self.embedding_client.generate_embedding(document_text)

                # 使用external_id作为ChromaDB ID，确保与vector_sync一致
                chroma_id = item.get('external_id') or str(uuid.uuid4())

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
                logger.debug(f"Inserted to ChromaDB: url={item.get('url')}")
        except Exception as e:
            logger.error(f"Failed to store to ChromaDB: {e}")

    async def _generate_summary(self, summary: Optional[str], content: str) -> str:
        """
        生成摘要（支持中文翻译）

        外文内容自动翻译成中文，中文内容直接返回或截断

        Args:
            summary: 网页提取的摘要
            content: 正文内容

        Returns:
            摘要文本（中文）
        """
        # 1. 确定原始摘要来源
        source_text = summary if summary and len(summary.strip()) > 0 else content

        if not source_text:
            return ""

        # 2. 判断是否需要翻译（语言检测）
        if self.language == 'zh' or self._is_chinese(source_text):
            # 中文内容：直接返回或截断
            if len(source_text) <= 1000:
                return source_text
            return source_text[:1000] + "..."

        # 3. 外文内容：翻译成中文
        if self.translator:
            try:
                # 短文本直接翻译
                text_to_translate = source_text if len(source_text) <= 1000 else source_text[:1000]
                translated = await self.translator.translate(
                    text_to_translate,
                    context="GovAI研究论文摘要"
                )
                return translated
            except Exception as e:
                logger.error(f"翻译失败: {e}")
                # 降级策略：返回截断原文
                return source_text[:500] + "... [AI翻译暂不可用]"
        else:
            # 无翻译器：返回截断原文
            if len(source_text) <= 1000:
                return source_text
            return source_text[:500] + "..."

    def _is_chinese(self, text: str) -> bool:
        """
        检测文本是否为中文

        Args:
            text: 待检测文本

        Returns:
            是否为中文
        """
        if not text:
            return False

        # 提取前200字符作为样本
        sample = text[:200]
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', sample))
        total_chars = len(sample)

        if total_chars == 0:
            return False

        # 中文字符占比>30%判定为中文
        return (chinese_chars / total_chars) > 0.3

