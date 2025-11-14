# -*- coding: utf-8 -*-
"""
更新项目架构.md文档的Python脚本
补充7个新增欧洲智库采集器的文档
"""

import re


def update_architecture_doc():
    """更新项目架构文档"""

    # 读取原文档
    with open("/d/TechWork/message_platform/项目架构.md", "r", encoding="utf-8") as f:
        content = f.read()

    # 1. 更新消息源数量（20+ -> 30+）
    content = content.replace("覆盖20+国际智库", "覆盖30+国际智库")

    # 2. 在"区域智库"后添加"欧洲智库"
    old_regional = "- 区域智库：Takshashila（印度）、ICRIER（印度）、Stellenbosch（南非）、HSE AI（俄罗斯）、OBIA（巴西）"
    new_regional = """- 区域智库：Takshashila（印度）、ICRIER（印度）、Stellenbosch（南非）、HSE AI（俄罗斯）、OBIA（巴西）
  - 欧洲智库：Ada Lovelace Institute（英国）、IEAI（德国）、FARI（比利时）、KIRA（德国）、AISI（英国）、Future Society（跨大西洋）、SAIF（英国）"""
    content = content.replace(old_regional, new_regional)

    # 3. 在目录结构中的sources/部分添加新采集器
    sources_section = """│   ├── sources/                 # 消息源插件
│   │   ├── __init__.py
│   │   ├── tonghuashun/         # 同花顺采集器
│   │   │   ├── __init__.py
│   │   │   ├── collector.py
│   │   │   └── register.sql
│   │   ├── kr36/                # 36氪采集器
│   │   │   ├── __init__.py
│   │   │   ├── collector.py
│   │   │   └── register.sql
│   │   ├── arxiv/               # arXiv采集器
│   │   │   ├── __init__.py
│   │   │   ├── collector.py
│   │   │   ├── config.py
│   │   │   └── constants.py
│   │   ├── partnership_ai/      # Partnership on AI采集器
│   │   ├── govai/               # Centre for the Governance of AI采集器
│   │   ├── oecd_ai/             # OECD AI Policy Observatory采集器
│   │   ├── csis/                # CSIS AI Topic采集器
│   │   ├── wef_publications/    # World Economic Forum Publications采集器
│   │   ├── cigi/                # CIGI采集器
│   │   ├── cnas/                # CNAS采集器
│   │   ├── cset/                # CSET采集器
│   │   ├── rand/                # RAND Corporation采集器
│   │   ├── takshashila/         # Takshashila Institution采集器（印度）
│   │   ├── icrier/              # ICRIER采集器（印度）
│   │   ├── stellenbosch/        # Stellenbosch University采集器（南非）
│   │   ├── gcg_ai/              # Global Center on AI Governance采集器（南非）
│   │   ├── obia/                # OBIA采集器（巴西）
│   │   └── hse_ai/              # HSE AI Centre采集器（俄罗斯）"""

    new_sources_section = """│   ├── sources/                 # 消息源插件
│   │   ├── __init__.py
│   │   ├── tonghuashun/         # 同花顺采集器
│   │   │   ├── __init__.py
│   │   │   ├── collector.py
│   │   │   └── register.sql
│   │   ├── kr36/                # 36氪采集器
│   │   │   ├── __init__.py
│   │   │   ├── collector.py
│   │   │   └── register.sql
│   │   ├── arxiv/               # arXiv采集器
│   │   │   ├── __init__.py
│   │   │   ├── collector.py
│   │   │   ├── config.py
│   │   │   └── constants.py
│   │   ├── partnership_ai/      # Partnership on AI采集器
│   │   ├── govai/               # Centre for the Governance of AI采集器
│   │   ├── oecd_ai/             # OECD AI Policy Observatory采集器
│   │   ├── csis/                # CSIS AI Topic采集器
│   │   ├── wef_publications/    # World Economic Forum Publications采集器
│   │   ├── cigi/                # CIGI采集器
│   │   ├── cnas/                # CNAS采集器
│   │   ├── cset/                # CSET采集器
│   │   ├── rand/                # RAND Corporation采集器
│   │   ├── takshashila/         # Takshashila Institution采集器（印度）
│   │   ├── icrier/              # ICRIER采集器（印度）
│   │   ├── stellenbosch/        # Stellenbosch University采集器（南非）
│   │   ├── gcg_ai/              # Global Center on AI Governance采集器（南非）
│   │   ├── obia/                # OBIA采集器（巴西）
│   │   ├── hse_ai/              # HSE AI Centre采集器（俄罗斯）
│   │   ├── ada_lovelace/        # Ada Lovelace Institute采集器（英国）
│   │   ├── ieai/                # Institute for Ethics in AI采集器（德国）
│   │   ├── fari/                # FARI - AI for the Common Good采集器（比利时）
│   │   ├── kira/                # KIRA Center采集器（德国）
│   │   ├── aisi/                # AI Security Institute采集器（英国）
│   │   ├── future_society/      # The Future Society采集器（跨大西洋）
│   │   └── saif/                # Safe AI Forum采集器（英国）"""

    content = content.replace(sources_section, new_sources_section)

    # 4. 在entities.py ORM实体列表中添加新实体
    old_entities = """- StellenboschMessage：Stellenbosch University消息表（南非）
- GCGAIMessage：Global Center on AI Governance消息表（南非/非洲）
- OBIAMessage：OBIA消息表（巴西）
- HSEAIMessage：HSE AI Centre消息表（俄罗斯）"""

    new_entities = """- StellenboschMessage：Stellenbosch University消息表（南非）
- GCGAIMessage：Global Center on AI Governance消息表（南非/非洲）
- OBIAMessage：OBIA消息表（巴西）
- HSEAIMessage：HSE AI Centre消息表（俄罗斯）
- AdaLovelaceMessage：Ada Lovelace Institute消息表（英国）
- IEAIMessage：Institute for Ethics in AI消息表（德国）
- FARIMessage：FARI - AI for the Common Good消息表（比利时）
- KIRAMessage：KIRA Center消息表（德国）
- AISIMessage：AI Security Institute消息表（英国）
- FutureSocietyMessage：The Future Society消息表（跨大西洋）
- SAIFMessage：Safe AI Forum消息表（英国）"""

    content = content.replace(old_entities, new_entities)

    # 5. 在外键关系图中添加新表
    old_fk = """├── mp_stellenbosch_messages (N)
├── mp_gcg_ai_messages (N)
├── mp_obia_messages (N)
└── mp_hse_ai_messages (N)"""

    new_fk = """├── mp_stellenbosch_messages (N)
├── mp_gcg_ai_messages (N)
├── mp_obia_messages (N)
├── mp_hse_ai_messages (N)
├── mp_ada_lovelace_messages (N)
├── mp_ieai_messages (N)
├── mp_fari_messages (N)
├── mp_kira_messages (N)
├── mp_aisi_messages (N)
├── mp_future_society_messages (N)
└── mp_saif_messages (N)"""

    content = content.replace(old_fk, new_fk)

    # 6. 更新"新增消息源检查清单"，删除COLLECTOR_REGISTRY相关内容
    old_checklist = """**必做项**：
1. 在backend/sources/新增采集器模块
2. 在backend/database/entities.py定义ORM实体（_messages结尾，自动注册）
3. 在数据库mp_message_sources表注册消息源配置
4. 在CollectorService.COLLECTOR_REGISTRY注册采集器"""

    new_checklist = """**必做项**：
1. 在backend/sources/新增采集器模块
2. 在backend/database/entities.py定义ORM实体（_messages结尾，自动注册）
3. 在数据库mp_message_sources表注册消息源配置（包含config.collector_module字段）
4. 无需修改CollectorService代码（采用动态加载机制）"""

    content = content.replace(old_checklist, new_checklist)

    # 7. 在文档末尾添加新增采集器详情
    new_collectors_docs = """

### 12.8 Ada Lovelace Institute 采集器（英国AI治理与伦理智库）

**backend/sources/ada_lovelace/collector.py**：

**类**：`AdaLovelaceCollector`

**配置**：
- url：https://www.adalovelaceinstitute.org/blog/
- interval：86400秒（每日采集）
- region：UK（United Kingdom）
- language：en
- mysql_table：mp_ada_lovelace_messages
- chroma_collection：mp_ada_lovelace

**数据字段**：
- external_id：从URL提取的文章slug
- title：文章标题
- content：完整文章内容（从详情页提取）
- summary：中文摘要（翻译后）
- provider：作者（多个用逗号分隔）
- published_at：发布时间
- url：原文链接
- region：UK
- category：内容类型（Commentary/Report/Blog Post等）
- language：en

**采集流程**：
- 使用Playwright抓取博客列表页
- 访问详情页获取完整内容
- 预翻译所有摘要（在session外执行）
- 并发存储到MySQL和ChromaDB

**去重策略**：url字段（UNIQUE约束）

### 12.9 IEAI 采集器（德国慕尼黑技术大学AI伦理研究所）

**backend/sources/ieai/collector.py**：

**类**：`IEAICollector`

**配置**：
- url：https://ieai.mcts.tum.de/news/
- interval：86400秒（每日采集）
- region：DE（Germany）
- language：en
- mysql_table：mp_ieai_messages
- chroma_collection：mp_ieai

**数据字段**：
- external_id：从URL提取的文章slug
- title：文章标题
- content：完整文章内容
- summary：中文摘要（翻译后）
- provider：作者（多个用逗号分隔）
- published_at：发布时间
- url：原文链接
- region：DE
- category：文章类型（News/Blog/Research等）
- language：en

**采集流程**：
- 使用Playwright抓取新闻列表页
- 访问详情页获取完整内容
- 预翻译所有摘要
- 并发存储

**去重策略**：url字段（UNIQUE约束）

### 12.10 FARI 采集器（比利时AI公益研究所）

**backend/sources/fari/collector.py**：

**类**：`FARICollector`

**配置**：
- url：https://fari.brussels/news-publications/
- interval：86400秒（每日采集）
- region：BE（Belgium）
- language：en
- mysql_table：mp_fari_messages
- chroma_collection：mp_fari

**数据字段**：
- external_id：从URL提取的文章slug
- title：标题
- content：完整内容（从详情页提取）
- summary：中文摘要（翻译后）
- provider：作者（多个用逗号分隔）
- published_at：发布时间
- url：原文链接
- region：BE
- content_type：内容类型（News/Report/Journal Article/Conference Proceeding/Thesis）
- language：en

**采集流程**：
- 使用Playwright抓取新闻与出版物列表页
- 访问详情页获取完整内容
- 预翻译所有摘要
- 并发存储

**去重策略**：url字段（UNIQUE约束）

### 12.11 KIRA 采集器（德国AI风险与影响研究中心）

**backend/sources/kira/collector.py**：

**类**：`KIRACollector`

**配置**：
- url：https://kira-research.org/blog/
- interval：86400秒（每日采集）
- region：DE（Germany）
- language：en/de
- mysql_table：mp_kira_messages
- chroma_collection：mp_kira

**数据字段**：
- external_id：从URL提取的文章slug
- title：标题
- content：完整内容（从详情页提取）
- summary：中文摘要（翻译后）
- provider：作者（多个用逗号分隔）
- published_at：发布时间
- url：原文链接
- region：DE
- content_type：内容类型（Blog/Report/Policy Analysis）
- language：en/de（支持英文和德文内容）

**采集流程**：
- 使用Playwright抓取博客与报告列表页
- 访问详情页获取完整内容
- 预翻译所有摘要（支持德文翻译）
- 并发存储

**去重策略**：url字段（UNIQUE约束）

### 12.12 AISI 采集器（英国政府AI安全研究机构）

**backend/sources/aisi/collector.py**：

**类**：`AISICollector`

**配置**：
- url：https://www.aisi.gov.uk/research-blog
- interval：86400秒（每日采集）
- region：UK（United Kingdom）
- language：en
- mysql_table：mp_aisi_messages
- chroma_collection：mp_aisi

**数据字段**：
- external_id：从URL提取的文章slug
- title：标题
- content：完整内容（从详情页提取）
- summary：中文摘要（翻译后）
- provider：作者（多个用逗号分隔）
- published_at：发布时间
- url：原文链接
- region：UK
- content_type：内容类型（Research/Blog/Technical Report）
- language：en

**采集流程**：
- 使用Playwright抓取研究与博客列表页
- 访问详情页获取完整内容
- 预翻译所有摘要
- 并发存储

**去重策略**：url字段（UNIQUE约束）

### 12.13 Future Society 采集器（跨大西洋AI治理智库）

**backend/sources/future_society/collector.py**：

**类**：`FutureSocietyCollector`

**配置**：
- url：https://thefuturesociety.org/research-publications/
- interval：86400秒（每日采集）
- region：GLOBAL（美国+比利时）
- language：en
- mysql_table：mp_future_society_messages
- chroma_collection：mp_future_society

**数据字段**：
- external_id：从URL提取的文章slug
- title：标题
- content：完整内容（从详情页提取）
- summary：中文摘要（翻译后）
- provider：作者（多个用逗号分隔）
- published_at：发布时间
- url：原文链接
- region：GLOBAL
- content_type：内容类型（Report/Policy Brief/Article等）
- language：en

**采集流程**：
- 使用Playwright抓取研究报告与政策简报列表页
- 访问详情页获取完整内容
- 预翻译所有摘要
- 并发存储

**去重策略**：url字段（UNIQUE约束）

### 12.14 SAIF 采集器（英国AI安全论坛）

**backend/sources/saif/collector.py**：

**类**：`SAIFCollector`

**配置**：
- url：https://saif.gov.uk/publications/
- interval：86400秒（每日采集）
- region：UK（United Kingdom）
- language：en/zh（中英双语出版物）
- mysql_table：mp_saif_messages
- chroma_collection：mp_saif

**数据字段**：
- external_id：从URL提取的文章slug
- title：标题
- content：摘要或完整内容
- summary：中文摘要（翻译后，或使用原始中文版本）
- provider：作者（多个用逗号分隔）
- published_at：发布时间
- url：原文链接
- region：UK
- content_type：内容类型（Research/Policy Guide/Primer/Report等）
- language：en/zh

**采集流程**：
- 使用Playwright抓取出版物列表页
- 访问详情页获取摘要或完整内容
- 预翻译英文摘要（中文出版物保留原文）
- 并发存储

**去重策略**：url字段（UNIQUE约束）

**特殊说明**：SAIF发布中英双语出版物，采集器会识别语言并优先使用中文版本
"""

    # 在文档末尾（最后一个###章节后）插入新内容
    # 找到最后的采集器详情章节
    last_collector_pattern = r"(### 12\.7 HSE AI 采集器.*?)\n\n(?=##|$)"
    match = re.search(last_collector_pattern, content, re.DOTALL)

    if match:
        # 在HSE AI章节后插入新章节
        insert_pos = match.end()
        content = content[:insert_pos] + new_collectors_docs + "\n\n" + content[insert_pos:]
    else:
        # 如果找不到，直接追加到文档末尾
        content += new_collectors_docs

    # 写回文件
    with open("/d/TechWork/message_platform/项目架构.md", "w", encoding="utf-8") as f:
        f.write(content)

    print("✓ 项目架构.md 更新完成")
    print(f"✓ 新增7个欧洲智库采集器的完整文档")


if __name__ == "__main__":
    update_architecture_doc()
