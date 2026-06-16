import asyncio
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from functools import partial

from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def write_progress(session_dir: str, stage: str, percent: int, detail: str = "") -> None:
    """Write progress.json for frontend polling."""
    path = os.path.join(session_dir, "progress.json")
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"stage": stage, "percent": percent, "detail": detail}, f, ensure_ascii=False)
    except Exception:
        pass


MEETING_TYPE_CONFIG = {
    "progress": {
        "extraction_prompt": os.path.join("prompts", "ex_prompt_project.txt"),
        "template": os.path.join("templates", "template_project.md"),
        "description": "项目进度、计划和任务分配",
    },
    "discussion": {
        "extraction_prompt": os.path.join("prompts", "ex_prompt_problem.txt"),
        "template": os.path.join("templates", "template_problem.md"),
        "description": "问题分析、解决方案和责任人",
    },
    "lecture": {
        "extraction_prompt": os.path.join("prompts", "ex_prompt_study.txt"),
        "template": os.path.join("templates", "template_study.md"),
        "description": "知识分享、学习心得和应用计划",
    },
    "custom": {
        "extraction_prompt": os.path.join("prompts", "ex_prompt_custom.txt"),
        "template": "template_custom.md",
        "description": "自定义会议类型",
    },
}


def _escape_braces(text: str) -> str:
    """Escape all { } as {{ }} to prevent PromptTemplate misinterpretation."""
    return text.replace("{", "{{").replace("}", "}}")


def _restore_placeholders(text: str, vars_list: list[str]) -> str:
    """Restore {key_points} etc. from {{key_points}} after escaping."""
    for var in vars_list:
        text = text.replace("{{" + var + "}}", "{" + var + "}")
    return text


async def extract_key_point(executor, loop, llm, extraction_prompt, result, index, total):
    start_time = time.time()
    print(f"正在提炼第 {index + 1}/{total} 个结果的要点...")

    input_text = extraction_prompt + "\n\n" + result

    try:
        response = await loop.run_in_executor(executor, partial(llm.invoke, input_text))
        elapsed_time = time.time() - start_time
        print(f"第 {index + 1} 个结果要点提炼完成，耗时: {elapsed_time:.2f} 秒")
        return response.content
    except Exception as e:
        print(f"第 {index + 1} 个结果要点提炼失败: {e}")
        return f"[该片段处理失败: {e}]"


async def extract_key_points(
    results: list[str], extraction_prompt_file: str, api_key: str, session_dir: str = ""
) -> list[str]:
    """Concurrently extract key points from each text chunk using LLM."""
    llm = ChatOpenAI(
        openai_api_key=api_key,
        base_url="https://api.deepseek.com",
        model="deepseek-chat",
        temperature=0,
        max_tokens=8192,
    )

    with open(extraction_prompt_file, encoding="utf-8") as f:
        extraction_prompt = f.read()

    total = len(results)
    print(f"开始提炼 {total} 个结果的要点...")
    start_time = time.time()

    loop = asyncio.get_running_loop()
    completed = 0

    async def tracked_extract(i, result):
        nonlocal completed
        kp = await extract_key_point(executor_inner, loop, llm, extraction_prompt, result, i, total)
        completed += 1
        if session_dir:
            pct = 15 + int(45 * completed / total)
            write_progress(session_dir, "extracting", pct, f"正在提取要点 ({completed}/{total})")
        return kp

    with ThreadPoolExecutor(max_workers=5) as executor_inner:
        tasks = [tracked_extract(i, result) for i, result in enumerate(results)]
        key_points = await asyncio.gather(*tasks)

    total_time = time.time() - start_time
    print(f"所有结果要点提炼完成，总耗时: {total_time:.2f} 秒")
    return key_points


async def load_prompt(meeting_type: str, user_prompt_file: str, template_file: str) -> PromptTemplate | None:
    """Load and assemble the final prompt template from instruction + user prompt + template file."""
    try:
        with open(template_file, encoding="utf-8") as f:
            template_content = f.read()

        if meeting_type == "custom":
            try:
                instruction_file = os.path.join(SCRIPT_DIR, "prompts", "custom.md")
                with open(instruction_file, encoding="utf-8") as f:
                    instructions = f.read()
                template_content = instructions + "\n\n" + template_content
            except Exception as e:
                print(f"加载自定义模板指令失败: {e}")

        if user_prompt_file:
            try:
                with open(user_prompt_file, encoding="utf-8") as f:
                    user_prompt = f.read()
                template_content = user_prompt + "\n\n" + template_content
            except Exception as e:
                print(f"加载用户个性化prompt失败: {e}")

        placeholder_vars = ["key_points", "meeting_info", "title"]
        template_content = _escape_braces(template_content)
        template_content = _restore_placeholders(template_content, placeholder_vars)

        input_vars = [var for var in placeholder_vars if "{" + var + "}" in template_content]
        if not input_vars:
            input_vars = placeholder_vars

        return PromptTemplate(template=template_content, input_variables=input_vars)
    except Exception as e:
        print(f"加载提示词模板失败: {e}")
        return None


async def load_meeting_info(file_path):
    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        meeting_info = {}
        for line in content.strip().split("\n"):
            if ":" in line:
                key, value = line.split(":", 1)
                meeting_info[key.strip()] = value.strip()

        required_fields = ["时间", "参会人", "记录人"]
        for field in required_fields:
            if field not in meeting_info:
                print(f"会议信息文件缺少必要字段: {field}")
                return None

        formatted_info = (
            f"**时间**: {meeting_info['时间']}\n"
            f"**参会人**: {meeting_info['参会人']}\n"
            f"**记录人**: {meeting_info['记录人']}\n\n"
        )

        return formatted_info
    except Exception as e:
        print(f"加载会议信息失败: {e}")
        return None


async def load_title(file_path):
    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read().strip()
        return content if content else "未命名会议"
    except Exception as e:
        print(f"加载标题失败: {e}")
        return "未命名会议"


async def generate_final_report(
    key_points: list[str],
    api_key: str,
    meeting_type: str,
    prompt_file: str,
    user_prompt_file: str,
    meeting_info_file: str,
    title_file: str,
) -> str | None:
    """Generate the final meeting minutes by feeding key points into the prompt template."""
    llm = ChatOpenAI(
        openai_api_key=api_key,
        base_url="https://api.deepseek.com",
        model="deepseek-chat",
        temperature=0,
        max_tokens=16384,
        top_p=0.9,
        frequency_penalty=0.0,
        presence_penalty=0.0,
        request_timeout=120,
    )

    meeting_info = await load_meeting_info(meeting_info_file)
    if not meeting_info:
        return None

    title = await load_title(title_file)

    prompt = await load_prompt(meeting_type, user_prompt_file, prompt_file)
    if not prompt:
        return None

    print("开始生成最终会议纪要...")
    start_time = time.time()

    combined_key_points = "\n\n".join(key_points)
    formatted_prompt = prompt.format(key_points=combined_key_points, meeting_info=meeting_info, title=title)

    loop = asyncio.get_running_loop()
    with ThreadPoolExecutor(max_workers=1) as executor:
        final_report = await loop.run_in_executor(executor, partial(llm.invoke, formatted_prompt))
    final_report = final_report.content

    total_time = time.time() - start_time
    print(f"会议纪要生成完成，耗时: {total_time:.2f} 秒")
    return final_report


async def main():
    if len(sys.argv) < 2:
        print("用法: python summary.py <session_dir>")
        sys.exit(1)

    session_dir = sys.argv[1]

    def write_error(msg):
        with open(os.path.join(session_dir, "error_summary.txt"), "w", encoding="utf-8") as f:
            f.write(msg)

    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        raise ValueError("请设置环境变量 DEEPSEEK_API_KEY")

    print("支持的会议类型:")
    for key, config in MEETING_TYPE_CONFIG.items():
        print(f"- {key}: {config['description']}")

    meeting_type_file = os.path.join(session_dir, "meeting_type.txt")
    try:
        with open(meeting_type_file, encoding="utf-8") as f:
            meeting_type = f.read().strip().lower()
    except FileNotFoundError:
        print(f"错误: 未找到会议类型文件 '{meeting_type_file}'，默认使用 progress")
        meeting_type = "progress"

    if meeting_type not in MEETING_TYPE_CONFIG:
        msg = f"不支持的会议类型 '{meeting_type}'，支持的类型: {', '.join(MEETING_TYPE_CONFIG.keys())}"
        print(f"错误: {msg}")
        write_error(msg)
        return

    config = MEETING_TYPE_CONFIG[meeting_type]
    print(f"已选择会议类型: {meeting_type} ({config['description']})")

    user_prompt_file = os.path.join(session_dir, "user_prompt.txt")
    meeting_info_file = os.path.join(session_dir, "meeting_info.txt")
    title_file = os.path.join(session_dir, "title.txt")
    extraction_prompt_file = os.path.join(SCRIPT_DIR, config["extraction_prompt"])
    if meeting_type == "custom":
        template_file = os.path.join(session_dir, "template_custom.md")
    else:
        template_file = os.path.join(SCRIPT_DIR, config["template"])
    intermediate_file = os.path.join(session_dir, "intermediate_results.json")

    print(f"使用用户个性化prompt文件: {user_prompt_file}")
    print(f"使用会议信息文件: {meeting_info_file}")
    print(f"使用标题文件: {title_file}")

    try:
        with open(intermediate_file, encoding="utf-8") as f:
            results = json.load(f)
    except FileNotFoundError:
        msg = f"未找到中间结果文件 '{intermediate_file}'"
        print(f"错误: {msg}")
        write_error(msg)
        return

    if not results:
        msg = "中间结果为空，无法生成纪要"
        print(f"错误: {msg}")
        write_error(msg)
        return

    write_progress(session_dir, "extracting", 10, "正在提取要点...")
    key_points = await extract_key_points(results, extraction_prompt_file, api_key, session_dir)

    key_points_file = os.path.join(session_dir, "key_points_output.txt")
    merged_key_points = "\n\n".join(key_points)
    with open(key_points_file, "w", encoding="utf-8") as f:
        f.write(merged_key_points)

    print(f"已保存提炼要点结果到 {key_points_file}")

    write_progress(session_dir, "generating", 70, "正在生成会议纪要...")
    final_report = await generate_final_report(
        key_points, api_key, meeting_type, template_file, user_prompt_file, meeting_info_file, title_file
    )
    if not final_report:
        write_error("生成会议纪要失败，请检查会议信息是否完整")
        return

    output_file = os.path.join(session_dir, "summary.md")
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(final_report)

    write_progress(session_dir, "done", 100, "纪要生成完成")
    print(f"已保存最终会议纪要到 {output_file}")


if __name__ == "__main__":
    asyncio.run(main())
