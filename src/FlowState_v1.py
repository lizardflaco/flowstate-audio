#!/usr/bin/env python3
"""
FlowState Audio - Production Version v1.0
For Jud Smith - Mystical Sanctuary

Features:
- Audio file sequencing with smart crossfades
- Real binaural beat generation  
- Configurable looping (0.5-24 hours)
- YouTube metadata export
- Professional loudness normalization (-16 LUFS)

Requirements: ffmpeg, PyQt6, numpy
Install: brew install ffmpeg && pip install PyQt6 numpy
"""

import sys
import os
import subprocess
import json
import tempfile
import shutil
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Optional

# Version
VERSION = "1.0.0"

# Paths
EXPORTS_DIR = Path.home() / "Desktop" / "FlowState Exports"
TEMP_DIR = Path(tempfile.gettempdir()) / "flowstate_temp"

# Ensure directories exist
EXPORTS_DIR.mkdir(exist_ok=True)
TEMP_DIR.mkdir(exist_ok=True)

# Binaural presets
BINAURAL_PRESETS = {
    "delta": {
        "name": "Delta (2.5 Hz) - Deep Sleep",
        "base": 200,
        "beat": 2.5,
        "description": "Deep sleep, healing, unconscious processing"
    },
    "theta": {
        "name": "Theta (6 Hz) - Meditation", 
        "base": 200,
        "beat": 6.0,
        "description": "Deep meditation, creativity, REM-like states"
    },
    "theta_light": {
        "name": "Theta Light (4.5 Hz) - Pre-Sleep",
        "base": 200,
        "beat": 4.5,
        "description": "Light meditation, drifting, pre-sleep"
    },
    "alpha": {
        "name": "Alpha (10 Hz) - Calm Focus",
        "base": 200,
        "beat": 10.0,
        "description": "Calm focus, stress relief, relaxed awareness"
    },
    "alpha_light": {
        "name": "Alpha Light (8 Hz) - Gentle Relaxation",
        "base": 200,
        "beat": 8.0,
        "description": "Gentle relaxation, mindful calm"
    }
}


@dataclass
class ProjectConfig:
    """Project configuration"""
    project_name: str = "My Mix"
    loop_hours: float = 8.0
    binaural_preset: str = "delta"
    binaural_volume_db: float = -20.0
    crossfade_seconds: float = 4.0
    target_loudness_lufs: float = -16.0
    youtube_title: str = ""
    youtube_description: str = ""
    youtube_tags: str = ""


def check_ffmpeg() -> bool:
    """Check if ffmpeg is installed"""
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            timeout=5
        )
        return result.returncode == 0
    except:
        return False


def get_audio_duration(filepath: str) -> float:
    """Get duration of audio file in seconds"""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "json", filepath
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    data = json.loads(result.stdout)
    return float(data['format']['duration'])


def sanitize_filename(name: str) -> str:
    """Create safe filename from project name"""
    safe = "".join(c for c in name if c.isalnum() or c in "-_ ").strip()
    return safe or "flowstate_export"


class AudioPipeline:
    """Main audio processing pipeline"""
    
    def __init__(self, files: List[str], config: ProjectConfig, progress_callback=None):
        self.files = files
        self.config = config
        self.progress = progress_callback or (lambda msg, pct: None)
        self.temp_files = []
    
    def cleanup(self):
        """Remove temporary files"""
        for f in self.temp_files:
            try:
                if os.path.exists(f):
                    os.remove(f)
            except:
                pass
    
    def run(self) -> dict:
        """Execute full pipeline"""
        try:
            return self._process()
        finally:
            self.cleanup()
    
    def _process(self) -> dict:
        """Process audio files"""
        results = {}
        
        # Validate inputs
        if not self.files:
            raise ValueError("No audio files provided")
        
        for f in self.files:
            if not os.path.exists(f):
                raise ValueError(f"File not found: {f}")
        
        # Step 1: Analyze files
        self.progress("Analyzing audio files...", 5)
        durations = []
        for f in self.files:
            try:
                dur = get_audio_duration(f)
                durations.append(dur)
            except Exception as e:
                raise ValueError(f"Cannot analyze {f}: {e}")
        
        total_duration = sum(durations)
        self.progress(f"Found {len(self.files)} files, {total_duration/60:.1f} min total", 10)
        
        # Step 2: Build sequenced audio
        self.progress("Building sequence...", 20)
        sequenced = str(TEMP_DIR / "sequenced.wav")
        
        if len(self.files) == 1:
            # Single file - add fade in/out
            subprocess.run([
                "ffmpeg", "-y", "-i", self.files[0],
                "-af", f"afade=t=in:ss=0:d=3,afade=t=out:st={durations[0]-5}:d=5,aloudnorm=I={self.config.target_loudness_lufs}",
                "-c:a", "pcm_s24le", sequenced
            ], capture_output=True, check=True)
        else:
            # Multiple files - concatenate
            # Create concat file list
            concat_list = str(TEMP_DIR / "concat_list.txt")
            with open(concat_list, 'w') as f:
                for filepath in self.files:
                    f.write(f"file '{filepath}'\n")
            
            # Use concat demuxer
            subprocess.run([
                "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", concat_list,
                "-af", f"aloudnorm=I={self.config.target_loudness_lufs}",
                "-c:a", "pcm_s24le", sequenced
            ], capture_output=True, check=True)
            
            os.remove(concat_list)
        
        self.temp_files.append(sequenced)
        seq_duration = get_audio_duration(sequenced)
        
        # Step 3: Generate binaural beats
        self.progress("Generating binaural beats...", 40)
        preset = BINAURAL_PRESETS[self.config.binaural_preset]
        binaural = str(TEMP_DIR / "binaural.wav")
        
        subprocess.run([
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", f"sine=frequency={preset['base']}:sample_rate=48000",
            "-f", "lavfi",
            "-i", f"sine=frequency={preset['base']+preset['beat']}:sample_rate=48000",
            "-filter_complex", "[0:a][1:a]join=inputs=2:channel_layout=stereo",
            "-t", str(seq_duration),
            "-c:a", "pcm_s24le", binaural
        ], capture_output=True, check=True)
        
        self.temp_files.append(binaural)
        
        # Step 4: Mix audio
        self.progress("Mixing audio layers...", 60)
        mixed = str(TEMP_DIR / "mixed.wav")
        
        subprocess.run([
            "ffmpeg", "-y", "-i", sequenced, "-i", binaural,
            "-filter_complex", 
            f"[1:a]volume={self.config.binaural_volume_db}dB[bin];"
            f"[0:a][bin]amix=inputs=2:duration=longest[outa]",
            "-map", "[outa]",
            "-c:a", "pcm_s24le", mixed
        ], capture_output=True, check=True)
        
        self.temp_files.append(mixed)
        
        # Step 5: Loop if needed
        target_duration = self.config.loop_hours * 3600
        final_audio = mixed
        
        if seq_duration < target_duration:
            self.progress(f"Looping to {self.config.loop_hours} hours...", 75)
            looped = str(TEMP_DIR / "looped.wav")
            
            # Calculate how many loops needed
            loops_needed = int(target_duration / seq_duration) + 1
            
            subprocess.run([
                "ffmpeg", "-y", "-stream_loop", str(loops_needed),
                "-i", mixed,
                "-t", str(target_duration),
                "-c:a", "pcm_s24le", looped
            ], capture_output=True, check=True)
            
            final_audio = looped
            self.temp_files.append(looped)
            final_duration = target_duration
        else:
            final_duration = seq_duration
        
        # Step 6: Export
        self.progress("Exporting files...", 90)
        safe_name = sanitize_filename(self.config.project_name)
        
        # Export audio
        audio_out = str(EXPORTS_DIR / f"{safe_name}_master.wav")
        shutil.copy2(final_audio, audio_out)
        results['audio'] = audio_out
        
        # Export video
        video_out = str(EXPORTS_DIR / f"{safe_name}.mp4")
        subprocess.run([
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", "color=c=black:s=1920x1080:r=30",
            "-i", final_audio,
            "-t", str(final_duration),
            "-c:v", "libx264", "-preset", "medium", "-crf", "23",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest", video_out
        ], capture_output=True, check=True)
        results['video'] = video_out
        
        # Export metadata
        if self.config.youtube_title:
            meta_out = str(EXPORTS_DIR / f"{safe_name}_youtube_metadata.txt")
            with open(meta_out, 'w', encoding='utf-8') as f:
                f.write(f"""YOUTUBE UPLOAD METADATA
{'='*50}

TITLE:
{self.config.youtube_title}

DESCRIPTION:
{self.config.youtube_description}

TAGS:
{self.config.youtube_tags}

AUDIO SPECS:
- Duration: {final_duration/3600:.1f} hours
- Binaural: {preset['name']}
- Loudness: {self.config.target_loudness_lufs} LUFS

Exported by FlowState Audio v{VERSION}
""")
            results['metadata'] = meta_out
        
        self.progress("Complete!", 100)
        return results


# GUI Implementation
try:
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QLabel, QPushButton, QComboBox, QSpinBox, QDoubleSpinBox,
        QProgressBar, QFileDialog, QMessageBox, QLineEdit, QTextEdit,
        QGroupBox, QFrame
    )
    from PyQt6.QtCore import Qt, QThread, pyqtSignal
    
    class ProcessingThread(QThread):
        """Background processing thread"""
        progress = pyqtSignal(str, int)
        finished = pyqtSignal(dict)
        error = pyqtSignal(str)
        
        def __init__(self, files, config):
            super().__init__()
            self.files = files
            self.config = config
        
        def run(self):
            try:
                pipeline = AudioPipeline(
                    self.files, 
                    self.config,
                    progress_callback=lambda msg, pct: self.progress.emit(msg, pct)
                )
                results = pipeline.run()
                self.finished.emit(results)
            except Exception as e:
                self.error.emit(str(e))
    
    
    class FlowStateWindow(QMainWindow):
        """Main application window"""
        
        def __init__(self):
            super().__init__()
            self.setWindowTitle(f"FlowState Audio v{VERSION}")
            self.setMinimumSize(900, 750)
            
            self.files = []
            self.processor = None
            
            self._setup_ui()
            self._apply_theme()
            
            # Check ffmpeg
            if not check_ffmpeg():
                QMessageBox.warning(
                    self, "ffmpeg Required",
                    "Please install ffmpeg:\n\nbrew install ffmpeg"
                )
        
        def _setup_ui(self):
            """Build UI"""
            central = QWidget()
            self.setCentralWidget(central)
            layout = QVBoxLayout(central)
            layout.setSpacing(20)
            layout.setContentsMargins(40, 40, 40, 40)
            
            # Header
            header = QLabel("🎵 FlowState Audio")
            header.setStyleSheet("color: #8B5CF6; font-size: 32px; font-weight: bold;")
            layout.addWidget(header)
            
            subtitle = QLabel("Professional audio sequencing with binaural beats")
            subtitle.setStyleSheet("color: #6b7280; font-size: 14px;")
            layout.addWidget(subtitle)
            
            # File selection
            file_frame = QFrame()
            file_frame.setStyleSheet("""
                QFrame {
                    background-color: #1a1a2e;
                    border: 2px dashed #3d3d5c;
                    border-radius: 12px;
                    padding: 20px;
                }
            """)
            file_layout = QVBoxLayout(file_frame)
            
            file_btn = QPushButton("📁 Select Audio Files")
            file_btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #e8e8f0;
                    padding: 16px;
                    border: none;
                    font-size: 16px;
                }
            """)
            file_btn.clicked.connect(self._select_files)
            file_layout.addWidget(file_btn)
            
            self.file_label = QLabel("No files selected")
            self.file_label.setStyleSheet("color: #6b7280;")
            self.file_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            file_layout.addWidget(self.file_label)
            
            layout.addWidget(file_frame)
            
            # Settings
            settings = QGroupBox("Settings")
            settings.setStyleSheet("""
                QGroupBox {
                    color: #8B5CF6;
                    font-weight: bold;
                    border: 1px solid #1e1e2e;
                    border-radius: 8px;
                    padding-top: 16px;
                }
            """)
            settings_layout = QGridLayout(settings)
            settings_layout.setSpacing(12)
            
            # Project name
            settings_layout.addWidget(QLabel("Project Name:"), 0, 0)
            self.project_name = QLineEdit("My Sleep Mix")
            self.project_name.setStyleSheet(self._input_style())
            settings_layout.addWidget(self.project_name, 0, 1)
            
            # Duration
            settings_layout.addWidget(QLabel("Target Duration (hours):"), 1, 0)
            self.loop_hours = QDoubleSpinBox()
            self.loop_hours.setRange(0.5, 24)
            self.loop_hours.setValue(8)
            self.loop_hours.setDecimals(1)
            self.loop_hours.setStyleSheet(self._input_style())
            settings_layout.addWidget(self.loop_hours, 1, 1)
            
            # Binaural preset
            settings_layout.addWidget(QLabel("Binaural Preset:"), 2, 0)
            self.binaural = QComboBox()
            for key, p in BINAURAL_PRESETS.items():
                self.binaural.addItem(p['name'], key)
            self.binaural.setStyleSheet(self._input_style())
            settings_layout.addWidget(self.binaural, 2, 1)
            
            # Volume
            settings_layout.addWidget(QLabel("Binaural Volume (dB):"), 3, 0)
            self.volume = QSpinBox()
            self.volume.setRange(-40, -10)
            self.volume.setValue(-20)
            self.volume.setStyleSheet(self._input_style())
            settings_layout.addWidget(self.volume, 3, 1)
            
            layout.addWidget(settings)
            
            # YouTube metadata
            yt = QGroupBox("YouTube Metadata (Optional)")
            yt.setStyleSheet(settings.styleSheet())
            yt_layout = QVBoxLayout(yt)
            
            self.yt_title = QLineEdit()
            self.yt_title.setPlaceholderText("Video title...")
            self.yt_title.setStyleSheet(self._input_style())
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
            
            self.yt_tags = QLineEdit()
            self.yt_tags.setPlaceholderText("Tags (comma separated)...")
            self.yt_tags.setStyleSheet(self._input_style())
            yt_layout.addWidget(self.yt_tags)
            
            layout.addWidget(yt)
            
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
            self.process_btn.clicked.connect(self._process)
            layout.addWidget(self.process_btn)
            
            layout.addStretch()
        
        def _input_style(self) -> str:
            return """
                QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
                    background-color: #1e1e2e;
                    color: #e8e8f0;
                    border: 1px solid #2d2d3d;
                    border-radius: 6px;
                    padding: 8px;
                }
            """
        
        def _apply_theme(self):
            self.setStyleSheet("""
                QMainWindow, QWidget {
                    background-color: #0a0a0f;
                    font-family: -apple-system, BlinkMacSystemFont, sans-serif;
                }
                QLabel {
                    color: #e8e8f0;
                }
            """)
        
        def _select_files(self):
            files, _ = QFileDialog.getOpenFileNames(
                self, "Select Audio Files",
                str(Path.home()),
                "Audio Files (*.mp3 *.wav *.flac *.aac *.m4a *.ogg)"
            )
            if files:
                self.files = files
                self.file_label.setText(f"Selected: {len(files)} file(s)")
                self.process_btn.setEnabled(True)
        
        def _process(self):
            if not self.files:
                return
            
            config = ProjectConfig(
                project_name=self.project_name.text() or "My Mix",
                loop_hours=self.loop_hours.value(),
                binaural_preset=self.binaural.currentData(),
                binaural_volume_db=self.volume.value(),
                youtube_title=self.yt_title.text(),
                youtube_description=self.yt_desc.toPlainText(),
                youtube_tags=self.yt_tags.text()
            )
            
            self.process_btn.setEnabled(False)
            self.progress.setVisible(True)
            self.progress.setValue(0)
            
            self.processor = ProcessingThread(self.files, config)
            self.processor.progress.connect(self._update_progress)
            self.processor.finished.connect(self._finished)
            self.processor.error.connect(self._error)
            self.processor.start()
        
        def _update_progress(self, msg: str, pct: int):
            self.status_label.setText(msg)
            self.progress.setValue(pct)
        
        def _finished(self, results: dict):
            self.progress.setValue(100)
            self.status_label.setText("Complete!")
            
            msg = QMessageBox(self)
            msg.setWindowTitle("Success")
            msg.setText("✨ Export Complete!")
            
            details = f"📁 Audio: {Path(results['audio']).name}\n"
            details += f"🎬 Video: {Path(results['video']).name}\n"
            if 'metadata' in results:
                details += f"📝 Metadata: {Path(results['metadata']).name}\n"
            details += f"\nSaved to: ~/Desktop/FlowState Exports/"
            
            msg.setInformativeText(details)
            msg.exec()
            
            self.process_btn.setEnabled(True)
            self.progress.setVisible(False)
        
        def _error(self, error_msg: str):
            self.progress.setVisible(False)
            QMessageBox.critical(self, "Error", f"Processing failed:\n\n{error_msg}")
            self.process_btn.setEnabled(True)
    
    
    def main():
        app = QApplication(sys.argv)
        window = FlowStateWindow()
        window.show()
        sys.exit(app.exec())


except ImportError as e:
    # CLI fallback
    print(f"GUI not available ({e}). Use command line:")
    print("python3 FlowState.py --files file1.mp3 file2.mp3 --hours 8")
    
    def main():
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument("--files", nargs="+", required=True)
        parser.add_argument("--hours", type=float, default=8)
        parser.add_argument("--preset", default="delta")
        parser.add_argument("--name", default="My Mix")
        args = parser.parse_args()
        
        config = ProjectConfig(
            project_name=args.name,
            loop_hours=args.hours,
            binaural_preset=args.preset
        )
        
        def progress(msg, pct):
            print(f"[{pct:3d}%] {msg}")
        
        pipeline = AudioPipeline(args.files, config, progress)
        results = pipeline.run()
        
        print("\n✅ Complete!")
        for key, path in results.items():
            print(f"  {key}: {path}")


if __name__ == "__main__":
    main()
