import time
import threading
from flask import Flask, render_template, request, jsonify, Response, send_from_directory, session
from flask_cors import CORS
import os
import subprocess
import secrets

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

app = Flask(__name__)
CORS(app, supports_credentials=True)
UPLOAD_FOLDER = 'uploads'
LOG_FILE = 'processing.log'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.secret_key = secrets.token_hex(16)


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
    allowed_extensions = {'mp3', 'wav', 'm4a', 'flac', 'wma'}
    if '.' not in file.filename:
        return jsonify({'error': '文件格式错误'}), 400

    file_ext = file.filename.split('.')[-1].lower()
    if file_ext not in allowed_extensions:
        return jsonify({'error': '文件格式错误'}), 400
    if file:
        filename = file.filename
        file.save(os.path.join(UPLOAD_FOLDER, filename))
        return jsonify({'success': True, 'message': '上传成功', 'filename': filename})


@app.route('/logs')
def logs():
    def generate():
        with open(LOG_FILE, 'r') as log_file:
            yield log_file.read()
    return Response(generate(), mimetype='text/plain')


@app.route('/transcribe', methods=['GET'])
def transcribe():
    filename = request.args.get('filename')
    if not filename:
        return jsonify({'error': 'No filename provided'}), 400

    uploads_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    audio_path = os.path.join(uploads_dir, filename)
    if not os.path.exists(audio_path):
        return jsonify({'error': 'File not found'}), 404

    result_file = "combined_output.txt"
    if os.path.exists(result_file):
        os.remove(result_file)

    def run_transcription():
        subprocess.run(["python", "combined_transcription.py", audio_path])

    threading.Thread(target=run_transcription).start()

    return jsonify({'success': True, 'message': 'Transcription started'})


@app.route('/check_transcription')
def check_transcription():
    result_file = "combined_output.txt"
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
    def run_result():
        subprocess.run(["python", "summary.py"])

    summary_file = "summary.md"
    if os.path.exists(summary_file):
        os.remove(summary_file)

    threading.Thread(target=run_result).start()
    return jsonify({'success': True, 'message': 'Summary generation started'})


@app.route('/summary.md')
def get_summary():
    return send_from_directory(app.root_path, 'summary.md')


@app.route('/combined_output.txt')
def get_combined_output():
    return send_from_directory(app.root_path, 'combined_output.txt')


@app.route('/save_meeting_name', methods=['POST'])
def save_meeting_name():
    meeting_name = request.form.get('meeting_name', '').strip()
    with open('title.txt', 'w', encoding='utf-8') as f:
        f.write(f"{meeting_name or ''}\n")
    return jsonify({'success': True, 'message': 'Meeting name saved successfully'})


@app.route('/save_meeting_type', methods=['POST'])
def save_meeting_type():
    try:
        data = request.get_json()
        meeting_type = data.get('type', '未设置')

        with open('meeting_type.txt', 'w', encoding='utf-8') as f:
            f.write(meeting_type)

        return jsonify({'success': True, 'message': '会议类型保存成功'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/save_meeting_info', methods=['POST'])
def save_meeting_info():
    try:
        meeting_info = request.get_json()

        info_str = (
            f"时间: {meeting_info.get('time', '未设置')}\n"
            f"参会人: {meeting_info.get('participants', '未设置')}\n"
            f"记录人: {meeting_info.get('recorder', '未设置')}\n"
            f"会议类型: {meeting_info.get('type', '未设置')}\n"
            f"个性化要求: {meeting_info.get('requirements', '无')}"
        )

        with open('meeting_info.txt', 'w', encoding='utf-8') as f:
            f.write(info_str)

        with open('user_prompt.txt', 'w', encoding='utf-8') as f:
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

    allowed_extensions = {'md', 'markdown'}
    if '.' not in file.filename:
        return jsonify({'error': '文件格式错误，仅支持.md和.markdown'}), 400

    file_ext = file.filename.split('.')[-1].lower()
    if file_ext not in allowed_extensions:
        return jsonify({'error': '文件格式错误，仅支持.md和.markdown'}), 400

    try:
        root_path = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(root_path, 'template_custom.md')
        file.save(file_path)
        return jsonify({
            'success': True,
            'message': '模板上传成功'
        })
    except Exception as e:
        return jsonify({'error': f'保存失败：{str(e)}'}), 500


if __name__ == '__main__':
    app.run(debug=True)
