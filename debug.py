"""
Debug script to test BPM-X core components
"""

import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path.cwd()))

print("=" * 60)
print("BPM-X DEBUG & TEST")
print("=" * 60)

# Test 1: Import core modules
print("\n[TEST 1] Importing core modules...")
try:
    from core.engine import BPMDetector, KeyDetector, AudioAnalyzer
    print("✓ Core modules imported successfully")
except Exception as e:
    print(f"✗ Failed to import core modules: {e}")
    sys.exit(1)

# Test 2: Import translator
print("\n[TEST 2] Importing translator...")
try:
    from core.translator import KeyTranslator
    print("✓ Translator imported successfully")
except Exception as e:
    print(f"✗ Failed to import translator: {e}")
    sys.exit(1)

# Test 3: Test KeyTranslator
print("\n[TEST 3] Testing KeyTranslator...")
try:
    translator = KeyTranslator()
    
    # Test conversion
    camelot = translator.to_camelot("D Minor")
    print(f"  'D Minor' -> '{camelot}'")
    assert camelot == "7A", f"Expected '7A', got '{camelot}'"
    
    camelot = translator.to_camelot("C Major")
    print(f"  'C Major' -> '{camelot}'")
    assert camelot == "8B", f"Expected '8B', got '{camelot}'"
    
    # Test reverse
    key = translator.from_camelot("8A")
    print(f"  '8A' -> '{key}'")
    assert key == "A Minor", f"Expected 'A Minor', got '{key}'"
    
    print("✓ KeyTranslator working correctly")
except Exception as e:
    print(f"✗ KeyTranslator test failed: {e}")
    sys.exit(1)

# Test 4: Import meta_tagger
print("\n[TEST 4] Importing metadata tagger...")
try:
    from modules.meta_tagger import MetaTagger
    print("✓ MetaTagger imported successfully")
except Exception as e:
    print(f"✗ Failed to import MetaTagger: {e}")
    sys.exit(1)

# Test 5: Import file organizer
print("\n[TEST 5] Importing file organizer...")
try:
    from modules.file_auto import FileOrganizer
    print("✓ FileOrganizer imported successfully")
except Exception as e:
    print(f"✗ Failed to import FileOrganizer: {e}")
    sys.exit(1)

# Test 6: Check if test files exist
print("\n[TEST 6] Checking test audio files...")
test_files = [
    "data/workspace/test_120bpm.wav",
    "data/workspace/test_128bpm.wav"
]
for file in test_files:
    if Path(file).exists():
        size = Path(file).stat().st_size
        print(f"✓ {file} ({size} bytes)")
    else:
        print(f"✗ {file} NOT FOUND")

# Test 7: Try to analyze a test file (with timeout)
print("\n[TEST 7] Testing audio analysis (short timeout)...")
print("  Note: This may take 15-30 seconds...")

test_file = "data/workspace/test_120bpm.wav"
if Path(test_file).exists():
    try:
        print(f"  Analyzing {test_file}...")
        
        # Create simple detector
        detector = BPMDetector()
        bpm, metadata = detector.detect(test_file)
        
        print(f"  ✓ BPM detected: {bpm:.1f}")
        print(f"    Confidence: {metadata.get('confidence', 'N/A')}")
        print(f"    Duration: {metadata.get('duration_seconds', 'N/A')}s")
        
    except Exception as e:
        print(f"  ✗ Analysis failed: {e}")
        import traceback
        traceback.print_exc()
else:
    print(f"  ✗ Test file not found: {test_file}")

# Test 8: Config loader
print("\n[TEST 8] Testing config loader...")
try:
    from utils.config_loader import ConfigLoader
    config = ConfigLoader()
    lib_path = config.get('library_path')
    print(f"✓ Config loaded. Library path: {lib_path}")
except Exception as e:
    print(f"✗ Config loader failed: {e}")

print("\n" + "=" * 60)
print("DEBUG TESTS COMPLETE")
print("=" * 60)
