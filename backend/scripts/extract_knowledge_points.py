# -*- coding: utf-8 -*-
"""
从思政课教材章节中自动提取知识点
"""
import json
import sys
import os
import asyncio
from pathlib import Path
from typing import List, Dict

# 设置控制台输出编码为UTF-8
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 添加backend目录到path
backend_dir = Path(__file__).parent.parent
project_root = backend_dir.parent
sys.path.insert(0, str(project_root))  # 添加项目根目录
sys.path.insert(0, str(backend_dir))    # 添加backend目录

from llm.global_llm_manager import GlobalLLMManager
from config import GlobalConfig


def initialize_llm_manager():
    """初始化LLM管理器"""
    # 加载配置
    config_instance = GlobalConfig.get_instance()

    # 配置文件路径（相对于项目根目录）
    project_root = Path(__file__).parent.parent.parent
    config_path = project_root / "config.yaml"

    config_instance.initialize(str(config_path))

    # 获取LLM配置
    llm_config = config_instance.get_config('llm', {})
    chat_config = llm_config.get('chat', {})
    embedding_config = llm_config.get('embedding', {})
    fast_config = llm_config.get('fast', {})

    # 初始化LLM管理器
    llm_manager = GlobalLLMManager.get_instance()
    llm_manager.initialize(chat_config, embedding_config, fast_config)

    print("[初始化] LLM管理器初始化成功")
    print(f"  Chat模型: {chat_config.get('model')}")
    print(f"  Embedding模型: {embedding_config.get('model')}")

    return llm_manager


# 提示词模板
EXTRACT_PROMPT_TEMPLATE = """你是一位资深的思想政治理论课教师。请从以下教材章节中提取核心知识点。

【章节内容】
{chapter_text}

【提取要求】

1. 识别本章节的核心知识点（5-10个）
2. 对每个知识点，提供以下信息：

**知识点名称**：简洁明确（10-20字）
例如："以人民为中心的发展思想"、"共同富裕理论"

**理论描述**：学术定义和核心要义（150-200字）

**应用场景**：该理论在实际中的应用和体现（3-5个场景，每个30-50字）
重要：请用日常新闻语言描述，不要用理论术语
例如：
- "政府推出养老食堂、托幼服务等惠民政策，解决群众急难愁盼"
- "城乡教育资源均衡配置，山区孩子也能享受优质教育"
- "基层干部深入社区倾听居民诉求，改善公共服务"

**典型关键词**：与应用场景相关的常见词汇（10-15个）
重点包含实践领域的词汇，不仅是理论术语
例如：["民生", "惠民", "社区服务", "养老食堂", "教育公平", "医疗保障"]

【输出格式】

请严格按照JSON格式输出，不要添加任何其他文字：

```json
[
  {{
    "name": "知识点名称",
    "theory_description": "理论描述...",
    "application_scenarios": [
      "应用场景1",
      "应用场景2",
      "应用场景3"
    ],
    "typical_keywords": ["关键词1", "关键词2", "关键词3"]
  }}
]
```
"""


async def extract_knowledge_points_from_chapter(
    chapter_id: str,
    chapter_name: str,
    chapter_text: str
) -> List[Dict]:
    """
    从单个章节提取知识点

    Args:
        chapter_id: 章节ID
        chapter_name: 章节名称
        chapter_text: 章节文本内容

    Returns:
        知识点列表
    """
    print(f"\n正在处理章节: {chapter_name}")

    # 填充提示词模板
    prompt = EXTRACT_PROMPT_TEMPLATE.format(chapter_text=chapter_text)

    # 获取LLM管理器
    llm_manager = GlobalLLMManager.get_instance()

    try:
        # 调用LLM
        response = await llm_manager.chat_client.generate_with_messages_async(
            messages=[
                {
                    "role": "system",
                    "content": "你是一位资深的思想政治理论课教师，擅长提取和总结知识点。"
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,  # 较低温度保证稳定输出
            max_tokens=3000
        )

        # 解析响应
        content = response.choices[0].message.content

        # 提取JSON部分（可能包含```json```标记）
        import re
        json_match = re.search(r'```json\s*(\[.*?\])\s*```', content, re.DOTALL)
        if json_match:
            content = json_match.group(1)

        # 解析JSON
        knowledge_points = json.loads(content)

        # 添加章节信息和生成embedding_text
        for kp in knowledge_points:
            kp['chapter'] = chapter_name
            kp['chapter_id'] = chapter_id

            # 生成embedding_text（理论+关键词+场景）
            keywords_text = ' '.join(kp.get('typical_keywords', []))
            scenarios_text = ' '.join(kp.get('application_scenarios', []))
            theory_snippet = kp.get('theory_description', '')[:100]

            kp['embedding_text'] = f"{kp['name']} {theory_snippet} {keywords_text} {scenarios_text}"

        print(f"  [成功] 提取到 {len(knowledge_points)} 个知识点")
        for kp in knowledge_points:
            print(f"    - {kp['name']}")

        return knowledge_points

    except Exception as e:
        print(f"  [错误] 提取失败: {e}")
        import traceback
        traceback.print_exc()
        return []


async def extract_all_knowledge_points(
    textbook_file: str = None
):
    """
    提取整本教材的知识点

    Args:
        textbook_file: 教材章节JSON文件路径
    """
    # 默认路径
    if textbook_file is None:
        data_dir = Path(__file__).parent.parent / "data"
        textbook_file = data_dir / "textbook_chapters.json"

    print(f"正在读取教材章节: {textbook_file}")

    # 读取教材章节
    with open(textbook_file, 'r', encoding='utf-8') as f:
        textbook = json.load(f)

    print(f"共找到 {len(textbook)} 个章节")

    all_knowledge_points = []

    for chapter in textbook:
        # 拼接章节文本（取第一个section的text）
        if 'sections' in chapter and len(chapter['sections']) > 0:
            chapter_text = chapter['sections'][0]['text']
        else:
            print(f"  [警告] 章节 {chapter['chapter_name']} 没有文本内容，跳过")
            continue

        # 提取知识点
        try:
            kps = await extract_knowledge_points_from_chapter(
                chapter_id=chapter['chapter_id'],
                chapter_name=chapter['chapter_name'],
                chapter_text=chapter_text
            )

            all_knowledge_points.extend(kps)

            # 延迟避免API限流
            await asyncio.sleep(2)

        except Exception as e:
            print(f"  [错误] 处理章节失败: {e}")
            continue

    # 保存结果
    output_dir = Path(__file__).parent.parent / "data"
    output_file = output_dir / "knowledge_points.json"

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_knowledge_points, f, ensure_ascii=False, indent=2)

    print(f"\n[完成] 成功提取 {len(all_knowledge_points)} 个知识点")
    print(f"[保存] 保存到: {output_file}")

    return all_knowledge_points


if __name__ == "__main__":
    # 初始化LLM管理器
    initialize_llm_manager()

    # 运行提取任务
    asyncio.run(extract_all_knowledge_points())
