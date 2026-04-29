import json
import time
import asyncio
import os
from langchain_openai import ChatOpenAI
from concurrent.futures import ThreadPoolExecutor
from functools import partial

import re

def chunk_text_with_overlap(text):
    sentence_end_pattern = r'(?<=[。！？!?\.\?!])\s*'
    sentences = re.split(sentence_end_pattern, text)
    sentences = [s for s in sentences if s.strip()]

    chunks = []
    current_chunk = []
    current_char_count = 0
    target_chars = 1250

    for sentence in sentences:
        sentence_char_count = len(sentence)
        if current_char_count + sentence_char_count > target_chars and current_chunk:
            chunks.append(''.join(current_chunk))
            current_chunk = [sentence]
            current_char_count = sentence_char_count
        else:
            current_chunk.append(sentence)
            current_char_count += sentence_char_count

    if current_chunk:
        chunks.append(''.join(current_chunk))

    return chunks


async def process_chunk(llm, fixed_prompt, chunk, chunk_index, total_chunks):
    start_time = time.time()
    print(f"正在处理第 {chunk_index+1}/{total_chunks} 个文本块...")

    input_text = fixed_prompt + chunk

    with ThreadPoolExecutor() as executor:
        loop = asyncio.get_event_loop()
        r = await loop.run_in_executor(executor, partial(llm.invoke, input_text))

    elapsed_time = time.time() - start_time
    print(f"第 {chunk_index+1} 个文本块处理完成，耗时: {elapsed_time:.2f} 秒")
    return r.content


async def main():
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        raise ValueError("请设置环境变量 DEEPSEEK_API_KEY")

    llm = ChatOpenAI(
        openai_api_key=api_key,
        base_url="https://api.deepseek.com",
        model="deepseek-chat",
        temperature=0,
        max_tokens=8192,
    )

    with open("prompt_tra.txt", "r", encoding="utf-8") as f:
        fixed_prompt = f.read()

    with open("transcription_result.txt", "r", encoding="utf-8") as f:
        user_input = f.read()

    chunks = chunk_text_with_overlap(user_input)
    print(f"开始处理 {len(chunks)} 个文本块...")
    start_time = time.time()

    tasks = []
    for i, chunk in enumerate(chunks):
        tasks.append(process_chunk(llm, fixed_prompt, chunk, i, len(chunks)))

    results = await asyncio.gather(*tasks)

    total_time = time.time() - start_time
    print(f"所有文本块处理完成，总耗时: {total_time:.2f} 秒")

    combined_output = "".join(results)
    with open("combined_output.txt", "w", encoding="utf-8") as f:
        f.write(combined_output)
    print("已保存切片合成结果到 combined_output.txt")

    with open("intermediate_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print("已保存中间结果到 intermediate_results.json")

if __name__ == "__main__":
    asyncio.run(main())