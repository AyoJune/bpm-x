# BPM-X Quick Start Guide

## Installation (2 minutes)

```bash
cd c:\Projects\bpm-x

# Create virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## First Run (3 examples)

### 1️⃣ Analyze a Track
```bash
# Detect BPM and Key from MP3
python -m bpm_x analyze C:\Path\To\track.mp3

# Expected output:
# File: track.mp3
#   BPM: 128.5
#   Key: D Minor
#   Confidence (BPM): 0.89
#   Confidence (Key): 0.76
```

### 2️⃣ Tag Your Files
```bash
# Auto-detect BPM/Key and inject metadata
python -m bpm_x tag *.mp3
```

### 3️⃣ Organize Sample Pack
```bash
# Sort sample pack by BPM/Camelot (8A, 8B, 9A, etc)
python -m bpm_x batch C:\samples\pack \
  --dest C:\Music\library \
  --move

# Result:
# library\
# ├── 8/
# │   ├── 128 - 8A - kick.mp3
# │   ├── 128 - 8A - bass.mp3
# │   └── 130 - 8B - synth.mp3
# └── 9/
#     └── 128 - 9A - snare.mp3
```

## Command Reference (Copy & Paste)

```bash
# ANALYZE - Detect BPM/Key
python -m bpm_x analyze file.mp3

# TAG - Inject metadata
python -m bpm_x tag *.mp3 --overwrite

# ORGANIZE - Sort into library
python -m bpm_x organize file.mp3 --dest data/library --move

# BATCH - Full workflow (analyze + tag + organize)
python -m bpm_x batch C:\samples --dest C:\Music\lib --move -v
```

## Metadata Verification Steps

1. **Run BPM-X on your samples:**
   ```bash
   python -m bpm_x batch C:\samples --move
   ```

2. **Verify tagging worked:**
   ```bash
   python -m bpm_x analyze track.mp3
   ```
   Should show BPM detected.

3. **Inspect output metadata:**
  - Confirm BPM and key are present in command output
  - Confirm organized naming includes BPM/Camelot when templates are used

## Configuration

Edit `config.yaml` to customize:
```yaml
# Default naming: 128 - 8A - kickdrum
naming_template: "{BPM} - {CAMELOT} - {ORIGINAL}"

# Sample rate (lower = faster, less accurate)
audio_sample_rate: 22050

# Auto-organize after tagging
auto_organize: false
```

## Troubleshooting

**Q: "ModuleNotFound: librosa"**
```bash
pip install librosa mutagen pydub
```

**Q: "ffmpeg not found"**
```bash
winget install ffmpeg
```

**Q: Analysis is slow**
```yaml
# In config.yaml, reduce sample rate:
audio_sample_rate: 11050
```

**Q: Key detection inaccurate**
```bash
# Use manual key:
python -m bpm_x tag track.mp3 --key "C Major"
```

## Next Steps

📚 **Read full docs:** See [README.md](README.md)

🎛️ **Batch workflow:** Process entire sample packs automatically

🔧 **Custom templates:** Organize by genre/artist/BPM

💻 **Python API:** Import and use programmatically

```python
from core import AudioAnalyzer
from modules import MetaTagger
from core.translator import KeyTranslator

analyzer = AudioAnalyzer()
analysis = analyzer.analyze('track.mp3')
print(f"{analysis['bpm']} BPM, {analysis['key']}")
```

## Performance Expectations

| Task | Time | Notes |
|------|------|-------|
| Single file analysis | 5-15s | Per 1 min audio |
| Batch 100 files | 20-30 min | Depends on CPU |
| Tagging | < 100ms | Per file |
| Organization | < 50ms | Per file |

## Key Features

✅ BPM detection (onset + autocorrelation)
✅ Key detection (chromagram analysis)
✅ Camelot wheel conversion (1A-12B)
✅ Metadata injection (ID3, Vorbis, WAV)
✅ Metadata tagging
✅ Smart file organization
✅ Batch processing
✅ Energy analysis
✅ Custom naming templates

## Getting Help

- Run with `-v` flag for verbose logging:
  ```bash
  python -m bpm_x batch path --move -v
  ```

- Check logs:
  ```bash
  cat %USERPROFILE%\.bpm-x\logs\bpm-x.log
  ```

- Review examples in README.md

---

**Ready to organize your music? Start with:**
```bash
python -m bpm_x batch C:\samples --dest C:\Music\library --move -v
```
