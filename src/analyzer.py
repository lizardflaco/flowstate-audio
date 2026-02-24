#!/usr/bin/env python3
"""
FlowState Channel Analyzer v2.0
Analyzes YouTube channel performance and generates recommendations
Built for Jud Smith - Mystical Sanctuary

Features:
- Channel performance analysis
- Thumbnail generator
- SEO recommendations
- Content strategy suggestions
"""

import sys
import json
import re
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Tuple
from datetime import datetime

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QSpinBox, QDoubleSpinBox,
    QTextEdit, QProgressBar, QFileDialog, QMessageBox, QGroupBox,
    QCheckBox, QLineEdit, QStackedWidget, QFrame, QScrollArea,
    QGridLayout, QTabWidget, QListWidget, QListWidgetItem
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QColor, QPalette, QLinearGradient, QBrush

# Paths
EXPORTS_DIR = Path.home() / "Desktop" / "FlowState Exports"
ANALYSIS_DIR = Path.home() / "Desktop" / "FlowState Analysis"
EXPORTS_DIR.mkdir(exist_ok=True)
ANALYSIS_DIR.mkdir(exist_ok=True)


@dataclass
class VideoData:
    """Represents a YouTube video's performance data"""
    video_id: str
    title: str
    description: str = ""
    view_count: int = 0
    like_count: int = 0
    comment_count: int = 0
    duration: str = ""
    thumbnail_url: str = ""
    published_at: str = ""
    tags: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
    
    @property
    def engagement_rate(self) -> float:
        """Calculate engagement rate (likes + comments / views)"""
        if self.view_count == 0:
            return 0.0
        return (self.like_count + self.comment_count) / self.view_count * 100


@dataclass
class ChannelAnalysis:
    """Complete channel analysis results"""
    channel_name: str = ""
    subscriber_count: int = 0
    total_views: int = 0
    total_videos: int = 0
    videos: List[VideoData] = None
    
    # Performance metrics
    avg_views: float = 0.0
    avg_engagement: float = 0.0
    best_performing_video: Optional[VideoData] = None
    worst_performing_video: Optional[VideoData] = None
    
    # Content patterns
    common_words_in_titles: List[Tuple[str, int]] = None
    optimal_video_length: str = ""
    best_posting_time: str = ""
    
    def __post_init__(self):
        if self.videos is None:
            self.videos = []
        if self.common_words_in_titles is None:
            self.common_words_in_titles = []


class ChannelAnalyzer(QThread):
    """Background thread for analyzing channel data"""
    
    progress = pyqtSignal(str, int)
    finished = pyqtSignal(ChannelAnalysis)
    error = pyqtSignal(str)
    
    def __init__(self, channel_url: str, data_file: Optional[str] = None):
        super().__init__()
        self.channel_url = channel_url
        self.data_file = data_file
    
    def run(self):
        try:
            analysis = self.analyze()
            self.finished.emit(analysis)
        except Exception as e:
            self.error.emit(str(e))
    
    def analyze(self) -> ChannelAnalysis:
        """Analyze channel data"""
        self.progress.emit("Loading channel data...", 10)
        
        # For now, load from exported JSON file
        # In production, this would scrape or use YouTube API
        if self.data_file and Path(self.data_file).exists():
            with open(self.data_file, 'r') as f:
                data = json.load(f)
        else:
            # Create sample data for demonstration
            data = self._create_sample_data()
        
        self.progress.emit("Processing video data...", 30)
        
        analysis = ChannelAnalysis(
            channel_name=data.get('channel_name', 'Unknown'),
            subscriber_count=data.get('subscriber_count', 0),
            total_videos=len(data.get('videos', []))
        )
        
        # Parse video data
        for vid_data in data.get('videos', []):
            video = VideoData(**vid_data)
            analysis.videos.append(video)
            analysis.total_views += video.view_count
        
        self.progress.emit("Calculating performance metrics...", 50)
        
        # Calculate averages
        if analysis.videos:
            analysis.avg_views = sum(v.view_count for v in analysis.videos) / len(analysis.videos)
            analysis.avg_engagement = sum(v.engagement_rate for v in analysis.videos) / len(analysis.videos)
            
            # Find best and worst performing
            sorted_by_views = sorted(analysis.videos, key=lambda v: v.view_count, reverse=True)
            analysis.best_performing_video = sorted_by_views[0] if sorted_by_views else None
            analysis.worst_performing_video = sorted_by_views[-1] if sorted_by_views else None
        
        self.progress.emit("Analyzing content patterns...", 70)
        
        # Analyze title patterns
        analysis.common_words_in_titles = self._analyze_titles(analysis.videos)
        
        # Determine optimal length
        analysis.optimal_video_length = self._find_optimal_length(analysis.videos)
        
        self.progress.emit("Generating recommendations...", 90)
        
        return analysis
    
    def _create_sample_data(self) -> dict:
        """Create sample data for demonstration"""
        return {
            "channel_name": "Mystical Sanctuary",
            "subscriber_count": 150,
            "videos": [
                {
                    "video_id": "sample1",
                    "title": "8 Hour Deep Sleep Music with Delta Waves",
                    "description": "Relaxing sleep music for deep rest...",
                    "view_count": 245,
                    "like_count": 12,
                    "comment_count": 3,
                    "duration": "8:00:00",
                    "published_at": "2025-01-15"
                },
                {
                    "video_id": "sample2", 
                    "title": "Meditation Music for Stress Relief",
                    "description": "Calming meditation music...",
                    "view_count": 189,
                    "like_count": 8,
                    "comment_count": 2,
                    "duration": "3:00:00",
                    "published_at": "2025-01-20"
                },
                {
                    "video_id": "sample3",
                    "title": "Binaural Beats for Focus and Concentration",
                    "description": "Alpha waves for productivity...",
                    "view_count": 156,
                    "like_count": 6,
                    "comment_count": 1,
                    "duration": "2:00:00",
                    "published_at": "2025-01-25"
                }
            ]
        }
    
    def _analyze_titles(self, videos: List[VideoData]) -> List[Tuple[str, int]]:
        """Analyze common words in video titles"""
        word_counts = {}
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        
        for video in videos:
            words = re.findall(r'\b[a-zA-Z]+\b', video.title.lower())
            for word in words:
                if word not in stop_words and len(word) > 2:
                    word_counts[word] = word_counts.get(word, 0) + 1
        
        return sorted(word_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    
    def _find_optimal_length(self, videos: List[VideoData]) -> str:
        """Find the optimal video length based on performance"""
        if not videos:
            return "Unknown"
        
        # Group by duration ranges
        ranges = {
            "Short (0-30 min)": [],
            "Medium (30 min - 2 hr)": [],
            "Long (2-8 hr)": [],
            "Very Long (8+ hr)": []
        }
        
        for video in videos:
            # Parse duration
            parts = video.duration.split(':')
            if len(parts) == 3:
                hours = int(parts[0])
                if hours >= 8:
                    ranges["Very Long (8+ hr)"].append(video.view_count)
                elif hours >= 2:
                    ranges["Long (2-8 hr)"].append(video.view_count)
                else:
                    ranges["Medium (30 min - 2 hr)"].append(video.view_count)
            else:
                ranges["Short (0-30 min)"].append(video.view_count)
        
        # Find range with highest average views
        best_range = max(ranges.items(), key=lambda x: sum(x[1]) / len(x[1]) if x[1] else 0)
        return best_range[0]


class ThumbnailGenerator:
    """Generate YouTube thumbnails"""
    
    TEMPLATES = {
        "sleep": {
            "bg_color": "#1a1a2e",
            "text_color": "#8B5CF6",
            "accent_color": "#60A5FA",
            "font_size": 72,
            "layout": "center"
        },
        "meditation": {
            "bg_color": "#0f172a",
            "text_color": "#10B981",
            "accent_color": "#34D399",
            "font_size": 68,
            "layout": "center"
        },
        "focus": {
            "bg_color": "#1e1b4b",
            "text_color": "#F59E0B",
            "accent_color": "#FBBF24",
            "font_size": 70,
            "layout": "center"
        }
    }
    
    @classmethod
    def generate(cls, title: str, template: str = "sleep", output_path: str = None) -> str:
        """Generate a thumbnail using ffmpeg"""
        if output_path is None:
            output_path = str(EXPORTS_DIR / "thumbnail.jpg")
        
        template_data = cls.TEMPLATES.get(template, cls.TEMPLATES["sleep"])
        
        # Escape text for ffmpeg
        safe_title = title.replace("'", "\\'")[:50]  # Limit length
        
        # Create thumbnail with ffmpeg
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", f"color=c={template_data['bg_color'].replace('#', '')}:s=1280x720",
            "-vf",
            f"drawtext=text='{safe_title}':fontcolor={template_data['text_color']}:"
            f"fontsize={template_data['font_size']}:x=(w-text_w)/2:y=(h-text_h)/2:"
            f"fontfile=/System/Library/Fonts/Helvetica.ttc",
            "-frames:v", "1",
            output_path
        ]
        
        import subprocess
        subprocess.run(cmd, capture_output=True)
        
        return output_path


class RecommendationEngine:
    """Generate recommendations based on channel analysis"""
    
    @staticmethod
    def generate_title_suggestions(analysis: ChannelAnalysis) -> List[str]:
        """Generate title suggestions based on top performers"""
        suggestions = []
        
        if analysis.best_performing_video:
            best_title = analysis.best_performing_video.title
            
            # Extract patterns
            patterns = [
                (r"(\d+)\s*Hour", "duration"),
                (r"(Sleep|Relaxation|Meditation|Focus)", "category"),
                (r"(Delta|Theta|Alpha|Binaural)", "technique")
            ]
            
            found_patterns = {}
            for pattern, name in patterns:
                match = re.search(pattern, best_title, re.IGNORECASE)
                if match:
                    found_patterns[name] = match.group(1)
            
            # Generate variations
            if "duration" in found_patterns and "category" in found_patterns:
                base = f"{found_patterns['duration']} Hour {found_patterns['category']}"
                suggestions.extend([
                    f"{base} Music for Deep Rest",
                    f"{base} with Binaural Beats",
                    f"Instant {base}",
                    f"{base} - No Ads, Pure Audio"
                ])
        
        # Default suggestions
        if not suggestions:
            suggestions = [
                "8 Hour Deep Sleep Music with Delta Waves",
                "Meditation Music for Stress Relief and Relaxation",
                "Binaural Beats for Focus and Productivity",
                "Sleep Music: Fall Asleep in 10 Minutes"
            ]
        
        return suggestions
    
    @staticmethod
    def generate_description_template(analysis: ChannelAnalysis) -> str:
        """Generate an optimized description template"""
        template = """🎵 Welcome to {channel_name}

This {duration} track is designed to help you {benefit}.

✨ BENEFITS:
• Deep relaxation and calm
• Stress and anxiety relief  
• Improved sleep quality
• Mental clarity and focus

🧠 ABOUT THE AUDIO:
This track uses {technique} to entrain your brainwaves into a {state} state.

⏱️ TIMESTAMPS:
00:00 - Introduction
{timestamps}

💡 HOW TO USE:
1. Use headphones for best results
2. Set volume to a comfortable level
3. Let the music play as you {activity}

🔔 SUBSCRIBE for more {content_type} content

#SleepMusic #BinauralBeats #{hashtag} #Relaxation #Meditation
"""
        return template
    
    @staticmethod
    def generate_content_ideas(analysis: ChannelAnalysis) -> List[Dict]:
        """Generate content ideas based on gaps and opportunities"""
        ideas = []
        
        # Check what's missing
        has_sleep = any("sleep" in v.title.lower() for v in analysis.videos)
        has_meditation = any("meditation" in v.title.lower() for v in analysis.videos)
        has_focus = any("focus" in v.title.lower() for v in analysis.videos)
        
        if not has_sleep or analysis.optimal_video_length == "Long (2-8 hr)":
            ideas.append({
                "title": "8 Hour Deep Sleep Music - Delta Waves",
                "rationale": "Long-form sleep content performs well in your niche",
                "priority": "High"
            })
        
        if not has_meditation:
            ideas.append({
                "title": "10 Minute Meditation for Anxiety Relief",
                "rationale": "Short meditation content has high search volume",
                "priority": "Medium"
            })
        
        if not has_focus:
            ideas.append({
                "title": "Study Music: Alpha Waves for Concentration",
                "rationale": "Focus music appeals to students and professionals",
                "priority": "Medium"
            })
        
        ideas.append({
            "title": f"{analysis.optimal_video_length} - Your Sweet Spot",
            "rationale": f"Your data shows {analysis.optimal_video_length} videos perform best",
            "priority": "High"
        })
        
        return ideas


class AnalyzerWindow(QMainWindow):
    """Main window for Channel Analyzer"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FlowState Channel Analyzer v2.0")
        self.setMinimumSize(1200, 800)
        
        self.analysis: Optional[ChannelAnalysis] = None
        self.analyzer: Optional[ChannelAnalyzer] = None
        
        self.setup_ui()
        self.apply_theme()
    
    def setup_ui(self):
        """Build the user interface"""
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Sidebar
        sidebar = self._create_sidebar()
        layout.addWidget(sidebar)
        
        # Content
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                background-color: #0a0a0f;
                border: none;
            }
            QTabBar::tab {
                background-color: #1e1e2e;
                color: #9ca3af;
                padding: 12px 24px;
                border: none;
            }
            QTabBar::tab:selected {
                background-color: #8B5CF6;
                color: white;
            }
        """)
        
        # Analysis Tab
        self.tabs.addTab(self._create_analysis_tab(), "📊 Analysis")
        
        # Recommendations Tab
        self.tabs.addTab(self._create_recommendations_tab(), "💡 Recommendations")
        
        # Thumbnail Generator Tab
        self.tabs.addTab(self._create_thumbnail_tab(), "🎨 Thumbnails")
        
        layout.addWidget(self.tabs, 1)
    
    def _create_sidebar(self) -> QWidget:
        """Create the sidebar"""
        sidebar = QWidget()
        sidebar.setFixedWidth(280)
        sidebar.setStyleSheet("""
            QWidget {
                background-color: #12121a;
                border-right: 1px solid #1e1e2e;
            }
        """)
        
        layout = QVBoxLayout(sidebar)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 24, 20, 24)
        
        # Logo
        logo = QLabel("🔮 FlowState")
        logo.setStyleSheet("color: #8B5CF6; font-size: 24px; font-weight: bold;")
        layout.addWidget(logo)
        
        subtitle = QLabel("Channel Analyzer v2.0")
        subtitle.setStyleSheet("color: #6b7280; font-size: 12px;")
        layout.addWidget(subtitle)
        
        # Channel input
        channel_group = QGroupBox("Channel")
        channel_group.setStyleSheet("""
            QGroupBox {
                color: #8B5CF6;
                font-weight: 600;
                border: 1px solid #1e1e2e;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 12px;
            }
        """)
        channel_layout = QVBoxLayout(channel_group)
        
        self.channel_input = QLineEdit("https://youtube.com/@Mysticalmusic381")
        self.channel_input.setStyleSheet("""
            QLineEdit {
                background-color: #1e1e2e;
                color: #e8e8f0;
                border: 1px solid #2d2d3d;
                border-radius: 6px;
                padding: 10px;
            }
        """)
        channel_layout.addWidget(self.channel_input)
        
        # Data file input
        data_layout = QHBoxLayout()
        self.data_file_input = QLineEdit()
        self.data_file_input.setPlaceholderText("Optional: Path to channel data JSON")
        self.data_file_input.setStyleSheet(self.channel_input.styleSheet())
        
        browse_btn = QPushButton("📁")
        browse_btn.setFixedWidth(40)
        browse_btn.clicked.connect(self.browse_data_file)
        
        data_layout.addWidget(self.data_file_input)
        data_layout.addWidget(browse_btn)
        channel_layout.addLayout(data_layout)
        
        layout.addWidget(channel_group)
        
        # Analyze button
        self.analyze_btn = QPushButton("🔍 Analyze Channel")
        self.analyze_btn.setStyleSheet("""
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
        """)
        self.analyze_btn.clicked.connect(self.start_analysis)
        layout.addWidget(self.analyze_btn)
        
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
        self.status_label.setStyleSheet("color: #6b7280; font-size: 11px;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
        
        layout.addStretch()
        
        # Export button
        export_btn = QPushButton("📥 Export Report")
        export_btn.setStyleSheet("""
            QPushButton {
                background-color: #1e1e2e;
                color: #e8e8f0;
                padding: 12px;
                border: none;
                border-radius: 8px;
            }
        """)
        export_btn.clicked.connect(self.export_report)
        layout.addWidget(export_btn)
        
        return sidebar
    
    def _create_analysis_tab(self) -> QWidget:
        """Create the analysis results tab"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(20)
        layout.setContentsMargins(32, 32, 32, 32)
        
        # Header
        header = QLabel("Channel Performance")
        header.setStyleSheet("color: #e8e8f0; font-size: 28px; font-weight: 600;")
        layout.addWidget(header)
        
        # Metrics grid
        metrics = QWidget()
        metrics_layout = QGridLayout(metrics)
        metrics_layout.setSpacing(16)
        
        self.metric_labels = {}
        metric_data = [
            ("Subscribers", "0", "#8B5CF6"),
            ("Total Views", "0", "#10B981"),
            ("Avg Views/Video", "0", "#3B82F6"),
            ("Avg Engagement", "0%", "#F59E0B"),
        ]
        
        for i, (label, value, color) in enumerate(metric_data):
            card = QFrame()
            card.setStyleSheet(f"""
                QFrame {{
                    background-color: #1e1e2e;
                    border-radius: 12px;
                    padding: 20px;
                }}
            """)
            card_layout = QVBoxLayout(card)
            
            title = QLabel(label)
            title.setStyleSheet("color: #6b7280; font-size: 12px;")
            
            value_label = QLabel(value)
            value_label.setStyleSheet(f"color: {color}; font-size: 32px; font-weight: bold;")
            
            card_layout.addWidget(title)
            card_layout.addWidget(value_label)
            
            metrics_layout.addWidget(card, i // 2, i % 2)
            self.metric_labels[label] = value_label
        
        layout.addWidget(metrics)
        
        # Best performing video
        best_group = QGroupBox("🏆 Best Performing Video")
        best_group.setStyleSheet("""
            QGroupBox {
                color: #10B981;
                font-weight: 600;
                border: 1px solid #1e1e2e;
                border-radius: 8px;
                padding-top: 12px;
            }
        """)
        best_layout = QVBoxLayout(best_group)
        
        self.best_video_label = QLabel("No analysis yet")
        self.best_video_label.setStyleSheet("color: #e8e8f0;")
        self.best_video_label.setWordWrap(True)
        best_layout.addWidget(self.best_video_label)
        
        layout.addWidget(best_group)
        
        # Content patterns
        patterns_group = QGroupBox("📈 Content Patterns")
        patterns_group.setStyleSheet(best_group.styleSheet().replace("#10B981", "#3B82F6"))
        patterns_layout = QVBoxLayout(patterns_group)
        
        self.patterns_label = QLabel("Run analysis to see patterns")
        self.patterns_label.setStyleSheet("color: #e8e8f0;")
        patterns_layout.addWidget(self.patterns_label)
        
        layout.addWidget(patterns_group)
        
        layout.addStretch()
        return page
    
    def _create_recommendations_tab(self) -> QWidget:
        """Create the recommendations tab"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(20)
        layout.setContentsMargins(32, 32, 32, 32)
        
        # Header
        header = QLabel("AI Recommendations")
        header.setStyleSheet("color: #e8e8f0; font-size: 28px; font-weight: 600;")
        layout.addWidget(header)
        
        # Title suggestions
        titles_group = QGroupBox("📝 Title Suggestions")
        titles_group.setStyleSheet("""
            QGroupBox {
                color: #8B5CF6;
                font-weight: 600;
                border: 1px solid #1e1e2e;
                border-radius: 8px;
                padding-top: 12px;
            }
        """)
        titles_layout = QVBoxLayout(titles_group)
        
        self.titles_list = QListWidget()
        self.titles_list.setStyleSheet("""
            QListWidget {
                background-color: #1e1e2e;
                color: #e8e8f0;
                border: none;
                border-radius: 6px;
                padding: 8px;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #2d2d3d;
            }
        """)
        titles_layout.addWidget(self.titles_list)
        
        layout.addWidget(titles_group)
        
        # Content ideas
        ideas_group = QGroupBox("💡 Content Ideas")
        ideas_group.setStyleSheet(titles_group.styleSheet())
        ideas_layout = QVBoxLayout(ideas_group)
        
        self.ideas_list = QListWidget()
        self.ideas_list.setStyleSheet(self.titles_list.styleSheet())
        ideas_layout.addWidget(self.ideas_list)
        
        layout.addWidget(ideas_group)
        
        # Description template
        desc_group = QGroupBox("📄 Description Template")
        desc_group.setStyleSheet(titles_group.styleSheet())
        desc_layout = QVBoxLayout(desc_group)
        
        self.desc_template = QTextEdit()
        self.desc_template.setReadOnly(True)
        self.desc_template.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e2e;
                color: #e8e8f0;
                border: none;
                border-radius: 6px;
                padding: 12px;
            }
        """)
        desc_layout.addWidget(self.desc_template)
        
        copy_desc_btn = QPushButton("📋 Copy to Clipboard")
        copy_desc_btn.clicked.connect(lambda: self.copy_to_clipboard(self.desc_template.toPlainText()))
        desc_layout.addWidget(copy_desc_btn)
        
        layout.addWidget(desc_group)
        
        layout.addStretch()
        return page
    
    def _create_thumbnail_tab(self) -> QWidget:
        """Create the thumbnail generator tab"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(20)
        layout.setContentsMargins(32, 32, 32, 32)
        
        # Header
        header = QLabel("Thumbnail Generator")
        header.setStyleSheet("color: #e8e8f0; font-size: 28px; font-weight: 600;")
        layout.addWidget(header)
        
        # Title input
        title_layout = QHBoxLayout()
        title_label = QLabel("Video Title:")
        title_label.setStyleSheet("color: #9ca3af;")
        
        self.thumb_title = QLineEdit()
        self.thumb_title.setPlaceholderText("Enter video title...")
        self.thumb_title.setStyleSheet("""
            QLineEdit {
                background-color: #1e1e2e;
                color: #e8e8f0;
                border: 1px solid #2d2d3d;
                border-radius: 6px;
                padding: 10px;
            }
        """)
        
        title_layout.addWidget(title_label)
        title_layout.addWidget(self.thumb_title, 1)
        layout.addLayout(title_layout)
        
        # Template selection
        template_layout = QHBoxLayout()
        template_label = QLabel("Template:")
        template_label.setStyleSheet("color: #9ca3af;")
        
        self.thumb_template = QComboBox()
        self.thumb_template.addItem("🌙 Sleep", "sleep")
        self.thumb_template.addItem("🧘 Meditation", "meditation")
        self.thumb_template.addItem("🎯 Focus", "focus")
        self.thumb_template.setStyleSheet("""
            QComboBox {
                background-color: #1e1e2e;
                color: #e8e8f0;
                border: 1px solid #2d2d3d;
                border-radius: 6px;
                padding: 8px;
            }
        """)
        
        template_layout.addWidget(template_label)
        template_layout.addWidget(self.thumb_template)
        template_layout.addStretch()
        layout.addLayout(template_layout)
        
        # Generate button
        gen_btn = QPushButton("🎨 Generate Thumbnail")
        gen_btn.setStyleSheet("""
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
        """)
        gen_btn.clicked.connect(self.generate_thumbnail)
        layout.addWidget(gen_btn)
        
        # Preview area
        preview_label = QLabel("Thumbnail Preview:")
        preview_label.setStyleSheet("color: #9ca3af;")
        layout.addWidget(preview_label)
        
        self.thumb_preview = QLabel("No thumbnail generated yet")
        self.thumb_preview.setStyleSheet("""
            QLabel {
                background-color: #1e1e2e;
                border-radius: 8px;
                padding: 20px;
                color: #6b7280;
                min-height: 200px;
            }
        """)
        self.thumb_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.thumb_preview)
        
        layout.addStretch()
        return page
    
    def apply_theme(self):
        """Apply dark theme"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #0a0a0f;
            }
            QWidget {
                font-family: -apple-system, BlinkMacSystemFont, sans-serif;
            }
        """)
    
    def browse_data_file(self):
        """Browse for channel data file"""
        file, _ = QFileDialog.getOpenFileName(
            self, "Select Channel Data", str(Path.home()),
            "JSON Files (*.json)"
        )
        if file:
            self.data_file_input.setText(file)
    
    def start_analysis(self):
        """Start channel analysis"""
        self.analyze_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.status_label.setText("Analyzing...")
        
        self.analyzer = ChannelAnalyzer(
            self.channel_input.text(),
            self.data_file_input.text() or None
        )
        self.analyzer.progress.connect(self.update_progress)
        self.analyzer.finished.connect(self.analysis_complete)
        self.analyzer.error.connect(self.analysis_error)
        self.analyzer.start()
    
    def update_progress(self, msg, pct):
        """Update progress"""
        self.status_label.setText(msg)
        self.progress.setValue(pct)
    
    def analysis_complete(self, analysis: ChannelAnalysis):
        """Handle analysis completion"""
        self.analysis = analysis
        self.progress.setValue(100)
        self.status_label.setText("Analysis complete!")
        
        # Update metrics
        self.metric_labels["Subscribers"].setText(f"{analysis.subscriber_count:,}")
        self.metric_labels["Total Views"].setText(f"{analysis.total_views:,}")
        self.metric_labels["Avg Views/Video"].setText(f"{int(analysis.avg_views):,}")
        self.metric_labels["Avg Engagement"].setText(f"{analysis.avg_engagement:.2f}%")
        
        # Update best video
        if analysis.best_performing_video:
            bv = analysis.best_performing_video
            self.best_video_label.setText(
                f"📹 {bv.title}\n"
                f"👁️ {bv.view_count:,} views | "
                f"👍 {bv.like_count} likes | "
                f"💬 {bv.comment_count} comments"
            )
        
        # Update patterns
        patterns_text = f"""
        🎯 Optimal Video Length: {analysis.optimal_video_length}
        
        🔤 Common Words in Titles:
        {', '.join(f"{word} ({count})" for word, count in analysis.common_words_in_titles[:5])}
        """
        self.patterns_label.setText(patterns_text)
        
        # Generate recommendations
        self.generate_recommendations(analysis)
        
        self.analyze_btn.setEnabled(True)
    
    def generate_recommendations(self, analysis: ChannelAnalysis):
        """Generate and display recommendations"""
        # Title suggestions
        titles = RecommendationEngine.generate_title_suggestions(analysis)
        self.titles_list.clear()
        for title in titles:
            item = QListWidgetItem(title)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsSelectable)
            self.titles_list.addItem(item)
        
        # Content ideas
        ideas = RecommendationEngine.generate_content_ideas(analysis)
        self.ideas_list.clear()
        for idea in ideas:
            text = f"{idea['priority']} Priority: {idea['title']}\n   {idea['rationale']}"
            item = QListWidgetItem(text)
            self.ideas_list.addItem(item)
        
        # Description template
        template = RecommendationEngine.generate_description_template(analysis)
        self.desc_template.setText(template)
    
    def analysis_error(self, error_msg: str):
        """Handle analysis error"""
        self.progress.setVisible(False)
        self.status_label.setText("Error occurred")
        QMessageBox.critical(self, "Error", error_msg)
        self.analyze_btn.setEnabled(True)
    
    def generate_thumbnail(self):
        """Generate thumbnail"""
        title = self.thumb_title.text() or "Sample Title"
        template = self.thumb_template.currentData()
        
        output_path = str(EXPORTS_DIR / f"thumbnail_{template}.jpg")
        
        try:
            ThumbnailGenerator.generate(title, template, output_path)
            self.thumb_preview.setText(f"✅ Thumbnail saved to:\n{output_path}")
            
            # Open the thumbnail
            import subprocess
            subprocess.run(["open", output_path])
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate thumbnail:\n{str(e)}")
    
    def copy_to_clipboard(self, text: str):
        """Copy text to clipboard"""
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        QMessageBox.information(self, "Copied", "Text copied to clipboard!")
    
    def export_report(self):
        """Export analysis report"""
        if not self.analysis:
            QMessageBox.warning(self, "No Data", "Please run analysis first")
            return
        
        filename = ANALYSIS_DIR / f"channel_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        report = f"""CHANNEL ANALYSIS REPORT
{'='*60}
Channel: {self.analysis.channel_name}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

PERFORMANCE METRICS
{'='*60}
Subscribers: {self.analysis.subscriber_count:,}
Total Views: {self.analysis.total_views:,}
Total Videos: {self.analysis.total_videos}
Average Views/Video: {int(self.analysis.avg_views):,}
Average Engagement: {self.analysis.avg_engagement:.2f}%

BEST PERFORMING VIDEO
{'='*60}
{self.analysis.best_performing_video.title if self.analysis.best_performing_video else 'N/A'}
Views: {self.analysis.best_performing_video.view_count if self.analysis.best_performing_video else 0:,}

CONTENT PATTERNS
{'='*60}
Optimal Video Length: {self.analysis.optimal_video_length}
Common Words: {', '.join(word for word, _ in self.analysis.common_words_in_titles[:5])}

RECOMMENDATIONS
{'='*60}
{self.desc_template.toPlainText()}

---
Generated by FlowState Channel Analyzer v2.0
"""
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(report)
        
        QMessageBox.information(self, "Report Exported", f"Report saved to:\n{filename}")


def main():
    app = QApplication(sys.argv)
    window = AnalyzerWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
