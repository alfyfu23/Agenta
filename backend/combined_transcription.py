import asyncio
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from functools import partial

from funasr import AutoModel
from funasr.utils.postprocess_utils import rich_transcription_postprocess
from langchain_openai import ChatOpenAI

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)


def write_progress(session_dir: str, stage: str, percent: int, detail: str = "") -> None:
    """Write progress.json for frontend polling."""
    path = os.path.join(session_dir, "progress.json")
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"stage": stage, "percent": percent, "detail": detail}, f, ensure_ascii=False)
    except Exception:
        pass


def chunk_text(text: str) -> list[str]:
    """Split text into chunks of ~1250 chars at sentence boundaries (。！？.!?)."""
    sentence_end_pattern = r"(?<=[。！？.!?])\s*"
    sentences = re.split(sentence_end_pattern, text)
    sentences = [s for s in sentences if s.strip()]

    chunks = []
    current_chunk = []
    current_char_count = 0
    target_chars = 1250

    for sentence in sentences:
        sentence_char_count = len(sentence)
        if sentence_char_count > target_chars and not current_chunk:
            for i in range(0, sentence_char_count, target_chars):
                chunks.append(sentence[i : i + target_chars])
            continue
        if current_char_count + sentence_char_count > target_chars and current_chunk:
            chunks.append("".join(current_chunk))
            current_chunk = [sentence]
            current_char_count = sentence_char_count
        else:
            current_chunk.append(sentence)
            current_char_count += sentence_char_count

    if current_chunk:
        chunks.append("".join(current_chunk))

    return chunks


async def process_chunk(executor, loop, llm, fixed_prompt, chunk, chunk_index, total_chunks):
    start_time = time.time()
    print(f"正在处理第 {chunk_index + 1}/{total_chunks} 个文本块...")

    input_text = fixed_prompt + "\n\n" + chunk

    try:
        r = await loop.run_in_executor(executor, partial(llm.invoke, input_text))
        elapsed_time = time.time() - start_time
        print(f"第 {chunk_index + 1} 个文本块处理完成，耗时: {elapsed_time:.2f} 秒")
        return r.content
    except Exception as e:
        print(f"第 {chunk_index + 1} 个文本块处理失败: {e}")
        return f"[该片段校对失败: {e}]"


async def process_transcription(session_dir: str) -> None:
    """Run AI proofreading on the transcription text in session_dir."""
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

    prompt_file = os.path.join(SCRIPT_DIR, "prompts", "prompt_tra.txt")
    with open(prompt_file, encoding="utf-8") as f:
        fixed_prompt = f.read()

    transcription_file = os.path.join(session_dir, "transcription_result.txt")
    with open(transcription_file, encoding="utf-8") as f:
        user_input = f.read()

    chunks = chunk_text(user_input)
    total = len(chunks)
    print(f"开始处理 {total} 个文本块...")
    start_time = time.time()

    loop = asyncio.get_running_loop()
    completed = 0

    async def tracked_chunk(i, chunk):
        nonlocal completed
        result = await process_chunk(executor_inner, loop, llm, fixed_prompt, chunk, i, total)
        completed += 1
        pct = 60 + int(35 * completed / total)
        write_progress(session_dir, "proofreading", pct, f"正在 AI 校对 ({completed}/{total} 块)")
        return result

    with ThreadPoolExecutor(max_workers=5) as executor_inner:
        tasks = [tracked_chunk(i, chunk) for i, chunk in enumerate(chunks)]
        results = await asyncio.gather(*tasks)

    total_time = time.time() - start_time
    print(f"所有文本块处理完成，总耗时: {total_time:.2f} 秒")

    combined_output = "\n".join(results)
    output_file = os.path.join(session_dir, "combined_output.txt")
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(combined_output)
    print(f"已保存切片合成结果到 {output_file}")

    intermediate_file = os.path.join(session_dir, "intermediate_results.json")
    with open(intermediate_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"已保存中间结果到 {intermediate_file}")


def _get_device() -> str:
    """Detect best available compute device (CUDA or CPU)."""
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

    write_progress(session_dir, "loading_model", 5, "正在加载语音模型...")
    device = _get_device()
    print(f"使用设备: {device}")
    print("正在加载SenseVoice模型...")
    model = AutoModel(
        model=os.path.join(ROOT_DIR, "model", "SenseVoiceSmall"),
        trust_remote_code=False,
        vad_model=os.path.join(ROOT_DIR, "model", "speech_fsmn_vad_zh-cn-16k-common-pytorch"),
        vad_kwargs={"max_single_segment_time": 30000},
        device=device,
        disable_tqdm=True,
        disable_update=True,
    )

    write_progress(session_dir, "transcribing", 30, "正在识别语音...")
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

    write_progress(session_dir, "proofreading", 60, "正在 AI 校对...")
    print("开始处理转录文本...")
    asyncio.run(process_transcription(session_dir))

    write_progress(session_dir, "done", 100, "转写完成")


if __name__ == "__main__":
    main()
