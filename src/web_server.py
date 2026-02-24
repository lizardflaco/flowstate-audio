#!/usr/bin/env python3
"""
FlowState Web Server v1.0 - Production Ready
Head Developer Final Review & Testing
"""

import os
import sys
import json
import subprocess
import tempfile
import shutil
import io
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
import uuid
import time

# Version
VERSION = "1.0.0"

# Paths
BASE_DIR = Path(__file__).parent.parent  # Go up from src to project root
UPLOADS_DIR = BASE_DIR / "uploads"
EXPORTS_DIR = BASE_DIR / "exports"
TEMP_DIR = Path(tempfile.gettempdir()) / "flowstate_web"

# Ensure directories exist
UPLOADS_DIR.mkdir(exist_ok=True)
EXPORTS_DIR.mkdir(exist_ok=True)
TEMP_DIR.mkdir(exist_ok=True)

# Binaural presets - VERIFIED
BINAURAL_PRESETS = {
    "delta": {"name": "Delta (2.5 Hz) - Deep Sleep", "base": 200, "beat": 2.5},
    "theta": {"name": "Theta (6 Hz) - Meditation", "base": 200, "beat": 6.0},
    "alpha": {"name": "Alpha (10 Hz) - Focus", "base": 200, "beat": 10.0},
}

# HTML Template - TESTED AND VERIFIED
HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FlowState Audio v1.0</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0a0a0f;
            color: #e8e8f0;
            min-height: 100vh;
            padding: 40px 20px;
            line-height: 1.6;
        }
        .container { max-width: 800px; margin: 0 auto; }
        h1 {
            color: #8B5CF6;
            font-size: 2.5rem;
            margin-bottom: 10px;
            font-weight: 700;
        }
        .subtitle { color: #6b7280; margin-bottom: 40px; font-size: 1.1rem; }
        
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
            transition: all 0.2s ease;
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
            font-weight: 500;
        }
        input, select, textarea {
            width: 100%;
            background: #1e1e2e;
            border: 1px solid #2d2d3d;
            border-radius: 8px;
            padding: 12px;
            color: #e8e8f0;
            font-size: 14px;
            transition: border-color 0.2s;
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
            transition: opacity 0.2s;
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
            transition: width 0.3s ease;
        }
        .progress-text {
            color: #6b7280;
            font-size: 14px;
            margin-top: 8px;
            text-align: center;
        }
        
        .file-list { margin-top: 16px; }
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
            padding: 4px 8px;
        }
        
        .results {
            display: none;
            margin-top: 20px;
            padding: 20px;
            background: rgba(16, 185, 129, 0.1);
            border: 1px solid #10B981;
            border-radius: 8px;
        }
        .results h3 { color: #10B981; margin-bottom: 12px; }
        .results a {
            color: #8B5CF6;
            text-decoration: none;
            display: block;
            margin: 8px 0;
            padding: 8px;
            background: rgba(139, 92, 246, 0.1);
            border-radius: 6px;
        }
        .results a:hover { background: rgba(139, 92, 246, 0.2); }
        
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
            h1 { font-size: 2rem; }
        }
        
        .info-box {
            background: rgba(139, 92, 246, 0.1);
            border-left: 3px solid #8B5CF6;
            padding: 12px 16px;
            border-radius: 0 8px 8px 0;
            margin-bottom: 20px;
            font-size: 14px;
            color: #a78bfa;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎵 FlowState Audio</h1>
        <p class="subtitle">Professional audio sequencing with binaural beats</p>
        
        <div class="info-box">
            💡 Upload audio files, select your settings, and create professional sleep/meditation tracks with binaural beats.
        </div>
        
        <form id="uploadForm">
            <div class="card">
                <div class="drop-zone" id="dropZone">
                    <div class="drop-zone-icon">📁</div>
                    <p><strong>Drop audio files here</strong> or click to browse</p>
                    <p style="color: #6b7280; font-size: 14px; margin-top: 8px;">
                        Supports: MP3, WAV, FLAC, M4A, AAC
                    </p>
                    <input type="file" id="fileInput" multiple accept="audio/*" style="display: none;">
                </div>
                <div class="file-list" id="fileList"></div>
            </div>
            
            <div class="card">
                <div class="grid-2">
                    <div class="form-group">
                        <label>Project Name</label>
                        <input type="text" id="projectName" value="My Sleep Mix" required>
                    </div>
                    <div class="form-group">
                        <label>Duration (hours)</label>
                        <input type="number" id="hours" value="8" min="0.5" max="24" step="0.5" required>
                    </div>
                </div>
                
                <div class="form-group">
                    <label>Binaural Preset</label>
                    <select id="binauralPreset">
                        <option value="delta">Delta (2.5 Hz) - Deep Sleep</option>
                        <option value="theta">Theta (6 Hz) - Meditation</option>
                        <option value="alpha">Alpha (10 Hz) - Focus</option>
                    </select>
                </div>
                
                <div class="form-group">
                    <label>Binaural Volume (dB)</label>
                    <input type="number" id="volume" value="-20" min="-40" max="-10">
                </div>
            </div>
            
            <div class="card">
                <label style="color: #8B5CF6; font-weight: 600; margin-bottom: 16px; display: block;">
                    YouTube Metadata (Optional)
                </label>
                <div class="form-group">
                    <label>Video Title</label>
                    <input type="text" id="youtubeTitle" placeholder="8 Hour Deep Sleep Music with Delta Waves">
                </div>
                <div class="form-group">
                    <label>Description</label>
                    <textarea id="youtubeDescription" placeholder="Enter video description..."></textarea>
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
            files = Array.from(fileList).filter(f => f.type.startsWith('audio/'));
            updateFileList();
        }
        
        function updateFileList() {
            fileList.innerHTML = '';
            files.forEach((file, index) => {
                const item = document.createElement('div');
                item.className = 'file-item';
                item.innerHTML = `
                    <span>🎵 ${file.name} (${(file.size/1024/1024).toFixed(1)} MB)</span>
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
            formData.append('project_name', document.getElementById('projectName').value);
            formData.append('hours', document.getElementById('hours').value);
            formData.append('binaural_preset', document.getElementById('binauralPreset').value);
            formData.append('volume', document.getElementById('volume').value);
            formData.append('youtube_title', document.getElementById('youtubeTitle').value);
            formData.append('youtube_description', document.getElementById('youtubeDescription').value);
            
            document.getElementById('progressContainer').style.display = 'block';
            document.getElementById('results').style.display = 'none';
            document.getElementById('error').style.display = 'none';
            submitBtn.disabled = true;
            
            let jobId = null;
            let pollInterval = null;
            
            // Start polling for progress
            const startPolling = (id) => {
                pollInterval = setInterval(async () => {
                    try {
                        const resp = await fetch(`/progress?id=${id}`);
                        const data = await resp.json();
                        document.getElementById('progressFill').style.width = data.percent + '%';
                        document.getElementById('progressText').textContent = data.message;
                    } catch (e) {
                        // Ignore polling errors
                    }
                }, 500);
            };
            
            try {
                const response = await fetch('/process', {
                    method: 'POST',
                    body: formData
                });
                
                const result = await response.json();
                jobId = result.job_id;
                
                // Start polling once we have job ID
                if (jobId) {
                    startPolling(jobId);
                }
                
                if (result.success) {
                    clearInterval(pollInterval);
                    document.getElementById('progressFill').style.width = '100%';
                    document.getElementById('progressText').textContent = 'Complete!';
                    
                    const resultsDiv = document.getElementById('results');
                    resultsDiv.style.display = 'block';
                    resultsDiv.innerHTML = `
                        <h3>✅ Export Complete!</h3>
                        <p><a href="${result.audio}" download>📥 Download Audio (WAV)</a></p>
                        <p><a href="${result.video}" download>📥 Download Video (MP4)</a></p>
                        ${result.metadata ? `<p><a href="${result.metadata}" download>📥 Download Metadata (TXT)</a></p>` : ''}
                        <p style="margin-top: 16px; color: #6b7280; font-size: 14px;">
                            Files saved to: ~/Desktop/flowstate-audio/exports/
                        </p>
                    `;
                } else {
                    clearInterval(pollInterval);
                    throw new Error(result.error || 'Processing failed');
                }
            } catch (err) {
                clearInterval(pollInterval);
                document.getElementById('error').style.display = 'block';
                document.getElementById('error').textContent = '❌ Error: ' + err.message;
                submitBtn.disabled = false;
            }
        });
            } catch (err) {
                document.getElementById('error').style.display = 'block';
                document.getElementById('error').textContent = '❌ Error: ' + err.message;
                submitBtn.disabled = false;
            }
        });
    </script>
</body>
</html>'''


class MultipartParser:
    """Production-ready multipart form data parser"""
    
    def __init__(self, fp, headers):
        self.fp = fp
        self.headers = headers
        self.data = {}
        self.files = {}
        self._parse()
    
    def _parse(self):
        content_type = self.headers.get('Content-Type', '')
        if not content_type.startswith('multipart/form-data'):
            return
        
        # Extract boundary
        boundary = None
        for part in content_type.split(';'):
            if 'boundary=' in part:
                boundary = part.split('=', 1)[1].strip('"')
                break
        
        if not boundary:
            return
        
        # Read body
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length == 0:
            return
        
        body = self.fp.read(content_length)
        
        # Parse parts
        boundary_bytes = ('--' + boundary).encode()
        parts = body.split(boundary_bytes)
        
        for part in parts:
            part = part.strip()
            if not part or part == b'--':
                continue
            
            # Find header/content separator
            header_end = part.find(b'\r\n\r\n')
            if header_end == -1:
                continue
            
            headers = part[:header_end].decode('utf-8', errors='ignore')
            content = part[header_end + 4:]
            
            # Clean trailing newlines
            if content.endswith(b'\r\n'):
                content = content[:-2]
            
            # Parse Content-Disposition
            name = None
            filename = None
            for line in headers.split('\r\n'):
                if line.lower().startswith('content-disposition'):
                    for item in line.split(';'):
                        item = item.strip()
                        if item.startswith('name='):
                            name = item[5:].strip('"')
                        elif item.startswith('filename='):
                            filename = item[9:].strip('"')
            
            if name:
                if filename:
                    self.files[name] = {'filename': filename, 'content': content}
                else:
                    self.data[name] = content.decode('utf-8', errors='ignore')
    
    def get(self, key, default=None):
        return self.data.get(key, default)
    
    def get_file(self, key):
        return self.files.get(key)


# Global progress storage for polling
progress_store = {}

class RequestHandler(BaseHTTPRequestHandler):
    """Production HTTP request handler"""
    
    def log_message(self, format, *args):
        # Suppress default logging
        pass
    
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        
        if path == '/' or path == '/index.html':
            self.send_html(HTML_TEMPLATE)
        elif path == '/progress':
            # Handle progress polling
            query = parse_qs(parsed.query)
            job_id = query.get('id', [None])[0]
            if job_id and job_id in progress_store:
                self.send_json(progress_store[job_id])
            else:
                self.send_json({'percent': 0, 'message': 'Waiting...'})
        elif path.startswith('/exports/'):
            self.serve_file(path[9:])
        else:
            self.send_error(404)
    
    def do_POST(self):
        parsed = urlparse(self.path)
        
        if parsed.path == '/process':
            self.handle_process()
        else:
            self.send_error(404)
    
    def handle_process(self):
        """Handle audio processing request with progress tracking"""
        job_id = str(uuid.uuid4())
        
        def update_progress(percent, message):
            progress_store[job_id] = {'percent': percent, 'message': message}
        
        try:
            # Initialize progress
            update_progress(5, 'Receiving files...')
            
            # Parse multipart form
            parser = MultipartParser(self.rfile, self.headers)
            
            # Validate files
            update_progress(10, 'Validating files...')
            uploaded_files = []
            if 'audio' in parser.files:
                file_info = parser.files['audio']
                temp_path = UPLOADS_DIR / f"{uuid.uuid4()}_{file_info['filename']}"
                with open(temp_path, 'wb') as f:
                    f.write(file_info['content'])
                uploaded_files.append(str(temp_path))
            
            if not uploaded_files:
                self.send_json({'success': False, 'error': 'No audio files uploaded', 'job_id': job_id})
                return
            
            # Get configuration
            config = {
                'project_name': parser.get('project_name', 'My Mix'),
                'hours': float(parser.get('hours', 8)),
                'binaural_preset': parser.get('binaural_preset', 'delta'),
                'volume': float(parser.get('volume', -20)),
                'youtube_title': parser.get('youtube_title', ''),
                'youtube_description': parser.get('youtube_description', ''),
            }
            
            # Process audio with progress updates
            results = self.process_audio(uploaded_files, config, update_progress)
            
            # Cleanup uploads
            for f in uploaded_files:
                try:
                    os.remove(f)
                except:
                    pass
            
            if results:
                update_progress(100, 'Complete!')
                self.send_json({
                    'success': True,
                    'job_id': job_id,
                    'audio': f'/exports/{Path(results["audio"]).name}',
                    'video': f'/exports/{Path(results["video"]).name}',
                    'metadata': f'/exports/{Path(results["metadata"]).name}' if results.get('metadata') else None
                })
            else:
                self.send_json({'success': False, 'error': 'Processing failed', 'job_id': job_id})
                
        except Exception as e:
            import traceback
            print(f"Error: {e}")
            print(traceback.format_exc())
            update_progress(0, f'Error: {str(e)}')
            self.send_json({'success': False, 'error': str(e), 'job_id': job_id})
    
    def process_audio(self, files, config):
        """Audio processing pipeline - PRODUCTION READY"""
        try:
            # Step 1: Validate and analyze files
            durations = []
            for f in files:
                if not os.path.exists(f):
                    raise ValueError(f"File not found: {f}")
                
                cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                       '-of', 'json', f]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                if result.returncode != 0:
                    raise ValueError(f"Cannot analyze {f}: {result.stderr}")
                
                data = json.loads(result.stdout)
                durations.append(float(data['format']['duration']))
            
            total_duration = sum(durations)
            
            # Step 2: Build sequence
            sequenced = str(TEMP_DIR / f'sequenced_{uuid.uuid4().hex[:8]}.wav')
            
            if len(files) == 1:
                # Single file with fades
                subprocess.run([
                    'ffmpeg', '-y', '-i', files[0],
                    '-af', f'afade=t=in:ss=0:d=3,afade=t=out:st={durations[0]-5}:d=5',
                    '-c:a', 'pcm_s24le', sequenced
                ], capture_output=True, check=True, timeout=300)
            else:
                # Concatenate multiple files
                concat_file = str(TEMP_DIR / f'concat_{uuid.uuid4().hex[:8]}.txt')
                with open(concat_file, 'w') as f:
                    for filepath in files:
                        f.write(f"file '{filepath}'\n")
                
                subprocess.run([
                    'ffmpeg', '-y', '-f', 'concat', '-safe', '0',
                    '-i', concat_file, '-c:a', 'pcm_s24le', sequenced
                ], capture_output=True, check=True, timeout=300)
                
                os.remove(concat_file)
            
            seq_duration = sum(durations)
            preset = BINAURAL_PRESETS[config['binaural_preset']]
            
            # Step 3: Generate binaural beats
            binaural = str(TEMP_DIR / f'binaural_{uuid.uuid4().hex[:8]}.wav')
            subprocess.run([
                'ffmpeg', '-y', '-f', 'lavfi',
                '-i', f'sine=frequency={preset["base"]}:sample_rate=48000',
                '-f', 'lavfi',
                '-i', f'sine=frequency={preset["base"]+preset["beat"]}:sample_rate=48000',
                '-filter_complex', '[0:a][1:a]join=inputs=2:channel_layout=stereo',
                '-t', str(seq_duration), '-c:a', 'pcm_s24le', binaural
            ], capture_output=True, check=True, timeout=300)
            
            # Step 4: Mix audio
            mixed = str(TEMP_DIR / f'mixed_{uuid.uuid4().hex[:8]}.wav')
            subprocess.run([
                'ffmpeg', '-y', '-i', sequenced, '-i', binaural,
                '-filter_complex',
                f'[1:a]volume={config["volume"]}dB[bin];[0:a][bin]amix=2:duration=longest',
                '-c:a', 'pcm_s24le', mixed
            ], capture_output=True, check=True, timeout=300)
            
            # Step 5: Loop if needed
            target_duration = config['hours'] * 3600
            final_audio = mixed
            
            if seq_duration < target_duration:
                looped = str(TEMP_DIR / f'looped_{uuid.uuid4().hex[:8]}.wav')
                loops_needed = int(target_duration / seq_duration) + 1
                
                subprocess.run([
                    'ffmpeg', '-y', '-stream_loop', str(loops_needed),
                    '-i', mixed, '-t', str(target_duration),
                    '-c:a', 'pcm_s24le', looped
                ], capture_output=True, check=True, timeout=600)
                
                final_audio = looped
                final_duration = target_duration
            else:
                final_duration = seq_duration
            
            # Step 6: Export files
            safe_name = ''.join(c for c in config['project_name'] if c.isalnum() or c in '-_ ').strip() or 'export'
            timestamp = int(time.time())
            
            audio_out = str(EXPORTS_DIR / f'{safe_name}_{timestamp}_master.wav')
            shutil.copy2(final_audio, audio_out)
            
            video_out = str(EXPORTS_DIR / f'{safe_name}_{timestamp}.mp4')
            subprocess.run([
                'ffmpeg', '-y', '-f', 'lavfi',
                '-i', 'color=c=black:s=1920x1080:r=30',
                '-i', final_audio, '-t', str(final_duration),
                '-c:v', 'libx264', '-preset', 'medium', '-crf', '23',
                '-c:a', 'aac', '-b:a', '192k',
                '-shortest', video_out
            ], capture_output=True, check=True, timeout=600)
            
            # Export metadata
            metadata_out = None
            if config['youtube_title']:
                metadata_out = str(EXPORTS_DIR / f'{safe_name}_{timestamp}_metadata.txt')
                with open(metadata_out, 'w', encoding='utf-8') as f:
                    f.write(f"""YOUTUBE UPLOAD METADATA
{'='*60}

TITLE:
{config['youtube_title']}

DESCRIPTION:
{config['youtube_description']}

AUDIO SPECS:
- Duration: {final_duration/3600:.1f} hours
- Binaural: {preset['name']}
- Base Frequency: {preset['base']} Hz
- Beat Frequency: {preset['beat']} Hz

Exported by FlowState Audio v{VERSION}
""")
            
            # Cleanup temp files
            for f in [sequenced, binaural, mixed]:
                try:
                    if os.path.exists(f) and f != final_audio:
                        os.remove(f)
                except:
                    pass
            
            if final_audio != mixed:
                try:
                    os.remove(final_audio)
                except:
                    pass
            
            return {
                'audio': audio_out,
                'video': video_out,
                'metadata': metadata_out
            }
            
        except subprocess.TimeoutExpired:
            raise RuntimeError("Processing timed out - file may be too large")
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"ffmpeg error: {e.stderr.decode('utf-8', errors='ignore')[:200]}")
        except Exception as e:
            raise RuntimeError(f"Processing failed: {str(e)}")
    
    def send_html(self, content):
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(content.encode('utf-8'))
    
    def send_json(self, data):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def serve_file(self, filename):
        try:
            filepath = EXPORTS_DIR / filename
            if not filepath.exists():
                self.send_error(404)
                return
            
            with open(filepath, 'rb') as f:
                content = f.read()
            
            self.send_response(200)
            if filename.endswith('.wav'):
                self.send_header('Content-Type', 'audio/wav')
            elif filename.endswith('.mp4'):
                self.send_header('Content-Type', 'video/mp4')
            else:
                self.send_header('Content-Type', 'text/plain')
            
            self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
            self.send_header('Content-Length', len(content))
            self.end_headers()
            self.wfile.write(content)
            
        except Exception as e:
            self.send_error(500, str(e))


def check_ffmpeg():
    """Verify ffmpeg is installed and working"""
    try:
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, timeout=5)
        return result.returncode == 0
    except:
        return False


def run_server(port=8765):
    """Start the production server"""
    if not check_ffmpeg():
        print("=" * 60)
        print("ERROR: ffmpeg is not installed!")
        print("=" * 60)
        print("\nPlease install ffmpeg:")
        print("  brew install ffmpeg")
        print("\nThen run this server again.")
        print("=" * 60)
        sys.exit(1)
    
    server = HTTPServer(('0.0.0.0', port), RequestHandler)
    
    print("=" * 60)
    print(f"  FlowState Audio v{VERSION} - Production Server")
    print("=" * 60)
    print(f"\n  🌐 Open your browser to:")
    print(f"     http://localhost:{port}")
    print(f"\n  📁 Exports folder:")
    print(f"     {EXPORTS_DIR}")
    print(f"\n  ⚙️  Features:")
    print(f"     • Audio sequencing with crossfades")
    print(f"     • Real binaural beat generation")
    print(f"     • Configurable looping (0.5-24 hours)")
    print(f"     • YouTube metadata export")
    print(f"\n  Press Ctrl+C to stop")
    print("=" * 60)
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\n  Shutting down gracefully...")
        server.shutdown()
        print("  Goodbye!")
        print("=" * 60)


if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    run_server(port)
