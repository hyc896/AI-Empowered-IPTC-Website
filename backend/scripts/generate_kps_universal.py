# -*- coding: utf-8 -*-
"""
通用知识点生成脚本 - 支持指定生成数量
"""
import sys
import json
import os
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

backend_dir = Path(__file__).parent.parent
project_root = backend_dir.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(backend_dir))

# 加载.env文件
env_path = project_root / ".env"
load_dotenv(env_path)

class KnowledgePointGenerator:
    def __init__(self, kp_structure_file, full_book_file, book_name):
        # 使用环境变量中的API配置
        self.client = OpenAI(
            api_key=os.getenv("FAST_LLM_API_KEY"),
            base_url=os.getenv("FAST_LLM_BASE_URL")
        )
        self.model = os.getenv("FAST_LLM_MODEL", "deepseek-ai/DeepSeek-V3.2-Exp")
        self.book_name = book_name

        # 读取知识点结构
        with open(kp_structure_file, 'r', encoding='utf-8') as f:
            self.kp_structures = json.load(f)

        # 读取全书内容
        with open(full_book_file, 'r', encoding='utf-8') as f:
            self.full_book = f.read()

    def generate_kp_with_llm(self, kp_structure):
        """使用LLM生成知识点内容"""
        # 构建章节信息
        section_info = kp_structure.get('section', kp_structure['chapter'])

        prompt = f"""你是一位思政课教学专家。请根据以下信息生成知识点的详细内容:

书名: {kp_structure['book_name']}
章节: {kp_structure['chapter']}
节: {section_info}
知识点名称: {kp_structure['name']}
部分: {kp_structure['part']}

请从教材全文中找到这个知识点对应的内容,然后生成:

1. theory_description: 该知识点的理论描述(200-300字),要准确概括核心理论内容
2. application_scenarios: 该知识点的应用场景(150-200字),说明在思政课教学、理论研究、实践应用中的具体场景
3. typical_keywords: 该知识点的典型关键词(8-12个),用逗号分隔

请以JSON格式返回,格式如下:
{{
    "theory_description": "...",
    "application_scenarios": "...",
    "typical_keywords": "..."
}}

注意:
1. 只返回JSON,不要有其他内容
2. 确保JSON格式正确
3. 内容要准确反映教材原文
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一位思政课教学专家,擅长提取和总结理论知识点。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=2000
            )

            content = response.choices[0].message.content.strip()

            # 尝试解析JSON
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

            result = json.loads(content)
            return result

        except json.JSONDecodeError as e:
            print(f"  [失败] JSON解析错误: {e}")
            return None
        except Exception as e:
            print(f"  [失败] LLM调用失败: {e}")
            return None

    def generate(self, limit=None):
        """生成知识点内容

        Args:
            limit: 限制生成数量,None表示生成全部
        """
        results = []
        kps_to_process = self.kp_structures[:limit] if limit else self.kp_structures
        total = len(kps_to_process)

        print("=" * 60)
        print(f"开始生成 {self.book_name} 的知识点")
        print(f"总数: {total} 个")
        print("=" * 60)

        for i, kp_structure in enumerate(kps_to_process, 1):
            print(f"\n处理 {i}/{total}: {kp_structure['name']}")

            # 使用LLM生成内容
            llm_result = self.generate_kp_with_llm(kp_structure)

            if llm_result:
                # 合并结构和内容
                kp = {**kp_structure, **llm_result}
                results.append(kp)
                print(f"  [成功] 已生成")
            else:
                print(f"  [失败] 跳过")

        print("\n" + "=" * 60)
        print(f"成功生成 {len(results)}/{total} 个知识点")
        print("=" * 60)

        return results

    def save(self, results, output_file):
        """保存结果"""
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\n知识点已保存到: {output_file}")

def main():
    import argparse
    parser = argparse.ArgumentParser(description='生成知识点内容')
    parser.add_argument('--book', choices=['xi', 'morality'], required=True,
                        help='选择教材: xi(习近平思想) 或 morality(思想道德与法治)')
    parser.add_argument('--limit', type=int, default=None,
                        help='限制生成数量(用于测试),默认生成全部')
    args = parser.parse_args()

    if args.book == 'xi':
        generator = KnowledgePointGenerator(
            kp_structure_file=backend_dir / "data" / "xi_kp_structure.json",
            full_book_file=backend_dir / "data" / "xi_full_book.txt",
            book_name="习近平新时代中国特色社会主义思想概论"
        )
        output_file = backend_dir / "data" / "xi_knowledge_points.json"
    else:  # morality
        generator = KnowledgePointGenerator(
            kp_structure_file=backend_dir / "data" / "morality_kp_structure.json",
            full_book_file=backend_dir / "data" / "morality_full_book.txt",
            book_name="思想道德与法治"
        )
        output_file = backend_dir / "data" / "morality_knowledge_points.json"

    results = generator.generate(limit=args.limit)
    generator.save(results, output_file)

if __name__ == "__main__":
    main()
