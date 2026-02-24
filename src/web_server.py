#!/usr/bin/env python3
"""
FlowState Web - Browser-based audio pipeline
No PyQt6 required - works in any browser
"""

import os
import sys
import json
import subprocess
import tempfile
import shutil
from pathlib import Path
from dataclasses import dataclass
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
import uuid

# Python 3.13+ compatibility - cgi module removed
try:
    import cgi
except ImportError:
    # Minimal cgi replacement for multipart parsing
    class FieldStorage:
        def __init__(self, fp=None, headers=None, environ=None):
            self.fp = fp
            self.headers = headers
            self.environ = environ
            self._data = {}
            self._files = {}
            
        def __getitem__(self, key):
            return self._files.get(key) or self._data.get(key)
        
        def getvalue(self, key, default=None):
            return self._data.get(key, default)
        
        def parse(self):
            content_type = self.headers.get('Content-Type', '')
            if not content_type.startswith('multipart/form-data'):
                return
            
            # Parse boundary
            boundary = None
            for part in content_type.split(';'):
                if 'boundary=' in part:
                    boundary = part.split('=', 1)[1].strip('"')
                    break
            
            if not boundary:
                return
            
            # Read body
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.fp.read(content_length)
            
            # Split on boundary
            boundary_bytes = ('--' + boundary).encode()
            parts = body.split(boundary_bytes)
            
            for part in parts[1:]:  # Skip first empty part
                if b'--\r\n' in part or part.strip() == b'--':
                    continue
                
                # Parse headers and content
                header_end = part.find(b'\r\n\r\n')
                if header_end == -1:
                    continue
                
                headers = part[:header_end].decode('utf-8', errors='ignore')
                content = part[header_end + 4:]
                
                # Remove trailing \r\n
                if content.endswith(b'\r\n'):
                    content = content[:-2]
                
                # Parse Content-Disposition
                name = None
                filename = None
                for line in headers.split('\r\n'):
                    if line.lower().startswith('content-disposition'):
                        for item in line.split(';'):
                            if 'name=' in item:
                                name = item.split('=', 1)[1].strip('"')
                            if 'filename=' in item:
                                filename = item.split('=', 1)[1].strip('"')
                
                if name:
                    if filename:
                        # File upload
                        self._files[name] = FileItem(filename, content)
                    else:
                        # Regular field
                        self._data[name] = content.decode('utf-8', errors='ignore')
    
    class FileItem:
        def __init__(self, filename, content):
            self.filename = filename
            self.content = content
            import io
            self.file = io.BytesIO(content)
    
    cgi = type(sys)('cgi')
    cgi.FieldStorage = FieldStorage

# Paths
BASE_DIR = Path(__file__).parent
UPLOADS_DIR = BASE_DIR / "uploads"
EXPORTS_DIR = BASE_DIR / "exports"
TEMP_DIR = Path(tempfile.gettempdir()) / "flowstate_web"

UPLOADS_DIR.mkdir(exist_ok=True)
EXPORTS_DIR.mkdir(exist_ok=True)
TEMP_DIR.mkdir(exist_ok=True)

# Binaural presets
BINAURAL_PRESETS = {
    "delta": {"name": "Delta (2.5 Hz) - Deep Sleep", "base": 200, "beat": 2.5},
    "theta": {"name": "Theta (6 Hz) - Meditation", "base": 200, "beat": 6.0},
    "alpha": {"name": "Alpha (10 Hz) - Focus", "base": 200, "beat": 10.0},
}

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FlowState Audio - Web</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0a0a0f;
            color: #e8e8f0;
            min-height: 100vh;
            padding: 40px 20px;
        }
        .container { max-width: 800px; margin: 0 auto; }
        h1 {
            color: #8B5CF6;
            font-size: 2.5rem;
            margin-bottom: 10px;
        }
        .subtitle { color: #6b7280; margin-bottom: 40px; }
        
        .card {
            background: #12121a;
            border: 1px solid #1e1e2e;
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 20px;
        }
        
        .drop-zone {
            border: 2px dashed #3d3d5c;
            border-radius: 12px;
            padding: 60px 40px;
            text-align: center;
            cursor: pointer;
            transition: all 0.2s;
        }
        .drop-zone:hover, .drop-zone.dragover {
            border-color: #8B5CF6;
            background: rgba(139, 92, 246, 0.05);
        }
        .drop-zone-icon { font-size: 3rem; margin-bottom: 16px; }
        
        .form-group { margin-bottom: 20px; }
        label {
            display: block;
            color: #9ca3af;
            margin-bottom: 8px;
            font-size: 14px;
        }
        input, select, textarea {
            width: 100%;
            background: #1e1e2e;
            border: 1px solid #2d2d3d;
            border-radius: 8px;
            padding: 12px;
            color: #e8e8f0;
            font-size: 14px;
        }
        input:focus, select:focus, textarea:focus {
            outline: none;
            border-color: #8B5CF6;
        }
        textarea { min-height: 100px; resize: vertical; }
        
        .btn {
            background: linear-gradient(135deg, #8B5CF6 0%, #6366F1 100%);
            color: white;
            border: none;
            border-radius: 8px;
            padding: 16px 32px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            width: 100%;
        }
        .btn:hover { opacity: 0.9; }
        .btn:disabled {
            background: #374151;
            color: #6b7280;
            cursor: not-allowed;
        }
        
        .progress-container {
            display: none;
            margin-top: 20px;
        }
        .progress-bar {
            height: 8px;
            background: #1e1e2e;
            border-radius: 4px;
            overflow: hidden;
        }
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #8B5CF6, #60A5FA);
            width: 0%;
            transition: width 0.3s;
        }
        .progress-text {
            color: #6b7280;
            font-size: 14px;
            margin-top: 8px;
            text-align: center;
        }
        
        .file-list {
            margin-top: 16px;
        }
        .file-item {
            background: #1e1e2e;
            padding: 12px;
            border-radius: 8px;
            margin-bottom: 8px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .file-remove {
            color: #ef4444;
            cursor: pointer;
            background: none;
            border: none;
            font-size: 18px;
        }
        
        .results {
            display: none;
            margin-top: 20px;
            padding: 20px;
            background: #10B981;
            background: rgba(16, 185, 129, 0.1);
            border: 1px solid #10B981;
            border-radius: 8px;
        }
        .results a {
            color: #8B5CF6;
            text-decoration: none;
        }
        
        .error {
            display: none;
            margin-top: 20px;
            padding: 16px;
            background: rgba(239, 68, 68, 0.1);
            border: 1px solid #ef4444;
            border-radius: 8px;
            color: #ef4444;
        }
        
        .grid-2 {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 16px;
        }
        @media (max-width: 600px) {
            .grid-2 { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎵 FlowState Audio</h1>
        <p class="subtitle">Professional audio sequencing with binaural beats</p>
        
        <form id="uploadForm" action="/process" method="POST" enctype="multipart/form-data">
            <div class="card">
                <div class="drop-zone" id="dropZone">
                    <div class="drop-zone-icon">📁</div>
                    <p>Drop audio files here or click to browse</p>
                    <p style="color: #6b7280; font-size: 14px; margin-top: 8px;">MP3, WAV, FLAC, M4A supported</p>
                    <input type="file" id="fileInput" name="audio" multiple accept="audio/*" style="display: none;">
                </div>
                <div class="file-list" id="fileList"></div>
            </div>
            
            <div class="card">
                <div class="grid-2">
                    <div class="form-group">
                        <label>Project Name</label>
                        <input type="text" name="project_name" value="My Sleep Mix" required>
                    </div>
                    <div class="form-group">
                        <label>Duration (hours)</label>
                        <input type="number" name="hours" value="8" min="0.5" max="24" step="0.5" required>
                    </div>
                </div>
                
                <div class="form-group">
                    <label>Binaural Preset</label>
                    <select name="binaural_preset">
                        <option value="delta">Delta (2.5 Hz) - Deep Sleep</option>
                        <option value="theta">Theta (6 Hz) - Meditation</option>
                        <option value="alpha">Alpha (10 Hz) - Focus</option>
                    </select>
                </div>
                
                <div class="form-group">
                    <label>Binaural Volume (dB)</label>
                    <input type="number" name="volume" value="-20" min="-40" max="-10">
                </div>
            </div>
            
            <div class="card">
                <label style="color: #8B5CF6; font-weight: 600; margin-bottom: 16px; display: block;">
                    YouTube Metadata (Optional)
                </label>
                <div class="form-group">
                    <label>Video Title</label>
                    <input type="text" name="youtube_title" placeholder="8 Hour Deep Sleep Music with Delta Waves">
                </div>
                <div class="form-group">
                    <label>Description</label>
                    <textarea name="youtube_description" placeholder="Enter video description..."></textarea>
                </div>
            </div>
            
            <button type="submit" class="btn" id="submitBtn" disabled>
                ✨ Create Master Track
            </button>
            
            <div class="progress-container" id="progressContainer">
                <div class="progress-bar">
                    <div class="progress-fill" id="progressFill"></div>
                </div>
                <div class="progress-text" id="progressText">Preparing...</div>
            </div>
            
            <div class="results" id="results"></div>
            <div class="error" id="error"></div>
        </form>
    </div>
    
    <script>
        const dropZone = document.getElementById('dropZone');
        const fileInput = document.getElementById('fileInput');
        const fileList = document.getElementById('fileList');
        const submitBtn = document.getElementById('submitBtn');
        const form = document.getElementById('uploadForm');
        let files = [];
        
        dropZone.addEventListener('click', () => fileInput.click());
        
        dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropZone.classList.add('dragover');
        });
        
        dropZone.addEventListener('dragleave', () => {
            dropZone.classList.remove('dragover');
        });
        
        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropZone.classList.remove('dragover');
            handleFiles(e.dataTransfer.files);
        });
        
        fileInput.addEventListener('change', (e) => {
            handleFiles(e.target.files);
        });
        
        function handleFiles(fileList) {
            files = Array.from(fileList);
            updateFileList();
        }
        
        function updateFileList() {
            fileList.innerHTML = '';
            files.forEach((file, index) => {
                const item = document.createElement('div');
                item.className = 'file-item';
                item.innerHTML = `
                    <span>🎵 ${file.name}</span>
                    <button type="button" class="file-remove" onclick="removeFile(${index})">✕</button>
                `;
                fileList.appendChild(item);
            });
            submitBtn.disabled = files.length === 0;
        }
        
        function removeFile(index) {
            files.splice(index, 1);
            updateFileList();
        }
        
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const formData = new FormData();
            files.forEach(f => formData.append('audio', f));
            formData.append('project_name', form.project_name.value);
            formData.append('hours', form.hours.value);
            formData.append('binaural_preset', form.binaural_preset.value);
            formData.append('volume', form.volume.value);
            formData.append('youtube_title', form.youtube_title.value);
            formData.append('youtube_description', form.youtube_description.value);
            
            document.getElementById('progressContainer').style.display = 'block';
            document.getElementById('results').style.display = 'none';
            document.getElementById('error').style.display = 'none';
            submitBtn.disabled = true;
            
            try {
                const response = await fetch('/process', {
                    method: 'POST',
                    body: formData
                });
                
                const result = await response.json();
                
                if (result.success) {
                    document.getElementById('progressFill').style.width = '100%';
                    document.getElementById('progressText').textContent = 'Complete!';
                    
                    const resultsDiv = document.getElementById('results');
                    resultsDiv.style.display = 'block';
                    resultsDiv.innerHTML = `
                        <h3>✅ Export Complete!</h3>
                        <p><a href="${result.audio}" download>📥 Download Audio (WAV)</a></p>
                        <p><a href="${result.video}" download>📥 Download Video (MP4)</a></p>
                        ${result.metadata ? `<p><a href="${result.metadata}" download>📥 Download Metadata (TXT)</a></p>` : ''}
                    `;
                } else {
                    throw new Error(result.error || 'Processing failed');
                }
            } catch (err) {
                document.getElementById('error').style.display = 'block';
                document.getElementById('error').textContent = 'Error: ' + err.message;
                submitBtn.disabled = false;
            }
        });
    </script>
</body>
</html>
'''


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Quiet logging
    
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        
        if path == '/' or path == '/index.html':
            self.send_html(HTML_TEMPLATE)
        elif path.startswith('/exports/'):
            self.serve_file(EXPORTS_DIR / path[9:])
        else:
            self.send_error(404)
    
    def do_POST(self):
        parsed = urlparse(self.path)
        
        if parsed.path == '/process':
            self.handle_process()
        else:
            self.send_error(404)
    
    def handle_process(self):
        """Handle file upload and processing"""
        try:
            # Parse multipart form
            content_type = self.headers.get('Content-Type', '')
            if not content_type.startswith('multipart/form-data'):
                self.send_json({'success': False, 'error': 'Invalid content type'})
                return
            
            form = cgi.FieldStorage(
                fp=self.rfile,
                headers=self.headers,
                environ={'REQUEST_METHOD': 'POST'}
            )
            
            # Get uploaded files
            uploaded_files = []
            if 'audio' in form:
                audio_items = form['audio']
                if not isinstance(audio_items, list):
                    audio_items = [audio_items]
                
                for item in audio_items:
                    if item.filename:
                        temp_path = UPLOADS_DIR / f"{uuid.uuid4()}_{item.filename}"
                        with open(temp_path, 'wb') as f:
                            f.write(item.file.read())
                        uploaded_files.append(str(temp_path))
            
            if not uploaded_files:
                self.send_json({'success': False, 'error': 'No audio files uploaded'})
                return
            
            # Get form data
            config = {
                'project_name': form.getvalue('project_name', 'My Mix'),
                'hours': float(form.getvalue('hours', 8)),
                'binaural_preset': form.getvalue('binaural_preset', 'delta'),
                'volume': float(form.getvalue('volume', -20)),
                'youtube_title': form.getvalue('youtube_title', ''),
                'youtube_description': form.getvalue('youtube_description', ''),
            }
            
            # Process audio
            results = self.process_audio(uploaded_files, config)
            
            # Clean up uploads
            for f in uploaded_files:
                try:
                    os.remove(f)
                except:
                    pass
            
            if results:
                self.send_json({
                    'success': True,
                    'audio': f'/exports/{Path(results["audio"]).name}',
                    'video': f'/exports/{Path(results["video"]).name}',
                    'metadata': f'/exports/{Path(results["metadata"]).name}' if results.get('metadata') else None
                })
            else:
                self.send_json({'success': False, 'error': 'Processing failed'})
                
        except Exception as e:
            self.send_json({'success': False, 'error': str(e)})
    
    def process_audio(self, files, config):
        """Process audio files"""
        try:
            import json as json_mod
            
            # Get durations
            durations = []
            for f in files:
                cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                       '-of', 'json', f]
                result = subprocess.run(cmd, capture_output=True, text=True)
                dur = float(json_mod.loads(result.stdout)['format']['duration'])
                durations.append(dur)
            
            # Build sequence
            sequenced = str(TEMP_DIR / 'sequenced.wav')
            if len(files) == 1:
                subprocess.run([
                    'ffmpeg', '-y', '-i', files[0],
                    '-af', 'afade=t=in:ss=0:d=3,afade=t=out:st=0:d=5',
                    '-c:a', 'pcm_s24le', sequenced
                ], capture_output=True, check=True)
            else:
                concat_list = str(TEMP_DIR / 'concat.txt')
                with open(concat_list, 'w') as f:
                    for filepath in files:
                        f.write(f"file '{filepath}'\n")
                subprocess.run([
                    'ffmpeg', '-y', '-f', 'concat', '-safe', '0',
                    '-i', concat_list, '-c:a', 'pcm_s24le', sequenced
                ], capture_output=True, check=True)
                os.remove(concat_list)
            
            seq_duration = sum(durations)
            preset = BINAURAL_PRESETS[config['binaural_preset']]
            
            # Generate binaural
            binaural = str(TEMP_DIR / 'binaural.wav')
            subprocess.run([
                'ffmpeg', '-y', '-f', 'lavfi',
                '-i', f'sine=frequency={preset["base"]}:sample_rate=48000',
                '-f', 'lavfi',
                '-i', f'sine=frequency={preset["base"]+preset["beat"]}:sample_rate=48000',
                '-filter_complex', '[0:a][1:a]join=inputs=2:channel_layout=stereo',
                '-t', str(seq_duration), '-c:a', 'pcm_s24le', binaural
            ], capture_output=True, check=True)
            
            # Mix
            mixed = str(TEMP_DIR / 'mixed.wav')
            subprocess.run([
                'ffmpeg', '-y', '-i', sequenced, '-i', binaural,
                '-filter_complex',
                f'[1:a]volume={config["volume"]}dB[bin];[0:a][bin]amix=2',
                '-c:a', 'pcm_s24le', mixed
            ], capture_output=True, check=True)
            
            # Loop if needed
            target_duration = config['hours'] * 3600
            final_audio = mixed
            if seq_duration < target_duration:
                looped = str(TEMP_DIR / 'looped.wav')
                loops = int(target_duration / seq_duration) + 1
                subprocess.run([
                    'ffmpeg', '-y', '-stream_loop', str(loops),
                    '-i', mixed, '-t', str(target_duration),
                    '-c:a', 'pcm_s24le', looped
                ], capture_output=True, check=True)
                final_audio = looped
                final_duration = target_duration
            else:
                final_duration = seq_duration
            
            # Export
            safe_name = ''.join(c for c in config['project_name'] if c.isalnum() or c in '-_ ').strip() or 'export'
            
            audio_out = str(EXPORTS_DIR / f'{safe_name}_master.wav')
            shutil.copy2(final_audio, audio_out)
            
            video_out = str(EXPORTS_DIR / f'{safe_name}.mp4')
            subprocess.run([
                'ffmpeg', '-y', '-f', 'lavfi',
                '-i', 'color=c=black:s=1920x1080:r=30',
                '-i', final_audio, '-t', str(final_duration),
                '-c:v', 'libx264', '-c:a', 'aac', '-b:a', '192k',
                '-shortest', video_out
            ], capture_output=True, check=True)
            
            # Metadata
            metadata_out = None
            if config['youtube_title']:
                metadata_out = str(EXPORTS_DIR / f'{safe_name}_metadata.txt')
                with open(metadata_out, 'w') as f:
                    f.write(f"Title: {config['youtube_title']}\n\n")
                    f.write(f"Description:\n{config['youtube_description']}\n")
            
            # Cleanup
            for f in [sequenced, binaural, mixed]:
                try:
                    if os.path.exists(f):
                        os.remove(f)
                except:
                    pass
            
            return {
                'audio': audio_out,
                'video': video_out,
                'metadata': metadata_out
            }
            
        except Exception as e:
            print(f"Processing error: {e}")
            return None
    
    def send_html(self, content):
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        self.wfile.write(content.encode())
    
    def send_json(self, data):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def serve_file(self, filepath):
        try:
            with open(filepath, 'rb') as f:
                content = f.read()
            
            self.send_response(200)
            if str(filepath).endswith('.wav'):
                self.send_header('Content-Type', 'audio/wav')
            elif str(filepath).endswith('.mp4'):
                self.send_header('Content-Type', 'video/mp4')
            else:
                self.send_header('Content-Type', 'application/octet-stream')
            self.send_header('Content-Disposition', f'attachment; filename="{filepath.name}"')
            self.end_headers()
            self.wfile.write(content)
        except:
            self.send_error(404)


def run_server(port=8765):
    server = HTTPServer(('0.0.0.0', port), Handler)
    print(f"=" * 60)
    print(f"FlowState Web Server running!")
    print(f"=" * 60)
    print(f"Open your browser to: http://localhost:{port}")
    print(f"Exports will be saved to: {EXPORTS_DIR}")
    print(f"=" * 60)
    print(f"Press Ctrl+C to stop")
    print(f"=" * 60)
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\nShutting down...")
        server.shutdown()


if __name__ == '__main__':
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    run_server(port)
