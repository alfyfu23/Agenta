import sys

from funasr import AutoModel
from funasr.utils.postprocess_utils import rich_transcription_postprocess


def _get_device():
    try:
        import torch
        if torch.cuda.is_available():
            return "cuda:0"
    except ImportError:
        pass
    return "cpu"


if len(sys.argv) < 2:
    print("请提供音频文件名作为参数")
    sys.exit(1)

input_file = sys.argv[1]

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

output_file = "transcription_result.txt"
with open(output_file, "w", encoding="utf-8") as f:
    f.write(text)

print(f"转写结果已保存到 {output_file}")
