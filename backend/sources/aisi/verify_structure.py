# -*- coding: utf-8 -*-

"""
AISI采集器结构验证脚本
验证采集器代码和数据库配置的正确性
"""

import re


def verify_collector_code():
    """验证采集器代码结构"""
    print("=" * 60)
    print("验证采集器代码结构")
    print("=" * 60)

    with open('collector.py', 'r', encoding='utf-8') as f:
        code = f.read()

    checks = [
        ("导入AISIMessage实体", "from backend.database.entities import AISIMessage"),
        ("初始化translator", "self.translator = get_translator()"),
        ("_get_latest_stored_url方法", "async def _get_latest_stored_url"),
        ("_scrape_articles_list方法", "async def _scrape_articles_list"),
        ("_fetch_article_content方法", "async def _fetch_article_content"),
        ("_generate_summary方法", "async def _generate_summary"),
        ("预翻译模式（在session外）", "translated_summaries = []"),
        ("await translator.translate", "await self.translator.translate"),
        ("去重检查（遇到latest_url停止）", "if latest_url and article_url == latest_url:"),
        ("详情页延迟", "await asyncio.sleep(1.5)"),
    ]

    results = []
    for name, pattern in checks:
        if pattern in code:
            results.append(f"[OK] {name}")
        else:
            results.append(f"[FAIL] {name}")

    for result in results:
        print(result)

    print()
    return all('[OK]' in r for r in results)


def verify_database_registration():
    """验证数据库注册SQL"""
    print("=" * 60)
    print("验证SQL注册脚本")
    print("=" * 60)

    with open('register.sql', 'r', encoding='utf-8') as f:
        sql = f.read()

    checks = [
        ("CREATE TABLE mp_aisi_messages", "CREATE TABLE IF NOT EXISTS mp_aisi_messages"),
        ("核心字段: id", "id VARCHAR(36)"),
        ("核心字段: source_id", "source_id VARCHAR(36)"),
        ("核心字段: external_id", "external_id VARCHAR(200)"),
        ("核心字段: title", "title VARCHAR(500) NOT NULL"),
        ("核心字段: content", "content TEXT NOT NULL"),
        ("核心字段: summary", "summary TEXT"),
        ("核心字段: url", "url VARCHAR(500) NOT NULL UNIQUE"),
        ("扩展字段: region", "region VARCHAR(50)"),
        ("扩展字段: categories", "categories JSON"),
        ("外键约束", "FOREIGN KEY (source_id)"),
        ("CASCADE删除", "ON DELETE CASCADE"),
        ("索引: idx_url", "INDEX idx_url (url)"),
        ("INSERT消息源", "INSERT INTO mp_message_sources"),
        ("collector_module配置", "collector_module"),
        ("utf8mb4_unicode_ci编码", "utf8mb4_unicode_ci"),
    ]

    results = []
    for name, pattern in checks:
        if pattern in sql:
            results.append(f"[OK] {name}")
        else:
            results.append(f"[FAIL] {name}")

    for result in results:
        print(result)

    print()
    return all('[OK]' in r for r in results)


def verify_orm_entity():
    """验证ORM实体定义"""
    print("=" * 60)
    print("验证ORM实体定义（需要检查entities.py）")
    print("=" * 60)

    print("请手动验证以下内容：")
    print("1. backend/database/entities.py包含AISIMessage类定义")
    print("2. MessageSource类包含aisi_messages关系")
    print("3. AISIMessage包含所有核心字段（id, source_id, external_id, title, content, summary, provider, published_at, crawled_at, url）")
    print("4. AISIMessage包含扩展字段（region, content_type, language, categories）")
    print("5. AISIMessage包含所有索引定义")
    print()


if __name__ == '__main__':
    collector_ok = verify_collector_code()
    sql_ok = verify_database_registration()
    verify_orm_entity()

    print("=" * 60)
    print("验证结果汇总")
    print("=" * 60)
    print(f"采集器代码结构: {'通过' if collector_ok else '失败'}")
    print(f"SQL注册脚本: {'通过' if sql_ok else '失败'}")
    print()

    if collector_ok and sql_ok:
        print("[SUCCESS] 所有验证通过！采集器结构正确。")
        print()
        print("下一步:")
        print("1. 确保项目环境中安装了Playwright")
        print("2. 使用AutoCollector或手动运行采集器")
        print("3. 由于AISI网站可能有访问限制，可能需要调整User-Agent或添加代理")
    else:
        print("[FAIL] 验证失败，请检查上述错误项。")
