#!/usr/bin/env python3
"""
FlowState Diagnostic Tool
Tests each component to identify issues
"""

import sys
import subprocess
import os
from pathlib import Path

print("=" * 60)
print("FlowState Diagnostic Tool")
print("=" * 60)

# Test 1: Python version
print("\n1. Python Version:")
print(f"   {sys.version}")

# Test 2: Check ffmpeg
print("\n2. Checking ffmpeg:")
try:
    result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, timeout=5)
    if result.returncode == 0:
        version = result.stdout.split('\n')[0]
        print(f"   ✓ {version}")
    else:
        print("   ✗ ffmpeg not working properly")
except Exception as e:
    print(f"   ✗ ffmpeg error: {e}")

# Test 3: Check PyQt6
print("\n3. Checking PyQt6:")
try:
    from PyQt6.QtWidgets import QApplication, QLabel
    from PyQt6.QtCore import Qt
    print("   ✓ PyQt6 imported successfully")
    
    # Try to create a minimal app
    app = QApplication.instance() or QApplication(sys.argv)
    label = QLabel("Test")
    print("   ✓ PyQt6 widgets work")
except Exception as e:
    print(f"   ✗ PyQt6 error: {e}")

# Test 4: Check write permissions
print("\n4. Checking write permissions:")
test_paths = [
    Path.home() / "Desktop",
    Path.home() / "Desktop" / "FlowState Exports",
    Path(tempfile.gettempdir())
]
for path in test_paths:
    try:
        path.mkdir(exist_ok=True)
        test_file = path / ".test_write"
        test_file.write_text("test")
        test_file.unlink()
        print(f"   ✓ {path}")
    except Exception as e:
        print(f"   ✗ {path}: {e}")

# Test 5: Test audio file analysis
print("\n5. Testing audio analysis:")
# Create a test audio file
try:
    import tempfile
    test_audio = Path(tempfile.gettempdir()) / "test_audio.wav"
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=1000:duration=1",
        "-c:a", "pcm_s16le", str(test_audio)
    ], capture_output=True, check=True)
    
    # Try to analyze it
    result = subprocess.run([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "json", str(test_audio)
    ], capture_output=True, text=True, check=True)
    
    import json
    data = json.loads(result.stdout)
    duration = float(data['format']['duration'])
    print(f"   ✓ Audio analysis works (test file: {duration}s)")
    
    test_audio.unlink()
except Exception as e:
    print(f"   ✗ Audio analysis failed: {e}")

print("\n" + "=" * 60)
print("Diagnostic complete. Check for ✗ marks above.")
print("=" * 60)
