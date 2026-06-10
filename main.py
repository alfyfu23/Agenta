import threading
import uuid
from flask import Flask, request, jsonify, send_from_directory, session
from flask_cors import CORS
import os
import sys
import subprocess
import secrets
from werkzeug.utils import secure_filename

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

app = Flask(__name__)
CORS(app, supports_credentials=True, origins=["http://localhost:3000"])
UPLOAD_FOLDER = 'uploads'
ALLOWED_AUDIO_EXTENSIONS = {'mp3', 'wav', 'm4a', 'flac', 'wma'}
ALLOWED_TEMPLATE_EXTENSIONS = {'md', 'markdown'}
ALLOWED_AI_COMMANDS = {'rephrase', 'summarize', 'simplify', 'fixSpelling', 'translateChinese', 'translateEnglish'}

sessions = {}
sessions_lock = threading.Lock()

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.secret_key = os.environ.get('FLASK_SECRET_KEY') or secrets.token_hex(16)


def _validate_filename(filename):
    safe = secure_filename(filename)
    if not safe:
        return None
    base_path = os.path.abspath(UPLOAD_FOLDER)
    full_path = os.path.normpath(os.path.join(base_path, safe))
    if not full_path.startswith(base_path + os.sep) and full_path != base_path:
        return None
    return safe


def _get_session_id():
    sid = request.args.get('sid') or request.headers.get('X-Session-Id')
    if not sid:
        data = {}
        try:
            data = request.get_json(silent=True) or {}
        except Exception:
            pass
        sid = data.get('sid')
    if not sid:
        sid = session.get('sid')
    if not sid or sid not in sessions:
        sid = str(uuid.uuid4())
        session['sid'] = sid
        session_dir = os.path.join(UPLOAD_FOLDER, sid)
        with sessions_lock:
            sessions[sid] = {'dir': session_dir}
        os.makedirs(session_dir, exist_ok=True)
    return sid


def _get_session_dir():
    sid = _get_session_id()
    return sessions[sid]['dir']


@app.route('/')
def index():
    return jsonify({'success': True, 'message': 'API index'})


@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if '.' not in file.filename:
        return jsonify({'error': '文件格式错误'}), 400

    file_ext = file.filename.split('.')[-1].lower()
    if file_ext not in ALLOWED_AUDIO_EXTENSIONS:
        return jsonify({'error': '文件格式错误'}), 400

    safe_name = _validate_filename(file.filename)
    if not safe_name:
        return jsonify({'error': '文件名无效'}), 400

    session_dir = _get_session_dir()
    sid = _get_session_id()
    file.save(os.path.join(session_dir, safe_name))
    return jsonify({'success': True, 'message': '上传成功', 'filename': safe_name, 'session_id': sid})


@app.route('/transcribe', methods=['GET'])
def transcribe():
    filename = request.args.get('filename')
    if not filename:
        return jsonify({'error': 'No filename provided'}), 400

    safe_name = _validate_filename(filename)
    if not safe_name:
        return jsonify({'error': 'Invalid filename'}), 400

    session_dir = _get_session_dir()
    audio_path = os.path.join(session_dir, safe_name)
    if not os.path.exists(audio_path):
        return jsonify({'error': 'File not found'}), 404

    result_file = os.path.join(session_dir, "combined_output.txt")
    if os.path.exists(result_file):
        os.remove(result_file)

    def run_transcription():
        try:
            subprocess.run(
                [sys.executable, "combined_transcription.py",
                 os.path.abspath(audio_path), os.path.abspath(session_dir)],
                check=True,
            )
        except Exception as e:
            with open(os.path.join(session_dir, "error.txt"), "w", encoding="utf-8") as f:
                f.write(str(e))

    threading.Thread(target=run_transcription).start()

    return jsonify({'success': True, 'message': 'Transcription started'})


@app.route('/check_transcription')
def check_transcription():
    session_dir = _get_session_dir()
    error_file = os.path.join(session_dir, "error.txt")
    if os.path.exists(error_file):
        with open(error_file, "r", encoding="utf-8") as f:
            return jsonify({'completed': True, 'error': f.read()})
    result_file = os.path.join(session_dir, "combined_output.txt")
    if os.path.exists(result_file) and os.path.getsize(result_file) > 0:
        with open(result_file, "r", encoding="utf-8") as f:
            transcription = f.read()
        return jsonify({
            'completed': True,
            'transcription': transcription
        })
    else:
        return jsonify({
            'completed': False
        })


@app.route('/result', methods=['POST'])
def result():
    session_dir = _get_session_dir()

    def run_result():
        try:
            subprocess.run(
                [sys.executable, "summary.py", os.path.abspath(session_dir)],
                check=True,
            )
        except Exception as e:
            with open(os.path.join(session_dir, "error.txt"), "w", encoding="utf-8") as f:
                f.write(str(e))

    summary_file = os.path.join(session_dir, "summary.md")
    if os.path.exists(summary_file):
        os.remove(summary_file)

    threading.Thread(target=run_result).start()
    return jsonify({'success': True, 'message': 'Summary generation started'})


@app.route('/summary.md')
def get_summary():
    session_dir = _get_session_dir()
    error_file = os.path.join(session_dir, "error.txt")
    if os.path.exists(error_file):
        with open(error_file, "r", encoding="utf-8") as f:
            return jsonify({'error': f.read()}), 500
    return send_from_directory(session_dir, 'summary.md')


@app.route('/combined_output.txt')
def get_combined_output():
    session_dir = _get_session_dir()
    return send_from_directory(session_dir, 'combined_output.txt')


@app.route('/save_meeting_name', methods=['POST'])
def save_meeting_name():
    session_dir = _get_session_dir()
    meeting_name = request.form.get('meeting_name', '').strip()
    with open(os.path.join(session_dir, 'title.txt'), 'w', encoding='utf-8') as f:
        f.write(f"{meeting_name or ''}\n")
    return jsonify({'success': True, 'message': 'Meeting name saved successfully'})


@app.route('/save_meeting_type', methods=['POST'])
def save_meeting_type():
    session_dir = _get_session_dir()
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify({'success': False, 'error': '请求体不是有效的JSON'}), 400
        meeting_type = data.get('type', '未设置')

        with open(os.path.join(session_dir, 'meeting_type.txt'), 'w', encoding='utf-8') as f:
            f.write(meeting_type)

        return jsonify({'success': True, 'message': '会议类型保存成功'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/save_meeting_info', methods=['POST'])
def save_meeting_info():
    session_dir = _get_session_dir()
    try:
        meeting_info = request.get_json(silent=True)
        if not meeting_info:
            return jsonify({'success': False, 'error': '请求体不是有效的JSON'}), 400

        info_str = (
            f"时间: {meeting_info.get('time', '未设置')}\n"
            f"参会人: {meeting_info.get('participants', '未设置')}\n"
            f"记录人: {meeting_info.get('recorder', '未设置')}\n"
            f"会议类型: {meeting_info.get('type', '未设置')}\n"
            f"个性化要求: {meeting_info.get('requirements', '无')}"
        )

        with open(os.path.join(session_dir, 'meeting_info.txt'), 'w', encoding='utf-8') as f:
            f.write(info_str)

        with open(os.path.join(session_dir, 'user_prompt.txt'), 'w', encoding='utf-8') as f:
            f.write(meeting_info.get('requirements', ''))

        session['run_summary'] = True

        return jsonify({'success': True, 'message': '会议信息保存成功'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/upload_custom_template', methods=['POST'])
def upload_custom_template():
    if 'file' not in request.files:
        return jsonify({'error': '未选择文件'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': '未选择文件'}), 400

    if '.' not in file.filename:
        return jsonify({'error': '文件格式错误，仅支持.md和.markdown'}), 400

    file_ext = file.filename.split('.')[-1].lower()
    if file_ext not in ALLOWED_TEMPLATE_EXTENSIONS:
        return jsonify({'error': '文件格式错误，仅支持.md和.markdown'}), 400

    session_dir = _get_session_dir()
    try:
        file_path = os.path.join(session_dir, 'template_custom.md')
        file.save(file_path)
        return jsonify({
            'success': True,
            'message': '模板上传成功'
        })
    except Exception as e:
        return jsonify({'error': f'保存失败：{str(e)}'}), 500


@app.route('/ai_proxy', methods=['POST'])
def ai_proxy():
    try:
        data = request.get_json()
        command = data.get('command', '')
        prompt = data.get('prompt', '')

        if not prompt:
            return jsonify({'error': 'prompt is required'}), 400

        api_key = os.environ.get("DEEPSEEK_API_KEY", "")
        if not api_key:
            return jsonify({'error': 'API key not configured on server'}), 500

        from openai import OpenAI
        client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com/v1")

        system_prompt = '你是一个智能写作助手，帮助用户处理文本。请保持文本的格式，仅修改内容，除非用户让你修改格式。如果用户不要求翻译，原文使用哪种语言，返回文本使用哪种语言。只需要返回修改后的内容，不要前后有任何说明。'
        if command == 'custom':
            system_prompt = '你是一个智能写作助手，帮助用户处理文本。请只返回普通文本，不要使用markdown格式。'

        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1000,
        )

        ai_response = response.choices[0].message.content
        return jsonify({'success': True, 'response': ai_response})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=False, host='127.0.0.1', port=5000)
