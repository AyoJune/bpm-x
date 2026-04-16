"""Audio finishing utilities for destructive cleanup (trim + normalize)."""

from __future__ import annotations

import logging
import os
import shutil
import tempfile
from pathlib import Path

import librosa
import numpy as np
import soundfile as sf
try:
    import pyloudnorm as pyln
    HAS_PYLOUDNORM = True
except Exception:
    HAS_PYLOUDNORM = False

try:
    from pydub import AudioSegment
    HAS_PYDUB = True
except Exception:
    HAS_PYDUB = False

logger = logging.getLogger(__name__)


class AudioFinisher:
    """Applies optional destructive cleanup to audio files.

    Operations:
      - Trim leading/trailing silence using librosa.effects.trim
      - Peak-normalize to target dBFS (default: -1 dBFS)
            - LUFS normalize to integrated loudness target (default: -14 LUFS)

    Notes:
      - PCM/container formats are written directly with soundfile.
      - MP3/M4A rewrite requires pydub + ffmpeg.
    """

    _PCM_WRITE_EXTS = {".wav", ".flac", ".ogg", ".aif", ".aiff", ".au"}

    @staticmethod
    def _build_output_path(source: Path, trim: bool, normalize: bool, lufs_normalize: bool) -> Path:
        suffix_parts: list[str] = []
        if trim:
            suffix_parts.append("trimmed")
        if normalize:
            suffix_parts.append("norm")
        if lufs_normalize:
            suffix_parts.append("lufs")
        suffix = "_" + "_".join(suffix_parts) if suffix_parts else "_finished"
        return source.with_name(f"{source.stem}{suffix}{source.suffix}")

    def trim_silence(self, file_path: str | Path, top_db: float = 60.0) -> bool:
        """Trim silence and overwrite file in-place.

        Returns True if any samples were removed, otherwise False.
        """
        path = Path(file_path)
        y, sr = librosa.load(str(path), sr=None, mono=False)

        trimmed, index = librosa.effects.trim(y, top_db=top_db)
        start_sample = int(index[0]) if len(index) > 0 else 0
        end_sample = int(index[1]) if len(index) > 1 else (y.shape[-1] if y.ndim > 0 else 0)

        if start_sample <= 0 and end_sample >= y.shape[-1]:
            return False

        self._write_audio(path, trimmed, sr)
        return True

    def normalize_peaks(self, file_path: str | Path, target_dbfs: float = -1.0) -> bool:
        """Peak-normalize and overwrite file in-place.

        Returns True when gain is applied, otherwise False.
        """
        path = Path(file_path)
        y, sr = librosa.load(str(path), sr=None, mono=False)

        peak = float(np.max(np.abs(y))) if np.size(y) else 0.0
        if peak <= 1e-10:
            return False

        target_peak = float(10 ** (target_dbfs / 20.0))
        gain = target_peak / peak

        if abs(gain - 1.0) < 1e-3:
            return False

        y_norm = np.clip(y * gain, -1.0, 1.0)
        self._write_audio(path, y_norm, sr)
        return True

    def normalize_lufs(
        self,
        file_path: str | Path,
        target_lufs: float = -14.0,
        peak_limit_dbtp: float = -1.0,
    ) -> bool:
        """Normalize integrated loudness to LUFS target with a true-peak-style safety ceiling.

        Returns True when gain/limiting changed the signal, otherwise False.
        """
        if not HAS_PYLOUDNORM:
            raise RuntimeError("LUFS normalization requires pyloudnorm (pip install pyloudnorm)")

        path = Path(file_path)
        y, sr = librosa.load(str(path), sr=None, mono=False)

        y_sf = self._to_soundfile_shape(y).astype(np.float32, copy=False)
        meter = pyln.Meter(sr)
        loudness = float(meter.integrated_loudness(y_sf))
        if not np.isfinite(loudness):
            return False

        adjusted = pyln.normalize.loudness(y_sf, loudness, target_lufs)

        peak_limit = float(10 ** (peak_limit_dbtp / 20.0))
        peak = float(np.max(np.abs(adjusted))) if np.size(adjusted) else 0.0
        peak_limited = False
        if peak > peak_limit:
            adjusted = adjusted * (peak_limit / (peak + 1e-10))
            peak_limited = True

        changed = abs(loudness - target_lufs) >= 0.1 or peak_limited
        if not changed:
            return False

        if adjusted.ndim == 1:
            y_out = adjusted
        else:
            y_out = np.ascontiguousarray(adjusted.T)

        self._write_audio(path, y_out, sr)
        return True

    def finish(
        self,
        file_path: str | Path,
        *,
        trim: bool,
        normalize: bool,
        lufs_normalize: bool = False,
        keep_originals: bool = False,
        trim_top_db: float = 60.0,
        normalize_target_dbfs: float = -1.0,
        lufs_target: float = -14.0,
        lufs_peak_limit_dbtp: float = -1.0,
    ) -> dict[str, object]:
        """Run enabled finishing operations against a file.

        Returns a small status payload for UI logging.
        """
        input_path = Path(file_path)
        path = input_path
        trimmed = False
        normalized = False
        lufs_applied = False
        tags: list[str] = []

        if keep_originals and (trim or normalize or lufs_normalize):
            path = self._build_output_path(
                input_path,
                trim=trim,
                normalize=normalize,
                lufs_normalize=lufs_normalize,
            )
            shutil.copy2(input_path, path)

        if trim:
            trimmed = self.trim_silence(path, top_db=trim_top_db)
            if trimmed:
                tags.append("TRIMMED")

        if normalize:
            normalized = self.normalize_peaks(path, target_dbfs=normalize_target_dbfs)
            if normalized:
                tags.append("NORM")

        if lufs_normalize:
            lufs_applied = self.normalize_lufs(
                path,
                target_lufs=lufs_target,
                peak_limit_dbtp=lufs_peak_limit_dbtp,
            )
            if lufs_applied:
                tags.append("LUFS")

        if keep_originals and not tags and (trim or normalize or lufs_normalize):
            tags.append("COPY")

        summary = ", ".join(tag.lower() for tag in tags) if tags else "no change"

        return {
            "trimmed": trimmed,
            "normalized": normalized,
            "lufs_normalized": lufs_applied,
            "changed": bool(trimmed or normalized or lufs_applied),
            "kept_originals": keep_originals,
            "summary": summary,
            "path": str(path),
            "source_path": str(input_path),
            "tags": tags,
        }

    def _write_audio(self, path: Path, y: np.ndarray, sr: int) -> None:
        ext = path.suffix.lower()

        if ext in self._PCM_WRITE_EXTS:
            sf.write(str(path), self._to_soundfile_shape(y), sr)
            return

        if ext in {".mp3", ".m4a"}:
            if not HAS_PYDUB:
                raise RuntimeError("MP3/M4A rewrite needs pydub + ffmpeg installed")

            # Export through a temporary WAV to preserve the target container/codec.
            tmp_wav = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
            tmp_wav_path = Path(tmp_wav.name)
            tmp_wav.close()
            try:
                sf.write(str(tmp_wav_path), self._to_soundfile_shape(y), sr)
                segment = AudioSegment.from_file(str(tmp_wav_path))
                fmt = "mp4" if ext == ".m4a" else "mp3"
                segment.export(str(path), format=fmt)
            finally:
                try:
                    os.remove(tmp_wav_path)
                except OSError:
                    pass
            return

        raise RuntimeError(f"Unsupported format for destructive write: {ext}")

    @staticmethod
    def _to_soundfile_shape(y: np.ndarray) -> np.ndarray:
        # librosa returns multi-channel as (channels, samples);
        # soundfile expects (samples, channels).
        if y.ndim == 1:
            return y
        return np.ascontiguousarray(y.T)
