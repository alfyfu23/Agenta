import os
import secrets
import subprocess
import sys
import threading
import time
import uuid

from flask import Flask, jsonify, request, send_from_directory, session
from flask_cors import CORS
from werkzeug.utils import secure_filename

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

app = Flask(__name__)
CORS(app, supports_credentials=True, origins=["http://localhost:3000"])
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads")
ALLOWED_AUDIO_EXTENSIONS = {"mp3", "wav", "m4a", "flac", "wma"}
ALLOWED_TEMPLATE_EXTENSIONS = {"md", "markdown"}
ALLOWED_AI_COMMANDS = {
    "rephrase",
    "summarize",
    "simplify",
    "fixSpelling",
    "translateChinese",
    "translateEnglish",
    "custom",
}
SESSION_TIMEOUT = 3600

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

sessions = {}
sessions_lock = threading.Lock()

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.secret_key = os.environ.get("FLASK_SECRET_KEY") or secrets.token_hex(16)

_openai_client = None
_openai_lock = threading.Lock()


def _get_openai_client():
    """Return a cached OpenAI client instance (thread-safe singleton)."""
    global _openai_client
    if _openai_client is None:
        with _openai_lock:
            if _openai_client is None:
                from openai import OpenAI

                api_key = os.environ.get("DEEPSEEK_API_KEY", "")
                _openai_client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com/v1")
    return _openai_client


def _validate_filename(filename: str) -> str | None:
    """Sanitize filename and verify it stays within UPLOAD_FOLDER."""
    safe = secure_filename(filename)
    if not safe:
        return None
    base_path = os.path.abspath(UPLOAD_FOLDER)
    full_path = os.path.normpath(os.path.join(base_path, safe))
    if not full_path.startswith(base_path + os.sep) and full_path != base_path:
        return None
    return safe


def _cleanup_expired_sessions() -> None:
    """Remove sessions older than SESSION_TIMEOUT from the sessions dict."""
    now = time.time()
    expired = [sid for sid, s in sessions.items() if now - s.get("last_access", now) > SESSION_TIMEOUT]
    for sid in expired:
        sessions.pop(sid, None)


def _get_session_id() -> str:
    """Resolve or create a session ID from request params, headers, or cookie."""
    sid = request.args.get("sid") or request.headers.get("X-Session-Id")
    if not sid:
        data = {}
        try:
            data = request.get_json(silent=True) or {}
        except Exception:
            data = {}
        sid = data.get("sid")
    if not sid:
        sid = session.get("sid")
    if not sid or sid not in sessions:
        sid = str(uuid.uuid4())
        session["sid"] = sid
        session_dir = os.path.join(UPLOAD_FOLDER, sid)
        with sessions_lock:
            _cleanup_expired_sessions()
            sessions[sid] = {"dir": session_dir, "lock": threading.Lock(), "last_access": time.time()}
        os.makedirs(session_dir, exist_ok=True)
    else:
        sessions[sid]["last_access"] = time.time()
    return sid


def _get_session_dir() -> str:
    """Return the filesystem path for the current session's working directory."""
    sid = _get_session_id()
    return sessions[sid]["dir"]


def _get_session_lock():
    sid = _get_session_id()
    return sessions[sid]["lock"]


@app.route("/")
def index():
    return jsonify({"success": True, "message": "API index"})


@app.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files["file"]
    filename = file.filename or ""
    if filename == "":
        return jsonify({"error": "No selected file"}), 400
    if "." not in filename:
        return jsonify({"error": "文件格式错误"}), 400

    file_ext = filename.split(".")[-1].lower()
    if file_ext not in ALLOWED_AUDIO_EXTENSIONS:
        return jsonify({"error": "文件格式错误"}), 400

    safe_name = _validate_filename(filename)
    if not safe_name:
        return jsonify({"error": "文件名无效"}), 400

    sid = _get_session_id()
    session_dir = sessions[sid]["dir"]
    file.save(os.path.join(session_dir, safe_name))
    return jsonify({"success": True, "message": "上传成功", "filename": safe_name, "session_id": sid})


@app.route("/transcribe", methods=["GET"])
def transcribe():
    filename = request.args.get("filename")
    if not filename:
        return jsonify({"error": "No filename provided"}), 400

    safe_name = _validate_filename(filename)
    if not safe_name:
        return jsonify({"error": "Invalid filename"}), 400

    sid = _get_session_id()
    session_dir = sessions[sid]["dir"]
    session_lock = sessions[sid]["lock"]

    if not session_lock.acquire(blocking=False):
        return jsonify({"error": "当前会话已有任务在运行，请稍后再试"}), 409

    audio_path = os.path.join(session_dir, safe_name)
    if not os.path.exists(audio_path):
        session_lock.release()
        return jsonify({"error": "File not found"}), 404

    for fname in ("combined_output.txt", "error_transcription.txt"):
        fpath = os.path.join(session_dir, fname)
        if os.path.exists(fpath):
            os.remove(fpath)

    def run_transcription():
        try:
            subprocess.run(
                [
                    sys.executable,
                    os.path.join(SCRIPT_DIR, "combined_transcription.py"),
                    os.path.abspath(audio_path),
                    os.path.abspath(session_dir),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr or e.stdout or str(e)
            with open(os.path.join(session_dir, "error_transcription.txt"), "w", encoding="utf-8") as f:
                f.write(error_msg[:2000])
        except Exception as e:
            with open(os.path.join(session_dir, "error_transcription.txt"), "w", encoding="utf-8") as f:
                f.write(str(e))
        finally:
            session_lock.release()

    threading.Thread(target=run_transcription).start()

    return jsonify({"success": True, "message": "Transcription started"})


@app.route("/check_transcription")
def check_transcription():
    session_dir = _get_session_dir()
    error_file = os.path.join(session_dir, "error_transcription.txt")
    if os.path.exists(error_file):
        with open(error_file, encoding="utf-8") as f:
            return jsonify({"completed": True, "error": f.read()})
    result_file = os.path.join(session_dir, "combined_output.txt")
    if os.path.exists(result_file) and os.path.getsize(result_file) > 0:
        with open(result_file, encoding="utf-8") as f:
            transcription = f.read()
        return jsonify({"completed": True, "transcription": transcription})
    else:
        return jsonify({"completed": False})


@app.route("/result", methods=["POST"])
def result():
    sid = _get_session_id()
    session_dir = sessions[sid]["dir"]
    session_lock = sessions[sid]["lock"]

    if not session_lock.acquire(blocking=False):
        return jsonify({"error": "当前会话已有任务在运行，请稍后再试"}), 409

    for fname in ("summary.md", "error_summary.txt"):
        fpath = os.path.join(session_dir, fname)
        if os.path.exists(fpath):
            os.remove(fpath)

    def run_result():
        try:
            subprocess.run(
                [sys.executable, os.path.join(SCRIPT_DIR, "summary.py"), os.path.abspath(session_dir)],
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr or e.stdout or str(e)
            with open(os.path.join(session_dir, "error_summary.txt"), "w", encoding="utf-8") as f:
                f.write(error_msg[:2000])
        except Exception as e:
            with open(os.path.join(session_dir, "error_summary.txt"), "w", encoding="utf-8") as f:
                f.write(str(e))
        finally:
            session_lock.release()

    threading.Thread(target=run_result).start()
    return jsonify({"success": True, "message": "Summary generation started"})


@app.route("/summary.md")
def get_summary():
    session_dir = _get_session_dir()
    error_file = os.path.join(session_dir, "error_summary.txt")
    if os.path.exists(error_file):
        with open(error_file, encoding="utf-8") as f:
            return jsonify({"error": f.read()}), 500
    return send_from_directory(session_dir, "summary.md")


@app.route("/combined_output.txt")
def get_combined_output():
    session_dir = _get_session_dir()
    return send_from_directory(session_dir, "combined_output.txt")


@app.route("/save_meeting_name", methods=["POST"])
def save_meeting_name():
    session_dir = _get_session_dir()
    meeting_name = request.form.get("meeting_name", "").strip()
    with open(os.path.join(session_dir, "title.txt"), "w", encoding="utf-8") as f:
        f.write(f"{meeting_name or '未命名会议'}\n")
    return jsonify({"success": True, "message": "Meeting name saved successfully"})


@app.route("/save_meeting_type", methods=["POST"])
def save_meeting_type():
    session_dir = _get_session_dir()
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"success": False, "error": "请求体不是有效的JSON"}), 400
        meeting_type = data.get("type", "未设置")

        with open(os.path.join(session_dir, "meeting_type.txt"), "w", encoding="utf-8") as f:
            f.write(meeting_type)

        return jsonify({"success": True, "message": "会议类型保存成功"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/save_meeting_info", methods=["POST"])
def save_meeting_info():
    session_dir = _get_session_dir()
    try:
        meeting_info = request.get_json(silent=True)
        if not meeting_info:
            return jsonify({"success": False, "error": "请求体不是有效的JSON"}), 400

        requirements = meeting_info.get("requirements") or "无"

        info_str = (
            f"时间: {meeting_info.get('time') or '未设置'}\n"
            f"参会人: {meeting_info.get('participants') or '未设置'}\n"
            f"记录人: {meeting_info.get('recorder') or '未设置'}\n"
            f"会议类型: {meeting_info.get('type') or '未设置'}\n"
            f"个性化要求: {requirements}"
        )

        with open(os.path.join(session_dir, "meeting_info.txt"), "w", encoding="utf-8") as f:
            f.write(info_str)

        with open(os.path.join(session_dir, "user_prompt.txt"), "w", encoding="utf-8") as f:
            f.write(meeting_info.get("requirements") or "")

        return jsonify({"success": True, "message": "会议信息保存成功"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/upload_custom_template", methods=["POST"])
def upload_custom_template():
    if "file" not in request.files:
        return jsonify({"error": "未选择文件"}), 400

    file = request.files["file"]
    filename = file.filename or ""
    if filename == "":
        return jsonify({"error": "未选择文件"}), 400

    if "." not in filename:
        return jsonify({"error": "文件格式错误，仅支持.md和.markdown"}), 400

    file_ext = filename.split(".")[-1].lower()
    if file_ext not in ALLOWED_TEMPLATE_EXTENSIONS:
        return jsonify({"error": "文件格式错误，仅支持.md和.markdown"}), 400

    session_dir = _get_session_dir()
    try:
        file_path = os.path.join(session_dir, "template_custom.md")
        file.save(file_path)
        return jsonify({"success": True, "message": "模板上传成功"})
    except Exception as e:
        return jsonify({"error": f"保存失败：{str(e)}"}), 500


@app.route("/ai_proxy", methods=["POST"])
def ai_proxy():
    try:
        data = request.get_json(silent=True) or {}
        command = data.get("command", "")
        prompt = data.get("prompt", "")

        if command not in ALLOWED_AI_COMMANDS:
            return jsonify({"error": f"不支持的命令: {command}"}), 400

        if not prompt:
            return jsonify({"error": "prompt is required"}), 400

        api_key = os.environ.get("DEEPSEEK_API_KEY", "")
        if not api_key:
            return jsonify({"error": "API key not configured on server"}), 500

        client = _get_openai_client()

        system_prompt = "你是一个智能写作助手，帮助用户处理文本。请保持文本的格式，仅修改内容，除非用户让你修改格式。如果用户不要求翻译，原文使用哪种语言，返回文本使用哪种语言。只需要返回修改后的内容，不要前后有任何说明。"
        if command == "custom":
            system_prompt = "你是一个智能写作助手，帮助用户处理文本。请只返回普通文本，不要使用markdown格式。"

        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=2000,
        )

        ai_response = response.choices[0].message.content
        return jsonify({"success": True, "response": ai_response})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=False, host="127.0.0.1", port=5000)
