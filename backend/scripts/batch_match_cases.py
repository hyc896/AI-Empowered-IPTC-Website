# -*- coding: utf-8 -*-
"""
批量撞库案例生成服务
将国内思政消息与知识点向量库进行匹配，自动生成教学案例
"""
import uuid
import json
import sys
import os
import logging
from datetime import datetime
from typing import List, Dict, Any
from collections import defaultdict
from pathlib import Path

# 添加backend目录到path
backend_dir = Path(__file__).parent.parent
project_root = backend_dir.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(backend_dir))

from database.connection import create_session, init_database
from database.entities import (
    MessageSource,
    IPTCCase,
    IPTCKnowledgePointStats,
    IPTCMessageKnowledgeRelation
)
from database.orm_registry import get_orm_registry, auto_register_all_models
from llm.global_llm_manager import GlobalLLMManager
from config import GlobalConfig
import chromadb

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BatchMatchCasesService:
    """批量撞库案例生成服务"""

    # 配置参数
    BATCH_SIZE = None                   # 批量处理消息数（None表示处理所有未处理消息）
    SIMILARITY_THRESHOLD = 0.55         # 相似度阈值（提高到0.55以确保更高的匹配质量）
    CASE_GENERATION_THRESHOLD = 4       # 案例生成阈值（提高到4条以确保案例质量）
    MAX_MESSAGES_PER_CASE = 6           # 每个案例最多使用的消息数量
    MAX_MESSAGE_USAGE = 3               # 每条消息最多使用次数（增加以充分利用有限消息）

    def __init__(self):
        """初始化服务"""
        self.logger = logger
        self.llm_manager = None
        self.chroma_client = None
        self.kp_collection = None
        self.message_tables = {}  # 动态加载的消息表映射
        self.knowledge_points = {}  # 知识点完整信息字典 {kp_id: kp_data}
        self._initialize()

    def _load_chinese_sources(self):
        """动态加载所有中国来源的消息表"""
        try:
            orm_registry = get_orm_registry()

            with create_session() as db:
                # 查询所有激活的中国来源消息源
                sources = db.query(MessageSource).filter(
                    MessageSource.is_active == True
                ).all()

                for source in sources:
                    # 判断是否为中国来源
                    if not self._is_chinese_source(source):
                        continue

                    # 从config中获取mysql_table
                    config = source.config or {}
                    table_name = config.get('mysql_table')

                    if not table_name:
                        self.logger.warning(f"消息源 '{source.name}' 缺少mysql_table配置")
                        continue

                    # 从ORM Registry获取对应的ORM类
                    model_class = orm_registry.get_model(table_name)
                    if not model_class:
                        self.logger.warning(f"消息源 '{source.name}' 的表 '{table_name}' 未找到对应的ORM类")
                        continue

                    self.message_tables[table_name] = model_class
                    self.logger.debug(f"加载中国来源: {source.name} → {table_name}")

        except Exception as e:
            self.logger.error(f"加载中国来源失败: {e}")
            raise

    def _is_chinese_source(self, source: MessageSource) -> bool:
        """
        判断是否为中国来源

        判断标准：
        1. config.config.region 包含 "中国" 或 "CN"
        2. config.config.language 为 "zh"
        3. 或在已知的中国来源名称列表中
        """
        # 已知的中国来源名称列表
        known_chinese_sources = {
            'people_theory', 'gmw_theory', 'cssn', 'qstheory',
            'tonghuashun', 'securities_times', 'kr36'
        }

        # 检查名称
        if source.name in known_chinese_sources:
            return True

        # 检查config
        config = source.config or {}
        inner_config = config.get('config', {})

        # 检查region字段
        region = inner_config.get('region', '')
        if region and ('中国' in region or 'CN' in region.upper()):
            return True

        # 检查language字段
        language = inner_config.get('language', '')
        if language and language.lower() == 'zh':
            return True

        return False


    def _initialize(self):
        """初始化LLM和ChromaDB"""
        try:
            # 加载配置
            config_instance = GlobalConfig.get_instance()
            config_path = project_root / "config.yaml"
            config_instance.initialize(str(config_path))

            # 初始化数据库连接
            if not init_database():
                raise Exception("数据库初始化失败")
            self.logger.info("[初始化] 数据库连接初始化成功")

            # 自动注册所有ORM类
            auto_register_all_models()

            # 动态加载所有中国来源的消息表
            self._load_chinese_sources()
            self.logger.info(f"[初始化] 加载了 {len(self.message_tables)} 个中国来源的消息表")
            for table_name in self.message_tables:
                self.logger.info(f"  - {table_name}")

            # 初始化LLM管理器
            llm_config = config_instance.get_config('llm', {})
            self.llm_manager = GlobalLLMManager.get_instance()
            self.llm_manager.initialize(
                llm_config.get('chat', {}),
                llm_config.get('embedding', {}),
                llm_config.get('fast', {})
            )
            self.logger.info("[初始化] LLM管理器初始化成功")

            # 初始化ChromaDB
            chroma_config = config_instance.get_config('database.chromadb', {})
            chroma_path = chroma_config.get('path', './data/chromadb')
            # 如果是相对路径，转换为相对于项目根目录的路径
            if not os.path.isabs(chroma_path):
                chroma_path = os.path.join(project_root, chroma_path)
            self.logger.info(f"[初始化] ChromaDB路径: {chroma_path}")
            self.chroma_client = chromadb.PersistentClient(path=chroma_path)
            self.kp_collection = self.chroma_client.get_collection(name="iptc_knowledge_points")
            self.logger.info(f"[初始化] ChromaDB初始化成功，知识点数: {self.kp_collection.count()}")

            # 加载知识点完整信息
            kp_json_path = project_root / "backend" / "data" / "knowledge_points.json"
            with open(kp_json_path, 'r', encoding='utf-8') as f:
                kp_list = json.load(f)
                # 构建字典映射 {name: kp_data}，因为ChromaDB中使用name作为ID
                for kp in kp_list:
                    self.knowledge_points[kp['name']] = kp
            self.logger.info(f"[初始化] 加载知识点信息成功，共 {len(self.knowledge_points)} 个")

        except Exception as e:
            self.logger.error(f"[初始化] 失败: {e}")
            raise

    def run_batch_match(self, limit: int = None, dry_run: bool = False):
        """
        执行批量撞库任务

        Args:
            limit: 限制处理的消息数量（用于测试）
            dry_run: 试运行模式，不实际写入数据库
        """
        self.logger.info("="*60)
        self.logger.info("开始批量撞库任务")
        if dry_run:
            self.logger.info("[模式] 试运行（不写入数据库）")
        self.logger.info("="*60)

        try:
            # Step 1: 获取待处理消息
            # 如果指定了limit，使用limit；否则使用BATCH_SIZE（可能为None表示处理所有）
            batch_size = limit if limit else self.BATCH_SIZE
            messages = self._get_unprocessed_messages(batch_size)

            # 只有在设置了batch_size且未指定limit时才检查阈值
            if batch_size is not None and len(messages) < batch_size and not limit:
                self.logger.info(f"当前未处理消息数: {len(messages)}/{batch_size}，等待积攒")
                return {
                    "status": "pending",
                    "total_messages": len(messages),
                    "threshold": batch_size
                }

            self.logger.info(f"获取到 {len(messages)} 条待处理消息，开始撞库...")

            # Step 2: 向量撞库匹配知识点
            matches = self._match_knowledge_points(messages)
            self.logger.info(f"匹配到 {len(matches)} 条消息-知识点关联")

            if not dry_run:
                # Step 3: 保存关联关系到数据库
                self._save_relations(matches)

                # Step 4: 统计知识点关联数
                kp_stats = self._calculate_kp_statistics()
                self.logger.info(f"统计到 {len(kp_stats)} 个知识点有关联消息")

                # Step 5: 触发案例生成
                generated_cases = self._generate_cases(kp_stats)
            else:
                self.logger.info("[试运行] 跳过数据库写入和案例生成")
                generated_cases = []

            self.logger.info("="*60)
            self.logger.info(f"✅ 批量撞库任务完成")
            self.logger.info(f"   - 处理消息: {len(messages)} 条")
            self.logger.info(f"   - 匹配关联: {len(matches)} 条")
            self.logger.info(f"   - 生成案例: {len(generated_cases)} 个")
            self.logger.info("="*60)

            return {
                "status": "success",
                "total_messages": len(messages),
                "matched_pairs": len(matches),
                "generated_cases": len(generated_cases)
            }

        except Exception as e:
            self.logger.error(f"[错误] 批量撞库任务失败: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e)
            }

    def _get_unprocessed_messages(self, limit: int = None) -> List[Dict[str, Any]]:
        """
        获取未处理的消息

        Args:
            limit: 最大消息数量（None表示获取所有未处理消息）

        Returns:
            消息列表
        """
        messages = []

        try:
            with create_session() as db:
                # 如果limit为None，则获取所有未处理消息；否则每个表固定查询100条
                per_table_limit = None if limit is None else 100

                for table_name, orm_class in self.message_tables.items():
                    # 子查询：已处理的消息ID
                    processed_ids_subquery = db.query(
                        IPTCMessageKnowledgeRelation.message_id
                    ).filter(
                        IPTCMessageKnowledgeRelation.source_table == table_name
                    ).subquery()

                    # 查询未处理的消息
                    query = db.query(orm_class).filter(
                        ~orm_class.id.in_(processed_ids_subquery)
                    ).order_by(
                        orm_class.published_at.desc()
                    )

                    # 只有在per_table_limit不为None时才应用limit
                    if per_table_limit is not None:
                        query = query.limit(per_table_limit)

                    results = query.all()

                    for row in results:
                        # 兼容新旧表的url字段（旧表：source_url，新表：url）
                        url = getattr(row, 'url', None) or getattr(row, 'source_url', '')

                        messages.append({
                            "id": row.id,
                            "title": row.title,
                            "content": row.content,
                            "summary": row.summary,
                            "published_at": row.published_at,
                            "url": url,
                            "provider": getattr(row, 'provider', '未知'),
                            "source_table": table_name
                        })

                    self.logger.debug(f"[{table_name}] 获取 {len(results)} 条未处理消息")

        except Exception as e:
            self.logger.error(f"[错误] 获取未处理消息失败: {e}")
            return []

        return messages[:limit]

    def _match_knowledge_points(self, messages: List[Dict]) -> List[Dict]:
        """
        向量撞库匹配知识点

        Args:
            messages: 消息列表

        Returns:
            匹配结果列表
        """
        matches = []

        for i, msg in enumerate(messages, 1):
            try:
                # 构造查询文本（标题+内容前1000字）
                content = msg.get('content', '')
                if len(content) > 1000:
                    content = content[:1000]
                query_text = f"{msg['title']} {content}"

                # 生成查询向量
                embedding = self.llm_manager.embedding_client.generate_embedding(query_text)

                # 在知识点库中检索Top 3
                results = self.kp_collection.query(
                    query_embeddings=[embedding],
                    n_results=3,
                    include=['metadatas', 'distances']
                )

                # 解析结果并筛选相似度>=阈值的知识点
                if results and results['ids'] and len(results['ids'][0]) > 0:
                    for j, kp_id in enumerate(results['ids'][0]):
                        # 距离转换为相似度（余弦距离: distance = 1 - similarity）
                        distance = results['distances'][0][j]
                        similarity = 1 - distance

                        # 记录前3个知识点的相似度
                        metadata = results['metadatas'][0][j]
                        kp_name = metadata.get('name', '')
                        self.logger.info(f"  [{i}] {msg['title'][:30]} <-> {kp_name[:30]}: {similarity:.3f}")

                        if similarity >= self.SIMILARITY_THRESHOLD:
                            matches.append({
                                "message_id": msg['id'],
                                "source_table": msg['source_table'],
                                "knowledge_point_id": kp_id,
                                "knowledge_point_name": kp_name,
                                "similarity": similarity
                            })

                if i % 50 == 0:
                    self.logger.info(f"  进度: {i}/{len(messages)}")

            except Exception as e:
                self.logger.error(f"[错误] 匹配失败 {msg['id']}: {e}")
                continue

        return matches

    def _save_relations(self, matches: List[Dict]):
        """
        保存消息-知识点关联关系

        Args:
            matches: 匹配结果列表
        """
        try:
            with create_session() as db:
                saved_count = 0
                for match in matches:
                    # 检查是否已存在
                    existing = db.query(IPTCMessageKnowledgeRelation).filter_by(
                        message_id=match['message_id'],
                        knowledge_point_id=match['knowledge_point_id']
                    ).first()

                    if existing:
                        # 更新相似度
                        existing.similarity_score = match['similarity']
                    else:
                        # 插入新记录
                        relation = IPTCMessageKnowledgeRelation(
                            id=str(uuid.uuid4()),
                            message_id=match['message_id'],
                            source_table=match['source_table'],
                            knowledge_point_id=match['knowledge_point_id'],
                            knowledge_point_name=match['knowledge_point_name'],
                            similarity_score=match['similarity'],
                            created_at=datetime.now()
                        )
                        db.add(relation)
                        saved_count += 1

                db.commit()
                self.logger.info(f"[保存] 新增 {saved_count} 条关联关系")

        except Exception as e:
            self.logger.error(f"[错误] 保存关联关系失败: {e}")
            raise

    def _calculate_kp_statistics(self) -> Dict[str, Dict]:
        """
        统计每个知识点的关联消息数

        注意：允许为同一知识点生成多个不同角度的案例

        Returns:
            知识点统计字典 {kp_id: {name, count}}
        """
        kp_stats = {}

        try:
            with create_session() as db:
                # 统计每个知识点的消息数（不排除已生成案例的知识点）
                from sqlalchemy import func
                results = db.query(
                    IPTCMessageKnowledgeRelation.knowledge_point_id,
                    IPTCMessageKnowledgeRelation.knowledge_point_name,
                    func.count(IPTCMessageKnowledgeRelation.message_id).label('count')
                ).group_by(
                    IPTCMessageKnowledgeRelation.knowledge_point_id,
                    IPTCMessageKnowledgeRelation.knowledge_point_name
                ).having(
                    func.count(IPTCMessageKnowledgeRelation.message_id) >= self.CASE_GENERATION_THRESHOLD
                ).all()

                for row in results:
                    kp_stats[row[0]] = {
                        "name": row[1],
                        "count": row[2]
                    }

        except Exception as e:
            self.logger.error(f"[错误] 统计知识点失败: {e}")

        return kp_stats

    def _generate_cases(self, kp_stats: Dict[str, Dict]) -> List[Dict]:
        """
        生成案例

        Args:
            kp_stats: 知识点统计

        Returns:
            生成的案例列表
        """
        generated_cases = []

        for kp_id, stat in kp_stats.items():
            self.logger.info(f"\n[案例生成] {stat['name']} (关联消息: {stat['count']}条)")

            try:
                # 获取该知识点的所有关联消息
                messages = self._get_related_messages(kp_id)

                # 调用LLM生成案例
                case = self._generate_case_for_knowledge_point(
                    knowledge_point_id=kp_id,
                    knowledge_point_name=stat['name'],
                    related_messages=messages
                )

                # 保存案例
                self._save_case(case)

                # 标记知识点已生成案例
                self._mark_case_generated(kp_id, stat['name'])

                generated_cases.append(case)

                self.logger.info(f"  ✅ 案例生成成功: {case['title']}")

            except Exception as e:
                self.logger.error(f"  ❌ 案例生成失败: {e}", exc_info=True)
                continue

        return generated_cases

    def _count_message_usage(self, db) -> Dict[str, int]:
        """
        统计每条消息的使用次数（通过查询案例表中的source_message_ids）

        Args:
            db: 数据库会话

        Returns:
            消息ID -> 使用次数的字典
        """
        usage_count = defaultdict(int)

        try:
            # 查询所有案例的source_message_ids字段
            cases = db.query(IPTCCase.source_message_ids).all()

            for case in cases:
                if case.source_message_ids:
                    # source_message_ids是JSON数组，包含消息ID列表
                    message_ids = case.source_message_ids
                    if isinstance(message_ids, list):
                        for msg_id in message_ids:
                            usage_count[msg_id] += 1

        except Exception as e:
            self.logger.error(f"[错误] 统计消息使用次数失败: {e}")

        return dict(usage_count)

    def _get_related_messages(self, kp_id: str) -> List[Dict]:
        """
        获取知识点关联的消息（最多MAX_MESSAGES_PER_CASE条，且每条消息使用次数<MAX_MESSAGE_USAGE）

        Args:
            kp_id: 知识点ID

        Returns:
            消息列表（按相似度降序，最多6条，过滤掉已使用2次的消息）
        """
        messages = []

        try:
            with create_session() as db:
                # 1. 统计所有消息的使用次数
                message_usage_count = self._count_message_usage(db)

                # 2. 查询知识点关联的所有消息（不限制数量，因为需要过滤）
                relations = db.query(IPTCMessageKnowledgeRelation).filter_by(
                    knowledge_point_id=kp_id
                ).order_by(
                    IPTCMessageKnowledgeRelation.similarity_score.desc()
                ).all()

                # 3. 遍历关联消息，过滤掉使用次数>=MAX_MESSAGE_USAGE的消息
                for rel in relations:
                    # 检查消息使用次数
                    usage_count = message_usage_count.get(rel.message_id, 0)
                    if usage_count >= self.MAX_MESSAGE_USAGE:
                        self.logger.debug(f"  跳过消息 {rel.message_id}（已使用{usage_count}次）")
                        continue

                    # 获取对应的ORM类
                    orm_class = self.message_tables.get(rel.source_table)
                    if not orm_class:
                        continue

                    # 查询消息
                    msg = db.query(orm_class).filter_by(id=rel.message_id).first()
                    if msg:
                        messages.append({
                            "id": msg.id,
                            "title": msg.title,
                            "content": msg.content,
                            "summary": msg.summary,
                            "provider": getattr(msg, 'provider', '未知'),
                            "published_at": msg.published_at,
                            "url": getattr(msg, 'url', None) or getattr(msg, 'source_url', ''),
                            "similarity": rel.similarity_score
                        })

                        # 达到最大数量后停止
                        if len(messages) >= self.MAX_MESSAGES_PER_CASE:
                            break

        except Exception as e:
            self.logger.error(f"[错误] 获取关联消息失败: {e}")

        return messages

    def _generate_case_for_knowledge_point(
        self,
        knowledge_point_id: str,
        knowledge_point_name: str,
        related_messages: List[Dict]
    ) -> Dict:
        """
        为单个知识点生成案例（聚合多条消息）

        Args:
            knowledge_point_id: 知识点ID
            knowledge_point_name: 知识点名称
            related_messages: 关联消息列表

        Returns:
            案例字典
        """
        # 1. 获取知识点完整信息
        kp_data = self.knowledge_points.get(knowledge_point_name, {})

        # 提取教材元数据
        book_name = kp_data.get('book_name', '')
        chapter = kp_data.get('chapter', '')
        section = kp_data.get('section', '')

        # 构造教学应用说明（章节定位）
        # 格式：《书名》章 节
        if book_name and chapter:
            teaching_application = f"《{book_name}》{chapter}"
            if section:
                teaching_application += f" {section}"
        else:
            teaching_application = ''

        # 2. 读取新闻转案例提示词模板
        template_path = r"D:\AI-Empowered IPTC Website\新闻转案例提示词.md"
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                prompt_template = f.read()
        except Exception as e:
            self.logger.error(f"[错误] 读取提示词模板失败: {e}")
            raise

        # 3. 构建模板参数
        template_params = {
            'related_knowledge_points': f"- {knowledge_point_name}",
            'teaching_application': teaching_application,
            'book_name': book_name if book_name else '思想政治理论课',
            'case_date': datetime.now().strftime('%Y-%m-%d')
        }

        # 为每条新闻构建参数（最多7条）
        for i, msg in enumerate(related_messages[:7], 1):
            template_params[f'news_title_{i}'] = msg['title']
            template_params[f'news_source_{i}'] = msg['provider']
            template_params[f'published_at_{i}'] = msg['published_at'].strftime('%Y-%m-%d') if msg['published_at'] else ''
            template_params[f'url_{i}'] = msg['url']
            template_params[f'news_content_{i}'] = msg['content'] or msg['summary'] or ''

        # 如果消息数量少于7条，为剩余占位符填充空字符串
        for i in range(len(related_messages) + 1, 8):
            template_params[f'news_title_{i}'] = ''
            template_params[f'news_source_{i}'] = ''
            template_params[f'published_at_{i}'] = ''
            template_params[f'url_{i}'] = ''
            template_params[f'news_content_{i}'] = ''

        # 4. 填充模板
        prompt = prompt_template.format(**template_params)

        # 4. 调用LLM生成案例
        self.logger.info(f"  [LLM] 开始生成案例，知识点: {knowledge_point_name}")
        response = self.llm_manager.chat_client.generate_with_messages(
            messages=[
                {
                    "role": "system",
                    "content": "你是一位资深的思想政治理论课教师和教学案例编写专家，擅长从多个时事新闻中提炼共同主题，编写富有教育意义、逻辑连贯的思政课教学案例。"
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=4000
        )

        case_content = response.choices[0].message.content

        # 5. 提取案例元数据
        import re

        # 提取标题（寻找第一行非空文本，或第一个【】前的内容）
        lines = case_content.strip().split('\n')
        title = related_messages[0]['title'] if related_messages else knowledge_point_name  # 默认使用第一条消息的标题
        for line in lines[:5]:  # 检查前5行
            line = line.strip()
            if line and not line.startswith('【') and not line.startswith('#'):
                title = line
                break

        # 提取核心阅读作为摘要
        summary_match = re.search(r'【核心阅读】\s*\n\s*(.+?)(?=\n\n|【|■)', case_content, re.DOTALL)
        if summary_match:
            summary = summary_match.group(1).strip()
        else:
            # 备用：取前500字
            summary = case_content[:500]

        # 6. 构造案例对象
        case = {
            "id": str(uuid.uuid4()),
            "title": title,
            "content": case_content,
            "summary": summary,
            "source_url": related_messages[0]['url'],
            "tags": knowledge_point_name,
            "related_knowledge_points": [{
                "id": knowledge_point_id,
                "name": knowledge_point_name
            }],
            "source_message_ids": [msg['id'] for msg in related_messages],
            "published_at": related_messages[0]['published_at'],
            "created_at": datetime.now()
        }

        return case

    def _aggregate_messages(self, messages: List[Dict]) -> Dict:
        """
        智能聚合多条消息的内容

        使用LLM提取核心要点，找出共同主题，生成连贯的综合描述

        Args:
            messages: 消息列表

        Returns:
            聚合结果 {title, content}
        """
        try:
            # 第一步：为每条消息提取核心要点
            message_summaries = []
            for i, msg in enumerate(messages[:5], 1):  # 限制最多5条消息
                # 构造简短的消息描述
                msg_text = f"""
【消息{i}】
标题：{msg['title']}
来源：{msg['provider']}
时间：{msg['published_at'].strftime("%Y-%m-%d") if msg['published_at'] else '未知'}
内容：{msg['content'][:800] if msg['content'] else msg['summary']}
"""
                message_summaries.append(msg_text)

            # 第二步：使用LLM提取共同主题和核心要点
            aggregation_prompt = f"""
请分析以下{len(messages)}条新闻消息，提取它们的共同主题和核心要点。

{chr(10).join(message_summaries)}

请完成以下任务：
1. 提取这些消息的共同主题（1-2句话）
2. 提炼每条消息的核心要点（每条1-2句话）
3. 找出这些消息之间的内在联系

输出格式：
共同主题：[主题描述]

核心要点：
1. [消息1要点]
2. [消息2要点]
...

内在联系：[分析这些事件之间的关联]
"""

            # 调用fast client（更快速）
            response = self.llm_manager.fast_client.generate_with_messages(
                messages=[
                    {"role": "system", "content": "你是一位擅长内容分析和信息提炼的助手。"},
                    {"role": "user", "content": aggregation_prompt}
                ],
                temperature=0.3,
                max_tokens=1000
            )

            analysis_result = response.choices[0].message.content

            # 第三步：生成综合标题
            title_prompt = f"""
基于以下分析结果，生成一个简洁有力的标题（15-25字），突出核心主题：

{analysis_result}

只输出标题，不要其他内容。
"""

            title_response = self.llm_manager.fast_client.generate_with_messages(
                messages=[
                    {"role": "system", "content": "你是标题编写专家。"},
                    {"role": "user", "content": title_prompt}
                ],
                temperature=0.5,
                max_tokens=50
            )

            title = title_response.choices[0].message.content.strip()

            # 第四步：构造最终内容
            content = f"""
{analysis_result}

---

原始消息详情：

{chr(10).join(message_summaries)}
"""

            self.logger.info(f"  [聚合] 生成综合标题: {title}")
            self.logger.info(f"  [聚合] 分析了 {len(messages)} 条消息")

            return {"title": title, "content": content}

        except Exception as e:
            self.logger.error(f"[错误] 智能聚合失败，使用备用方案: {e}")
            # 备用方案：简单聚合
            title = messages[0]['title']
            content_parts = []
            for i, msg in enumerate(messages, 1):
                content_parts.append(f"""
【消息{i}】来源: {msg['provider']} | 时间: {msg['published_at'].strftime("%Y-%m-%d") if msg['published_at'] else '未知'}
标题: {msg['title']}
内容: {msg['content'][:800] if msg['content'] else msg['summary']}...
""")
            content = "\n\n".join(content_parts)
            return {"title": title, "content": content}

    def _save_case(self, case: Dict):
        """
        保存案例到数据库

        Args:
            case: 案例字典
        """
        try:
            with create_session() as db:
                case_obj = IPTCCase(
                    id=case['id'],
                    title=case['title'],
                    content=case['content'],
                    summary=case['summary'],
                    source_url=case['source_url'],
                    tags=case['tags'],
                    related_knowledge_points=case['related_knowledge_points'],
                    source_message_ids=case['source_message_ids'],
                    published_at=case['published_at'],
                    created_at=case['created_at']
                )

                db.add(case_obj)
                db.commit()

        except Exception as e:
            self.logger.error(f"[错误] 保存案例失败: {e}")
            raise

    def _mark_case_generated(self, kp_id: str, kp_name: str):
        """
        标记知识点已生成案例

        Args:
            kp_id: 知识点ID
            kp_name: 知识点名称
        """
        try:
            with create_session() as db:
                # 使用knowledge_point_name作为查询条件，防止重复记录
                stat = db.query(IPTCKnowledgePointStats).filter_by(
                    knowledge_point_name=kp_name
                ).first()

                if stat:
                    # 更新现有记录
                    stat.case_generated = 1
                    stat.last_matched_at = datetime.now()
                    # 更新knowledge_point_id（可能会变化）
                    stat.knowledge_point_id = kp_id
                else:
                    # 创建新记录
                    stat = IPTCKnowledgePointStats(
                        id=str(uuid.uuid4()),
                        knowledge_point_id=kp_id,
                        knowledge_point_name=kp_name,
                        case_generated=1,
                        last_matched_at=datetime.now()
                    )
                    db.add(stat)

                db.commit()

        except Exception as e:
            self.logger.error(f"[错误] 标记已生成失败: {e}")
            raise


def main():
    """主函数"""
    import argparse
    parser = argparse.ArgumentParser(description='批量撞库案例生成')
    parser.add_argument('--limit', type=int, help='限制处理的消息数量（用于测试）')
    parser.add_argument('--dry-run', action='store_true', help='试运行模式（不写入数据库）')
    args = parser.parse_args()

    service = BatchMatchCasesService()
    result = service.run_batch_match(limit=args.limit, dry_run=args.dry_run)

    print(f"\n{'='*60}")
    print(f"任务结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
