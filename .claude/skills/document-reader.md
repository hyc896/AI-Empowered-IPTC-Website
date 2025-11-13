# Document Reader Skill

读取和解析 Excel、Word 和 PDF 文件的专用技能。

## 支持的文件格式

- Excel 文件 (.xlsx, .xls)
- Word 文档 (.docx)
- PDF 文件 (.pdf)

## 使用方法

当用户要求读取或分析这些类型的文件时，按照以下步骤操作：

### 1. Excel 文件读取

使用 Python 的 pandas 或 openpyxl 库读取 Excel 文件：

```python
import pandas as pd

# 读取 Excel 文件
df = pd.read_excel('文件路径.xlsx', sheet_name='Sheet1')

# 显示基本信息
print(f"行数: {len(df)}")
print(f"列数: {len(df.columns)}")
print(f"列名: {list(df.columns)}")

# 显示前几行
print(df.head())

# 获取特定数据
# df['列名']  # 获取特定列
# df.iloc[0]  # 获取第一行
```

**读取所有工作表**：
```python
# 读取所有工作表
excel_file = pd.ExcelFile('文件路径.xlsx')
sheet_names = excel_file.sheet_names
print(f"工作表: {sheet_names}")

# 遍历所有工作表
for sheet in sheet_names:
    df = pd.read_excel(excel_file, sheet_name=sheet)
    print(f"\n工作表: {sheet}")
    print(df.head())
```

### 2. Word 文档读取

使用 python-docx 库读取 Word 文档：

```python
from docx import Document

# 读取 Word 文档
doc = Document('文件路径.docx')

# 读取所有段落
paragraphs = []
for para in doc.paragraphs:
    if para.text.strip():  # 跳过空段落
        paragraphs.append(para.text)

print(f"总段落数: {len(paragraphs)}")
print("\n".join(paragraphs))

# 读取表格
for i, table in enumerate(doc.tables):
    print(f"\n表格 {i+1}:")
    for row in table.rows:
        cells = [cell.text for cell in row.cells]
        print(" | ".join(cells))
```

### 3. PDF 文件读取

**方法一：使用 Read 工具（推荐）**

Claude Code 的 Read 工具原生支持 PDF：

```
直接使用 Read 工具读取 PDF 文件路径
```

**方法二：使用 Python 库**

```python
import PyPDF2

# 读取 PDF
with open('文件路径.pdf', 'rb') as file:
    pdf_reader = PyPDF2.PdfReader(file)
    num_pages = len(pdf_reader.pages)

    print(f"总页数: {num_pages}")

    # 读取所有页面
    text = ""
    for page_num in range(num_pages):
        page = pdf_reader.pages[page_num]
        text += page.extract_text()

    print(text)
```

## 依赖安装

使用此 skill 前需要安装以下 Python 库：

```bash
pip install pandas openpyxl python-docx PyPDF2
```

或者在项目的 requirements.txt 中添加：
```
pandas
openpyxl
python-docx
PyPDF2
```

## 工作流程

1. **接收文件路径**：用户提供要读取的文件路径
2. **识别文件类型**：根据文件扩展名判断类型
3. **选择合适的库**：
   - Excel → pandas
   - Word → python-docx
   - PDF → Read 工具或 PyPDF2
4. **读取并解析**：使用相应的方法读取文件
5. **格式化输出**：以清晰的格式展示内容
6. **提供摘要**：总结文件的关键信息（行数、段落数、页数等）

## 示例场景

### 场景 1：分析 Excel 数据表

用户: "读取这个 Excel 文件并告诉我有哪些列"

响应:
1. 使用 pandas 读取 Excel
2. 显示列名、行数、数据类型
3. 展示前几行数据作为示例

### 场景 2：提取 Word 文档内容

用户: "从这个 Word 文档中提取所有文字"

响应:
1. 使用 python-docx 读取文档
2. 提取所有段落
3. 如果有表格，也一并提取
4. 返回完整文本

### 场景 3：读取 PDF 报告

用户: "读取这个 PDF 文件"

响应:
1. 优先使用 Read 工具直接读取
2. 如果需要编程处理，使用 PyPDF2
3. 提取文本内容并格式化展示

## 注意事项

1. **文件路径**：确保使用绝对路径，Windows 路径使用原始字符串 r"D:\path\file.xlsx" 或双反斜杠
2. **编码问题**：如果遇到中文乱码，尝试指定编码：`pd.read_excel(..., encoding='utf-8')`
3. **大文件处理**：对于大型 Excel 文件，可以分块读取：`pd.read_excel(..., chunksize=1000)`
4. **PDF 复杂格式**：PDF 中的图片、复杂排版可能无法完美提取，建议使用 Read 工具
5. **错误处理**：使用 try-except 捕获文件读取错误

## 错误处理示例

```python
import pandas as pd
from pathlib import Path

def read_document(file_path):
    """通用文档读取函数"""
    path = Path(file_path)

    if not path.exists():
        return f"错误：文件不存在: {file_path}"

    try:
        if path.suffix in ['.xlsx', '.xls']:
            df = pd.read_excel(file_path)
            return f"成功读取 Excel 文件\n行数: {len(df)}\n列: {list(df.columns)}\n\n{df.head()}"

        elif path.suffix == '.docx':
            from docx import Document
            doc = Document(file_path)
            text = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
            return f"成功读取 Word 文档\n段落数: {len(doc.paragraphs)}\n\n{text[:1000]}..."

        elif path.suffix == '.pdf':
            # 建议使用 Read 工具
            return "PDF 文件请使用 Read 工具直接读取"

        else:
            return f"不支持的文件类型: {path.suffix}"

    except Exception as e:
        return f"读取文件时出错: {str(e)}"
```

## 高级功能

### Excel 数据分析

```python
# 基本统计
df.describe()

# 筛选数据
filtered = df[df['列名'] > 100]

# 数据透视
pivot = df.pivot_table(values='值列', index='行列', columns='列列', aggfunc='sum')

# 导出为 JSON
df.to_json('output.json', orient='records', force_ascii=False)
```

### Word 文档结构分析

```python
from docx import Document

doc = Document('file.docx')

# 分析标题结构
for para in doc.paragraphs:
    if para.style.name.startswith('Heading'):
        print(f"{para.style.name}: {para.text}")

# 提取图片（需要额外处理）
for rel in doc.part.rels.values():
    if "image" in rel.target_ref:
        print(f"发现图片: {rel.target_ref}")
```

## 输出格式建议

读取文件后，提供结构化的输出：

```
📄 文件信息
- 文件名: xxx.xlsx
- 类型: Excel 工作簿
- 大小: 1.2 MB
- 工作表数量: 3

📊 数据概览
- 总行数: 1,234
- 总列数: 15
- 列名: ['ID', '姓名', '日期', ...]

📋 内容预览
[显示前 5-10 行数据]

💡 摘要
[根据内容提供关键洞察]
```

## 集成到工作流

此 skill 可与其他 Claude Code 功能结合：

1. **读取后分析**：读取 Excel 后进行数据分析
2. **内容提取**：从 PDF 中提取文本后进行摘要
3. **格式转换**：Excel → JSON/CSV，Word → Markdown
4. **批量处理**：遍历目录中的所有文档文件
