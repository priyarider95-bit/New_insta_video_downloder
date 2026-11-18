import os
import uuid
import threading
import yt_dlp
from flask import Flask, render_template, request, jsonify, send_file

app = Flask(__name__)
DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

tasks = {}

def download_worker(task_id, url):
    def progress_hook(d):
        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
            downloaded = d.get('downloaded_bytes', 0)
            speed = d.get('speed') or 0
            percent = int((downloaded / total) * 100) if total > 0 else 0
            
            tasks[task_id].update({
                'status': 'Downloading...',
                'percent': percent,
                'downloaded_mb': round(downloaded / (1024 * 1024), 2),
                'speed_mb': round(speed / (1024 * 1024), 2)
            })
        elif d['status'] == 'finished':
            tasks[task_id].update({
                'status': 'Completed!',
                'percent': 100
            })

    ydl_opts = {
        'format': 'best[ext=mp4]/best',
        'outtmpl': os.path.join(DOWNLOAD_FOLDER, f'DUSHYANT_{task_id}.%(ext)s'),
        'progress_hooks': [progress_hook],
        'quiet': True,
        'no_warnings': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            tasks[task_id]['file'] = filename
            tasks[task_id]['done'] = True
    except Exception as e:
        tasks[task_id]['status'] = 'Error: Invalid or Private Link'
        tasks[task_id]['error'] = True

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start', methods=['POST'])
def start_download():
    url = request.json.get('url')
    if not url:
        return jsonify({'error': 'URL missing'}), 400
    
    task_id = str(uuid.uuid4())[:8]
    tasks[task_id] = {
        'status': 'Starting...',
        'percent': 0,
        'downloaded_mb': 0,
        'speed_mb': 0,
        'done': False,
        'error': False,
        'file': None
    }
    
    thread = threading.Thread(target=download_worker, args=(task_id, url))
    thread.start()
    return jsonify({'task_id': task_id})

@app.route('/progress/<task_id>')
def get_progress(task_id):
    task = tasks.get(task_id)
    if not task:
        return jsonify({'error': 'Task not found'}), 404
    return jsonify(task)

@app.route('/get-file/<task_id>')
def get_file(task_id):
    task = tasks.get(task_id)
    if task and task.get('file') and os.path.exists(task['file']):
        return send_file(task['file'], as_attachment=True)
    return "File not found", 404

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

