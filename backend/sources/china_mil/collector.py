# -*- coding: utf-8 -*-

"""
中国军网采集器
China Military Network Collector

数据来源：http://www.81.cn/
特点：官方军事新闻，权威军事资讯
"""

import re
import uuid
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List
from playwright.async_api import Page
from sqlalchemy.exc import IntegrityError

from backend.database.entities import ChinaMilMessage
from backend.database.connection import create_session
from backend.collectors.base import PlaywrightCollectorBase

logger = logging.getLogger(__name__)


class ChinaMilCollector(PlaywrightCollectorBase):
    """中国军网采集器"""

    def __init__(self, config: Dict[str, Any]):
        """初始化采集器"""
        super().__init__(config)
        self.url = config.get('url', 'http://www.81.cn/')
        self.max_articles = config.get('max_articles', 20)
        self.source_id = config['id']

        logger.info(f"【中国军网】采集器初始化成功")

    async def _collect_once(self) -> Dict[str, Any]:
        """单次采集逻辑"""
        try:
            # 阶段1：网页抓取
            existing_urls = await self._get_existing_urls()
            articles = await self._scrape_articles(existing_urls)

            if not articles:
                logger.info(f"【中国军网】没有新文章需要采集")
                return {'success': True, 'collected_count': 0}

            # 阶段2：字段补全
            enriched_articles = await self._enrich_fields(articles)

            # 阶段3：数据库存储
            saved_count = await self._store_to_mysql(enriched_articles)

            logger.info(f"【中国军网】采集完成，成功保存 {saved_count} 篇文章")
            return {'success': True, 'collected_count': saved_count}

        except Exception as e:
            logger.error(f"【中国军网】采集失败: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}

    async def _get_existing_urls(self) -> set:
        """获取已存在的URL"""
        try:
            with create_session() as db:
                results = db.query(ChinaMilMessage.url).all()
                return {row[0] for row in results}
        except Exception as e:
            logger.error(f"【中国军网】获取已存在URL失败: {e}")
            return set()

    async def _scrape_articles(self, existing_urls: set) -> List[Dict[str, Any]]:
        """阶段1：网页抓取"""
        articles = []
        page = None

        try:
            page = await self._browser.new_page()
            logger.info(f"【中国军网】访问: {self.url}")
            await page.goto(self.url, wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(2)

            # 提取新闻列表（需要根据实际页面结构调整选择器）
            # 这里使用通用的新闻列表选择器
            news_links = await page.query_selector_all('a[href*="/"]')
            logger.info(f"【中国军网】找到 {len(news_links)} 个链接")

            processed = 0
            for link in news_links:
                if processed >= self.max_articles:
                    break

                try:
                    href = await link.get_attribute('href')
                    title_text = await link.inner_text()

                    if not href or not title_text:
                        continue

                    title = title_text.strip()[:500]
                    if len(title) < 5:
                        continue

                    # 处理相对链接
                    if href.startswith('/'):
                        href = f"http://www.81.cn{href}"
                    elif not href.startswith('http'):
                        continue

                    # 跳过已存在的URL
                    if href in existing_urls:
                        continue

                    # 去重检查
                    if any(a['url'] == href for a in articles):
                        continue

                    articles.append({
                        'url': href,
                        'title': title,
                        'provider': '中国军网',
                        'region': '中国',
                    })
                    processed += 1

                except Exception as e:
                    logger.warning(f"【中国军网】提取链接失败: {e}")
                    continue

            logger.info(f"【中国军网】采集到 {len(articles)} 篇新文章")

        except Exception as e:
            logger.error(f"【中国军网】抓取失败: {e}", exc_info=True)
        finally:
            if page:
                await page.close()

        return articles

    async def _enrich_fields(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """阶段2：字段补全"""
        CONCURRENT_LIMIT = 10
        enriched = []

        total_batches = (len(articles) + CONCURRENT_LIMIT - 1) // CONCURRENT_LIMIT

        for i in range(0, len(articles), CONCURRENT_LIMIT):
            batch = articles[i:i + CONCURRENT_LIMIT]
            batch_num = i // CONCURRENT_LIMIT + 1
            logger.info(f"【中国军网】处理批次 {batch_num}/{total_batches}，本批 {len(batch)} 篇")

            tasks = [
                self._enrich_single_article(article, idx + i + 1, len(articles))
                for idx, article in enumerate(batch)
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, dict):
                    enriched.append(result)
                elif isinstance(result, Exception):
                    logger.error(f"【中国军网】字段补全异常: {result}")

        logger.info(f"【中国军网】字段补全完成，成功 {len(enriched)}/{len(articles)} 篇")
        return enriched

    async def _enrich_single_article(self, article: Dict[str, Any], index: int, total: int) -> Dict[str, Any]:
        """处理单篇文章的字段补全"""
        page = None
        try:
            logger.debug(f"【中国军网】补全字段 ({index}/{total}): {article['title'][:30]}")

            page = await self._browser.new_page()
            await page.goto(article['url'], wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(1)

            # 提取正文内容
            content = await self._extract_content(page)
            published_at = await self._extract_publish_time(page)

            article['content'] = content
            article['published_at'] = published_at
            article['summary'] = content[:1000] if content and len(content) > 1000 else content

            return article

        except Exception as e:
            logger.error(f"【中国军网】字段补全失败 ({index}/{total}): {e}")
            return None
        finally:
            if page:
                await page.close()

    async def _extract_content(self, page: Page) -> str:
        """提取正文内容"""
        try:
            # 尝试多个常见的正文选择器
            selectors = [
                'article',
                '.article-content',
                '.content',
                '#content',
                '.text',
                'main',
            ]

            for selector in selectors:
                element = await page.query_selector(selector)
                if element:
                    content = await element.inner_text()
                    if content and len(content) > 100:
                        return content.strip()

            # 如果都没找到，返回body文本
            body = await page.query_selector('body')
            if body:
                return (await body.inner_text()).strip()

            return ""

        except Exception as e:
            logger.error(f"【中国军网】提取正文失败: {e}")
            return ""

    async def _extract_publish_time(self, page: Page) -> datetime:
        """提取发布时间"""
        try:
            # 尝试多个常见的时间选择器
            selectors = [
                '.time',
                '.date',
                '.publish-time',
                'time',
                '[class*="time"]',
                '[class*="date"]',
            ]

            for selector in selectors:
                element = await page.query_selector(selector)
                if element:
                    time_text = await element.inner_text()
                    if time_text:
                        # 尝试解析时间
                        parsed_time = self._parse_time(time_text)
                        if parsed_time:
                            return parsed_time

            return None

        except Exception as e:
            logger.error(f"【中国军网】提取发布时间失败: {e}")
            return None

    def _parse_time(self, time_text: str) -> datetime:
        """解析时间字符串"""
        try:
            # 移除多余的空白字符
            time_text = re.sub(r'\s+', ' ', time_text.strip())

            # 尝试多种时间格式
            formats = [
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%d %H:%M',
                '%Y-%m-%d',
                '%Y年%m月%d日 %H:%M:%S',
                '%Y年%m月%d日 %H:%M',
                '%Y年%m月%d日',
            ]

            for fmt in formats:
                try:
                    return datetime.strptime(time_text, fmt)
                except ValueError:
                    continue

            return None

        except Exception as e:
            logger.error(f"【中国军网】解析时间失败: {e}")
            return None

    async def _store_to_mysql(self, articles: List[Dict[str, Any]]) -> int:
        """阶段3：数据库存储"""
        saved_count = 0

        try:
            with create_session() as db:
                for article in articles:
                    try:
                        message = ChinaMilMessage(
                            id=str(uuid.uuid4()),
                            source_id=self.source_id,
                            external_id=self._extract_external_id(article['url']),
                            title=article['title'],
                            content=article.get('content', ''),
                            summary=article.get('summary'),
                            provider=article.get('provider', '中国军网'),
                            published_at=article.get('published_at'),
                            url=article['url'],
                            region=article.get('region', '中国'),
                            language='zh',
                        )

                        db.add(message)
                        db.commit()
                        saved_count += 1

                    except IntegrityError:
                        db.rollback()
                        logger.debug(f"【中国军网】URL已存在，跳过: {article['url']}")
                    except Exception as e:
                        db.rollback()
                        logger.error(f"【中国军网】保存失败: {e}")

        except Exception as e:
            logger.error(f"【中国军网】数据库存储失败: {e}")

        return saved_count

    def _extract_external_id(self, url: str) -> str:
        """从URL提取外部ID"""
        try:
            # 尝试从URL中提取ID
            match = re.search(r'/(\d+)\.html?', url)
            if match:
                return match.group(1)

            # 如果没有找到，使用URL的哈希值
            return str(hash(url))

        except Exception:
            return str(hash(url))
