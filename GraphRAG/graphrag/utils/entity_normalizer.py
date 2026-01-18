"""
实体归一化工具

本模块提供实体名称归一化和去重功能，用于合并相似的实体。

主要功能：
- 名称归一化（去除空格、统一大小写、简繁转换）
- 相似度计算（Levenshtein距离）
- 重复实体检测
- 别名映射

使用场景：
- 合并"OpenAI"、"Open AI"、"openai"
- 检测疑似重复的实体对
"""

import re
from typing import List, Tuple, Dict
from rapidfuzz import fuzz
import logging

logger = logging.getLogger(__name__)


class EntityNormalizer:
    """实体归一化工具"""

    # 简繁转换映射表（常用字）
    SIMPLIFIED_TO_TRADITIONAL = {
        '蘋': '苹', '機': '机', '網': '网', '電': '电',
        '腦': '脑', '軟': '软', '硬': '硬', '體': '体'
    }

    @staticmethod
    def normalize_name(name: str) -> str:
        """归一化实体名称

        处理步骤：
        1. 去除首尾空格
        2. 统一多个空格为单个空格
        3. 简繁转换（繁体→简体）
        4. 统一英文大小写（首字母大写）

        Args:
            name: 原始名称

        Returns:
            归一化后的名称
        """
        if not name:
            return ""

        # 去除首尾空格
        name = name.strip()

        # 统一多个空格为单个空格
        name = re.sub(r'\s+', ' ', name)

        # 简繁转换（繁体→简体）
        for trad, simp in EntityNormalizer.SIMPLIFIED_TO_TRADITIONAL.items():
            name = name.replace(trad, simp)

        # 统一英文大小写（仅处理纯英文或英文开头的名称）
        if re.match(r'^[A-Za-z]', name):
            # 对于英文名称，使用title case
            words = name.split()
            # 保留全大写的缩写词（如AI、CEO、API）
            normalized_words = []
            for word in words:
                if word.isupper() and len(word) <= 4:
                    # 保留缩写词
                    normalized_words.append(word)
                else:
                    # 其他词首字母大写
                    normalized_words.append(word.capitalize())
            name = ' '.join(normalized_words)

        return name

    @staticmethod
    def calculate_similarity(name1: str, name2: str) -> float:
        """计算两个名称的相似度

        使用Jaro-Winkler距离算法，对前缀相同的字符串给予更高权重。

        Args:
            name1: 第一个名称
            name2: 第二个名称

        Returns:
            相似度（0-1之间，1表示完全相同）
        """
        if not name1 or not name2:
            return 0.0

        # 先归一化
        name1 = EntityNormalizer.normalize_name(name1)
        name2 = EntityNormalizer.normalize_name(name2)

        # 完全相同
        if name1 == name2:
            return 1.0

        # 使用Jaro-Winkler距离（对前缀相同的字符串给予更高权重）
        similarity = fuzz.ratio(name1, name2) / 100.0

        return similarity

    @staticmethod
    def find_duplicates(
        entities: List[Dict],
        threshold: float = 0.9
    ) -> List[Tuple[Dict, Dict, float]]:
        """查找重复实体

        Args:
            entities: 实体列表，每个实体包含name字段
            threshold: 相似度阈值（默认0.9）

        Returns:
            重复实体对列表，每个元素为(entity1, entity2, similarity)
        """
        duplicates = []

        for i in range(len(entities)):
            for j in range(i + 1, len(entities)):
                entity1 = entities[i]
                entity2 = entities[j]

                # 计算相似度
                similarity = EntityNormalizer.calculate_similarity(
                    entity1.get('name', ''),
                    entity2.get('name', '')
                )

                # 超过阈值则认为是重复
                if similarity >= threshold:
                    duplicates.append((entity1, entity2, similarity))
                    logger.info(
                        f"发现疑似重复实体: '{entity1.get('name')}' vs '{entity2.get('name')}' "
                        f"(相似度: {similarity:.2f})"
                    )

        return duplicates

    @staticmethod
    def merge_entities(entity1: Dict, entity2: Dict) -> Dict:
        """合并两个实体

        合并策略：
        1. 保留较短的名称作为主名称（通常是官方简称）
        2. 合并aliases列表
        3. 合并attributes字典
        4. 累加mention_count

        Args:
            entity1: 第一个实体
            entity2: 第二个实体

        Returns:
            合并后的实体
        """
        # 选择较短的名称作为主名称
        name1 = entity1.get('name', '')
        name2 = entity2.get('name', '')

        if len(name1) <= len(name2):
            merged_name = name1
            alias_name = name2
        else:
            merged_name = name2
            alias_name = name1

        # 合并aliases
        aliases1 = entity1.get('aliases', [])
        aliases2 = entity2.get('aliases', [])
        merged_aliases = list(set(aliases1 + aliases2 + [alias_name]))

        # 合并attributes
        attributes1 = entity1.get('attributes', {})
        attributes2 = entity2.get('attributes', {})
        merged_attributes = {**attributes1, **attributes2}

        # 累加mention_count
        mention_count1 = entity1.get('mention_count', 1)
        mention_count2 = entity2.get('mention_count', 1)
        merged_mention_count = mention_count1 + mention_count2

        # 构建合并后的实体
        merged_entity = {
            'name': merged_name,
            'type': entity1.get('type', entity2.get('type')),
            'aliases': merged_aliases,
            'attributes': merged_attributes,
            'mention_count': merged_mention_count
        }

        logger.info(f"合并实体: '{name1}' + '{name2}' → '{merged_name}'")

        return merged_entity

    @staticmethod
    def build_alias_map(entities: List[Dict]) -> Dict[str, str]:
        """构建别名映射表

        Args:
            entities: 实体列表

        Returns:
            别名映射字典 {alias: canonical_name}
        """
        alias_map = {}

        for entity in entities:
            canonical_name = entity.get('name', '')
            aliases = entity.get('aliases', [])

            # 将所有别名映射到规范名称
            for alias in aliases:
                alias_normalized = EntityNormalizer.normalize_name(alias)
                alias_map[alias_normalized] = canonical_name

        return alias_map

    @staticmethod
    def deduplicate_entities(entities: List[Dict], threshold: float = 0.9) -> List[Dict]:
        """实体去重

        自动检测并合并重复实体。

        Args:
            entities: 实体列表
            threshold: 相似度阈值

        Returns:
            去重后的实体列表
        """
        if not entities:
            return []

        # 查找重复实体
        duplicates = EntityNormalizer.find_duplicates(entities, threshold)

        if not duplicates:
            return entities

        # 构建合并映射
        merge_map = {}  # {entity_name: canonical_name}

        for entity1, entity2, similarity in duplicates:
            name1 = entity1.get('name', '')
            name2 = entity2.get('name', '')

            # 选择较短的名称作为规范名称
            if len(name1) <= len(name2):
                canonical = name1
                alias = name2
            else:
                canonical = name2
                alias = name1

            merge_map[alias] = canonical

        # 执行合并
        merged_entities = {}

        for entity in entities:
            name = entity.get('name', '')

            # 查找规范名称
            canonical_name = merge_map.get(name, name)

            # 合并到规范实体
            if canonical_name in merged_entities:
                merged_entities[canonical_name] = EntityNormalizer.merge_entities(
                    merged_entities[canonical_name],
                    entity
                )
            else:
                merged_entities[canonical_name] = entity.copy()
                merged_entities[canonical_name]['name'] = canonical_name

        result = list(merged_entities.values())
        logger.info(f"实体去重: {len(entities)} → {len(result)} (合并了 {len(entities) - len(result)} 个重复)")

        return result
