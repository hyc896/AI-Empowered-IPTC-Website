"""测试改进后的分块逻辑"""
import re

def split_text_into_chunks_improved(text: str, max_chunk_chars: int = 20000):
    """改进后的分块逻辑"""
    paragraphs = text.split('\n\n')

    chunks = []
    current_chunk = []
    current_length = 0

    for para in paragraphs:
        para_length = len(para)

        # 如果单个段落就超过限制，按句子分割
        if para_length > max_chunk_chars:
            if current_chunk:
                chunks.append('\n\n'.join(current_chunk))
                current_chunk = []
                current_length = 0

            # 按句子分割超长段落
            sentences = re.split(r'([。！？\.!?])', para)
            combined_sentences = []
            for i in range(0, len(sentences) - 1, 2):
                if i + 1 < len(sentences):
                    combined_sentences.append(sentences[i] + sentences[i + 1])
                else:
                    combined_sentences.append(sentences[i])
            if len(sentences) % 2 == 1:
                combined_sentences.append(sentences[-1])

            # 按句子组装块
            sentence_chunk = []
            sentence_chunk_length = 0
            for sentence in combined_sentences:
                sentence_length = len(sentence)

                if sentence_length > max_chunk_chars:
                    if sentence_chunk:
                        chunks.append(''.join(sentence_chunk))
                        sentence_chunk = []
                        sentence_chunk_length = 0
                    for i in range(0, sentence_length, max_chunk_chars):
                        chunks.append(sentence[i:i+max_chunk_chars])
                    continue

                if sentence_chunk_length + sentence_length > max_chunk_chars:
                    if sentence_chunk:
                        chunks.append(''.join(sentence_chunk))
                    sentence_chunk = [sentence]
                    sentence_chunk_length = sentence_length
                else:
                    sentence_chunk.append(sentence)
                    sentence_chunk_length += sentence_length

            if sentence_chunk:
                chunks.append(''.join(sentence_chunk))
            continue

        if current_length + para_length > max_chunk_chars:
            if current_chunk:
                chunks.append('\n\n'.join(current_chunk))
            current_chunk = [para]
            current_length = para_length
        else:
            current_chunk.append(para)
            current_length += para_length + 2

    if current_chunk:
        chunks.append('\n\n'.join(current_chunk))

    return chunks

# 测试：超长段落按句子分割
print("=" * 60)
print("测试：超长段落按句子分割")
text = "这是第一句话。这是第二句话。这是第三句话。" * 2000
chunks = split_text_into_chunks_improved(text, max_chunk_chars=20000)
print(f"文本长度: {len(text)}")
print(f"块数量: {len(chunks)}")
for i, chunk in enumerate(chunks):
    print(f"\n块{i+1}:")
    print(f"  长度: {len(chunk)}")
    print(f"  开头: {chunk[:50]}...")
    print(f"  结尾: ...{chunk[-50:]}")
