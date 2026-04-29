import os
import json
import time
import asyncio
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from concurrent.futures import ThreadPoolExecutor
from functools import partial

MEETING_TYPE_CONFIG = {
    "progress": {
        "extraction_prompt": "ex_prompt_project.txt",
        "template": "template_project.md",
        "description": "项目进度、计划和任务分配"
    },
    "discussion": {
        "extraction_prompt": "ex_prompt_problem.txt",
        "template": "template_problem.md",
        "description": "问题分析、解决方案和责任人"
    },
    "lecture": {
        "extraction_prompt": "ex_prompt_study.txt",
        "template": "template_study.md",
        "description": "知识分享、学习心得和应用计划"
    },
    "custom": {
        "extraction_prompt": "ex_prompt_custom.txt",
        "template": "template_custom.md",
        "description": "自定义会议类型"
    }
}

USER_PROMPT_FILE = "user_prompt.txt"
MEETING_INFO_FILE = "meeting_info.txt"
TITLE_FILE = "title.txt"


async def extract_key_point(llm, extraction_prompt, result, index, total):
    start_time = time.time()
    print(f"正在提炼第 {index+1}/{total} 个结果的要点...")

    input_text = extraction_prompt + "\n\n" + result

    with ThreadPoolExecutor() as executor:
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            executor,
            partial(llm.invoke, input_text)
        )

    elapsed_time = time.time() - start_time
    print(f"第 {index+1} 个结果要点提炼完成，耗时: {elapsed_time:.2f} 秒")
    return response.content


async def extract_key_points(results, extraction_prompt_file, api_key):
    llm = ChatOpenAI(
        openai_api_key=api_key,
        base_url="https://api.deepseek.com",
        model="deepseek-chat",
        temperature=0,
        max_tokens=8192,
    )

    with open(extraction_prompt_file, "r", encoding="utf-8") as f:
        extraction_prompt = f.read()

    print(f"开始提炼 {len(results)} 个结果的要点...")
    start_time = time.time()

    tasks = []
    for i, result in enumerate(results):
        tasks.append(extract_key_point(llm, extraction_prompt, result, i, len(results)))

    key_points = await asyncio.gather(*tasks)

    total_time = time.time() - start_time
    print(f"所有结果要点提炼完成，总耗时: {total_time:.2f} 秒")
    return key_points


async def load_prompt(meeting_type, template_file, user_prompt_file=None):
    try:
        with open(template_file, 'r', encoding='utf-8') as f:
            template_content = f.read()

        if meeting_type == "custom":
            try:
                with open("custom.md", 'r', encoding='utf-8') as f:
                    custom = f.read()
                template_content = custom + "\n\n" + template_content
            except Exception as e:
                print(f"加载自定义模板失败: {e}")

        user_prompt = ""
        if user_prompt_file:
            try:
                with open(user_prompt_file, 'r', encoding='utf-8') as f:
                    user_prompt = f.read()
                template_content = user_prompt + "\n\n" + template_content
            except Exception as e:
                print(f"加载用户个性化prompt失败: {e}")

        return PromptTemplate(
            template=template_content,
            input_variables=["key_points", "meeting_info", "title"]
        )
    except Exception as e:
        print(f"加载提示词模板失败: {e}")
        return None


async def load_meeting_info(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        meeting_info = {}
        for line in content.strip().split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                meeting_info[key.strip()] = value.strip()

        required_fields = ['时间', '参会人', '记录人']
        for field in required_fields:
            if field not in meeting_info:
                print(f"会议信息文件缺少必要字段: {field}")
                return None

        formatted_info = (
            f"**时间**：{meeting_info['时间']}\n"
            f"**参会人**：{meeting_info['参会人']}\n"
            f"**记录人**：{meeting_info['记录人']}\n\n"
        )

        return formatted_info
    except Exception as e:
        print(f"加载会议信息失败: {e}")
        return None


async def load_title(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    except Exception as e:
        print(f"加载标题失败: {e}")
        return None


async def generate_final_report(key_points, api_key, meeting_type, prompt_file, user_prompt_file, meeting_info_file, title_file):
    llm = ChatOpenAI(
        openai_api_key=api_key,
        base_url="https://api.deepseek.com",
        model_name="deepseek-chat",
        temperature=0,
        max_tokens=16384,
        top_p=0.9,
        frequency_penalty=0.0,
        presence_penalty=0.0,
        request_timeout=120
    )

    meeting_info = await load_meeting_info(meeting_info_file)
    if not meeting_info:
        return None

    title = await load_title(title_file)
    if not title:
        return None

    prompt = await load_prompt(meeting_type, prompt_file, user_prompt_file)
    if not prompt:
        return None

    print("开始生成最终会议纪要...")
    start_time = time.time()

    chain = LLMChain(llm=llm, prompt=prompt)
    combined_key_points = "\n\n".join(key_points)

    with ThreadPoolExecutor() as executor:
        loop = asyncio.get_event_loop()
        final_report = await loop.run_in_executor(
            executor,
            partial(chain.run, key_points=combined_key_points, meeting_info=meeting_info, title=title)
        )

    total_time = time.time() - start_time
    print(f"会议纪要生成完成，耗时: {total_time:.2f} 秒")
    return final_report


async def main():
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        raise ValueError("请设置环境变量 DEEPSEEK_API_KEY")

    print("支持的会议类型:")
    for key, config in MEETING_TYPE_CONFIG.items():
        print(f"- {key}: {config['description']}")

    with open('meeting_type.txt', 'r', encoding='utf-8') as f:
        meeting_type = f.read().strip().lower()

    if meeting_type not in MEETING_TYPE_CONFIG:
        print(f"错误: 不支持的会议类型 '{meeting_type}'")
        print("支持的类型: " + ", ".join(MEETING_TYPE_CONFIG.keys()))
        return

    config = MEETING_TYPE_CONFIG[meeting_type]
    print(f"已选择会议类型: {meeting_type} ({config['description']})")

    user_prompt_file = USER_PROMPT_FILE
    meeting_info_file = MEETING_INFO_FILE
    title_file = TITLE_FILE

    print(f"使用统一用户个性化prompt文件: {user_prompt_file}")
    print(f"使用统一会议信息文件: {meeting_info_file}")
    print(f"使用统一标题文件: {title_file}")

    try:
        with open("intermediate_results.json", "r", encoding="utf-8") as f:
            results = json.load(f)
    except FileNotFoundError:
        print("错误: 未找到中间结果文件 'intermediate_results.json'")
        return

    key_points = await extract_key_points(results, config["extraction_prompt"], api_key)

    merged_key_points = "\n\n".join(key_points)
    with open("key_points_output.txt", "w", encoding="utf-8") as f:
        f.write(merged_key_points)

    print("已保存提炼要点结果到 key_points_output.txt")

    final_report = await generate_final_report(
        key_points, api_key, meeting_type, config["template"], user_prompt_file, meeting_info_file, title_file
    )
    if not final_report:
        return

    output_file = "summary.md"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(final_report)

    print(f"已保存最终会议纪要到 {output_file}")


if __name__ == "__main__":
    asyncio.run(main())
