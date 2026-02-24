#!/bin/bash
# FlowState Audio - Quick Setup for Jud
# This script handles all the setup automatically

set -e

echo "🎵 FlowState Audio Setup"
echo "========================"

# Check if we're in the right directory
if [ ! -f "src/FlowState.py" ]; then
    echo "❌ Error: Please run this from the flowstate-gui folder"
    exit 1
fi

# Create virtual environment
echo "📦 Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -q PyQt6 numpy

# Check for ffmpeg
if ! command -v ffmpeg &> /dev/null; then
    echo ""
    echo "⚠️  ffmpeg not found!"
    echo "Please install it: brew install ffmpeg"
    echo ""
    read -p "Press Enter to continue anyway (app won't work without ffmpeg)..."
fi

# Create exports directory
mkdir -p ~/Desktop/FlowState\ Exports

echo ""
echo "✅ Setup complete!"
echo ""
echo "🚀 Starting FlowState Audio..."
echo ""

# Run the app
python3 src/FlowState.py
