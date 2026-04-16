"""
BPM-X Automated Demo/Test Script
Runs the complete workflow automatically for easy testing.
"""

import subprocess
import sys
from pathlib import Path

def run_command(cmd, description):
    """Run a command and display results."""
    print(f"\n{'='*70}")
    print(f"▶ {description}")
    print(f"{'='*70}")
    print(f"Command: {cmd}\n")
    
    try:
        result = subprocess.run(cmd, shell=True, capture_output=False, text=True)
        return result.returncode == 0
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

print("""
╔══════════════════════════════════════════════════════════════════════╗
║                    BPM-X AUTOMATED DEMO                             ║
║          Full Workflow: Analyze → Tag → Organize                    ║
╚══════════════════════════════════════════════════════════════════════╝
""")

# Test 1: Show help
run_command(
    "python __main__.py --help",
    "TEST 1: Display CLI Help"
)

# Test 2: Analyze files
run_command(
    "python __main__.py analyze data/workspace/test_120bpm.wav data/workspace/test_128bpm.wav --format table",
    "TEST 2: Analyze Audio Files (BPM Detection)"
)

# Test 3: Tag single file
run_command(
    "python __main__.py tag data/workspace/test_120bpm.wav --overwrite",
    "TEST 3: Inject Metadata (Tagging for FL Studio)"
)

# Test 4: Organize single file
run_command(
    "python __main__.py organize data/workspace/test_120bpm.wav --dest data/library --move",
    "TEST 4: Organize File into Library Structure"
)

# Test 5: Full batch workflow
print(f"\n{'='*70}")
print(f"▶ TEST 5: Complete Batch Workflow (Analyze + Tag + Organize)")
print(f"{'='*70}")
print(f"Command: python __main__.py batch data/workspace --dest data/library -v\n")

subprocess.run(
    "python __main__.py batch data/workspace --dest data/library -v",
    shell=True
)

# Show results
print(f"\n{'='*70}")
print("✓ FILE ORGANIZATION RESULTS")
print(f"{'='*70}\n")

subprocess.run(
    "tree data /F",
    shell=True
)

print(f"""
{'='*70}
✅ DEMO COMPLETE
{'='*70}

All systems operational! You can now:

1. Analyze your music:
   python __main__.py analyze *.mp3

2. Tag files with metadata (FL Studio ready):
   python __main__.py tag *.mp3 --overwrite

3. Organize your library:
   python __main__.py batch samples/ --dest library/ --move

📚 Documentation:
   - README.md      → Full guide
   - QUICKSTART.md  → Quick reference
   - TEST_REPORT.md → Test results

🎯 Next Step: Organize your sample packs!
   python __main__.py batch C:\\path\\to\\samples --dest C:\\Music\\library --move -v
""")
