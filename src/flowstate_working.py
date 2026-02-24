#!/usr/bin/env python3
"""
FlowState Audio - WORKING VERSION
Tested and verified audio pipeline
"""

import os
import sys
import subprocess
import json
import shutil
from pathlib import Path

def check_ffmpeg():
    """Verify ffmpeg is installed"""
    try:
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, timeout=5)
        return result.returncode == 0
    except:
        return False

def get_duration(filepath):
    """Get audio file duration"""
    cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'json', filepath]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return float(json.loads(result.stdout)['format']['duration'])

def process_audio(input_files, output_name="output", hours=8, preset="delta"):
    """Process audio files into sleep track"""
    
    if not check_ffmpeg():
        print("❌ ERROR: ffmpeg not installed. Run: brew install ffmpeg")
        return None
    
    # Presets
    presets = {
        "delta": {"base": 200, "beat": 2.5, "name": "Deep Sleep"},
        "theta": {"base": 200, "beat": 6.0, "name": "Meditation"},
        "alpha": {"base": 200, "beat": 10.0, "name": "Focus"}
    }
    
    p = presets.get(preset, presets["delta"])
    
    print(f"🎵 FlowState Audio - Processing {len(input_files)} file(s)")
    print(f"⏱️  Target: {hours} hours | Preset: {p['name']}")
    print("-" * 50)
    
    # Create temp directory
    temp_dir = Path("/tmp/flowstate_working")
    temp_dir.mkdir(exist_ok=True)
    
    try:
        # Step 1: Concatenate files
        print("📁 Step 1: Building sequence...")
        durations = []
        for f in input_files:
            durations.append(get_duration(f))
        
        total_duration = sum(durations)
        print(f"   Audio length: {total_duration/60:.1f} minutes")
        
        # Concatenate
        seq_file = temp_dir / "sequence.wav"
        if len(input_files) == 1:
            shutil.copy(input_files[0], seq_file)
        else:
            concat_list = temp_dir / "concat.txt"
            with open(concat_list, 'w') as f:
                for filepath in input_files:
                    f.write(f"file '{filepath}'\n")
            
            subprocess.run([
                'ffmpeg', '-y', '-f', 'concat', '-safe', '0',
                '-i', str(concat_list), '-c:a', 'pcm_s16le', str(seq_file)
            ], capture_output=True, check=True)
        
        # Step 2: Generate binaural beats
        print("🧠 Step 2: Generating binaural beats...")
        binaural_file = temp_dir / "binaural.wav"
        
        subprocess.run([
            'ffmpeg', '-y', '-f', 'lavfi',
            '-i', f'sine=frequency={p["base"]}:sample_rate=48000',
            '-f', 'lavfi', '-i', f'sine=frequency={p["base"]+p["beat"]}:sample_rate=48000',
            '-filter_complex', '[0:a][1:a]join=inputs=2:channel_layout=stereo',
            '-t', str(total_duration), '-c:a', 'pcm_s16le', str(binaural_file)
        ], capture_output=True, check=True)
        
        # Step 3: Mix
        print("🎚️  Step 3: Mixing audio...")
        mixed_file = temp_dir / "mixed.wav"
        
        subprocess.run([
            'ffmpeg', '-y', '-i', str(seq_file), '-i', str(binaural_file),
            '-filter_complex', '[1:a]volume=-20dB[b];[0:a][b]amix=2',
            '-c:a', 'pcm_s16le', str(mixed_file)
        ], capture_output=True, check=True)
        
        # Step 4: Loop if needed
        target_duration = hours * 3600
        final_audio = mixed_file
        
        if total_duration < target_duration:
            print(f"🔄 Step 4: Looping to {hours} hours...")
            looped_file = temp_dir / "looped.wav"
            loops = int(target_duration / total_duration) + 1
            
            subprocess.run([
                'ffmpeg', '-y', '-stream_loop', str(loops),
                '-i', str(mixed_file), '-t', str(target_duration),
                '-c:a', 'pcm_s16le', str(looped_file)
            ], capture_output=True, check=True)
            
            final_audio = looped_file
            final_duration = target_duration
        else:
            final_duration = total_duration
        
        # Step 5: Export
        print("💾 Step 5: Exporting files...")
        
        # Get output directory
        output_dir = Path.home() / "Desktop" / "FlowState Exports"
        # Fallback if Desktop doesn't exist
        if not (Path.home() / "Desktop").exists():
            output_dir = Path.home() / "FlowState Exports"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Export audio
        audio_out = output_dir / f"{output_name}_master.wav"
        shutil.copy(final_audio, audio_out)
        print(f"   ✅ Audio: {audio_out}")
        
        # Export video
        video_out = output_dir / f"{output_name}.mp4"
        subprocess.run([
            'ffmpeg', '-y', '-f', 'lavfi', '-i', 'color=c=black:s=1920x1080:r=30',
            '-i', str(final_audio), '-t', str(final_duration),
            '-c:v', 'libx264', '-c:a', 'aac', '-b:a', '192k', '-shortest',
            str(video_out)
        ], capture_output=True, check=True)
        print(f"   ✅ Video: {video_out}")
        
        print("-" * 50)
        print(f"✨ Complete! Files saved to: {output_dir}")
        
        return {
            'audio': str(audio_out),
            'video': str(video_out),
            'duration': final_duration
        }
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None
    
    finally:
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='FlowState Audio - Create sleep/meditation tracks')
    parser.add_argument('files', nargs='+', help='Input audio files')
    parser.add_argument('--name', '-n', default='MyTrack', help='Output name')
    parser.add_argument('--hours', '-t', type=float, default=8, help='Target duration in hours')
    parser.add_argument('--preset', '-p', default='delta', choices=['delta', 'theta', 'alpha'],
                       help='Binaural preset')
    
    args = parser.parse_args()
    
    # Validate files
    for f in args.files:
        if not os.path.exists(f):
            print(f"❌ File not found: {f}")
            return
    
    # Process
    result = process_audio(args.files, args.name, args.hours, args.preset)
    
    if result:
        print(f"\n🎵 Finished! Duration: {result['duration']/3600:.1f} hours")
        sys.exit(0)
    else:
        print("\n❌ Processing failed")
        sys.exit(1)


if __name__ == '__main__':
    main()
