from funasr import AutoModel
from funasr.utils.postprocess_utils import rich_transcription_postprocess
import sys
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


async def process_chunk(executor, loop, llm, fixed_prompt, chunk, chunk_index, total_chunks):
    start_time = time.time()
    print(f"正在处理第 {chunk_index+1}/{total_chunks} 个文本块...")

    input_text = fixed_prompt + chunk

    r = await loop.run_in_executor(executor, partial(llm.invoke, input_text))

    elapsed_time = time.time() - start_time
    print(f"第 {chunk_index+1} 个文本块处理完成，耗时: {elapsed_time:.2f} 秒")
    return r.content


async def process_transcription(session_dir):
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

    prompt_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prompt_tra.txt")
    with open(prompt_file, "r", encoding="utf-8") as f:
        fixed_prompt = f.read()

    transcription_file = os.path.join(session_dir, "transcription_result.txt")
    with open(transcription_file, "r", encoding="utf-8") as f:
        user_input = f.read()

    chunks = chunk_text_with_overlap(user_input)
    print(f"开始处理 {len(chunks)} 个文本块...")
    start_time = time.time()

    loop = asyncio.get_running_loop()
    with ThreadPoolExecutor() as executor:
        tasks = []
        for i, chunk in enumerate(chunks):
            tasks.append(process_chunk(executor, loop, llm, fixed_prompt, chunk, i, len(chunks)))
        results = await asyncio.gather(*tasks)

    total_time = time.time() - start_time
    print(f"所有文本块处理完成，总耗时: {total_time:.2f} 秒")

    combined_output = "".join(results)
    output_file = os.path.join(session_dir, "combined_output.txt")
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(combined_output)
    print(f"已保存切片合成结果到 {output_file}")

    intermediate_file = os.path.join(session_dir, "intermediate_results.json")
    with open(intermediate_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"已保存中间结果到 {intermediate_file}")


def _get_device():
    try:
        import torch
        if torch.cuda.is_available():
            return "cuda:0"
    except ImportError:
        pass
    return "cpu"


def main():
    if len(sys.argv) < 3:
        print("用法: python combined_transcription.py <audio_path> <session_dir>")
        sys.exit(1)

    input_file = sys.argv[1]
    session_dir = sys.argv[2]

    device = _get_device()
    print(f"使用设备: {device}")
    print("正在加载SenseVoice模型...")
    model = AutoModel(
        model="model/SenseVoiceSmall",
        trust_remote_code=False,
        vad_model="model/speech_fsmn_vad_zh-cn-16k-common-pytorch",
        vad_kwargs={"max_single_segment_time": 30000},
        device=device,
        disable_tqdm=True,
        disable_update=True,
    )

    print("开始处理音频文件...")
    res = model.generate(
        input=input_file,
        cache={},
        language="auto",
        use_itn=True,
        batch_size_s=60,
        merge_vad=True,
        merge_length_s=15,
    )

    if not res or not res[0] or "text" not in res[0]:
        print("错误: 模型未返回有效转写结果")
        sys.exit(1)

    text = rich_transcription_postprocess(res[0]["text"])

    output_file = os.path.join(session_dir, "transcription_result.txt")
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(text)

    print(f"转写结果已保存到 {output_file}")

    print("开始处理转录文本...")
    asyncio.run(process_transcription(session_dir))

if __name__ == "__main__":
    main()
