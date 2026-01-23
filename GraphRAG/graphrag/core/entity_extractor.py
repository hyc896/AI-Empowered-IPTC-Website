"""
实体提取服务

本模块使用LLM从文本中提取实体和关系，用于构建知识图谱。

主要功能：
- 从消息文本中提取实体（公司、人物、技术、产品等）
- 提取实体间的关系（任职、投资、竞争、合作等）
- 实体归一化和去重
- 幻觉检测和降级策略

设计原则：
- 使用system/user消息结构，避免标签式格式
- 严格的JSON格式验证
- 多种幻觉模式检测
- 失败降级：提取失败返回空列表，不中断流程
"""

import json
import logging
from typing import Dict, List, Any, Optional
import re

logger = logging.getLogger(__name__)


class EntityExtractorService:
    """实体提取服务"""

    # 实体类型枚举
    ENTITY_TYPES = [
        "Company",      # 公司
        "Person",       # 人物
        "Technology",   # 技术
        "Product",      # 产品
        "Organization", # 组织/机构
        "Event",        # 事件
        "Concept",      # 概念
        "Location",     # 地点
        "Document",     # 文档
        "Theory",       # 理论
        "Policy",       # 政策
        "Party",        # 政党
        "Government",   # 政府机构
        "Law",          # 法律法规
        "Meeting",      # 会议
        "Movement",     # 运动/改革
        "Ideology",     # 意识形态
        "Period"        # 时期/阶段
    ]

    # 关系类型枚举
    RELATION_TYPES = [
        "WORKS_AT",      # 任职
        "INVESTS_IN",    # 投资
        "DEVELOPS",      # 开发
        "COMPETES_WITH", # 竞争
        "PARTNERS_WITH", # 合作
        "BASED_ON",      # 基于
        "LOCATED_IN",    # 位于
        "PROMOTES",      # 推动
        "LEADS",         # 领导
        "GOVERNS",       # 治理
        "PRESERVES",     # 保持
        "PARTICIPATES_IN", # 参与
        "REPRESENTS",    # 代表
        "BUILDING",      # 建设
        "APPLIES",       # 应用
        "ACHIEVES",      # 实现
        "PROPOSES",      # 提出
        "IMPLEMENTS",    # 实施
        "GUIDES",        # 指导
        "INHERITS",      # 继承
        "SERVES",        # 服务
        "UPHOLDS",       # 坚持
        "OPPOSES",       # 反对
        "BELONGS_TO",    # 属于
        "ENACTS"         # 制定
    ]

    def __init__(self, llm_manager, max_chunk_chars: int = 20000):
        """初始化实体提取服务

        Args:
            llm_manager: GlobalLLMManager实例
            max_chunk_chars: 单个文本块的最大字符数（默认20000，约对应15000-20000 tokens）
        """
        self.llm_manager = llm_manager
        self.max_chunk_chars = max_chunk_chars

    async def extract_entities(
        self,
        text: str,
        language: str = "zh",
        file_id: str = None,
        progress_manager = None
    ) -> Dict[str, Any]:
        """从文本中提取实体和关系

        Args:
            text: 消息文本（标题+内容）
            language: 语言代码（zh/en）

        Returns:
            Dict包含：
            {
                "entities": [
                    {
                        "name": "OpenAI",
                        "type": "Company",
                        "aliases": ["Open AI"],
                        "attributes": {"country": "美国", "industry": "人工智能"}
                    },
                    ...
                ],
                "relations": [
                    {
                        "source": "Sam Altman",
                        "target": "OpenAI",
                        "type": "WORKS_AT",
                        "properties": {"role": "CEO"}
                    },
                    ...
                ]
            }

        如果提取失败，返回空列表
        """
        print(f"🔍 EntityExtractor.extract_entities 被调用，文本长度: {len(text) if text else 0}")

        if not text or len(text.strip()) < 10:
            logger.warning("文本过短，跳过实体提取")
            print(f"⚠️ 文本过短，跳过实体提取")
            return {"entities": [], "relations": []}

        try:
            # 检查文本长度，决定是否需要分块处理
            if len(text) > self.max_chunk_chars:
                logger.info(f"文本过长({len(text)}字符)，启用分块处理")
                print(f"📦 文本过长({len(text)}字符)，启用分块处理")
                return await self._extract_entities_chunked(text, language, file_id, progress_manager)
            else:
                print(f"📄 使用单块处理，文本长度: {len(text)}")
                return await self._extract_entities_single(text, language)

        except Exception as e:
            logger.error(f"实体提取失败: {e}", exc_info=True)
            print(f"❌ 实体提取失败: {e}")
            return {"entities": [], "relations": []}

    async def _extract_entities_single(
        self,
        text: str,
        language: str = "zh"
    ) -> Dict[str, Any]:
        """从单个文本块中提取实体和关系

        Args:
            text: 文本内容
            language: 语言代码

        Returns:
            提取结果字典
        """
        # 构建提示词
        messages = self._build_extraction_prompt(text, language)

        # 获取LLM客户端
        llm_client = self.llm_manager
        if not llm_client:
            logger.error("LLM客户端未初始化")
            return {"entities": [], "relations": []}

        # 调用LLM
        print(f"🤖 准备调用 LLM，temperature=0.3, max_tokens=8000")
        response = await llm_client.generate_async(
            messages=messages,
            temperature=0.3,
            max_tokens=8000
        )

        # 提取响应文本
        response_text = response.choices[0].message.content
        print(f"📥 LLM 响应长度: {len(response_text)} 字符")
        print(f"📥 LLM 响应前200字符: {response_text[:200]}")

        # 解析响应
        print(f"🔧 开始解析 JSON 响应")
        result = self._parse_extraction_result(response_text)
        print(f"✅ JSON 解析完成: entities={len(result.get('entities', []))}, relations={len(result.get('relations', []))}")

        # 验证结果
        print(f"🔍 开始验证提取结果")
        if not self._validate_extraction_result(result):
            logger.warning("实体提取结果验证失败，返回空列表")
            print(f"❌ 验证失败，返回空列表")
            return {"entities": [], "relations": []}

        print(f"✅ 验证通过")
        logger.info(f"成功提取 {len(result['entities'])} 个实体, {len(result['relations'])} 个关系")
        return result

    async def _extract_entities_chunked(
        self,
        text: str,
        language: str = "zh",
        file_id: str = None,
        progress_manager = None
    ) -> Dict[str, Any]:
        """分块提取实体和关系(用于超长文本)

        Args:
            text: 文本内容
            language: 语言代码
            file_id: 文件ID(用于进度更新)
            progress_manager: 进度管理器(可选)

        Returns:
            合并后的提取结果
        """
        # 分块
        chunks = self._split_text_into_chunks(text)
        total_chunks = len(chunks)
        print(f"📦 文本已分为 {total_chunks} 个块,准备处理")
        logger.info(f"文本已分为 {total_chunks} 个块")

        # 更新进度: 分块完成
        if progress_manager and file_id:
            await progress_manager.set_progress(
                file_id=file_id,
                status="processing",
                progress=25,
                message=f"文本已分为 {total_chunks} 个块,开始提取...",
                total_blocks=total_chunks,
                current_block=0
            )

        # 使用信号量限制并发数量（最多3个并发请求）
        import asyncio
        semaphore = asyncio.Semaphore(3)
        completed_chunks = 0

        async def extract_with_semaphore(chunk, index):
            nonlocal completed_chunks
            async with semaphore:
                print(f"🔄 正在处理块 {index+1}/{total_chunks}...")
                result = await self._extract_entities_single(chunk, language)

                # 更新进度
                completed_chunks += 1
                if progress_manager and file_id:
                    # 进度从 25% 到 75%,共 50% 的进度空间
                    progress = 25 + int((completed_chunks / total_chunks) * 50)
                    await progress_manager.set_progress(
                        file_id=file_id,
                        status="processing",
                        progress=progress,
                        message=f"正在处理块 {completed_chunks}/{total_chunks}...",
                        total_blocks=total_chunks,
                        current_block=completed_chunks
                    )
                    print(f"✓ 块 {index+1}/{total_chunks} 处理完成")

                return result

        tasks = [extract_with_semaphore(chunk, i) for i, chunk in enumerate(chunks)]

        print(f"🔄 开始提取 {len(tasks)} 个文本块（每次最多3个并发）...")
        chunk_results = await asyncio.gather(*tasks, return_exceptions=True)
        print(f"✅ 所有文本块提取完成")

        # 合并结果
        merged_entities = []
        merged_relations = []
        entity_names_seen = set()
        relation_keys_seen = set()  # 用于关系去重

        for i, result in enumerate(chunk_results):
            if isinstance(result, Exception):
                logger.error(f"块 {i+1} 提取失败: {result}")
                print(f"❌ 块 {i+1}/{len(chunks)} 提取失败: {result}")
                continue

            # 合并实体(去重)
            for entity in result.get("entities", []):
                entity_name = entity.get("name")
                if entity_name and entity_name not in entity_names_seen:
                    merged_entities.append(entity)
                    entity_names_seen.add(entity_name)

            # 合并关系(去重)
            for relation in result.get("relations", []):
                # 使用 (source, target, type) 作为唯一标识
                relation_key = (
                    relation.get("source"),
                    relation.get("target"),
                    relation.get("type")
                )
                if relation_key not in relation_keys_seen:
                    merged_relations.append(relation)
                    relation_keys_seen.add(relation_key)
            print(f"✓ 块 {i+1}/{len(chunks)} 处理完成")

        print(f"🎉 分块提取完成: 总计 {len(merged_entities)} 个实体, {len(merged_relations)} 个关系")
        logger.info(f"分块提取完成: 总计 {len(merged_entities)} 个实体, {len(merged_relations)} 个关系")
        return {
            "entities": merged_entities,
            "relations": merged_relations
        }

    def _split_text_into_chunks(self, text: str) -> List[str]:
        """将长文本分割成多个块

        策略：
        1. 按段落分割（\n\n）
        2. 每个块不超过max_chunk_chars字符
        3. 尽量保持段落完整性
        4. 超长段落按句子分割，避免破坏语义

        Args:
            text: 原始文本

        Returns:
            文本块列表
        """
        import re

        # 按段落分割
        paragraphs = text.split('\n\n')

        chunks = []
        current_chunk = []
        current_length = 0

        for para in paragraphs:
            para_length = len(para)

            # 如果单个段落就超过限制，按句子分割
            if para_length > self.max_chunk_chars:
                # 先保存当前块
                if current_chunk:
                    chunks.append('\n\n'.join(current_chunk))
                    current_chunk = []
                    current_length = 0

                # 按句子分割超长段落（中文句号、问号、感叹号、英文句号）
                sentences = re.split(r'([。！？\.!?])', para)
                # 重新组合句子和标点
                combined_sentences = []
                for i in range(0, len(sentences) - 1, 2):
                    if i + 1 < len(sentences):
                        combined_sentences.append(sentences[i] + sentences[i + 1])
                    else:
                        combined_sentences.append(sentences[i])
                if len(sentences) % 2 == 1:  # 处理最后一个没有标点的部分
                    combined_sentences.append(sentences[-1])

                # 按句子组装块
                sentence_chunk = []
                sentence_chunk_length = 0
                for sentence in combined_sentences:
                    sentence_length = len(sentence)

                    # 如果单个句子就超过限制，强制分割
                    if sentence_length > self.max_chunk_chars:
                        if sentence_chunk:
                            chunks.append(''.join(sentence_chunk))
                            sentence_chunk = []
                            sentence_chunk_length = 0
                        # 强制按字符分割（最后的手段）
                        for i in range(0, sentence_length, self.max_chunk_chars):
                            chunks.append(sentence[i:i+self.max_chunk_chars])
                        continue

                    if sentence_chunk_length + sentence_length > self.max_chunk_chars:
                        if sentence_chunk:
                            chunks.append(''.join(sentence_chunk))
                        sentence_chunk = [sentence]
                        sentence_chunk_length = sentence_length
                    else:
                        sentence_chunk.append(sentence)
                        sentence_chunk_length += sentence_length

                # 保存最后一个句子块
                if sentence_chunk:
                    chunks.append(''.join(sentence_chunk))
                continue

            # 如果加入当前段落会超过限制，先保存当前块
            if current_length + para_length > self.max_chunk_chars:
                if current_chunk:
                    chunks.append('\n\n'.join(current_chunk))
                current_chunk = [para]
                current_length = para_length
            else:
                current_chunk.append(para)
                current_length += para_length + 2  # +2 for '\n\n'

        # 保存最后一个块
        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))

        return chunks

    def _build_extraction_prompt(self, text: str, language: str) -> List[Dict]:
        """构建实体提取提示词

        使用system/user消息结构，避免标签式格式（防止LLM进入"引导模式"）

        Args:
            text: 待提取文本
            language: 语言代码

        Returns:
            消息列表
        """
        system_prompt = """你是一个专业的知识图谱构建助手。你的任务是从文本中提取实体和关系。

## 实体类型
1. Company（公司）：科技公司、投资机构、初创企业
2. Person（人物）：CEO、创始人、研究者
3. Technology（技术）：算法、框架、产品技术
4. Product（产品）：具体产品名称
5. Organization（组织）：政府机构、研究机构
6. Event（事件）：发布会、融资、合作
7. Concept（概念）：技术概念、商业模式
8. Location（地点）：国家、城市、地区

## 关系类型
- WORKS_AT（任职）：Person → Company/Organization
- INVESTS_IN（投资）：Company → Company
- DEVELOPS（开发）：Company → Technology/Product
- COMPETES_WITH（竞争）：Company ↔ Company
- PARTNERS_WITH（合作）：Company ↔ Company
- BASED_ON（基于）：Technology → Technology
- LOCATED_IN（位于）：Company/Event → Location

## 提取规则
1. 仅提取明确出现的实体，不要推断
2. 人名需要完整，不要只提取姓氏
3. 公司名称使用官方全称
4. 避免提取过于宽泛的概念（如"人工智能"除非作为核心主题）
5. 关系必须在文本中明确提及，不要推断潜在关系
6. 同一实体的不同表述归并到aliases

## 输出格式
必须返回严格的JSON格式，包含entities和relations两个数组。

示例：
{
  "entities": [
    {
      "name": "OpenAI",
      "type": "Company",
      "aliases": ["Open AI"],
      "attributes": {"country": "美国", "industry": "人工智能"}
    }
  ],
  "relations": [
    {
      "source": "Sam Altman",
      "target": "OpenAI",
      "type": "WORKS_AT",
      "properties": {"role": "CEO"}
    }
  ]
}"""

        user_prompt = f"请从以下文本中提取实体和关系：\n\n{text}"

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

    def _parse_extraction_result(self, response: str) -> Dict[str, Any]:
        """解析LLM返回的提取结果

        Args:
            response: LLM响应文本

        Returns:
            解析后的字典

        Raises:
            ValueError: JSON解析失败
        """
        # 检测幻觉
        if self._is_hallucination(response):
            logger.warning("检测到幻觉输出，返回空结果")
            print(f"⚠️ 检测到幻觉输出，返回空结果")
            return {"entities": [], "relations": []}

        # 尝试提取JSON
        try:
            # 尝试直接解析
            print(f"🔧 尝试直接解析 JSON")
            result = json.loads(response)
            print(f"✅ 直接解析成功")
            return result
        except json.JSONDecodeError as e:
            print(f"⚠️ 直接解析失败: {str(e)}")
            # 尝试从markdown代码块中提取
            print(f"🔧 尝试从 markdown 代码块中提取")
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
            if json_match:
                try:
                    result = json.loads(json_match.group(1))
                    print(f"✅ 从 markdown 代码块解析成功")
                    return result
                except json.JSONDecodeError as e:
                    print(f"⚠️ markdown 代码块解析失败: {str(e)}")
                    pass

            # 尝试查找第一个完整的JSON对象
            print(f"🔧 尝试查找完整的 JSON 对象")
            json_match = re.search(r'\{.*"entities".*"relations".*\}', response, re.DOTALL)
            if json_match:
                try:
                    result = json.loads(json_match.group(0))
                    print(f"✅ 查找 JSON 对象解析成功")
                    return result
                except json.JSONDecodeError as e:
                    print(f"⚠️ JSON 对象解析失败: {str(e)}")
                    pass

            logger.error(f"无法解析JSON响应: {response[:200]}")
            print(f"❌ 所有 JSON 解析尝试都失败")
            print(f"❌ 响应内容（前500字符）: {response[:500]}")
            return {"entities": [], "relations": []}

    def _is_hallucination(self, response: str) -> bool:
        """检测LLM幻觉输出

        检测多种幻觉模式：
        1. 模板占位符：{{variable}}
        2. 引导式回复："请提供"、"我将为您"
        3. 元描述："以下是提取结果"、"提取如下"

        Args:
            response: LLM响应

        Returns:
            是否为幻觉
        """
        # 检测模板占位符（排除LaTeX公式中的合法大括号）
        # 精确匹配 {{word}} 模式，不匹配 LaTeX 的 {^{...}}
        template_pattern = r'\{\{[a-zA-Z_][a-zA-Z0-9_]*\}\}'
        if re.search(template_pattern, response):
            logger.warning(f"检测到模板占位符幻觉")
            return True

        # 检测引导式回复
        guide_patterns = [
            r'请提供.*?文本',
            r'我将为您',
            r'需要您提供',
            r'请输入',
            r'等待您的'
        ]
        for pattern in guide_patterns:
            if re.search(pattern, response, re.IGNORECASE):
                logger.warning(f"检测到引导式回复幻觉: {pattern}")
                return True

        # 检测元描述（但允许在JSON之外的说明文字）
        meta_patterns = [
            r'^以下是.*?结果',
            r'^提取结果如下',
            r'^根据文本.*?提取'
        ]
        for pattern in meta_patterns:
            if re.search(pattern, response.strip(), re.IGNORECASE):
                # 如果同时包含有效的JSON，则不算幻觉
                if not re.search(r'\{.*"entities".*\}', response, re.DOTALL):
                    logger.warning(f"检测到元描述幻觉: {pattern}")
                    return True

        return False

    def _validate_extraction_result(self, result: Dict) -> bool:
        """验证提取结果的有效性

        Args:
            result: 提取结果字典

        Returns:
            是否有效
        """
        # 检查必需字段
        if not isinstance(result, dict):
            logger.warning("结果不是字典类型")
            return False

        if "entities" not in result or "relations" not in result:
            logger.warning("缺少必需字段: entities或relations")
            return False

        if not isinstance(result["entities"], list) or not isinstance(result["relations"], list):
            logger.warning("entities或relations不是列表类型")
            return False

        # 验证实体格式
        for entity in result["entities"]:
            if not isinstance(entity, dict):
                logger.warning(f"实体不是字典类型: {entity}")
                return False

            if "name" not in entity or "type" not in entity:
                logger.warning(f"实体缺少必需字段: {entity}")
                return False

            # 验证实体类型
            if entity["type"] not in self.ENTITY_TYPES:
                logger.warning(f"无效的实体类型: {entity['type']}")
                # 不返回False，只记录警告

        # 验证关系格式
        for relation in result["relations"]:
            if not isinstance(relation, dict):
                logger.warning(f"关系不是字典类型: {relation}")
                return False

            if "source" not in relation or "target" not in relation or "type" not in relation:
                logger.warning(f"关系缺少必需字段: {relation}")
                return False

            # 验证关系类型
            if relation["type"] not in self.RELATION_TYPES:
                logger.warning(f"无效的关系类型: {relation['type']}")
                # 不返回False，只记录警告

        return True
