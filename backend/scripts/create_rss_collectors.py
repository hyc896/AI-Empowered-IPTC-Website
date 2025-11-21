# -*- coding: utf-8 -*-

"""
批量创建RSS采集器脚本
基于Wired模板自动生成多个RSS消息源的采集器
"""

import os
import re

# 定义待创建的RSS消息源配置
RSS_SOURCES = [
    {
        'name': 'cnbc',
        'display_name': 'CNBC Technology',
        'class_name': 'CNBCMessage',
        'collector_class': 'CNBCCollector',
        'rss_url': 'https://www.cnbc.com/id/19854910/device/rss/rss.html',
        'region': '美国',
        'language': 'en',
        'description': 'CNBC是美国全球性财经媒体，科技频道专注商业科技报道',
        'frequency': 30,
        'log_prefix': 'CNBC'
    },
    {
        'name': 'financial_times',
        'display_name': 'Financial Times Technology',
        'class_name': 'FinancialTimesMessage',
        'collector_class': 'FinancialTimesCollector',
        'rss_url': 'https://www.ft.com/technology?format=rss',
        'region': '英国',
        'language': 'en',
        'description': '英国金融时报是全球顶级财经媒体，科技频道聚焦商业科技趋势',
        'frequency': 25,
        'log_prefix': 'FT'
    },
    {
        'name': 'ars_technica',
        'display_name': 'Ars Technica',
        'class_name': 'ArsTechnicaMessage',
        'collector_class': 'ArsTechnicaCollector',
        'rss_url': 'https://feeds.arstechnica.com/arstechnica/index',
        'region': '美国',
        'language': 'en',
        'description': 'Ars Technica专注科技深度分析和技术评测，读者群体以专业人士为主',
        'frequency': 20,
        'log_prefix': 'ArsTechnica'
    },
    {
        'name': 'der_spiegel',
        'display_name': 'Der Spiegel Netzwelt',
        'class_name': 'DerSpiegelMessage',
        'collector_class': 'DerSpiegelCollector',
        'rss_url': 'https://www.spiegel.de/netzwelt/index.rss',
        'region': '德国',
        'language': 'de',
        'description': '德国明镜周刊是欧洲权威新闻媒体，Netzwelt频道报道科技与网络文化',
        'frequency': 20,
        'log_prefix': 'DerSpiegel'
    },
    {
        'name': 'le_monde',
        'display_name': 'Le Monde Pixels',
        'class_name': 'LeMondeMessage',
        'collector_class': 'LeMondeCollector',
        'rss_url': 'https://www.lemonde.fr/pixels/rss_full.xml',
        'region': '法国',
        'language': 'fr',
        'description': '法国世界报是法国权威新闻媒体，Pixels频道专注数字科技与网络文化',
        'frequency': 20,
        'log_prefix': 'LeMonde'
    },
    {
        'name': 'times_of_india',
        'display_name': 'Times of India Tech',
        'class_name': 'TimesOfIndiaMessage',
        'collector_class': 'TimesOfIndiaCollector',
        'rss_url': 'https://timesofindia.indiatimes.com/rssfeeds/66949542.cms',
        'region': '印度',
        'language': 'en',
        'description': '印度时报是印度最大英文报纸，科技频道报道科技行业动态',
        'frequency': 20,
        'log_prefix': 'TimesOfIndia'
    },
    {
        'name': 'the_hindu',
        'display_name': 'The Hindu Business',
        'class_name': 'TheHinduMessage',
        'collector_class': 'TheHinduCollector',
        'rss_url': 'https://www.thehindu.com/business/feeder/default.rss',
        'region': '印度',
        'language': 'en',
        'description': '印度教徒报商业频道，报道商业科技与产业动态，更新频率高',
        'frequency': 100,
        'log_prefix': 'TheHindu'
    }
]


def create_collector_files(source_config: dict):
    """创建采集器文件"""
    name = source_config['name']
    base_dir = f"backend/sources/{name}"

    os.makedirs(base_dir, exist_ok=True)

    # 1. 创建__init__.py
    init_content = f"""# -*- coding: utf-8 -*-

\"""
{source_config['display_name']} Collector
{source_config['display_name']}采集器（基于RSS Feed）
\"""

from .collector import {source_config['collector_class']}

__all__ = ['{source_config['collector_class']}']
"""

    with open(f"{base_dir}/__init__.py", "w", encoding="utf-8") as f:
        f.write(init_content)

    # 2. 读取Wired模板
    with open("backend/sources/wired/collector.py", "r", encoding="utf-8") as f:
        template = f.read()

    # 3. 替换占位符
    collector_content = template.replace('Wired', source_config['log_prefix'])
    collector_content = collector_content.replace('WiredMessage', source_config['class_name'])
    collector_content = collector_content.replace('WiredCollector', source_config['collector_class'])
    collector_content = collector_content.replace('https://www.wired.com/feed/rss', source_config['rss_url'])
    collector_content = collector_content.replace('"美国"', f'"{source_config["region"]}"')
    collector_content = re.sub(
        r'Wired科技新闻采集器（基于RSS Feed）.*?\n\n数据来源：',
        f"{source_config['display_name']}采集器（基于RSS Feed）\n\n数据来源：",
        collector_content,
        flags=re.DOTALL
    )

    with open(f"{base_dir}/collector.py", "w", encoding="utf-8") as f:
        f.write(collector_content)

    print(f"[OK] 创建采集器文件：{base_dir}/")


def create_register_sql(source_config: dict):
    """创建注册SQL"""
    name = source_config['name']

    sql_content = f"""-- {source_config['display_name']}采集器注册脚本
-- 执行命令（Linux）：
-- mysql -h localhost -P 3306 -u root -p123456 --default-character-set=utf8mb4 message_platform < backend/sources/{name}/register.sql

USE message_platform;

-- 1. 创建消息表
CREATE TABLE IF NOT EXISTS mp_{name}_messages (
    id VARCHAR(36) PRIMARY KEY COMMENT '消息ID（UUID）',
    source_id VARCHAR(36) NOT NULL COMMENT '来源ID',
    external_id VARCHAR(200) COMMENT '外部唯一标识（RSS的guid字段）',
    title VARCHAR(500) NOT NULL COMMENT '标题（RSS的title字段）',
    content TEXT NOT NULL COMMENT '正文内容（RSS的description字段）',
    summary TEXT COMMENT '中文摘要（翻译后）',
    provider VARCHAR(500) COMMENT '作者（RSS的author字段）',
    published_at DATETIME COMMENT '发布时间（RSS的pubDate字段）',
    crawled_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '抓取时间',
    url VARCHAR(500) NOT NULL UNIQUE COMMENT '原文链接（RSS的link字段，用于去重）',

    region VARCHAR(200) COMMENT '地区（中文格式，从文章内容提取）',
    industry_tags TEXT COMMENT '行业标签（逗号分隔，最多3个，涉及AI必须包含"人工智能"标签）',
    ai_tag VARCHAR(50) COMMENT 'AI分类标签（AI科研信息/AI产业信息/AI治理信息）',

    category VARCHAR(100) COMMENT '文章分类（RSS的category字段）',
    language VARCHAR(10) DEFAULT '{source_config['language']}' COMMENT '语言',
    media_content VARCHAR(500) COMMENT '媒体内容URL（RSS的media:content字段）',
    tags JSON COMMENT '标签列表（JSON数组）',
    metadata JSON COMMENT '其他元数据（JSON对象）',

    FOREIGN KEY (source_id) REFERENCES mp_message_sources(id) ON DELETE CASCADE,
    INDEX idx_source_id (source_id),
    INDEX idx_published_at (published_at),
    INDEX idx_crawled_at (crawled_at),
    INDEX idx_source_published (source_id, published_at),
    INDEX idx_url (url),
    INDEX idx_external_id (external_id),
    INDEX idx_category (category),
    INDEX idx_region (region),
    INDEX idx_ai_tag (ai_tag)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='{source_config['display_name']}消息表（RSS Feed采集）';

-- 2. 注册消息源
INSERT INTO mp_message_sources (
    id,
    name,
    adapter_name,
    category,
    display_name,
    config,
    schedule,
    is_active,
    created_at,
    updated_at
) VALUES (
    UUID(),
    '{source_config['display_name']}',
    '{name}',
    'news',
    '{source_config['display_name']}（{source_config['description'].split('是')[0]}）',
    JSON_OBJECT(
        'mysql_table', 'mp_{name}_messages',
        'chroma_collection', '{name}_tech',
        'region', '{source_config['region']}',
        'language', '{source_config['language']}',
        'rss_url', '{source_config['rss_url']}',
        'collector_module', 'backend.sources.{name}.collector',
        'description', '{source_config['description']}'
    ),
    '0 */1 * * *',
    1,
    NOW(),
    NOW()
) ON DUPLICATE KEY UPDATE
    config = VALUES(config),
    updated_at = NOW();

-- 3. 验证注册结果
SELECT
    id,
    name,
    category,
    display_name,
    is_active,
    JSON_EXTRACT(config, '$.mysql_table') as mysql_table,
    JSON_EXTRACT(config, '$.chroma_collection') as chroma_collection,
    JSON_EXTRACT(config, '$.collector_module') as collector_module
FROM mp_message_sources
WHERE name = '{source_config['display_name']}';

-- 4. 检查表是否创建成功
SHOW CREATE TABLE mp_{name}_messages\\G
"""

    with open(f"backend/sources/{name}/register.sql", "w", encoding="utf-8") as f:
        f.write(sql_content)

    print(f"[OK] 创建注册SQL：backend/sources/{name}/register.sql")


def append_entity_to_orm(source_config: dict):
    """追加ORM实体到entities.py"""
    name = source_config['name']
    class_name = source_config['class_name']

    entity_code = f"""

class {class_name}(Base):
    \"\"\"{source_config['display_name']}消息表（基于RSS Feed采集）\"\"\"
    __tablename__ = "mp_{name}_messages"

    # 核心必备字段（遵循2025统一标准）
    id = Column(String(36), primary_key=True, comment="消息ID（UUID）")
    source_id = Column(String(36), ForeignKey("mp_message_sources.id", ondelete="CASCADE"), nullable=False, comment="来源ID")
    external_id = Column(String(200), comment="外部唯一标识（RSS的guid字段）")
    title = Column(String(500), nullable=False, comment="标题（RSS的title字段）")
    content = Column(Text, nullable=False, comment="正文内容（RSS的description字段）")
    summary = Column(Text, comment="中文摘要（翻译后）")
    provider = Column(String(500), comment="作者（RSS的author字段）")
    published_at = Column(DateTime, comment="发布时间（RSS的pubDate字段）")
    crawled_at = Column(DateTime, default=datetime.now, nullable=False, comment="抓取时间")
    url = Column(String(500), unique=True, nullable=False, comment="原文链接（RSS的link字段，用于去重）")

    # 新增必备字段（2025年强制要求）
    region = Column(String(200), comment="地区（中文格式，从文章内容提取，默认'{source_config['region']}'）")
    industry_tags = Column(Text, comment="行业标签（逗号分隔，最多3个，涉及AI必须包含'人工智能'标签）")
    ai_tag = Column(String(50), comment="AI分类标签（AI科研信息/AI产业信息/AI治理信息）")

    # 扩展字段
    category = Column(String(100), comment="文章分类（RSS的category字段）")
    language = Column(String(10), default="{source_config['language']}", comment="语言")
    media_content = Column(String(500), comment="媒体内容URL（RSS的media:content字段）")
    tags = Column(JSON, comment="标签列表（JSON数组）")
    extra_metadata = Column("metadata", JSON, comment="其他元数据（JSON对象）")

    # 关系
    source = relationship("MessageSource", back_populates="{name}_messages")

    # 索引（强制要求）
    __table_args__ = (
        Index("idx_source_id", "source_id"),
        Index("idx_published_at", "published_at"),
        Index("idx_crawled_at", "crawled_at"),
        Index("idx_source_published", "source_id", "published_at"),
        Index("idx_url", "url"),
        Index("idx_external_id", "external_id"),
        Index("idx_category", "category"),
        Index("idx_region", "region"),
        Index("idx_ai_tag", "ai_tag"),
    )
"""

    with open("backend/database/entities.py", "a", encoding="utf-8") as f:
        f.write(entity_code)

    print(f"[OK] 追加ORM实体：{class_name}")


def add_relationship_to_message_source(source_config: dict):
    """在MessageSource类中添加relationship"""
    name = source_config['name']
    class_name = source_config['class_name']

    # 读取entities.py
    with open("backend/database/entities.py", "r", encoding="utf-8") as f:
        content = f.read()

    # 查找MessageSource类的最后一个relationship
    relationship_pattern = r'(wired_messages = relationship\("WiredMessage", back_populates="source", cascade="all, delete-orphan"\))'

    new_relationship = f'    {name}_messages = relationship("{class_name}", back_populates="source", cascade="all, delete-orphan")'

    content = re.sub(
        relationship_pattern,
        r'\1\n' + new_relationship,
        content
    )

    with open("backend/database/entities.py", "w", encoding="utf-8") as f:
        f.write(content)

    print(f"[OK] 添加relationship：{name}_messages")


def main():
    print("开始批量创建RSS采集器...\n")

    for source in RSS_SOURCES:
        print(f"\n========== 创建 {source['display_name']} ==========")

        create_collector_files(source)
        create_register_sql(source)
        append_entity_to_orm(source)
        add_relationship_to_message_source(source)

        print(f"[OK] {source['display_name']} 采集器创建完成")

    print("\n\n全部采集器文件已生成！")
    print("\n下一步：执行注册SQL")
    print("for dir in backend/sources/*/; do")
    print("  if [ -f \"$dir/register.sql\" ]; then")
    print("    echo \"执行 $dir/register.sql\"")
    print("    mysql -h localhost -P 3306 -u root -p123456 --default-character-set=utf8mb4 message_platform < \"$dir/register.sql\" 2>&1 | grep -v Warning")
    print("  fi")
    print("done")


if __name__ == '__main__':
    main()
