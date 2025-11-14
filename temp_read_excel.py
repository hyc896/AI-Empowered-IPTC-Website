import pandas as pd
import json

# 读取Excel文件
excel_path = r'c:\Users\WaterFish\Documents\WeChat Files\wxid_gr4kjgxemwho22\FileStorage\File\2025-11\信源筛选结果.xlsx'
df = pd.read_excel(excel_path)

print(f"总共有 {len(df)} 个信源\n")

# 提取URL和名称
results = []
for idx, row in df.iterrows():
    name = str(row.iloc[0]) if pd.notna(row.iloc[0]) else "Unknown"
    url = str(row.iloc[1]) if pd.notna(row.iloc[1]) else ""

    # 检查是否包含Partnership on AI (已添加)
    if 'partnershiponai.org' not in url.lower():
        results.append({
            'index': idx + 1,
            'name': name,
            'url': url
        })
        print(f"{idx + 1}. {name}")
        print(f"   URL: {url}\n")

# 保存到JSON文件供后续使用
with open('D:/TechWork/message_platform/sources_to_add.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(f"\n需要添加的信源数量: {len(results)}")
print("已保存到 sources_to_add.json")
