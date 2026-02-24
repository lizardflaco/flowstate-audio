#!/bin/bash
# Build FlowState Audio macOS App
# This script creates a standalone .app bundle

set -e

echo "🏗️  Building FlowState Audio..."

# Paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_DIR="$SCRIPT_DIR/src"
BUILD_DIR="$SCRIPT_DIR/build"
APP_NAME="FlowState"
APP_BUNDLE="$BUILD_DIR/$APP_NAME.app"

# Clean previous build
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

echo "📦 Installing dependencies..."

# Check for Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3."
    exit 1
fi

# Create virtual environment
python3 -m venv "$BUILD_DIR/venv"
source "$BUILD_DIR/venv/bin/activate"

# Install dependencies
pip install -q PyQt6 py2app numpy

echo "🔨 Building app bundle..."

# Create setup.py for py2app
cat > "$BUILD_DIR/setup.py" << 'EOF'
from setuptools import setup

APP = ['../src/FlowState.py']
DATA_FILES = []
OPTIONS = {
    'argv_emulation': True,
    'packages': ['PyQt6'],
    'includes': ['numpy'],
    'excludes': ['tkinter', 'matplotlib', 'PIL'],
    'plist': {
        'CFBundleName': 'FlowState Audio',
        'CFBundleShortVersionString': '1.0.0',
        'CFBundleVersion': '1.0.0',
        'CFBundleIdentifier': 'ai.kimiclaw.flowstate',
        'NSHumanReadableCopyright': '© 2025 Kimi Claw for Jud Smith',
        'LSMinimumSystemVersion': '10.14',
        'NSRequiresAquaSystemAppearance': False,
    },
    'iconfile': '../src/icon.icns' if os.path.exists('../src/icon.icns') else None,
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
EOF

# Build the app
cd "$BUILD_DIR"
python setup.py py2app --dist-dir . --bdist-base build_temp > /dev/null 2>&1

# Check if build succeeded
if [ ! -d "$APP_BUNDLE" ]; then
    echo "❌ Build failed. Trying alternative method..."
    
    # Alternative: Create app structure manually
    mkdir -p "$APP_BUNDLE/Contents/MacOS"
    mkdir -p "$APP_BUNDLE/Contents/Resources"
    
    # Copy Python files
    cp "$SRC_DIR/FlowState.py" "$APP_BUNDLE/Contents/MacOS/FlowState"
    chmod +x "$APP_BUNDLE/Contents/MacOS/FlowState"
    
    # Create Info.plist
    cat > "$APP_BUNDLE/Contents/Info.plist" << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>
    <string>FlowState Audio</string>
    <key>CFBundleDisplayName</key>
    <string>FlowState Audio</string>
    <key>CFBundleIdentifier</key>
    <string>ai.kimiclaw.flowstate</string>
    <key>CFBundleVersion</key>
    <string>1.0.0</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0.0</string>
    <key>CFBundleExecutable</key>
    <string>FlowState</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.14</string>
    <key>NSHumanReadableCopyright</key>
    <string>© 2025 Kimi Claw for Jud Smith</string>
</dict>
</plist>
EOF
    
    # Create launcher script
    cat > "$APP_BUNDLE/Contents/MacOS/FlowState" << EOF
#!/bin/bash
DIR="\$(cd "\$(dirname "\$0")" && pwd)"
cd "\$DIR"

# Check for ffmpeg
if ! command -v ffmpeg &> /dev/null; then
    osascript -e 'display dialog "ffmpeg is required but not installed.\n\nInstall it with:\nbrew install ffmpeg" buttons {"OK"} default button "OK" with icon stop'
    exit 1
fi

# Run the app
exec python3 "\$DIR/FlowState.py" "\$@"
EOF
    chmod +x "$APP_BUNDLE/Contents/MacOS/FlowState"
    cp "$SRC_DIR/FlowState.py" "$APP_BUNDLE/Contents/MacOS/FlowState.py"
fi

# Create DMG
echo "💿 Creating DMG..."

DMG_NAME="FlowState-Audio-v1.0.0.dmg"
DMG_PATH="$SCRIPT_DIR/$DMG_NAME"

# Create temporary directory for DMG contents
DMG_TEMP=$(mktemp -d)
cp -R "$APP_BUNDLE" "$DMG_TEMP/"

# Create Applications symlink
ln -s /Applications "$DMG_TEMP/Applications"

# Create README
cat > "$DMG_TEMP/README.txt" <> 'EOF'
FlowState Audio v1.0.0
======================

Requirements:
- macOS 10.14 or later
- ffmpeg (install with: brew install ffmpeg)

Installation:
1. Drag FlowState.app to your Applications folder
2. Make sure ffmpeg is installed
3. Launch FlowState from Applications

Exports will be saved to: ~/Desktop/FlowState Exports/

Built with ❤️‍🔥 for Jud Smith
EOF

# Create the DMG
hdiutil create -volname "FlowState Audio" -srcfolder "$DMG_TEMP" -ov -format UDZO "$DMG_PATH" > /dev/null 2>&1

# Cleanup
rm -rf "$DMG_TEMP"
rm -rf "$BUILD_DIR"

echo ""
echo "✅ Build complete!"
echo ""
echo "📦 Installer: $DMG_PATH"
echo ""
echo "To install:"
echo "  1. Double-click $DMG_NAME"
echo "  2. Drag FlowState.app to Applications"
echo "  3. Launch from Applications folder"
