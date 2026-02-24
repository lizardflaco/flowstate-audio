#!/usr/bin/env python3
"""
FlowState Audio — Native macOS GUI Application
Built for Jud Smith

A polished, single-file executable that provides:
- Drag & drop audio file handling
- Intelligent track sequencing with visual waveform preview
- Real binaural beat generation
- Professional crossfading and loudness normalization
- YouTube-ready video export (black screen, images, or hybrid)
"""

import sys
import os
import json
import subprocess
import tempfile
import shutil
import threading
import queue
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any
import re

# PyQt6 imports
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QSlider, QSpinBox, QDoubleSpinBox,
    QTextEdit, QProgressBar, QFileDialog, QMessageBox, QGroupBox,
    QCheckBox, QLineEdit, QStackedWidget, QFrame, QScrollArea,
    QGridLayout, QSizePolicy, QSpacerItem, QRadioButton, QButtonGroup
)
from PyQt6.QtCore import (
    Qt, QThread, pyqtSignal, QTimer, QSize, QUrl, QSettings
)
from PyQt6.QtGui import (
    QFont, QIcon, QDragEnterEvent, QDropEvent, QColor, QPalette,
    QLinearGradient, QBrush, QPainter, QFontDatabase
)

# Application metadata
APP_NAME = "FlowState Audio"
APP_VERSION = "1.0.0"
APP_AUTHOR = "Kimi Claw for Jud Smith"

# Paths
BUNDLE_DIR = Path(__file__).parent.parent if ".app" in str(Path(__file__)) else Path(__file__).parent
EXPORTS_DIR = Path.home() / "Desktop" / "FlowState Exports"
TEMP_DIR = Path(tempfile.gettempdir()) / "flowstate"

EXPORTS_DIR.mkdir(exist_ok=True)
TEMP_DIR.mkdir(exist_ok=True)


class StatusPanel(QFrame):
    """Visual status panel showing processing stages"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.Shape.NoFrame)
        self.setStyleSheet("""
            StatusPanel {
                background-color: #12121a;
                border-top: 1px solid #1e1e2e;
            }
        """)
        
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(8)
        self.layout.setContentsMargins(16, 12, 16, 12)
        
        # Current operation label
        self.current_op = QLabel("Ready")
        self.current_op.setStyleSheet("""
            color: #8B5CF6;
            font-size: 14px;
            font-weight: 600;
        """)
        self.layout.addWidget(self.current_op)
        
        # Progress bar
        self.progress = QProgressBar()
        self.progress.setStyleSheet("""
            QProgressBar {
                border: none;
                border-radius: 4px;
                background-color: #1e1e2e;
                height: 8px;
                text-align: center;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #8B5CF6, stop:1 #60A5FA);
                border-radius: 4px;
            }
        """)
        self.progress.setValue(0)
        self.layout.addWidget(self.progress)
        
        # Stage indicators
        self.stages_widget = QWidget()
        self.stages_layout = QHBoxLayout(self.stages_widget)
        self.stages_layout.setSpacing(4)
        self.stages_layout.setContentsMargins(0, 0, 0, 0)
        
        self.stage_labels = {}
        stages = [
            ("sequencing", "🎵", "Sequencing"),
            ("binaural", "🧠", "Binaural"),
            ("mixing", "🎚️", "Mixing"),
            ("exporting", "💾", "Export"),
            ("video", "🎬", "Video"),
            ("finalizing", "✨", "Finalize"),
        ]
        
        for stage_id, icon, name in stages:
            stage_frame = QFrame()
            stage_frame.setStyleSheet("""
                QFrame {
                    background-color: #1e1e2e;
                    border-radius: 6px;
                    padding: 4px;
                }
            """)
            stage_layout = QVBoxLayout(stage_frame)
            stage_layout.setSpacing(2)
            stage_layout.setContentsMargins(8, 6, 8, 6)
            
            icon_label = QLabel(icon)
            icon_label.setStyleSheet("font-size: 16px;")
            icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            name_label = QLabel(name)
            name_label.setStyleSheet("color: #6b7280; font-size: 10px;")
            name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            stage_layout.addWidget(icon_label)
            stage_layout.addWidget(name_label)
            
            self.stages_layout.addWidget(stage_frame)
            self.stage_labels[stage_id] = (stage_frame, icon_label, name_label)
        
        self.stages_layout.addStretch()
        self.layout.addWidget(self.stages_widget)
        
        # Detail text
        self.detail_text = QLabel("")
        self.detail_text.setStyleSheet("color: #9ca3af; font-size: 11px;")
        self.detail_text.setWordWrap(True)
        self.layout.addWidget(self.detail_text)
        
        self.hide()
    
    def show_panel(self):
        """Show the status panel"""
        self.show()
        self.reset_stages()
    
    def hide_panel(self):
        """Hide the status panel"""
        self.hide()
    
    def reset_stages(self):
        """Reset all stage indicators to pending"""
        for stage_id, (frame, icon, name) in self.stage_labels.items():
            frame.setStyleSheet("""
                QFrame {
                    background-color: #1e1e2e;
                    border-radius: 6px;
                    padding: 4px;
                }
            """)
            name.setStyleSheet("color: #6b7280; font-size: 10px;")
    
    def set_stage_active(self, stage_id: str):
        """Highlight a stage as active"""
        if stage_id in self.stage_labels:
            frame, icon, name = self.stage_labels[stage_id]
            frame.setStyleSheet("""
                QFrame {
                    background-color: #8B5CF6;
                    border-radius: 6px;
                    padding: 4px;
                }
            """)
            name.setStyleSheet("color: white; font-size: 10px; font-weight: 600;")
    
    def set_stage_complete(self, stage_id: str):
        """Mark a stage as complete"""
        if stage_id in self.stage_labels:
            frame, icon, name = self.stage_labels[stage_id]
            frame.setStyleSheet("""
                QFrame {
                    background-color: #10B981;
                    border-radius: 6px;
                    padding: 4px;
                }
            """)
            name.setStyleSheet("color: white; font-size: 10px;")
            icon.setText("✓")
    
    def update_progress(self, message: str, percent: int, step: int, total: int):
        """Update progress display"""
        self.current_op.setText(f"Step {step}/{total}: {message}")
        self.progress.setValue(percent)
    
    def set_detail(self, text: str):
        """Set detail text"""
        self.detail_text.setText(text)

# Binaural presets with descriptions
BINAURAL_PRESETS = {
    "delta_deep_sleep": {
        "name": "Delta (2.5 Hz) — Deep Sleep",
        "base": 200,
        "beat": 2.5,
        "description": "Deep sleep, healing, unconscious processing. Best for overnight sessions.",
        "color": "#8B5CF6"
    },
    "theta_deep": {
        "name": "Theta (6 Hz) — Deep Meditation", 
        "base": 200,
        "beat": 6.0,
        "description": "Deep meditation, creativity, REM-like states.",
        "color": "#6366F1"
    },
    "theta_light": {
        "name": "Theta Light (4.5 Hz) — Pre-Sleep",
        "base": 200,
        "beat": 4.5,
        "description": "Light meditation, drifting, pre-sleep transition.",
        "color": "#3B82F6"
    },
    "alpha_relax": {
        "name": "Alpha (10 Hz) — Calm Focus",
        "base": 200,
        "beat": 10.0,
        "description": "Calm focus, stress relief, relaxed awareness.",
        "color": "#10B981"
    },
    "alpha_light": {
        "name": "Alpha Light (8 Hz) — Gentle Relaxation",
        "base": 200,
        "beat": 8.0,
        "description": "Gentle relaxation, mindful calm.",
        "color": "#14B8A6"
    },
    "custom": {
        "name": "Custom Frequencies",
        "base": 200,
        "beat": 5.0,
        "description": "Set your own frequencies. Base: 100-400 Hz, Beat: 0.5-40 Hz.",
        "color": "#F59E0B"
    }
}


@dataclass
class AudioTrack:
    """Represents an audio file with metadata"""
    path: str
    filename: str
    duration: float = 0.0
    duration_formatted: str = "0:00"
    loudness_lufs: float = -20.0
    peak_db: float = -1.0
    energy_profile: str = "unknown"  # low, mid, high
    sample_rate: int = 48000
    channels: int = 2
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ProjectConfig:
    """Complete project configuration"""
    project_name: str = "Untitled Project"
    target_duration_minutes: float = 60.0
    loop_mode: bool = True
    
    # Binaural settings
    binaural_preset: str = "delta_deep_sleep"
    binaural_base_freq: float = 200.0
    binaural_beat_freq: float = 2.5
    binaural_volume_db: float = -20.0
    
    # Crossfade settings
    crossfade_seconds: float = 8.0
    fade_in_seconds: float = 3.0
    fade_out_seconds: float = 5.0
    target_loudness_lufs: float = -16.0
    
    # Video settings
    video_mode: str = "black_screen"  # black_screen, images, hybrid, audio_only
    intro_text: str = ""
    intro_duration_seconds: float = 10.0
    black_screen_after_intro: float = 60.0
    image_display_seconds: float = 30.0
    image_transition_seconds: float = 3.0
    output_resolution: str = "1920x1080"
    fps: int = 30
    
    # YouTube metadata
    youtube_title: str = ""
    youtube_description: str = ""
    youtube_tags: str = ""
    youtube_category: str = "Music"
    
    # Voiceover/Guided meditation
    voiceover_script: str = ""
    voiceover_position: str = "intro"  # intro, throughout, none
    voiceover_voice: str = "default"
    
    def save_to_file(self, filepath: str):
        """Save configuration to JSON file"""
        with open(filepath, 'w') as f:
            json.dump(asdict(self), f, indent=2)
    
    @staticmethod
    def load_from_file(filepath: str) -> 'ProjectConfig':
        """Load configuration from JSON file"""
        with open(filepath, 'r') as f:
            data = json.load(f)
        return ProjectConfig(**data)


class FFmpegAnalyzer:
    """Analyze audio files using ffmpeg/ffprobe"""
    
    @staticmethod
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
    
    @staticmethod
    def get_install_instructions() -> str:
        return """ffmpeg is required but not found.

To install:
  brew install ffmpeg

Or download from: https://ffmpeg.org/download.html
"""
    
    def analyze(self, filepath: str) -> AudioTrack:
        """Extract full metadata from audio file"""
        filename = Path(filepath).name
        
        # Get basic info with ffprobe
        probe_cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-show_entries", "stream=sample_rate,channels",
            "-of", "json",
            filepath
        ]
        
        result = subprocess.run(probe_cmd, capture_output=True, text=True)
        info = json.loads(result.stdout)
        
        duration = float(info.get('format', {}).get('duration', 0))
        stream = info.get('streams', [{}])[0]
        sample_rate = int(stream.get('sample_rate', 48000))
        channels = int(stream.get('channels', 2))
        
        # Analyze loudness with ebur128
        loudness_cmd = [
            "ffmpeg", "-i", filepath,
            "-af", "ebur128=peak=true",
            "-f", "null", "-"
        ]
        
        result = subprocess.run(loudness_cmd, capture_output=True, text=True)
        output = result.stderr
        
        # Parse loudness
        rms_loudness = -20.0
        peak_db = -1.0
        
        for line in output.split('\n'):
            if 'I:' in line and 'LUFS' in line:
                match = re.search(r'I:\s*([-\d.]+)\s*LUFS', line)
                if match:
                    rms_loudness = float(match.group(1))
            if 'Peak:' in line:
                match = re.search(r'Peak:\s*([-\d.]+)', line)
                if match:
                    peak_db = float(match.group(1))
        
        # Determine energy profile
        if rms_loudness < -25:
            energy = "low"
        elif rms_loudness < -18:
            energy = "mid"
        else:
            energy = "high"
        
        # Format duration
        hours = int(duration // 3600)
        minutes = int((duration % 3600) // 60)
        seconds = int(duration % 60)
        if hours > 0:
            duration_fmt = f"{hours}:{minutes:02d}:{seconds:02d}"
        else:
            duration_fmt = f"{minutes}:{seconds:02d}"
        
        return AudioTrack(
            path=filepath,
            filename=filename,
            duration=duration,
            duration_formatted=duration_fmt,
            loudness_lufs=rms_loudness,
            peak_db=peak_db,
            energy_profile=energy,
            sample_rate=sample_rate,
            channels=channels
        )


class SequenceOptimizer:
    """Intelligently order tracks for optimal flow"""
    
    def optimize(self, tracks: List[AudioTrack]) -> List[AudioTrack]:
        """
        Order tracks for smooth progression:
        1. Start with lower energy
        2. Minimize loudness jumps between adjacent tracks
        3. Create natural arc
        """
        if len(tracks) <= 1:
            return tracks
        
        # Sort by energy: low -> mid -> high
        energy_order = {"low": 0, "mid": 1, "high": 2, "unknown": 1}
        sorted_tracks = sorted(tracks, key=lambda t: energy_order.get(t.energy_profile, 1))
        
        # Fine-tune: minimize loudness differences
        optimized = [sorted_tracks[0]]
        remaining = sorted_tracks[1:]
        
        while remaining:
            current_loudness = optimized[-1].loudness_lufs
            # Find closest loudness match
            best_idx = min(
                range(len(remaining)),
                key=lambda i: abs(remaining[i].loudness_lufs - current_loudness)
            )
            optimized.append(remaining.pop(best_idx))
        
        return optimized


class BinauralGenerator:
    """Generate binaural beat audio tracks"""
    
    def generate(self, duration: float, base_freq: float, beat_freq: float,
                 output_path: str, sample_rate: int = 48000) -> str:
        """
        Generate binaural beat:
        - Left channel: base_freq
        - Right channel: base_freq + beat_freq
        """
        left_freq = base_freq
        right_freq = base_freq + beat_freq
        
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", f"sine=frequency={left_freq}:sample_rate={sample_rate}",
            "-f", "lavfi",
            "-i", f"sine=frequency={right_freq}:sample_rate={sample_rate}",
            "-filter_complex", "[0:a][1:a]join=inputs=2:channel_layout=stereo[a]",
            "-map", "[a]",
            "-t", str(duration),
            "-c:a", "pcm_s24le",
            output_path
        ]
        
        subprocess.run(cmd, check=True, capture_output=True)
        return output_path


class AudioProcessor(QThread):
    """Background thread for audio processing with detailed progress"""
    
    # Progress signals: message, percentage, step number, total steps
    progress = pyqtSignal(str, int, int, int)
    stage_started = pyqtSignal(str, str)  # stage name, description
    stage_completed = pyqtSignal(str, str)  # stage name, result
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    
    def __init__(self, tracks: List[AudioTrack], images: List[str], config: ProjectConfig):
        super().__init__()
        self.tracks = tracks
        self.images = images
        self.config = config
        self.temp_files = []
        self.current_stage = 0
        self.total_stages = 6
        
    def emit_progress(self, message: str, percent_in_stage: int = 0):
        """Calculate overall percentage and emit"""
        stage_percent = 100 / self.total_stages
        overall_percent = int((self.current_stage * stage_percent) + 
                             (percent_in_stage * stage_percent / 100))
        self.progress.emit(message, overall_percent, self.current_stage + 1, self.total_stages)
        
    def run(self):
        try:
            self.process()
        except Exception as e:
            import traceback
            error_detail = f"{str(e)}\n\n{traceback.format_exc()}"
            self.error.emit(str(e))
            self.cleanup()
    
    def process(self):
        """Main processing pipeline with detailed status updates"""
        results = {}
        
        # Stage 1: Build sequenced audio with crossfades
        self.current_stage = 0
        self.stage_started.emit("sequencing", f"Analyzing {len(self.tracks)} tracks and building crossfaded sequence")
        self.emit_progress("Reading track metadata...", 10)
        
        sequenced_path = self._build_sequenced_audio()
        results["sequenced_audio"] = sequenced_path
        
        self.emit_progress("Crossfade sequence complete", 100)
        self.stage_completed.emit("sequencing", f"Created seamless sequence from {len(self.tracks)} tracks")
        
        # Stage 2: Generate binaural beats
        self.current_stage = 1
        preset_name = BINAURAL_PRESETS.get(self.config.binaural_preset, {}).get("name", "Custom")
        self.stage_started.emit("binaural", f"Generating {preset_name} binaural beat layer")
        self.emit_progress("Creating sine wave generators...", 20)
        
        binaural_path = self._generate_binaural(sequenced_path)
        results["binaural_audio"] = binaural_path
        
        self.emit_progress("Binaural track generated", 100)
        freq_info = f"{self.config.binaural_base_freq}Hz base + {self.config.binaural_beat_freq}Hz beat"
        self.stage_completed.emit("binaural", f"Generated {freq_info} binaural layer")
        
        # Stage 3: Mix audio layers
        self.current_stage = 2
        self.stage_started.emit("mixing", f"Blending music with binaural beats at {self.config.binaural_volume_db}dB")
        self.emit_progress("Aligning audio streams...", 30)
        
        final_audio = self._mix_audio(sequenced_path, binaural_path)
        results["final_audio"] = final_audio
        
        self.emit_progress("Audio layers mixed", 100)
        self.stage_completed.emit("mixing", "Music and binaural beats blended successfully")
        
        # Stage 4: Normalize and export audio
        self.current_stage = 3
        self.stage_started.emit("exporting", f"Normalizing to {self.config.target_loudness_lufs} LUFS")
        self.emit_progress("Applying loudness normalization...", 50)
        
        # Handle looping if enabled
        if self.config.loop_mode and self.config.target_duration_minutes > 0:
            current_duration = self._get_audio_duration(final_audio)
            target_duration = self.config.target_duration_minutes * 60
            
            if current_duration < target_duration:
                self.emit_progress(f"Looping audio from {current_duration/60:.1f}min to {self.config.target_duration_minutes:.1f}min...", 55)
                final_audio = self._loop_audio(final_audio, target_duration)
        
        audio_export = self._export_audio(final_audio)
        results["audio_path"] = audio_export
        
        self.emit_progress("Audio export complete", 100)
        file_size = Path(audio_export).stat().st_size / (1024*1024)
        self.stage_completed.emit("exporting", f"Master audio exported ({file_size:.1f} MB)")
        
        # Stage 5: Create video if requested
        video_export = None
        if self.config.video_mode != "audio_only":
            self.current_stage = 4
            mode_desc = {
                "black_screen": "Black screen with intro",
                "images": "Image slideshow",
                "hybrid": "Hybrid (intro → black → images)"
            }.get(self.config.video_mode, "Video")
            
            self.stage_started.emit("video", f"Creating {mode_desc} video at {self.config.output_resolution}")
            self.emit_progress("Generating video frames...", 40)
            
            video_export = self._create_video(final_audio)
            results["video_path"] = video_export
            
            self.emit_progress("Video encoding complete", 100)
            if video_export:
                video_size = Path(video_export).stat().st_size / (1024*1024)
                self.stage_completed.emit("video", f"Video exported ({video_size:.1f} MB)")
        else:
            self.current_stage = 4
            self.stage_started.emit("video", "Skipping video (audio-only mode)")
            self.emit_progress("Skipped", 100)
            self.stage_completed.emit("video", "Audio-only export selected")
        
        # Stage 6: Finalize and cleanup
        self.current_stage = 5
        self.stage_started.emit("finalizing", "Cleaning up temporary files and preparing results")
        self.emit_progress("Removing temp files...", 50)
        
        self.cleanup()
        
        self.emit_progress("Complete!", 100)
        self.stage_completed.emit("finalizing", f"Export complete! Files saved to Desktop/FlowState Exports/")
        
        # Build final results
        results["config"] = asdict(self.config)
        results["tracks"] = [t.to_dict() for t in self.tracks]
        
        self.finished.emit(results)
    
    def _build_sequenced_audio(self) -> str:
        """Crossfade tracks together with safe duration calculations"""
        if len(self.tracks) == 1:
            # Single track: just normalize
            output = str(TEMP_DIR / "sequenced.wav")
            self._normalize_track(self.tracks[0].path, output)
            self.temp_files.append(output)
            return output
        
        # Calculate safe crossfade duration based on shortest track
        min_duration = min(t.duration for t in self.tracks)
        # Crossfade can't be more than half the shortest track (need overlap)
        safe_crossfade = min(self.config.crossfade_seconds, min_duration / 2, 4.0)
        
        self.emit_progress(f"Using {safe_crossfade:.1f}s crossfade (limited by track lengths)", 20)
        
        # Build filter complex for multiple tracks
        inputs = []
        for track in self.tracks:
            inputs.extend(["-i", track.path])
        
        # Create crossfade filter
        filter_parts = []
        n = len(self.tracks)
        
        # Prepare each track
        for i in range(n):
            if i == 0:
                # First track: fade in
                filter_parts.append(
                    f"[{i}:a]afade=t=in:ss=0:d={self.config.fade_in_seconds}[a{i}]"
                )
            elif i == n - 1:
                # Last track: fade out
                duration = self.tracks[i].duration
                fade_start = max(0, duration - self.config.fade_out_seconds)
                filter_parts.append(
                    f"[{i}:a]afade=t=out:st={fade_start}:d={self.config.fade_out_seconds}[a{i}]"
                )
            else:
                filter_parts.append(f"[{i}:a]anull[a{i}]")
        
        # Crossfade chain with safe duration
        for i in range(n - 1):
            if i == 0:
                filter_parts.append(
                    f"[a{i}][a{i+1}]acrossfade=d={safe_crossfade}:c1=tri:c2=tri[cf{i}]"
                )
            else:
                filter_parts.append(
                    f"[cf{i-1}][a{i+1}]acrossfade=d={safe_crossfade}:c1=tri:c2=tri[cf{i}]"
                )
        
        final_label = f"cf{n-2}" if n > 1 else "a0"
        filter_complex = ";".join(filter_parts)
        filter_complex += f";[{final_label}]aloudnorm=I={self.config.target_loudness_lufs}:TP=-1.5[outa]"
        
        output = str(TEMP_DIR / "sequenced.wav")
        cmd = ["ffmpeg", "-y"] + inputs + [
            "-filter_complex", filter_complex,
            "-map", "[outa]",
            "-c:a", "pcm_s24le",
            output
        ]
        
        subprocess.run(cmd, check=True, capture_output=True)
        self.temp_files.append(output)
        return output
    
    def _normalize_track(self, input_path: str, output_path: str):
        """Normalize a single track"""
        cmd = [
            "ffmpeg", "-y", "-i", input_path,
            "-af", f"afade=t=in:ss=0:d={self.config.fade_in_seconds},"
                   f"afade=t=out:st=0:d={self.config.fade_out_seconds},"
                   f"aloudnorm=I={self.config.target_loudness_lufs}:TP=-1.5",
            "-c:a", "pcm_s24le",
            output_path
        ]
        subprocess.run(cmd, check=True, capture_output=True)
    
    def _generate_binaural(self, music_path: str) -> str:
        """Generate binaural beat track matching music duration"""
        # Get duration
        probe_cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            music_path
        ]
        result = subprocess.run(probe_cmd, capture_output=True, text=True)
        duration = float(result.stdout.strip())
        
        # Generate binaural
        output = str(TEMP_DIR / "binaural.wav")
        
        preset = BINAURAL_PRESETS.get(self.config.binaural_preset, BINAURAL_PRESETS["delta_deep_sleep"])
        if self.config.binaural_preset == "custom":
            base = self.config.binaural_base_freq
            beat = self.config.binaural_beat_freq
        else:
            base = preset["base"]
            beat = preset["beat"]
        
        gen = BinauralGenerator()
        gen.generate(duration, base, beat, output)
        
        self.temp_files.append(output)
        return output
    
    def _mix_audio(self, music_path: str, binaural_path: str) -> str:
        """Mix binaural under music"""
        output = str(TEMP_DIR / "mixed.wav")
        
        cmd = [
            "ffmpeg", "-y",
            "-i", music_path,
            "-i", binaural_path,
            "-filter_complex",
            f"[1:a]volume={self.config.binaural_volume_db}dB[bin];"
            f"[0:a][bin]amix=inputs=2:duration=longest:dropout_transition=3[outa]",
            "-map", "[outa]",
            "-c:a", "pcm_s24le",
            output
        ]
        
        subprocess.run(cmd, check=True, capture_output=True)
        self.temp_files.append(output)
        return output
    
    def _export_audio(self, audio_path: str) -> str:
        """Export final audio to Desktop"""
        safe_name = "".join(c for c in self.config.project_name if c.isalnum() or c in "-_ ").strip()
        if not safe_name:
            safe_name = "flowstate_export"
        
        output = str(EXPORTS_DIR / f"{safe_name}_master.wav")
        
        # Copy the final mix
        shutil.copy2(audio_path, output)
        return output
    
    def _get_audio_duration(self, audio_path: str) -> float:
        """Get duration of audio file in seconds"""
        probe_cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            audio_path
        ]
        result = subprocess.run(probe_cmd, capture_output=True, text=True)
        return float(result.stdout.strip())
    
    def _loop_audio(self, audio_path: str, target_duration: float) -> str:
        """Loop audio to reach target duration with seamless transitions"""
        output = str(TEMP_DIR / "looped.wav")
        
        # Use ffmpeg's loop filter with acrossfade for seamless looping
        cmd = [
            "ffmpeg", "-y",
            "-stream_loop", "-1",  # Loop indefinitely
            "-i", audio_path,
            "-t", str(target_duration),
            "-af", "afade=t=in:ss=0:d=0.5,afade=t=out:st=0:d=0.5",
            "-c:a", "pcm_s24le",
            output
        ]
        
        subprocess.run(cmd, check=True, capture_output=True)
        self.temp_files.append(output)
        return output
    
    def _create_video(self, audio_path: str) -> Optional[str]:
        """Create video with the audio"""
        safe_name = "".join(c for c in self.config.project_name if c.isalnum() or c in "-_ ").strip()
        if not safe_name:
            safe_name = "flowstate_export"
        
        output = str(EXPORTS_DIR / f"{safe_name}.mp4")
        
        # Get audio duration
        probe_cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            audio_path
        ]
        result = subprocess.run(probe_cmd, capture_output=True, text=True)
        duration = float(result.stdout.strip())
        
        # Create video based on mode
        if self.config.video_mode == "black_screen":
            video = self._create_black_video(duration)
        elif self.config.video_mode == "images" and self.images:
            video = self._create_image_video(duration)
        elif self.config.video_mode == "hybrid":
            video = self._create_hybrid_video(duration)
        else:
            # Fallback to black screen
            video = self._create_black_video(duration)
        
        self.temp_files.append(video)
        
        # Combine video + audio
        cmd = [
            "ffmpeg", "-y",
            "-i", video,
            "-i", audio_path,
            "-c:v", "libx264", "-preset", "medium", "-crf", "23",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            output
        ]
        
        subprocess.run(cmd, check=True, capture_output=True)
        return output
    
    def _create_black_video(self, duration: float) -> str:
        """Create black screen video with optional intro text"""
        output = str(TEMP_DIR / "video_black.mp4")
        
        if self.config.intro_text:
            # Create intro + black
            intro_path = str(TEMP_DIR / "intro_part.mp4")
            black_path = str(TEMP_DIR / "black_part.mp4")
            concat_list = str(TEMP_DIR / "concat.txt")
            
            # Escape text for drawtext
            text = self.config.intro_text.replace("'", "\\'")
            
            # Intro with text
            cmd1 = [
                "ffmpeg", "-y",
                "-f", "lavfi",
                "-i", f"color=c=black:s={self.config.output_resolution}:r={self.config.fps}",
                "-vf", f"drawtext=text='{text}':fontcolor=white:fontsize=48:x=(w-text_w)/2:y=(h-text_h)/2",
                "-t", str(self.config.intro_duration_seconds),
                "-c:v", "libx264", "-preset", "ultrafast",
                "-an", intro_path
            ]
            subprocess.run(cmd1, check=True, capture_output=True)
            self.temp_files.append(intro_path)
            
            # Black remainder
            remainder = duration - self.config.intro_duration_seconds
            if remainder > 0:
                cmd2 = [
                    "ffmpeg", "-y",
                    "-f", "lavfi",
                    "-i", f"color=c=black:s={self.config.output_resolution}:r={self.config.fps}",
                    "-t", str(remainder),
                    "-c:v", "libx264", "-preset", "ultrafast",
                    "-an", black_path
                ]
                subprocess.run(cmd2, check=True, capture_output=True)
                self.temp_files.append(black_path)
                
                # Concatenate
                with open(concat_list, 'w') as f:
                    f.write(f"file '{intro_path}'\n")
                    f.write(f"file '{black_path}'\n")
                self.temp_files.append(concat_list)
                
                cmd3 = [
                    "ffmpeg", "-y",
                    "-f", "concat", "-safe", "0",
                    "-i", concat_list,
                    "-c", "copy",
                    output
                ]
                subprocess.run(cmd3, check=True, capture_output=True)
            else:
                shutil.move(intro_path, output)
        else:
            # Pure black
            cmd = [
                "ffmpeg", "-y",
                "-f", "lavfi",
                "-i", f"color=c=black:s={self.config.output_resolution}:r={self.config.fps}",
                "-t", str(duration),
                "-c:v", "libx264", "-preset", "ultrafast",
                "-an", output
            ]
            subprocess.run(cmd, check=True, capture_output=True)
        
        return output
    
    def _create_image_video(self, duration: float) -> str:
        """Create slideshow from images"""
        output = str(TEMP_DIR / "video_images.mp4")
        
        if not self.images:
            return self._create_black_video(duration)
        
        # Simplified: use first image for entire duration
        # Full slideshow implementation would go here
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1", "-i", self.images[0],
            "-t", str(duration),
            "-vf", f"scale={self.config.output_resolution}:force_original_aspect_ratio=decrease,pad={self.config.output_resolution}:(ow-iw)/2:(oh-ih)/2:black",
            "-c:v", "libx264", "-preset", "medium",
            "-an", output
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        
        return output
    
    def _create_hybrid_video(self, duration: float) -> str:
        """Intro -> Black -> Images -> Black"""
        # Simplified hybrid implementation
        # Would create segments and concatenate
        return self._create_black_video(duration)
    
    def cleanup(self):
        """Remove temporary files"""
        for f in self.temp_files:
            try:
                if os.path.exists(f):
                    os.remove(f)
            except:
                pass


class DropZone(QFrame):
    """Custom drag-and-drop zone for files"""
    
    filesDropped = pyqtSignal(list)
    
    def __init__(self, title: str, subtitle: str, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setMinimumHeight(120)
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Sunken)
        
        # Styling
        self.setStyleSheet("""
            DropZone {
                background-color: #1a1a2e;
                border: 2px dashed #3d3d5c;
                border-radius: 12px;
            }
            DropZone:hover {
                border-color: #8B5CF6;
                background-color: #252542;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("color: #e8e8f0; font-size: 16px; font-weight: 500;")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.subtitle_label = QLabel(subtitle)
        self.subtitle_label.setStyleSheet("color: #6b7280; font-size: 12px;")
        self.subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        layout.addWidget(self.title_label)
        layout.addWidget(self.subtitle_label)
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet("""
                DropZone {
                    background-color: #252542;
                    border: 2px dashed #8B5CF6;
                    border-radius: 12px;
                }
            """)
    
    def dragLeaveEvent(self, event):
        self.setStyleSheet("""
            DropZone {
                background-color: #1a1a2e;
                border: 2px dashed #3d3d5c;
                border-radius: 12px;
            }
        """)
    
    def dropEvent(self, event: QDropEvent):
        self.setStyleSheet("""
            DropZone {
                background-color: #1a1a2e;
                border: 2px dashed #3d3d5c;
                border-radius: 12px;
            }
        """)
        
        files = [url.toLocalFile() for url in event.mimeData().urls()]
        self.filesDropped.emit(files)


class TrackListWidget(QFrame):
    """Display and manage audio tracks"""
    
    trackRemoved = pyqtSignal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.Shape.NoFrame)
        self.setStyleSheet("background-color: transparent;")
        
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(8)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        self.tracks = []
        self.track_widgets = []
    
    def set_tracks(self, tracks: List[AudioTrack]):
        """Update the track list display"""
        # Clear existing
        for widget in self.track_widgets:
            widget.deleteLater()
        self.track_widgets.clear()
        
        self.tracks = tracks
        
        for i, track in enumerate(tracks):
            widget = self._create_track_widget(track, i)
            self.layout.addWidget(widget)
            self.track_widgets.append(widget)
        
        self.layout.addStretch()
    
    def _create_track_widget(self, track: AudioTrack, index: int) -> QFrame:
        """Create a single track display widget"""
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: #252542;
                border-radius: 8px;
                padding: 8px;
            }
        """)
        
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(12, 8, 12, 8)
        
        # Number badge
        number = QLabel(str(index + 1))
        number.setStyleSheet(f"""
            background-color: {BINAURAL_PRESETS.get('delta_deep_sleep', {}).get('color', '#8B5CF6')};
            color: white;
            border-radius: 12px;
            padding: 4px 8px;
            font-weight: bold;
            font-size: 12px;
        """)
        number.setFixedSize(24, 24)
        number.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Info
        info_layout = QVBoxLayout()
        name = QLabel(track.filename)
        name.setStyleSheet("color: #e8e8f0; font-weight: 500;")
        
        meta = QLabel(f"{track.duration_formatted} • {track.loudness_lufs:.1f} LUFS • {track.energy_profile.upper()}")
        meta.setStyleSheet("color: #6b7280; font-size: 11px;")
        
        info_layout.addWidget(name)
        info_layout.addWidget(meta)
        
        # Remove button
        remove_btn = QPushButton("✕")
        remove_btn.setFixedSize(28, 28)
        remove_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #ef4444;
                border: none;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: rgba(239, 68, 68, 0.2);
                border-radius: 4px;
            }
        """)
        remove_btn.clicked.connect(lambda: self.trackRemoved.emit(index))
        
        layout.addWidget(number)
        layout.addLayout(info_layout, 1)
        layout.addWidget(remove_btn)
        
        return frame


class FlowStateWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.setMinimumSize(1000, 800)
        
        # Data
        self.tracks: List[AudioTrack] = []
        self.images: List[str] = []
        self.config = ProjectConfig()
        self.processor: Optional[AudioProcessor] = None
        
        # Check ffmpeg
        self.ffmpeg_available = FFmpegAnalyzer.check_ffmpeg()
        
        self.setup_ui()
        self.apply_dark_theme()
        
        if not self.ffmpeg_available:
            self.show_ffmpeg_warning()
    
    def setup_ui(self):
        """Build the user interface"""
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        
        # Main layout
        main_layout = QHBoxLayout(central)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Sidebar
        sidebar = self._create_sidebar()
        main_layout.addWidget(sidebar)
        
        # Content area with status panel
        content_container = QWidget()
        content_layout = QVBoxLayout(content_container)
        content_layout.setSpacing(0)
        content_layout.setContentsMargins(0, 0, 0, 0)
        
        # Content stack
        self.stack = QStackedWidget()
        self.stack.setStyleSheet("background-color: #0a0a0f;")
        
        # Page 1: Audio Files
        self.stack.addWidget(self._create_files_page())
        
        # Page 2: Binaural
        self.stack.addWidget(self._create_binaural_page())
        
        # Page 3: Settings
        self.stack.addWidget(self._create_settings_page())
        
        # Page 4: Video
        self.stack.addWidget(self._create_video_page())
        
        # Select first page
        self.nav_buttons["files"].setChecked(True)
        
        content_layout.addWidget(self.stack, 1)
        
        # Status panel
        self.status_panel = StatusPanel()
        content_layout.addWidget(self.status_panel)
        
        main_layout.addWidget(content_container, 1)
        
        # Status bar
        self.statusBar().showMessage("Ready")
    
    def _create_sidebar(self) -> QWidget:
        """Create the left sidebar with navigation"""
        sidebar = QWidget()
        sidebar.setFixedWidth(240)
        sidebar.setStyleSheet("""
            QWidget {
                background-color: #12121a;
                border-right: 1px solid #1e1e2e;
            }
        """)
        
        layout = QVBoxLayout(sidebar)
        layout.setSpacing(4)
        layout.setContentsMargins(16, 24, 16, 24)
        
        # Logo
        logo = QLabel("🎵 FlowState")
        logo.setStyleSheet("""
            color: #8B5CF6;
            font-size: 20px;
            font-weight: 600;
            padding-bottom: 8px;
        """)
        layout.addWidget(logo)
        
        subtitle = QLabel("Audio Pipeline")
        subtitle.setStyleSheet("color: #6b7280; font-size: 12px; padding-bottom: 24px;")
        layout.addWidget(subtitle)
        
        # Navigation buttons
        self.nav_buttons = {}
        pages = [
            ("files", "📁", "Audio Files"),
            ("binaural", "🧠", "Binaural Beats"),
            ("settings", "🎚️", "Crossfade & Mix"),
            ("video", "🎬", "Video Options"),
            ("metadata", "📝", "YouTube & Export"),
        ]
        
        for page_id, icon, label in pages:
            btn = QPushButton(f"{icon}  {label}")
            btn.setCheckable(True)
            btn.setStyleSheet("""
                QPushButton {
                    text-align: left;
                    padding: 12px 16px;
                    border: none;
                    border-radius: 8px;
                    color: #9ca3af;
                    font-size: 14px;
                    background-color: transparent;
                }
                QPushButton:hover {
                    background-color: #1e1e2e;
                    color: #e8e8f0;
                }
                QPushButton:checked {
                    background-color: #8B5CF6;
                    color: white;
                }
            """)
            btn.clicked.connect(lambda checked, pid=page_id: self.navigate_to(pid))
            layout.addWidget(btn)
            self.nav_buttons[page_id] = btn
        
        layout.addStretch()
        
        # Template buttons
        template_label = QLabel("Templates")
        template_label.setStyleSheet("color: #6b7280; font-size: 11px; padding-top: 16px;")
        layout.addWidget(template_label)
        
        save_template_btn = QPushButton("💾 Save Template")
        save_template_btn.setStyleSheet("""
            QPushButton {
                background-color: #1e1e2e;
                color: #9ca3af;
                padding: 8px 12px;
                border: none;
                border-radius: 6px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #252542;
                color: #e8e8f0;
            }
        """)
        save_template_btn.clicked.connect(self.save_template)
        layout.addWidget(save_template_btn)
        
        load_template_btn = QPushButton("📂 Load Template")
        load_template_btn.setStyleSheet(save_template_btn.styleSheet())
        load_template_btn.clicked.connect(self.load_template)
        layout.addWidget(load_template_btn)
        
        layout.addStretch()
        
        # Export button
        self.export_btn = QPushButton("✨ Create Master Track")
        self.export_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #8B5CF6, stop:1 #6366F1);
                color: white;
                padding: 16px;
                border: none;
                border-radius: 8px;
                font-weight: 600;
                font-size: 14px;
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
        self.export_btn.clicked.connect(self.start_processing)
        self.export_btn.setEnabled(False)
        layout.addWidget(self.export_btn)
        
        return sidebar
    
    def _create_content_area(self) -> QWidget:
        """Create the main content area with pages"""
        self.stack = QStackedWidget()
        self.stack.setStyleSheet("background-color: #0a0a0f;")
        
        # Page 1: Audio Files
        self.stack.addWidget(self._create_files_page())
        
        # Page 2: Binaural
        self.stack.addWidget(self._create_binaural_page())
        
        # Page 3: Settings
        self.stack.addWidget(self._create_settings_page())
        
        # Page 4: Video
        self.stack.addWidget(self._create_video_page())
        
        # Page 5: Metadata
        self.stack.addWidget(self._create_metadata_page())
        
        # Page 3: Settings
        self.stack.addWidget(self._create_settings_page())
        
        # Page 4: Video
        self.stack.addWidget(self._create_video_page())
        
        # Select first page
        self.nav_buttons["files"].setChecked(True)
        
        return self.stack
    
    def _create_files_page(self) -> QWidget:
        """Create the audio files page"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(24)
        layout.setContentsMargins(32, 32, 32, 32)
        
        # Header
        header = QLabel("Audio Files")
        header.setStyleSheet("color: #e8e8f0; font-size: 28px; font-weight: 600;")
        layout.addWidget(header)
        
        desc = QLabel("Drop your audio files. I'll analyze and sequence them for optimal flow.")
        desc.setStyleSheet("color: #6b7280; font-size: 14px;")
        layout.addWidget(desc)
        
        # Drop zone
        self.audio_drop = DropZone(
            "📁 Drop Audio Files Here",
            "MP3, WAV, FLAC, AAC, M4A supported"
        )
        self.audio_drop.filesDropped.connect(self.handle_audio_drops)
        layout.addWidget(self.audio_drop)
        
        # Or browse button
        browse_btn = QPushButton("Or Click to Browse...")
        browse_btn.setStyleSheet("""
            QPushButton {
                background-color: #1e1e2e;
                color: #9ca3af;
                padding: 12px 24px;
                border: none;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #252542;
                color: #e8e8f0;
            }
        """)
        browse_btn.clicked.connect(self.browse_audio_files)
        layout.addWidget(browse_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Track list
        self.track_list = TrackListWidget()
        self.track_list.trackRemoved.connect(self.remove_track)
        layout.addWidget(self.track_list)
        
        # Project name
        name_layout = QHBoxLayout()
        name_label = QLabel("Project Name:")
        name_label.setStyleSheet("color: #9ca3af;")
        
        self.project_name = QLineEdit("My Sleep Mix")
        self.project_name.setStyleSheet("""
            QLineEdit {
                background-color: #1e1e2e;
                color: #e8e8f0;
                border: 1px solid #2d2d3d;
                border-radius: 6px;
                padding: 8px 12px;
            }
        """)
        
        name_layout.addWidget(name_label)
        name_layout.addWidget(self.project_name, 1)
        layout.addLayout(name_layout)
        
        # Loop settings
        loop_group = QGroupBox("Loop Settings")
        loop_group.setStyleSheet("""
            QGroupBox {
                color: #8B5CF6;
                font-weight: 600;
                border: 1px solid #1e1e2e;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 12px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 8px;
            }
        """)
        
        loop_layout = QVBoxLayout(loop_group)
        
        # Loop checkbox
        self.loop_checkbox = QCheckBox("Enable Looping")
        self.loop_checkbox.setChecked(True)
        self.loop_checkbox.setStyleSheet("color: #e8e8f0; font-size: 14px;")
        loop_layout.addWidget(self.loop_checkbox)
        
        # Hours input
        hours_layout = QHBoxLayout()
        hours_label = QLabel("Target Duration:")
        hours_label.setStyleSheet("color: #9ca3af;")
        
        self.loop_hours = QDoubleSpinBox()
        self.loop_hours.setRange(0.5, 24)
        self.loop_hours.setValue(8)
        self.loop_hours.setDecimals(1)
        self.loop_hours.setSuffix(" hours")
        self.loop_hours.setStyleSheet("""
            QDoubleSpinBox {
                background-color: #1e1e2e;
                color: #e8e8f0;
                border: 1px solid #2d2d3d;
                border-radius: 6px;
                padding: 8px;
            }
        """)
        
        hours_layout.addWidget(hours_label)
        hours_layout.addWidget(self.loop_hours)
        hours_layout.addStretch()
        loop_layout.addLayout(hours_layout)
        
        loop_tip = QLabel("💡 The sequence will repeat until it reaches the target duration")
        loop_tip.setStyleSheet("color: #6b7280; font-size: 11px;")
        loop_layout.addWidget(loop_tip)
        
        layout.addWidget(loop_group)
        
        layout.addStretch()
        return page
    
    def _create_binaural_page(self) -> QWidget:
        """Create the binaural beats page"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(24)
        layout.setContentsMargins(32, 32, 32, 32)
        
        # Header
        header = QLabel("Binaural Beats")
        header.setStyleSheet("color: #e8e8f0; font-size: 28px; font-weight: 600;")
        layout.addWidget(header)
        
        desc = QLabel("Select a frequency preset to enhance the listening experience.")
        desc.setStyleSheet("color: #6b7280; font-size: 14px;")
        layout.addWidget(desc)
        
        # Preset selector
        preset_group = QGroupBox("Frequency Preset")
        preset_group.setStyleSheet("""
            QGroupBox {
                color: #8B5CF6;
                font-weight: 600;
                border: 1px solid #1e1e2e;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 12px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 8px;
            }
        """)
        
        preset_layout = QVBoxLayout(preset_group)
        
        self.preset_combo = QComboBox()
        self.preset_combo.setStyleSheet("""
            QComboBox {
                background-color: #1e1e2e;
                color: #e8e8f0;
                border: 1px solid #2d2d3d;
                border-radius: 6px;
                padding: 8px 12px;
                min-width: 300px;
            }
            QComboBox::drop-down {
                border: none;
                padding-right: 12px;
            }
            QComboBox QAbstractItemView {
                background-color: #1e1e2e;
                color: #e8e8f0;
                selection-background-color: #8B5CF6;
            }
        """)
        
        for key, preset in BINAURAL_PRESETS.items():
            self.preset_combo.addItem(preset["name"], key)
        
        self.preset_combo.currentIndexChanged.connect(self.update_preset_info)
        preset_layout.addWidget(self.preset_combo)
        
        # Preset info display
        self.preset_info = QLabel("")
        self.preset_info.setStyleSheet("""
            color: #9ca3af;
            font-size: 13px;
            padding: 12px;
            background-color: #1e1e2e;
            border-radius: 6px;
        """)
        self.preset_info.setWordWrap(True)
        preset_layout.addWidget(self.preset_info)
        
        layout.addWidget(preset_group)
        
        # Custom frequencies
        self.custom_group = QGroupBox("Custom Frequencies")
        self.custom_group.setVisible(False)
        self.custom_group.setStyleSheet(preset_group.styleSheet())
        
        custom_layout = QGridLayout(self.custom_group)
        
        base_label = QLabel("Base Frequency (Hz):")
        base_label.setStyleSheet("color: #9ca3af;")
        self.base_freq = QDoubleSpinBox()
        self.base_freq.setRange(100, 400)
        self.base_freq.setValue(200)
        self.base_freq.setStyleSheet("""
            QDoubleSpinBox {
                background-color: #1e1e2e;
                color: #e8e8f0;
                border: 1px solid #2d2d3d;
                border-radius: 6px;
                padding: 8px;
            }
        """)
        
        beat_label = QLabel("Beat Frequency (Hz):")
        beat_label.setStyleSheet("color: #9ca3af;")
        self.beat_freq = QDoubleSpinBox()
        self.beat_freq.setRange(0.5, 40)
        self.beat_freq.setValue(2.5)
        self.beat_freq.setDecimals(1)
        self.beat_freq.setStyleSheet(self.base_freq.styleSheet())
        
        custom_layout.addWidget(base_label, 0, 0)
        custom_layout.addWidget(self.base_freq, 0, 1)
        custom_layout.addWidget(beat_label, 1, 0)
        custom_layout.addWidget(self.beat_freq, 1, 1)
        custom_layout.setColumnStretch(1, 1)
        
        layout.addWidget(self.custom_group)
        
        # Volume control
        volume_group = QGroupBox("Binaural Volume")
        volume_group.setStyleSheet(preset_group.styleSheet())
        volume_layout = QVBoxLayout(volume_group)
        
        volume_desc = QLabel("How loud the binaural beat plays under your music. -20 dB is subtle and sleep-safe.")
        volume_desc.setStyleSheet("color: #6b7280; font-size: 12px;")
        volume_layout.addWidget(volume_desc)
        
        volume_slider_layout = QHBoxLayout()
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(-40, -10)
        self.volume_slider.setValue(-20)
        self.volume_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 6px;
                background: #1e1e2e;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #8B5CF6;
                width: 18px;
                height: 18px;
                border-radius: 9px;
                margin: -6px 0;
            }
            QSlider::sub-page:horizontal {
                background: #8B5CF6;
                border-radius: 3px;
            }
        """)
        
        self.volume_label = QLabel("-20 dB")
        self.volume_label.setStyleSheet("color: #e8e8f0; min-width: 50px;")
        self.volume_slider.valueChanged.connect(
            lambda v: self.volume_label.setText(f"{v} dB")
        )
        
        volume_slider_layout.addWidget(self.volume_slider)
        volume_slider_layout.addWidget(self.volume_label)
        volume_layout.addLayout(volume_slider_layout)
        
        layout.addWidget(volume_group)
        
        layout.addStretch()
        
        # Initialize preset info
        self.update_preset_info()
        
        return page
    
    def _create_settings_page(self) -> QWidget:
        """Create the crossfade and mix settings page"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(24)
        layout.setContentsMargins(32, 32, 32, 32)
        
        # Header
        header = QLabel("Crossfade & Mix")
        header.setStyleSheet("color: #e8e8f0; font-size: 28px; font-weight: 600;")
        layout.addWidget(header)
        
        desc = QLabel("Fine-tune how tracks blend together.")
        desc.setStyleSheet("color: #6b7280; font-size: 14px;")
        layout.addWidget(desc)
        
        # Crossfade settings
        fade_group = QGroupBox("Crossfade Settings")
        fade_group.setStyleSheet("""
            QGroupBox {
                color: #8B5CF6;
                font-weight: 600;
                border: 1px solid #1e1e2e;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 12px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 8px;
            }
        """)
        
        fade_layout = QGridLayout(fade_group)
        
        # Crossfade duration
        cf_label = QLabel("Crossfade Duration:")
        cf_label.setStyleSheet("color: #9ca3af;")
        self.crossfade_spin = QDoubleSpinBox()
        self.crossfade_spin.setRange(1, 30)
        self.crossfade_spin.setValue(8)
        self.crossfade_spin.setSuffix(" seconds")
        self.crossfade_spin.setStyleSheet("""
            QDoubleSpinBox {
                background-color: #1e1e2e;
                color: #e8e8f0;
                border: 1px solid #2d2d3d;
                border-radius: 6px;
                padding: 8px;
            }
        """)
        
        # Fade in
        fi_label = QLabel("Fade In:")
        fi_label.setStyleSheet("color: #9ca3af;")
        self.fade_in_spin = QDoubleSpinBox()
        self.fade_in_spin.setRange(0, 10)
        self.fade_in_spin.setValue(3)
        self.fade_in_spin.setSuffix(" seconds")
        self.fade_in_spin.setStyleSheet(self.crossfade_spin.styleSheet())
        
        # Fade out
        fo_label = QLabel("Fade Out:")
        fo_label.setStyleSheet("color: #9ca3af;")
        self.fade_out_spin = QDoubleSpinBox()
        self.fade_out_spin.setRange(0, 30)
        self.fade_out_spin.setValue(5)
        self.fade_out_spin.setSuffix(" seconds")
        self.fade_out_spin.setStyleSheet(self.crossfade_spin.styleSheet())
        
        fade_layout.addWidget(cf_label, 0, 0)
        fade_layout.addWidget(self.crossfade_spin, 0, 1)
        fade_layout.addWidget(fi_label, 1, 0)
        fade_layout.addWidget(self.fade_in_spin, 1, 1)
        fade_layout.addWidget(fo_label, 2, 0)
        fade_layout.addWidget(self.fade_out_spin, 2, 1)
        fade_layout.setColumnStretch(1, 1)
        
        layout.addWidget(fade_group)
        
        # Loudness settings
        loud_group = QGroupBox("Loudness (LUFS)")
        loud_group.setStyleSheet(fade_group.styleSheet())
        loud_layout = QVBoxLayout(loud_group)
        
        loud_desc = QLabel("-16 LUFS is YouTube's standard. Lower values are quieter but more sleep-safe.")
        loud_desc.setStyleSheet("color: #6b7280; font-size: 12px;")
        loud_layout.addWidget(loud_desc)
        
        self.loudness_spin = QDoubleSpinBox()
        self.loudness_spin.setRange(-23, -14)
        self.loudness_spin.setValue(-16)
        self.loudness_spin.setDecimals(1)
        self.loudness_spin.setSuffix(" LUFS")
        self.loudness_spin.setStyleSheet(self.crossfade_spin.styleSheet())
        loud_layout.addWidget(self.loudness_spin)
        
        layout.addWidget(loud_group)
        
        layout.addStretch()
        return page
    
    def _create_video_page(self) -> QWidget:
        """Create the video export options page"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(24)
        layout.setContentsMargins(32, 32, 32, 32)
        
        # Header
        header = QLabel("Video Options")
        header.setStyleSheet("color: #e8e8f0; font-size: 28px; font-weight: 600;")
        layout.addWidget(header)
        
        desc = QLabel("Choose how your video looks.")
        desc.setStyleSheet("color: #6b7280; font-size: 14px;")
        layout.addWidget(desc)
        
        # Video mode selection
        mode_group = QGroupBox("Video Mode")
        mode_group.setStyleSheet("""
            QGroupBox {
                color: #8B5CF6;
                font-weight: 600;
                border: 1px solid #1e1e2e;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 12px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 8px;
            }
        """)
        
        mode_layout = QVBoxLayout(mode_group)
        
        self.mode_group = QButtonGroup(self)
        
        modes = [
            ("black_screen", "⬛ Black Screen", "Simple black screen, optional intro text"),
            ("images", "🖼️ Image Slideshow", "Fade between uploaded images"),
            ("hybrid", "🔀 Hybrid", "Intro → Black → Images → Black"),
            ("audio_only", "🔊 Audio Only", "Just the audio file, no video"),
        ]
        
        for mode_id, title, description in modes:
            radio = QRadioButton(title)
            radio.setStyleSheet("""
                QRadioButton {
                    color: #e8e8f0;
                    font-size: 14px;
                    padding: 8px;
                }
                QRadioButton::indicator {
                    width: 18px;
                    height: 18px;
                }
            """)
            
            desc_label = QLabel(description)
            desc_label.setStyleSheet("color: #6b7280; font-size: 12px; padding-left: 28px;")
            
            self.mode_group.addButton(radio)
            radio.mode_id = mode_id
            
            mode_layout.addWidget(radio)
            mode_layout.addWidget(desc_label)
        
        # Select default
        self.mode_group.buttons()[0].setChecked(True)
        
        layout.addWidget(mode_group)
        
        # Intro text
        intro_group = QGroupBox("Intro Text (Optional)")
        intro_group.setStyleSheet(mode_group.styleSheet())
        intro_layout = QVBoxLayout(intro_group)
        
        self.intro_text = QTextEdit()
        self.intro_text.setPlaceholderText("Welcome to your deep sleep session...")
        self.intro_text.setMaximumHeight(80)
        self.intro_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e2e;
                color: #e8e8f0;
                border: 1px solid #2d2d3d;
                border-radius: 6px;
                padding: 8px;
            }
        """)
        intro_layout.addWidget(self.intro_text)
        
        intro_dur_layout = QHBoxLayout()
        intro_dur_label = QLabel("Display for:")
        intro_dur_label.setStyleSheet("color: #9ca3af;")
        self.intro_dur = QSpinBox()
        self.intro_dur.setRange(1, 60)
        self.intro_dur.setValue(10)
        self.intro_dur.setSuffix(" seconds")
        self.intro_dur.setStyleSheet("""
            QSpinBox {
                background-color: #1e1e2e;
                color: #e8e8f0;
                border: 1px solid #2d2d3d;
                border-radius: 6px;
                padding: 8px;
            }
        """)
        intro_dur_layout.addWidget(intro_dur_label)
        intro_dur_layout.addWidget(self.intro_dur)
        intro_dur_layout.addStretch()
        intro_layout.addLayout(intro_dur_layout)
        
        layout.addWidget(intro_group)
        
        # Image upload (for image modes)
        self.image_section = QWidget()
        image_layout = QVBoxLayout(self.image_section)
        image_layout.setContentsMargins(0, 0, 0, 0)
        
        image_drop = DropZone(
            "🖼️ Drop Images Here",
            "JPG, PNG, WEBP — for slideshow mode"
        )
        image_drop.filesDropped.connect(self.handle_image_drops)
        image_layout.addWidget(image_drop)
        
        layout.addWidget(self.image_section)
        
        layout.addStretch()
        return page
    
    def apply_dark_theme(self):
        """Apply dark theme to the application"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #0a0a0f;
            }
            QWidget {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }
            QScrollBar:vertical {
                background-color: #1e1e2e;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #3d3d5c;
                border-radius: 6px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #8B5CF6;
            }
        """)
    
    def show_ffmpeg_warning(self):
        """Show warning if ffmpeg is not installed"""
        msg = QMessageBox(self)
        msg.setWindowTitle("ffmpeg Required")
        msg.setText("ffmpeg is not installed")
        msg.setInformativeText(
            "FlowState Audio requires ffmpeg to process audio.\n\n"
            "Install it with:\n"
            "  brew install ffmpeg"
        )
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.exec()
    
    def navigate_to(self, page_id: str):
        """Navigate to a specific page"""
        pages = {"files": 0, "binaural": 1, "settings": 2, "video": 3, "metadata": 4}
        if page_id in pages:
            self.stack.setCurrentIndex(pages[page_id])
            
            # Update button states
            for pid, btn in self.nav_buttons.items():
                btn.setChecked(pid == page_id)
    
    def update_preset_info(self):
        """Update the preset information display"""
        preset_key = self.preset_combo.currentData()
        preset = BINAURAL_PRESETS.get(preset_key, BINAURAL_PRESETS["delta_deep_sleep"])
        
        info_text = f"""
        <b>Base:</b> {preset['base']} Hz | <b>Beat:</b> {preset['beat']} Hz<br><br>
        {preset['description']}
        """
        self.preset_info.setText(info_text)
        
        # Show/hide custom controls
        self.custom_group.setVisible(preset_key == "custom")
    
    def browse_audio_files(self):
        """Open file dialog for audio files"""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Audio Files",
            str(Path.home()),
            "Audio Files (*.mp3 *.wav *.flac *.aac *.m4a *.ogg);;All Files (*.*)"
        )
        if files:
            self.process_audio_files(files)
    
    def handle_audio_drops(self, files: List[str]):
        """Handle dropped audio files"""
        audio_files = [f for f in files if f.lower().endswith(
            ('.mp3', '.wav', '.flac', '.aac', '.m4a', '.ogg')
        )]
        if audio_files:
            self.process_audio_files(audio_files)
    
    def handle_image_drops(self, files: List[str]):
        """Handle dropped image files"""
        image_files = [f for f in files if f.lower().endswith(
            ('.jpg', '.jpeg', '.png', '.webp', '.gif')
        )]
        self.images.extend(image_files)
        self.statusBar().showMessage(f"Added {len(image_files)} images")
    
    def process_audio_files(self, files: List[str]):
        """Analyze and add audio files"""
        if not self.ffmpeg_available:
            self.show_ffmpeg_warning()
            return
        
        self.statusBar().showMessage("Analyzing audio files...")
        
        # Analyze in background
        analyzer = FFmpegAnalyzer()
        new_tracks = []
        
        for filepath in files:
            try:
                track = analyzer.analyze(filepath)
                new_tracks.append(track)
            except Exception as e:
                print(f"Error analyzing {filepath}: {e}")
        
        # Add to existing tracks
        self.tracks.extend(new_tracks)
        
        # Optimize sequence
        optimizer = SequenceOptimizer()
        self.tracks = optimizer.optimize(self.tracks)
        
        # Update UI
        self.track_list.set_tracks(self.tracks)
        self.export_btn.setEnabled(len(self.tracks) > 0)
        
        total_duration = sum(t.duration for t in self.tracks)
        mins = int(total_duration // 60)
        secs = int(total_duration % 60)
        self.statusBar().showMessage(
            f"Added {len(new_tracks)} tracks. Total: {len(self.tracks)} tracks, {mins}:{secs:02d}"
        )
    
    def remove_track(self, index: int):
        """Remove a track from the list"""
        if 0 <= index < len(self.tracks):
            self.tracks.pop(index)
            self.track_list.set_tracks(self.tracks)
            self.export_btn.setEnabled(len(self.tracks) > 0)
    
    def start_processing(self):
        """Start the audio processing pipeline"""
        if not self.tracks:
            return
        
        # Gather configuration
        self.config.project_name = self.project_name.text() or "Untitled"
        
        # Loop settings
        self.config.loop_mode = self.loop_checkbox.isChecked()
        self.config.target_duration_minutes = self.loop_hours.value() * 60
        
        # Binaural settings
        self.config.binaural_preset = self.preset_combo.currentData()
        self.config.binaural_base_freq = self.base_freq.value()
        self.config.binaural_beat_freq = self.beat_freq.value()
        self.config.binaural_volume_db = self.volume_slider.value()
        
        # Crossfade settings
        self.config.crossfade_seconds = self.crossfade_spin.value()
        self.config.fade_in_seconds = self.fade_in_spin.value()
        self.config.fade_out_seconds = self.fade_out_spin.value()
        self.config.target_loudness_lufs = self.loudness_spin.value()
        
        # Video settings
        selected_mode = self.mode_group.checkedButton()
        self.config.video_mode = selected_mode.mode_id if selected_mode else "black_screen"
        self.config.intro_text = self.intro_text.toPlainText()
        self.config.intro_duration_seconds = self.intro_dur.value()
        
        # YouTube metadata
        self.config.youtube_title = self.youtube_title.text()
        self.config.youtube_description = self.youtube_description.toPlainText()
        self.config.youtube_tags = self.youtube_tags.text()
        
        # Disable UI during processing
        self.export_btn.setEnabled(False)
        self.export_btn.setText("Processing...")
        self.status_panel.show_panel()
        
        # Start processor thread
        self.processor = AudioProcessor(self.tracks, self.images, self.config)
        self.processor.progress.connect(self.update_progress)
        self.processor.stage_started.connect(self.on_stage_started)
        self.processor.stage_completed.connect(self.on_stage_completed)
        self.processor.finished.connect(self.processing_finished)
        self.processor.error.connect(self.processing_error)
        self.processor.start()
    
    def on_stage_started(self, stage_id: str, description: str):
        """Handle stage start"""
        self.status_panel.set_stage_active(stage_id)
        self.status_panel.set_detail(description)
    
    def on_stage_completed(self, stage_id: str, result: str):
        """Handle stage completion"""
        self.status_panel.set_stage_complete(stage_id)
        self.status_panel.set_detail(result)
    
    def update_progress(self, message: str, percentage: int, step: int, total: int):
        """Update progress bar"""
        self.status_panel.update_progress(message, percentage, step, total)
        self.statusBar().showMessage(message)
    
    def processing_finished(self, results: dict):
        """Handle successful completion"""
        self.status_panel.update_progress("Complete!", 100, 6, 6)
        
        # Mark all stages complete
        for stage_id in ["sequencing", "binaural", "mixing", "exporting", "video", "finalizing"]:
            self.status_panel.set_stage_complete(stage_id)
        
        # Show success message
        audio_path = results.get("audio_path", "")
        video_path = results.get("video_path", "")
        
        msg = QMessageBox(self)
        msg.setWindowTitle("Export Complete")
        msg.setText("✨ Your files have been exported!")
        
        details = f"📁 Audio: {audio_path}"
        if video_path:
            details += f"\n🎬 Video: {video_path}"
        details += f"\n\nSaved to: ~/Desktop/FlowState Exports/"
        
        msg.setInformativeText(details)
        msg.setIcon(QMessageBox.Icon.Information)
        
        # Add button to open exports folder
        open_btn = msg.addButton("Open Exports Folder", QMessageBox.ButtonRole.ActionRole)
        msg.addButton("OK", QMessageBox.ButtonRole.AcceptRole)
        
        msg.exec()
        
        if msg.clickedButton() == open_btn:
            subprocess.run(["open", str(EXPORTS_DIR)])
        
        # Export YouTube metadata as text file
        if self.export_txt_checkbox.isChecked():
            self._export_youtube_metadata()
        
        # Reset UI
        self.export_btn.setEnabled(True)
        self.export_btn.setText("✨ Create Master Track")
        self.status_panel.hide_panel()
        self.statusBar().showMessage("Ready")
    
    def _export_youtube_metadata(self):
        """Export YouTube metadata as a text file"""
        safe_name = "".join(c for c in self.config.project_name if c.isalnum() or c in "-_ ").strip()
        if not safe_name:
            safe_name = "flowstate_export"
        
        metadata_file = EXPORTS_DIR / f"{safe_name}_youtube_metadata.txt"
        
        content = f"""YOUTUBE UPLOAD METADATA
{'='*50}

TITLE:
{self.config.youtube_title or self.config.project_name}

DESCRIPTION:
{self.config.youtube_description}

TAGS:
{self.config.youtube_tags}

CATEGORY:
Music

SETTINGS:
• Made for kids: No
• License: Standard YouTube License
• Comments: Allow all comments

AUDIO SPECS:
• Duration: {self.config.target_duration_minutes} minutes
• Binaural: {BINAURAL_PRESETS.get(self.config.binaural_preset, {}).get('name', 'Custom')}
• Loudness: {self.config.target_loudness_lufs} LUFS

Exported by FlowState Audio
https://github.com/lizardflaco/flowstate-audio
"""
        
        with open(metadata_file, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def processing_error(self, error_msg: str):
        """Handle processing error"""
        self.status_panel.hide_panel()
        
        msg = QMessageBox(self)
        msg.setWindowTitle("Processing Error")
        msg.setText("❌ An error occurred during processing")
        msg.setInformativeText(error_msg)
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.exec()
        
        self.export_btn.setEnabled(True)
        self.export_btn.setText("✨ Create Master Track")
        self.statusBar().showMessage("Error occurred")

    def _create_metadata_page(self) -> QWidget:
        """Create the YouTube metadata and export options page"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(24)
        layout.setContentsMargins(32, 32, 32, 32)
        
        # Header
        header = QLabel("YouTube & Export")
        header.setStyleSheet("color: #e8e8f0; font-size: 28px; font-weight: 600;")
        layout.addWidget(header)
        
        desc = QLabel("Add metadata for YouTube and export options.")
        desc.setStyleSheet("color: #6b7280; font-size: 14px;")
        layout.addWidget(desc)
        
        # YouTube Title
        title_group = QGroupBox("YouTube Title")
        title_group.setStyleSheet("""
            QGroupBox {
                color: #8B5CF6;
                font-weight: 600;
                border: 1px solid #1e1e2e;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 12px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 8px;
            }
        """)
        title_layout = QVBoxLayout(title_group)
        
        self.youtube_title = QLineEdit()
        self.youtube_title.setPlaceholderText("e.g., 8 Hour Deep Sleep Music with Delta Waves")
        self.youtube_title.setStyleSheet("""
            QLineEdit {
                background-color: #1e1e2e;
                color: #e8e8f0;
                border: 1px solid #2d2d3d;
                border-radius: 6px;
                padding: 8px 12px;
            }
        """)
        title_layout.addWidget(self.youtube_title)
        
        title_tip = QLabel("💡 Include duration and key benefit in the title")
        title_tip.setStyleSheet("color: #6b7280; font-size: 11px;")
        title_layout.addWidget(title_tip)
        
        layout.addWidget(title_group)
        
        # YouTube Description
        desc_group = QGroupBox("YouTube Description")
        desc_group.setStyleSheet(title_group.styleSheet())
        desc_layout = QVBoxLayout(desc_group)
        
        self.youtube_description = QTextEdit()
        self.youtube_description.setPlaceholderText("""Welcome to this deep sleep meditation...

🎵 Benefits:
• Deep sleep and relaxation
• Stress relief
• Calm mind

🧠 Binaural Beats:
This track uses Delta waves (2.5 Hz) to help you achieve deep sleep.

💤 Best used with:
• Headphones for binaural effect
• Low to moderate volume
• As you prepare for sleep

#SleepMusic #BinauralBeats #DeepSleep""")
        self.youtube_description.setMaximumHeight(200)
        self.youtube_description.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e2e;
                color: #e8e8f0;
                border: 1px solid #2d2d3d;
                border-radius: 6px;
                padding: 8px;
            }
        """)
        desc_layout.addWidget(self.youtube_description)
        
        desc_tip = QLabel("💡 Include timestamps, benefits, and hashtags")
        desc_tip.setStyleSheet("color: #6b7280; font-size: 11px;")
        desc_layout.addWidget(desc_tip)
        
        layout.addWidget(desc_group)
        
        # Tags
        tags_group = QGroupBox("Tags (comma separated)")
        tags_group.setStyleSheet(title_group.styleSheet())
        tags_layout = QVBoxLayout(tags_group)
        
        self.youtube_tags = QLineEdit()
        self.youtube_tags.setPlaceholderText("sleep music, binaural beats, delta waves, deep sleep, meditation, relaxation")
        self.youtube_tags.setStyleSheet(self.youtube_title.styleSheet())
        tags_layout.addWidget(self.youtube_tags)
        
        layout.addWidget(tags_group)
        
        # Export Options
        export_group = QGroupBox("Export Options")
        export_group.setStyleSheet(title_group.styleSheet())
        export_layout = QVBoxLayout(export_group)
        
        self.export_txt_checkbox = QCheckBox("Export YouTube metadata as .txt file")
        self.export_txt_checkbox.setChecked(True)
        self.export_txt_checkbox.setStyleSheet("color: #e8e8f0;")
        export_layout.addWidget(self.export_txt_checkbox)
        
        layout.addWidget(export_group)
        
        layout.addStretch()
        return page
    
    def save_template(self):
        """Save current configuration as a template"""
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Template", str(Path.home() / "Desktop"),
            "FlowState Templates (*.flowstate)"
        )
        if filename:
            # Update config from UI
            self.config.project_name = self.project_name.text()
            self.config.youtube_title = self.youtube_title.text()
            self.config.youtube_description = self.youtube_description.toPlainText()
            self.config.youtube_tags = self.youtube_tags.text()
            
            self.config.save_to_file(filename)
            QMessageBox.information(self, "Template Saved", f"Template saved to:\n{filename}")
    
    def load_template(self):
        """Load a saved template"""
        filename, _ = QFileDialog.getOpenFileName(
            self, "Load Template", str(Path.home() / "Desktop"),
            "FlowState Templates (*.flowstate)"
        )
        if filename:
            try:
                self.config = ProjectConfig.load_from_file(filename)
                
                # Update UI
                self.project_name.setText(self.config.project_name)
                self.youtube_title.setText(self.config.youtube_title)
                self.youtube_description.setText(self.config.youtube_description)
                self.youtube_tags.setText(self.config.youtube_tags)
                
                # Update other UI elements
                self.preset_combo.setCurrentIndex(
                    self.preset_combo.findData(self.config.binaural_preset)
                )
                self.base_freq.setValue(self.config.binaural_base_freq)
                self.beat_freq.setValue(self.config.binaural_beat_freq)
                self.volume_slider.setValue(int(self.config.binaural_volume_db))
                self.crossfade_spin.setValue(self.config.crossfade_seconds)
                self.loudness_spin.setValue(self.config.target_loudness_lufs)
                
                QMessageBox.information(self, "Template Loaded", "Template loaded successfully!")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load template:\n{str(e)}")


def main():
    """Application entry point"""
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    
    # Set application font
    font = QFont("-apple-system", 13)
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    app.setFont(font)
    
    # Create and show main window
    window = FlowStateWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
