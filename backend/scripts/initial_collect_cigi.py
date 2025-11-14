# -*- coding: utf-8 -*-

"""
CIGI Initial Collection Script
CIGI历史数据初始采集脚本

功能：
- 收集CIGI AI主题页的所有历史文章
- 支持无限滚动加载
- 访问每篇文章详情页获取完整内容
- 手动初始化所有依赖（ChromaDB、LLM、Config）
"""

import sys
import os
import asyncio
import logging
from pathlib import Path
from datetime import datetime

# Windows控制台UTF-8编码支持
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', line_buffering=True)

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from playwright.async_api import async_playwright
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database.entities import CIGIMessage, MessageSource
from backend.config import ConfigManager
from backend.storage.chromadb_storage import ChromaDBStorage
from backend.llm import GlobalLLMManager
from backend.sources.cigi.collector import CIGICollector

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def init_llm_clients(config):
    """
    初始化LLM客户端

    Args:
        config: ConfigManager实例
    """
    try:
        llm_config = config.get('llm', {})
        embedding_config = llm_config.get('embedding', {})
        fast_config = llm_config.get('fast', {})

        if not embedding_config:
            logger.error("未找到embedding配置")
            return False

        if not fast_config:
            logger.error("未找到fast配置（翻译用）")
            return False

        # 初始化GlobalLLMManager
        GlobalLLMManager.initialize(embedding_config, fast_config)
        logger.info("LLM客户端初始化成功")
        return True

    except Exception as e:
        logger.error(f"LLM客户端初始化失败: {e}")
        return False


def initialize_chromadb(config):
    """
    初始化ChromaDB

    Args:
        config: ConfigManager实例

    Returns:
        ChromaDBStorage实例
    """
    try:
        chroma_config = config.get('chromadb', {})
        host = chroma_config.get('host', 'localhost')
        port = chroma_config.get('port', 8000)

        storage = ChromaDBStorage(host=host, port=port)
        logger.info(f"ChromaDB初始化成功: {host}:{port}")
        return storage

    except Exception as e:
        logger.error(f"ChromaDB初始化失败: {e}")
        return None


async def collect_all_historical_data(collector: CIGICollector):
    """
    收集所有历史数据

    Args:
        collector: CIGICollector实例
    """
    logger.info("=" * 60)
    logger.info("开始收集CIGI AI主题历史数据")
    logger.info("=" * 60)

    page = None
    try:
        page = await collector._browser.new_page()

        await page.set_extra_http_headers({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
        })

        logger.info(f"正在导航到: {collector.url}")
        await page.goto(collector.url, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(5)

        # 等待表格加载
        table_selector = "table.custom-theme-table.search-results tbody tr"
        await page.wait_for_selector(table_selector, timeout=15000)
        logger.info("页面加载成功，开始采集文章列表")

        # 无限滚动策略：持续加载直到没有新内容
        all_articles = []
        no_change_rounds = 0
        max_no_change_rounds = 3
        previous_count = 0

        while no_change_rounds < max_no_change_rounds:
            # 滚动到底部
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(3)

            # 尝试点击"Load More"按钮（如果有）
            try:
                load_more_btn = await page.query_selector("button.load-more, a.load-more")
                if load_more_btn:
                    await load_more_btn.click()
                    await asyncio.sleep(3)
            except:
                pass

            # 获取当前所有行
            table_rows = await page.query_selector_all(table_selector)
            current_count = len(table_rows)

            logger.info(f"当前加载了 {current_count} 行数据")

            if current_count == previous_count:
                no_change_rounds += 1
                logger.info(f"数量未变化（{no_change_rounds}/{max_no_change_rounds}）")
            else:
                no_change_rounds = 0
                previous_count = current_count

            # 提取所有文章
            for row_elem in table_rows:
                article_data = await collector._extract_article_from_row(row_elem)
                if article_data and article_data['url']:
                    # 检查是否已在列表中（去重）
                    if not any(a['url'] == article_data['url'] for a in all_articles):
                        all_articles.append(article_data)

        logger.info("=" * 60)
        logger.info(f"列表页采集完成，共找到 {len(all_articles)} 篇文章")
        logger.info("=" * 60)

        # 访问详情页获取完整内容
        logger.info("开始访问详情页获取完整内容...")
        for idx, item in enumerate(all_articles, 1):
            try:
                logger.info(f"[{idx}/{len(all_articles)}] 正在获取: {item['title'][:50]}...")

                full_content = await collector._fetch_article_content(item['url'])
                if full_content:
                    item['content'] = full_content
                    logger.info(f"[{idx}/{len(all_articles)}] ✓ 成功获取完整内容 ({len(full_content)} 字符)")
                else:
                    logger.warning(f"[{idx}/{len(all_articles)}] ⚠ 保持使用摘要")

                # 每10篇文章稍作延迟，避免过于频繁
                if idx % 10 == 0:
                    await asyncio.sleep(2)

            except Exception as e:
                logger.error(f"[{idx}/{len(all_articles)}] ✗ 详情页访问失败: {e}")

        # 存储所有文章
        logger.info("=" * 60)
        logger.info(f"开始存储 {len(all_articles)} 篇文章...")
        logger.info("=" * 60)

        await collector._store_items(all_articles)

        logger.info("=" * 60)
        logger.info(f"历史数据采集完成！共采集 {len(all_articles)} 篇文章")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"采集过程出错: {e}", exc_info=True)
    finally:
        if page:
            await page.close()


async def main():
    """主函数"""
    logger.info("CIGI历史数据初始采集脚本")
    logger.info("=" * 60)

    # 1. 加载配置
    logger.info("正在加载配置...")
    config = ConfigManager()

    # 2. 初始化ChromaDB
    logger.info("正在初始化ChromaDB...")
    chroma_storage = initialize_chromadb(config)
    if not chroma_storage:
        logger.error("ChromaDB初始化失败，退出")
        return

    # 3. 初始化LLM客户端
    logger.info("正在初始化LLM客户端...")
    if not init_llm_clients(config):
        logger.error("LLM客户端初始化失败，退出")
        return

    # 4. 查询数据库获取消息源配置
    logger.info("正在查询消息源配置...")
    db_config = config.get('database', {})
    engine = create_engine(
        f"mysql+pymysql://{db_config['user']}:{db_config['password']}@"
        f"{db_config['host']}:{db_config['port']}/{db_config['database']}"
        f"?charset=utf8mb4"
    )
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        source = session.query(MessageSource).filter(
            MessageSource.name == 'cigi_ai'
        ).first()

        if not source:
            logger.error("未找到cigi_ai消息源，请先执行register.sql注册")
            return

        logger.info(f"找到消息源: {source.display_name} (ID: {source.id})")

        # 5. 创建采集器实例
        collector_config = {
            'id': source.id,
            'mysql_table': source.config.get('mysql_table'),
            'chroma_collection': source.config.get('chroma_collection'),
            'interval': source.config.get('interval', 86400),
            'config': source.config
        }

        # 6. 初始化采集器
        logger.info("正在初始化采集器...")
        collector = CIGICollector(collector_config)

        if not await collector.initialize():
            logger.error("采集器初始化失败，退出")
            return

        # 7. 开始采集
        await collect_all_historical_data(collector)

        # 8. 关闭浏览器
        await collector._close_browser()

    finally:
        session.close()
        logger.info("数据库连接已关闭")


if __name__ == '__main__':
    # Windows环境需要设置事件循环策略
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    asyncio.run(main())
