# -*- coding: utf-8 -*-

"""
中央广播电视总台地方新闻采集器
CNR Local News Collector

数据来源：https://news.cnr.cn/local/
特点：按省份/直辖市组织的地方新闻，每个地区5篇新闻
"""

import re
import uuid
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from playwright.async_api import Browser, Page
from sqlalchemy.exc import IntegrityError

from backend.database.entities import CNRLocalMessage
from backend.database.connection import create_session
from backend.collectors.base import PlaywrightCollectorBase

try:
    from backend.storage import get_chromadb_storage
    _chroma_available = True
except ImportError:
    _chroma_available = False

try:
    from backend.llm import get_embedding_client
    _llm_available = True
except ImportError:
    _llm_available = False

try:
    from backend.services import get_field_enricher
    _field_enricher_available = True
except ImportError:
    _field_enricher_available = False

logger = logging.getLogger(__name__)


class CNRLocalCollector(PlaywrightCollectorBase):
    """中央广播电视总台地方新闻采集器"""

    def __init__(self, config: Dict[str, Any]):
        """初始化采集器"""
        super().__init__(config)

        self.mysql_table = config['mysql_table']
        self.chroma_collection = config['chroma_collection']
        self.source_id = config.get('id', 'auto')

        self.url = config['config'].get('url', 'https://news.cnr.cn/local/')
        self.region = config['config'].get('region', '中国')
        self.language = config['config'].get('language', 'zh')
        self.max_articles = config['config'].get('max_articles', 50)

        if _chroma_available:
            self.chroma_storage = get_chromadb_storage()
        else:
            self.chroma_storage = None
            logger.warning("【CNR地方新闻】ChromaDB不可用")

        if _llm_available:
            self.embedding_client = get_embedding_client()
        else:
            self.embedding_client = None
            logger.warning("【CNR地方新闻】Embedding服务不可用")

        if _field_enricher_available:
            self.field_enricher = get_field_enricher()
        else:
            self.field_enricher = None
            logger.warning("【CNR地方新闻】FieldEnricher不可用")

    async def _on_initialize(self) -> bool:
        """初始化ChromaDB collection"""
        try:
            if self.chroma_storage:
                self.chroma_storage.create_collection(
                    collection_name=self.chroma_collection
                )
            logger.info(f"【CNR地方新闻】采集器初始化成功")
            return True
        except Exception as e:
            logger.error(f"【CNR地方新闻】初始化失败: {e}")
            return False

    async def _collect_once(self) -> Dict[str, Any]:
        """单次采集（三阶段架构）"""
        try:
            existing_urls = await self._get_existing_urls()
            logger.info(f"【CNR地方新闻】已存在 {len(existing_urls)} 条URL")

            articles = await self._scrape_articles(existing_urls)
            if not articles:
                logger.info("【CNR地方新闻】无新文章")
                return {'success': True, 'collected': 0, 'discovered': 0, 'enriched': 0, 'saved': 0}

            logger.info(f"【CNR地方新闻】采集到 {len(articles)} 篇新文章")

            # 阶段2：字段补全
            enriched_articles = await self._enrich_fields(articles)

            # 阶段3：存储
            saved_count = await self._store_articles(enriched_articles)

            logger.info(
                f"【CNR地方新闻】本轮采集完成，候选 {len(articles)} 篇，"
                f"可入库 {len(enriched_articles)} 篇，新增 {saved_count} 篇"
            )
            return {
                'success': True,
                'collected': saved_count,
                'discovered': len(articles),
                'enriched': len(enriched_articles),
                'saved': saved_count
            }

        except Exception as e:
            logger.error(f"【CNR地方新闻】采集失败: {e}", exc_info=True)
            raise

    async def _get_existing_urls(self) -> set:
        """获取数据库中已存在的URL"""
        try:
            with create_session() as db:
                results = db.query(CNRLocalMessage.url).all()
                return {row[0] for row in results}
        except Exception as e:
            logger.error(f"【CNR地方新闻】获取已存在URL失败: {e}")
            return set()

    async def _scrape_articles(self, existing_urls: set) -> List[Dict[str, Any]]:
        """阶段1：网页抓取（遍历所有省份，每个省份的新闻）"""
        articles = []
        page = None

        # 动态年份过滤：接受当前年份和前一年的文章
        current_year = datetime.now().year
        valid_year_patterns = [f'/t{current_year}', f'/t{current_year-1}']
        logger.info(f"【CNR地方新闻】年份过滤器: {valid_year_patterns}")

        try:
            page = await self._browser.new_page()

            logger.info(f"【CNR地方新闻】访问: {self.url}")
            await page.goto(self.url, wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(3)

            # 查找所有省份容器（使用div.item选择器）
            province_divs = await page.query_selector_all('div.item')
            logger.info(f"【CNR地方新闻】找到 {len(province_divs)} 个省份容器")

            processed = 0
            valid_provinces = 0

            for i, province_div in enumerate(province_divs, 1):
                if processed >= self.max_articles:
                    break

                try:
                    # 提取省份名称（从div[1]的文本中提取，只取第一行）
                    province_name_elem = await province_div.query_selector('div:nth-of-type(1)')
                    if not province_name_elem:
                        continue

                    province_text = await province_name_elem.inner_text()
                    # 只取第一行作为省份名称（去掉副标题）
                    province_name = province_text.strip().split('\n')[0].strip()

                    # 跳过空名称或异常长度
                    if not province_name or len(province_name) > 10:
                        continue

                    valid_provinces += 1
                    logger.info(f"【CNR地方新闻】处理省份 ({valid_provinces}): {province_name}")

                    # 提取该省份的所有新闻链接（第1条 + 第2-6条）
                    all_links = []

                    # 第1条新闻（div[2]/p/a）
                    first_link = await province_div.query_selector('div:nth-of-type(2) > p > a')
                    if first_link:
                        all_links.append(first_link)

                    # 第2-6条新闻（ul/li/a）
                    other_links = await province_div.query_selector_all('ul > li > a')
                    all_links.extend(other_links)

                    logger.debug(f"【CNR地方新闻】{province_name} 找到 {len(all_links)} 个链接")

                    for link in all_links:
                        if processed >= self.max_articles:
                            break

                        try:
                            href = await link.get_attribute('href')
                            title_text = await link.inner_text()

                            if not href or not title_text:
                                continue

                            # 限制title长度，只取前200字符
                            title = title_text.strip()[:200]

                            if len(title) < 5:
                                continue

                            # 跳过非新闻链接（导航、首页等）
                            if '://' not in href and not href.startswith('/'):
                                continue

                            # 处理相对链接
                            if href.startswith('/'):
                                href = f"https://www.cnr.cn{href}"
                            elif not href.startswith('http'):
                                continue

                            # 只采集新闻文章链接（包含日期和文章ID）
                            if not any(pattern in href for pattern in valid_year_patterns):
                                continue

                            # 跳过已存在的URL
                            if href in existing_urls:
                                continue

                            # 去重检查（避免同一批次重复）
                            if any(a['url'] == href for a in articles):
                                continue

                            articles.append({
                                'url': href,
                                'title': title.strip(),
                                'provider': '中央广播电视总台',
                                'region': f'中国/{province_name}',  # 设置具体地区
                            })
                            processed += 1

                        except Exception as e:
                            logger.warning(f"【CNR地方新闻】提取链接失败: {e}")
                            continue

                except Exception as e:
                    logger.warning(f"【CNR地方新闻】处理省份区域失败: {e}")
                    continue

            logger.info(f"【CNR地方新闻】采集到 {len(articles)} 篇新文章（有效省份: {valid_provinces}）")

        except Exception as e:
            logger.error(f"【CNR地方新闻】抓取失败: {e}", exc_info=True)
        finally:
            if page:
                await page.close()

        return articles

    async def _enrich_fields(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """阶段2：字段补全（并发访问详情页提取内容）"""
        CONCURRENT_LIMIT = 10  # 并发数量限制
        enriched = []

        # 分批并发处理
        total_batches = (len(articles) + CONCURRENT_LIMIT - 1) // CONCURRENT_LIMIT

        for i in range(0, len(articles), CONCURRENT_LIMIT):
            batch = articles[i:i + CONCURRENT_LIMIT]
            batch_num = i // CONCURRENT_LIMIT + 1
            logger.info(f"【CNR地方新闻】处理批次 {batch_num}/{total_batches}，本批 {len(batch)} 篇")

            # 并发处理这一批文章
            tasks = [
                self._enrich_single_article(article, idx + i + 1, len(articles))
                for idx, article in enumerate(batch)
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 收集结果；详情页失败时保留列表页基础信息，避免整篇丢失。
            for article, result in zip(batch, results):
                if isinstance(result, dict):
                    enriched.append(result)
                elif isinstance(result, Exception):
                    logger.warning(
                        f"【CNR地方新闻】字段补全失败，保留基础信息入库: "
                        f"{article.get('url', 'unknown')}, {result}"
                    )
                    fallback_article = dict(article)
                    fallback_article['content'] = article.get('content') or article.get('title', '')
                    fallback_article['summary'] = article.get('summary') or article.get('title', '')
                    fallback_article.setdefault('published_at', None)
                    enriched.append(fallback_article)

        logger.info(f"【CNR地方新闻】字段补全完成，可入库 {len(enriched)}/{len(articles)} 篇")
        return enriched

    async def _enrich_single_article(self, article: Dict[str, Any], index: int, total: int) -> Dict[str, Any]:
        """处理单篇文章的字段补全"""
        page = None
        try:
            logger.debug(f"【CNR地方新闻】补全字段 ({index}/{total}): {article['title'][:30]}")

            # 访问详情页提取内容
            page = await self._browser.new_page()
            await page.goto(article['url'], wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(1)  # 减少等待时间到1秒

            # 提取正文内容
            content = await self._extract_content(page)

            # 提取发布时间
            published_at = await self._extract_publish_time(page)

            article['content'] = content
            article['published_at'] = published_at

            # 生成摘要
            if content:
                article['summary'] = content[:200]
            else:
                article['summary'] = ""

            return article

        except Exception as e:
            logger.error(f"【CNR地方新闻】字段补全失败 {article.get('url', 'unknown')}: {e}")
            raise
        finally:
            if page:
                await page.close()

    async def _extract_content(self, page: Page) -> str:
        """从详情页提取正文内容"""
        try:
            # 尝试多种选择器
            selectors = [
                '.article-content',
                '.content',
                '.text',
                '#content',
                'article',
                '.article',
                '[class*="content"]',
                '[class*="article"]',
                '.TRS_Editor',  # CNR网站特定
            ]

            for selector in selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        content = await element.inner_text()
                        if content and len(content) > 100:
                            return content.strip()
                except Exception:
                    continue

            # 如果找不到内容，记录警告
            logger.warning(f"【CNR地方新闻】无法获取内容: {page.url}")
            return ""

        except Exception as e:
            logger.error(f"【CNR地方新闻】提取内容失败: {e}")
            return ""

    async def _extract_publish_time(self, page: Page) -> Optional[datetime]:
        """从详情页提取发布时间"""
        try:
            # 尝试多种选择器和格式
            selectors = [
                '.time',
                '.date',
                '.publish-time',
                '[class*="time"]',
                '[class*="date"]',
                '.info',  # CNR网站特定
            ]

            for selector in selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        time_text = await element.inner_text()

                        # 尝试解析时间
                        patterns = [
                            r'(\d{4})-(\d{2})-(\d{2})\s+(\d{2}):(\d{2}):(\d{2})',
                            r'(\d{4})-(\d{2})-(\d{2})\s+(\d{2}):(\d{2})',
                            r'(\d{4})-(\d{2})-(\d{2})',
                            r'(\d{4})年(\d{1,2})月(\d{1,2})日\s+(\d{2}):(\d{2})',
                            r'(\d{4})年(\d{1,2})月(\d{1,2})日'
                        ]

                        for pattern in patterns:
                            match = re.search(pattern, time_text)
                            if match:
                                groups = match.groups()
                                if len(groups) >= 6:
                                    return datetime(int(groups[0]), int(groups[1]), int(groups[2]),
                                                  int(groups[3]), int(groups[4]), int(groups[5]))
                                elif len(groups) >= 5:
                                    return datetime(int(groups[0]), int(groups[1]), int(groups[2]),
                                                  int(groups[3]), int(groups[4]))
                                elif len(groups) >= 3:
                                    return datetime(int(groups[0]), int(groups[1]), int(groups[2]))

                except Exception:
                    continue

            return None

        except Exception as e:
            logger.error(f"【CNR地方新闻】提取时间失败: {e}")
            return None

    async def _store_articles(self, articles: List[Dict[str, Any]]) -> int:
        """阶段3：存储到数据库和向量库"""
        saved_count = 0
        duplicate_count = 0
        error_count = 0

        with create_session() as db:
            for article in articles:
                try:
                    message = CNRLocalMessage(
                        id=str(uuid.uuid4()),
                        source_id=self.source_id,
                        external_id=self._extract_external_id(article['url']),
                        title=article['title'],
                        content=article.get('content') or article['title'],
                        summary=article.get('summary') or article['title'],
                        provider=article['provider'],
                        published_at=article.get('published_at'),
                        url=article['url'],
                        region=article.get('region', self.region),
                        language=self.language,
                        crawled_at=datetime.now()
                    )

                    db.add(message)
                    saved_count += 1

                except IntegrityError:
                    db.rollback()
                    duplicate_count += 1
                    logger.debug(f"【CNR地方新闻】重复URL: {article['url']}")
                except Exception as e:
                    db.rollback()
                    error_count += 1
                    logger.error(f"【CNR地方新闻】保存失败: {e}")

            # 批量提交所有成功的记录
            try:
                db.commit()
                logger.info(f"【CNR地方新闻】存储完成 - 成功: {saved_count}, 重复: {duplicate_count}, 失败: {error_count}")
                return saved_count
            except Exception as e:
                db.rollback()
                logger.error(f"【CNR地方新闻】批量提交失败: {e}")
                raise

    def _extract_external_id(self, url: str) -> str:
        """从URL中提取外部ID"""
        try:
            # CNR的URL格式：https://www.cnr.cn/bj/oiue/20251211/t20251211_527456857.shtml
            match = re.search(r't(\d+)_(\d+)\.', url)
            if match:
                return f"{match.group(1)}_{match.group(2)}"

            # 如果没有匹配，使用URL最后部分
            return url.split('/')[-1].split('.')[0]
        except:
            return url[-50:]
