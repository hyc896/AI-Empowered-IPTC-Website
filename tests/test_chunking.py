"""测试文本分块逻辑"""

def split_text_into_chunks(text: str, max_chunk_chars: int = 20000):
    """模拟分块逻辑"""
    paragraphs = text.split('\n\n')

    chunks = []
    current_chunk = []
    current_length = 0

    for para in paragraphs:
        para_length = len(para)

        # 如果单个段落就超过限制，强制分割
        if para_length > max_chunk_chars:
            if current_chunk:
                chunks.append('\n\n'.join(current_chunk))
                current_chunk = []
                current_length = 0

            # 强制分割超长段落
            for i in range(0, para_length, max_chunk_chars):
                chunks.append(para[i:i+max_chunk_chars])
            continue

        # 如果加入当前段落会超过限制，先保存当前块
        if current_length + para_length > max_chunk_chars:
            if current_chunk:
                chunks.append('\n\n'.join(current_chunk))
            current_chunk = [para]
            current_length = para_length
        else:
            current_chunk.append(para)
            current_length += para_length + 2

    # 保存最后一个块
    if current_chunk:
        chunks.append('\n\n'.join(current_chunk))

    return chunks

# 测试用例
print("=" * 60)
print("测试1: 正常文本（不超过限制）")
text1 = "段落1\n\n段落2\n\n段落3"
chunks1 = split_text_into_chunks(text1, max_chunk_chars=100)
print(f"文本长度: {len(text1)}")
print(f"块数量: {len(chunks1)}")
for i, chunk in enumerate(chunks1):
    print(f"块{i+1} 长度: {len(chunk)}")

print("\n" + "=" * 60)
print("测试2: 超长文本（需要分块）")
text2 = ("段落1" * 3000) + "\n\n" + ("段落2" * 3000) + "\n\n" + ("段落3" * 3000)
chunks2 = split_text_into_chunks(text2, max_chunk_chars=20000)
print(f"文本长度: {len(text2)}")
print(f"块数量: {len(chunks2)}")
for i, chunk in enumerate(chunks2):
    print(f"块{i+1} 长度: {len(chunk)}")

print("\n" + "=" * 60)
print("测试3: 单个超长段落（强制分割）")
text3 = "这是一个超长段落" * 5000
chunks3 = split_text_into_chunks(text3, max_chunk_chars=20000)
print(f"文本长度: {len(text3)}")
print(f"块数量: {len(chunks3)}")
for i, chunk in enumerate(chunks3):
    print(f"块{i+1} 长度: {len(chunk)}")
    print(f"块{i+1} 开头: {chunk[:50]}...")
    print(f"块{i+1} 结尾: ...{chunk[-50:]}")
