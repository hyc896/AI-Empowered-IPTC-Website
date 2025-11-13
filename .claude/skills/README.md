# Claude Skills 使用指南

本目录包含 Claude Code 的自定义 skills。

## 可用 Skills

### 📄 document-reader

读取和解析 Excel、Word 和 PDF 文件。

**激活方式：**
```
/skill document-reader
```

**支持的文件格式：**
- Excel (.xlsx, .xls)
- Word (.docx)
- PDF (.pdf)

**使用示例：**
```
用户: 帮我读取这个 Excel 文件 D:\data\report.xlsx
Claude: [激活 document-reader skill 并读取文件]
```

## 安装依赖

在使用 document-reader skill 之前，需要安装相关依赖：

```bash
pip install -r .claude/skills/document-reader-requirements.txt
```

或者单独安装：
```bash
pip install pandas openpyxl python-docx PyPDF2
```

## Skills 工作原理

1. Skills 是存储在 `.claude/skills/` 目录下的 Markdown 文件
2. 每个 skill 包含特定任务的指令和最佳实践
3. 使用 Skill 工具激活特定的 skill
4. Skill 被激活后，Claude 会遵循 skill 中定义的指令

## 创建自定义 Skill

在 `.claude/skills/` 目录下创建新的 `.md` 文件：

```markdown
# 你的 Skill 名称

简短描述此 skill 的用途。

## 使用方法

详细说明如何使用此 skill...

## 示例

提供具体的使用示例...
```

## 编程方式使用

除了通过 skill 交互，也可以直接使用工具模块：

```python
from backend.utils.document_reader import DocumentReader, format_document_summary

# 读取任意文档
result = DocumentReader.read_document("path/to/file.xlsx")

# 打印摘要
print(format_document_summary(result))

# 访问详细数据
if result["success"]:
    data = result["data"]  # Excel 数据
    # 或
    text = result["full_text"]  # Word/PDF 文本
```

## 命令行使用

```bash
python backend/utils/document_reader.py path/to/file.xlsx
```

这会输出文件摘要并保存完整结果为 JSON。

## 故障排除

### 依赖未安装

如果遇到 `ImportError`，安装对应的库：

```bash
# Excel 支持
pip install pandas openpyxl

# Word 支持
pip install python-docx

# PDF 支持
pip install PyPDF2
```

### 中文乱码

如果 Excel 中文显示乱码，尝试指定编码：

```python
pd.read_excel(file_path, encoding='utf-8')
# 或
pd.read_excel(file_path, encoding='gb18030')
```

### PDF 提取不完整

对于复杂的 PDF 格式，建议：
1. 优先使用 Claude Code 的 Read 工具（原生支持 PDF）
2. 或安装更强大的库：`pip install pdfplumber`

## 与 Claude Code 集成

这些 skills 与 Claude Code 的其他功能无缝集成：

- **Read 工具**：PDF 文件可直接使用 Read 工具读取
- **Bash 工具**：可以通过命令行调用 document_reader.py
- **Write 工具**：读取后可以将结果写入新文件

## 更多资源

- [Claude Code 文档](https://docs.claude.com/claude-code)
- [Skills 开发指南](https://docs.claude.com/claude-code/skills)
