"""
Generate a simple test audio file for BPM-X testing
"""

import numpy as np
import soundfile as sf
from pathlib import Path

def generate_test_audio(filename: str, bpm: int = 120, duration: float = 10.0):
    """
    Generate a simple test audio file with click track at specified BPM.
    
    Args:
        filename: Output filename
        bpm: Beats per minute
        duration: Duration in seconds
    """
    sr = 44100  # Sample rate
    
    # Calculate beat duration in samples
    beat_duration = sr * 60 / bpm  # Samples per beat
    
    # Create audio
    num_samples = int(sr * duration)
    audio = np.zeros(num_samples)
    
    # Add click track (metronome-like beats)
    click_freq = 1000  # Hz
    click_duration = 0.1  # seconds
    click_samples = int(sr * click_duration)
    
    # Generate click tone
    t = np.arange(click_samples) / sr
    click = np.sin(2 * np.pi * click_freq * t)
    # Fade out click
    fade = np.linspace(1, 0, click_samples)
    click = click * fade * 0.5
    
    # Place clicks at beat intervals
    beat_idx = 0
    idx = 0
    while idx + click_samples < num_samples:
        audio[idx:idx + click_samples] += click
        idx += int(beat_duration)
        beat_idx += 1
    
    # Add some bass sine wave (60 Hz, like a bass note)
    t_full = np.arange(num_samples) / sr
    bass = np.sin(2 * np.pi * 60 * t_full) * 0.3
    audio = audio + bass
    
    # Normalize
    audio = audio / (np.max(np.abs(audio)) + 0.001)
    
    # Save
    sf.write(filename, audio, sr)
    print(f"✓ Generated test audio: {filename} ({duration}s at {bpm} BPM)")
    return filename


if __name__ == '__main__':
    # Generate test files
    Path('data/workspace').mkdir(parents=True, exist_ok=True)
    
    generate_test_audio('data/workspace/test_120bpm.wav', bpm=120, duration=5)
    generate_test_audio('data/workspace/test_128bpm.wav', bpm=128, duration=5)
    print("\n✓ Test files created in data/workspace/")
