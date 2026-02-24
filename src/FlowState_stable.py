#!/usr/bin/env python3
"""
FlowState Audio - Stable Version
Simplified, working audio pipeline for Jud
"""

import sys
import subprocess
import json
from pathlib import Path
from dataclasses import dataclass, asdict

# Check for PyQt6, fall back to tkinter if not available
try:
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QLabel, QPushButton, QComboBox, QSpinBox, QDoubleSpinBox,
        QProgressBar, QFileDialog, QMessageBox, QLineEdit, QCheckBox,
        QTextEdit, QFrame
    )
    from PyQt6.QtCore import Qt, QThread, pyqtSignal
    GUI_BACKEND = "pyqt6"
except ImportError:
    print("PyQt6 not available. Please install: pip install PyQt6")
    sys.exit(1)

# Paths
EXPORTS_DIR = Path.home() / "Desktop" / "FlowState Exports"
EXPORTS_DIR.mkdir(exist_ok=True)

BINAURAL_PRESETS = {
    "delta": {"name": "Delta (2.5 Hz) - Deep Sleep", "base": 200, "beat": 2.5},
    "theta": {"name": "Theta (6 Hz) - Meditation", "base": 200, "beat": 6.0},
    "alpha": {"name": "Alpha (10 Hz) - Focus", "base": 200, "beat": 10.0},
}


@dataclass
class ProjectConfig:
    project_name: str = "My Mix"
    loop_hours: float = 8.0
    binaural_preset: str = "delta"
    binaural_volume: float = -20.0
    crossfade: float = 4.0
    target_loudness: float = -16.0
    youtube_title: str = ""
    youtube_description: str = ""


class AudioProcessor(QThread):
    progress = pyqtSignal(str, int)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    
    def __init__(self, files, config):
        super().__init__()
        self.files = files
        self.config = config
    
    def run(self):
        try:
            self.process()
        except Exception as e:
            self.error.emit(str(e))
    
    def process(self):
        # Step 1: Analyze files
        self.progress.emit("Analyzing audio files...", 10)
        durations = []
        for f in self.files:
            cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                   "-of", "json", f]
            r = subprocess.run(cmd, capture_output=True, text=True)
            dur = float(json.loads(r.stdout)['format']['duration'])
            durations.append(dur)
        
        total_duration = sum(durations)
        
        # Step 2: Build sequence
        self.progress.emit("Building audio sequence...", 30)
        seq_file = f"/tmp/sequenced.wav"
        
        if len(self.files) == 1:
            subprocess.run(["ffmpeg", "-y", "-i", self.files[0],
                          "-af", f"afade=t=in:ss=0:d=3,afade=t=out:st=0:d=5",
                          "-c:a", "pcm_s24le", seq_file], capture_output=True)
        else:
            # Concatenate with crossfade
            inputs = []
            for f in self.files:
                inputs.extend(["-i", f])
            
            # Simple concat for stability
            filter_str = ""
            for i in range(len(self.files)):
                filter_str += f"[{i}:a]"
            filter_str += f"concat=n={len(self.files)}:v=0:a=1[out]"
            
            cmd = ["ffmpeg", "-y"] + inputs + [
                "-filter_complex", filter_str,
                "-map", "[out]",
                "-c:a", "pcm_s24le", seq_file
            ]
            subprocess.run(cmd, capture_output=True)
        
        # Step 3: Generate binaural
        self.progress.emit("Generating binaural beats...", 50)
        preset = BINAURAL_PRESETS[self.config.binaural_preset]
        
        probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                               "format=duration", "-of", "json", seq_file],
                              capture_output=True, text=True)
        duration = float(json.loads(probe.stdout)['format']['duration'])
        
        binaural_file = "/tmp/binaural.wav"
        subprocess.run(["ffmpeg", "-y", "-f", "lavfi",
                       "-i", f"sine=frequency={preset['base']}:sample_rate=48000",
                       "-f", "lavfi",
                       "-i", f"sine=frequency={preset['base']+preset['beat']}:sample_rate=48000",
                       "-filter_complex", "[0:a][1:a]join=inputs=2:channel_layout=stereo",
                       "-t", str(duration), "-c:a", "pcm_s24le", binaural_file],
                      capture_output=True)
        
        # Step 4: Mix and loop if needed
        self.progress.emit("Mixing audio...", 70)
        mixed_file = "/tmp/mixed.wav"
        
        subprocess.run(["ffmpeg", "-y", "-i", seq_file, "-i", binaural_file,
                       "-filter_complex", f"[1:a]volume={self.config.binaural_volume}dB[bin];[0:a][bin]amix=2",
                       "-c:a", "pcm_s24le", mixed_file], capture_output=True)
        
        # Loop if needed
        target_duration = self.config.loop_hours * 3600
        if duration < target_duration:
            self.progress.emit(f"Looping to {self.config.loop_hours} hours...", 80)
            final_file = "/tmp/final.wav"
            subprocess.run(["ffmpeg", "-y", "-stream_loop", "-1", "-i", mixed_file,
                           "-t", str(target_duration), "-c:a", "pcm_s24le", final_file],
                          capture_output=True)
            mixed_file = final_file
        
        # Step 5: Export
        self.progress.emit("Exporting...", 90)
        safe_name = "".join(c for c in self.config.project_name if c.isalnum() or c in "-_ ").strip()
        audio_out = str(EXPORTS_DIR / f"{safe_name}_master.wav")
        video_out = str(EXPORTS_DIR / f"{safe_name}.mp4")
        
        subprocess.run(["cp", mixed_file, audio_out], capture_output=True)
        
        # Create video
        subprocess.run(["ffmpeg", "-y", "-f", "lavfi",
                       "-i", "color=c=black:s=1920x1080:r=30",
                       "-i", mixed_file, "-t", str(target_duration if duration < target_duration else duration),
                       "-c:v", "libx264", "-c:a", "aac", "-b:a", "192k",
                       "-shortest", video_out], capture_output=True)
        
        # Export metadata
        if self.config.youtube_title:
            meta_file = str(EXPORTS_DIR / f"{safe_name}_metadata.txt")
            with open(meta_file, 'w') as f:
                f.write(f"Title: {self.config.youtube_title}\n\n")
                f.write(f"Description:\n{self.config.youtube_description}\n")
        
        self.progress.emit("Complete!", 100)
        self.finished.emit({"audio": audio_out, "video": video_out})


class FlowStateApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FlowState Audio - Stable")
        self.setMinimumSize(900, 700)
        
        self.files = []
        self.config = ProjectConfig()
        
        self.setup_ui()
        self.apply_theme()
    
    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(20)
        layout.setContentsMargins(40, 40, 40, 40)
        
        # Title
        title = QLabel("🎵 FlowState Audio")
        title.setStyleSheet("color: #8B5CF6; font-size: 32px; font-weight: bold;")
        layout.addWidget(title)
        
        # File selection
        file_btn = QPushButton("📁 Select Audio Files")
        file_btn.setStyleSheet("""
            QPushButton {
                background-color: #1e1e2e;
                color: #e8e8f0;
                padding: 16px;
                border: 2px dashed #3d3d5c;
                border-radius: 8px;
                font-size: 16px;
            }
            QPushButton:hover {
                border-color: #8B5CF6;
            }
        """)
        file_btn.clicked.connect(self.select_files)
        layout.addWidget(file_btn)
        
        self.file_label = QLabel("No files selected")
        self.file_label.setStyleSheet("color: #6b7280;")
        layout.addWidget(self.file_label)
        
        # Settings grid
        settings = QWidget()
        settings_layout = QGridLayout(settings)
        settings_layout.setSpacing(16)
        
        # Project name
        settings_layout.addWidget(QLabel("Project:"), 0, 0)
        self.project_name = QLineEdit("My Sleep Mix")
        self.project_name.setStyleSheet("""
            QLineEdit {
                background-color: #1e1e2e;
                color: #e8e8f0;
                border: 1px solid #2d2d3d;
                border-radius: 6px;
                padding: 8px;
            }
        """)
        settings_layout.addWidget(self.project_name, 0, 1)
        
        # Loop hours
        settings_layout.addWidget(QLabel("Duration (hours):"), 1, 0)
        self.loop_hours = QDoubleSpinBox()
        self.loop_hours.setRange(0.5, 24)
        self.loop_hours.setValue(8)
        self.loop_hours.setStyleSheet(self.project_name.styleSheet())
        settings_layout.addWidget(self.loop_hours, 1, 1)
        
        # Binaural preset
        settings_layout.addWidget(QLabel("Binaural:"), 2, 0)
        self.binaural = QComboBox()
        for key, p in BINAURAL_PRESETS.items():
            self.binaural.addItem(p["name"], key)
        self.binaural.setStyleSheet(self.project_name.styleSheet())
        settings_layout.addWidget(self.binaural, 2, 1)
        
        # Volume
        settings_layout.addWidget(QLabel("Binaural Volume (dB):"), 3, 0)
        self.volume = QSpinBox()
        self.volume.setRange(-40, -10)
        self.volume.setValue(-20)
        self.volume.setStyleSheet(self.project_name.styleSheet())
        settings_layout.addWidget(self.volume, 3, 1)
        
        layout.addWidget(settings)
        
        # YouTube metadata
        yt_group = QFrame()
        yt_group.setStyleSheet("""
            QFrame {
                background-color: #1e1e2e;
                border-radius: 8px;
                padding: 16px;
            }
        """)
        yt_layout = QVBoxLayout(yt_group)
        
        yt_label = QLabel("📝 YouTube Metadata (Optional)")
        yt_label.setStyleSheet("color: #8B5CF6; font-weight: bold;")
        yt_layout.addWidget(yt_label)
        
        self.yt_title = QLineEdit()
        self.yt_title.setPlaceholderText("Video title...")
        self.yt_title.setStyleSheet(self.project_name.styleSheet())
        yt_layout.addWidget(self.yt_title)
        
        self.yt_desc = QTextEdit()
        self.yt_desc.setPlaceholderText("Video description...")
        self.yt_desc.setMaximumHeight(100)
        self.yt_desc.setStyleSheet("""
            QTextEdit {
                background-color: #0a0a0f;
                color: #e8e8f0;
                border: 1px solid #2d2d3d;
                border-radius: 6px;
                padding: 8px;
            }
        """)
        yt_layout.addWidget(self.yt_desc)
        
        layout.addWidget(yt_group)
        
        # Progress
        self.progress = QProgressBar()
        self.progress.setStyleSheet("""
            QProgressBar {
                border: none;
                border-radius: 4px;
                background-color: #1e1e2e;
                height: 8px;
            }
            QProgressBar::chunk {
                background-color: #8B5CF6;
                border-radius: 4px;
            }
        """)
        self.progress.setVisible(False)
        layout.addWidget(self.progress)
        
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #6b7280;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
        
        # Process button
        self.process_btn = QPushButton("✨ Create Master Track")
        self.process_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #8B5CF6, stop:1 #6366F1);
                color: white;
                padding: 20px;
                border: none;
                border-radius: 8px;
                font-weight: bold;
                font-size: 16px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #7C3AED, stop:1 #4F46E5);
            }
            QPushButton:disabled {
                background-color: #374151;
                color: #6b7280;
            }
        """)
        self.process_btn.setEnabled(False)
        self.process_btn.clicked.connect(self.process)
        layout.addWidget(self.process_btn)
        
        layout.addStretch()
    
    def apply_theme(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #0a0a0f;
            }
            QWidget {
                background-color: #0a0a0f;
                font-family: -apple-system, BlinkMacSystemFont, sans-serif;
            }
            QLabel {
                color: #e8e8f0;
            }
        """)
    
    def select_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select Audio", str(Path.home()),
            "Audio (*.mp3 *.wav *.flac *.m4a)"
        )
        if files:
            self.files = files
            self.file_label.setText(f"Selected: {len(files)} files")
            self.process_btn.setEnabled(True)
    
    def process(self):
        if not self.files:
            return
        
        self.config.project_name = self.project_name.text()
        self.config.loop_hours = self.loop_hours.value()
        self.config.binaural_preset = self.binaural.currentData()
        self.config.binaural_volume = self.volume.value()
        self.config.youtube_title = self.yt_title.text()
        self.config.youtube_description = self.yt_desc.toPlainText()
        
        self.process_btn.setEnabled(False)
        self.progress.setVisible(True)
        
        self.processor = AudioProcessor(self.files, self.config)
        self.processor.progress.connect(self.update_progress)
        self.processor.finished.connect(self.done)
        self.processor.error.connect(self.error)
        self.processor.start()
    
    def update_progress(self, msg, pct):
        self.status_label.setText(msg)
        self.progress.setValue(pct)
    
    def done(self, results):
        self.progress.setValue(100)
        self.status_label.setText("Complete!")
        
        msg = QMessageBox(self)
        msg.setWindowTitle("Success")
        msg.setText("✨ Files exported!")
        msg.setInformativeText(f"Saved to: ~/Desktop/FlowState Exports/")
        msg.exec()
        
        self.process_btn.setEnabled(True)
        self.progress.setVisible(False)
    
    def error(self, e):
        QMessageBox.critical(self, "Error", str(e))
        self.process_btn.setEnabled(True)
        self.progress.setVisible(False)


def main():
    app = QApplication(sys.argv)
    window = FlowStateApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
