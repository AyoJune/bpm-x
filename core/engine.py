"""
BPM Detector and Key Analyzer using Librosa
Detects tempo, key, and musical characteristics from audio files.
"""

import re
import os
import librosa
import numpy as np
from typing import Tuple, Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class BPMDetector:
    """Detects BPM from audio using onset detection and autocorrelation."""
    
    def __init__(self, sr: int = 22050, hop_length: int = 512):
        """
        Initialize BPM detector.
        
        Args:
            sr: Sample rate (Hz)
            hop_length: Number of samples between successive frames
        """
        self.sr = sr
        self.hop_length = hop_length
    
    def detect(self, audio_path: str) -> Tuple[float, Dict[str, Any]]:
        """
        Detect BPM from audio file.
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Tuple of (detected_bpm, metadata_dict)
        """
        try:
            # Load audio
            y, sr = librosa.load(audio_path, sr=self.sr)
            logger.info(f"Loaded audio: {audio_path} ({len(y)/sr:.2f}s)")
            
            # Compute onset strength
            onset_env = librosa.onset.onset_strength(y=y, sr=sr)
            
            # Estimate tempo using onset autocorrelation
            bpm, beats = librosa.beat.beat_track(
                y=y, 
                sr=sr,
                hop_length=self.hop_length,
                start_bpm=120  # Common starting point for music
            )
            
            # Convert to Python float (handle numpy arrays/scalars)
            bpm = float(bpm) if not isinstance(bpm, np.ndarray) else float(bpm.item())

            # Round to nearest integer — producers work in whole-number BPMs;
            # librosa's fractional outputs (117.5, 161.5) are beat-grid noise.
            bpm = float(round(bpm))

            # Confidence metric (power of onset envelope)
            confidence = float(np.mean(onset_env[beats]) / (np.std(onset_env) + 1e-10))
            confidence = min(confidence, 1.0)  # Clamp to [0, 1]
            
            logger.info(f"Detected BPM: {bpm:.1f} (confidence: {confidence:.2f})")
            
            return bpm, {
                'confidence': confidence,
                'beats_count': len(beats),
                'onset_strength_mean': float(np.mean(onset_env)),
                'duration_seconds': len(y) / sr
            }
        
        except Exception as e:
            logger.error(f"BPM detection failed for {audio_path}: {e}")
            raise


class KeyDetector:
    """Detects musical key from audio using chromagram analysis."""
    
    def __init__(self, sr: int = 22050, hop_length: int = 512):
        """
        Initialize key detector.
        
        Args:
            sr: Sample rate (Hz)
            hop_length: Number of samples between successive frames
        """
        self.sr = sr
        self.hop_length = hop_length
        
        # Pitch class labels (12-tone chromatic scale)
        self.pitch_classes = [
            'C', 'C#', 'D', 'D#', 'E', 'F',
            'F#', 'G', 'G#', 'A', 'A#', 'B'
        ]

        # Krumhansl-Schmuckler key profiles.
        self.major_profile = np.array(
            [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88],
            dtype=np.float32,
        )
        self.minor_profile = np.array(
            [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17],
            dtype=np.float32,
        )
        self.major_profile /= np.linalg.norm(self.major_profile) + 1e-10
        self.minor_profile /= np.linalg.norm(self.minor_profile) + 1e-10
    
    def detect(self, audio_path: str) -> Tuple[str, Dict[str, Any]]:
        """
        Detect musical key from audio file.
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Tuple of (detected_key, metadata_dict)
                detected_key format: "C Major" or "A Minor"
        """
        try:
            # Load audio
            y, sr = librosa.load(audio_path, sr=self.sr, mono=True)
            logger.info(f"Analyzing key for: {audio_path}")

            # Use harmonic content for more stable key estimation.
            y_harmonic, _ = librosa.effects.hpss(y)

            chroma_cqt = librosa.feature.chroma_cqt(y=y_harmonic, sr=sr, hop_length=self.hop_length)
            chroma_stft = librosa.feature.chroma_stft(y=y_harmonic, sr=sr, hop_length=self.hop_length)

            # Blend two chroma views to reduce edge-case bias.
            chroma = 0.6 * chroma_cqt + 0.4 * chroma_stft
            chroma_mean = np.mean(chroma, axis=1)
            chroma_norm = chroma_mean / (np.linalg.norm(chroma_mean) + 1e-10)

            key_candidates: list[tuple[str, str, float]] = []
            for tonic_idx, tonic in enumerate(self.pitch_classes):
                major_score = float(np.dot(chroma_norm, np.roll(self.major_profile, tonic_idx)))
                minor_score = float(np.dot(chroma_norm, np.roll(self.minor_profile, tonic_idx)))
                key_candidates.append((tonic, "Major", major_score))
                key_candidates.append((tonic, "Minor", minor_score))

            key_candidates.sort(key=lambda item: item[2], reverse=True)
            root_note, mode, best_score = key_candidates[0]
            second_score = key_candidates[1][2] if len(key_candidates) > 1 else 0.0
            detected_key = f"{root_note} {mode}"

            # Confidence reflects score margin and absolute fit quality.
            confidence = float(max(0.0, min(1.0, ((best_score - second_score) * 0.65) + (best_score * 0.35))))
            
            logger.info(f"Detected key: {detected_key} (confidence: {confidence:.2f})")
            
            return detected_key, {
                'root_note': root_note,
                'mode': mode,
                'confidence': confidence,
                'chroma_distribution': chroma_mean.tolist(),
                'key_fit_score': float(best_score),
                'runner_up_score': float(second_score),
                'top_candidates': [
                    {
                        'key': f"{cand[0]} {cand[1]}",
                        'score': float(cand[2]),
                    }
                    for cand in key_candidates[:5]
                ],
            }
        
        except Exception as e:
            logger.error(f"Key detection failed for {audio_path}: {e}")
            raise


class EnergyAnalyzer:
    """Rates track energy on a 1–10 scale using a multi-factor signal model.

    Factors (weighted blend):
      - RMS loudness          — overall power
      - Spectral centroid      — brightness / high-frequency content
      - Onset density         — rhythmic activity / percussion intensity
      - Low-frequency ratio   — bass / sub weight (inverted for "danceability")

    Each factor is normalized against the full dynamic range of that signal
    before blending, so quiet ambient pads score low and dense club kicks score
    high, regardless of overall file loudness.
    """

    def __init__(self, sr: int = 22050, hop_length: int = 512):
        self.sr = sr
        self.hop_length = hop_length

    def analyze(self, audio_path: str) -> Dict[str, Any]:
        try:
            y, sr = librosa.load(audio_path, sr=self.sr, mono=True)

            # ── RMS loudness (root-mean-square energy per frame) ──────────────
            rms = librosa.feature.rms(y=y, hop_length=self.hop_length)[0]
            rms_mean = float(np.mean(rms))

            # ── Spectral centroid (brightness) ────────────────────────────────
            centroid = librosa.feature.spectral_centroid(y=y, sr=sr, hop_length=self.hop_length)[0]
            centroid_norm = float(np.mean(centroid)) / (sr / 2.0)  # 0–1 relative to Nyquist

            # ── Onset density (percussive hit rate) ───────────────────────────
            onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=self.hop_length)
            onset_density = float(np.mean(onset_env))

            # ── Low-frequency power ratio (bass weight) ───────────────────────
            # Sub-bass and bass bins contribute to danceability — weight them in.
            stft = np.abs(librosa.stft(y, hop_length=self.hop_length))
            freqs = librosa.fft_frequencies(sr=sr)
            low_mask = freqs <= 250
            low_power = float(np.mean(stft[low_mask, :]))
            total_power = float(np.mean(stft)) + 1e-10
            low_ratio = min(low_power / total_power, 1.0)

            # ── Blend into a single 0–1 score ────────────────────────────────
            # Weights tuned for DJ / production context.
            raw_score = (
                0.35 * min(rms_mean / 0.15, 1.0)        # loudness   (0.15 RMS ≈ club level)
                + 0.25 * min(centroid_norm / 0.25, 1.0)  # brightness (0.25 Nyquist ≈ bright)
                + 0.25 * min(onset_density / 4.0, 1.0)   # hit rate   (4.0 ≈ dense 4-on-floor)
                + 0.15 * min(low_ratio / 0.35, 1.0)      # bass weight (0.35 ratio ≈ bass-heavy)
            )

            # Map to 1–10, round to nearest integer.
            energy_level = max(1, min(10, round(1 + raw_score * 9)))

            logger.info(f"Energy level: {energy_level}/10  (rms={rms_mean:.4f}, centroid={centroid_norm:.3f}, onsets={onset_density:.3f}, low={low_ratio:.3f})")

            return {
                "energy_level": energy_level,
                "rms_mean": rms_mean,
                "centroid_norm": centroid_norm,
                "onset_density": onset_density,
                "low_ratio": low_ratio,
            }

        except Exception as e:
            logger.error(f"Energy analysis failed for {audio_path}: {e}")
            return {"energy_level": 0}


class DanceabilityAnalyzer:
    """Rates how rhythmically dance-friendly a track is on a 1–10 scale.

    Distinct from Energy (which measures loudness/power intensity).
    Danceability measures:
      - Beat regularity   — how consistent the inter-beat intervals are
      - Beat strength     — how prominently beat frames stand out vs. background
      - Periodicity       — how sharp the dominant beat period is in the tempogram
      - Tempo consistency — how stable the tempo is across the full track

    A perfectly quantized 4-on-the-floor kick scores 10.
    Ambient pads, rubato performances, or highly syncopated tracks score low.
    """

    def __init__(self, sr: int = 22050, hop_length: int = 512):
        self.sr = sr
        self.hop_length = hop_length

    def analyze(self, audio_path: str) -> Dict[str, Any]:
        try:
            y, sr = librosa.load(audio_path, sr=self.sr, mono=True)

            onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=self.hop_length)
            _, beat_frames = librosa.beat.beat_track(
                y=y, sr=sr, hop_length=self.hop_length
            )

            # ── 1. Beat regularity — low IBI variance = tight grid ────────────
            if len(beat_frames) >= 4:
                ibi = np.diff(beat_frames).astype(float)
                regularity = float(
                    max(0.0, 1.0 - np.std(ibi) / (np.mean(ibi) + 1e-10))
                )
            else:
                regularity = 0.0

            # ── 2. Beat strength — onsets at beat frames vs. overall mean ─────
            valid_beats = beat_frames[beat_frames < len(onset_env)]
            if len(valid_beats) > 0:
                beat_env_mean = float(np.mean(onset_env[valid_beats]))
                global_env_mean = float(np.mean(onset_env)) + 1e-10
                beat_strength = min(beat_env_mean / (global_env_mean * 3.0), 1.0)
            else:
                beat_strength = 0.0

            # ── 3. Periodicity — sharpness of dominant beat peak ─────────────
            # Tempogram column means give a "consensus" autocorrelation curve;
            # a sharp, tall peak means a clear, repeated period.
            tempogram = librosa.feature.tempogram(
                onset_envelope=onset_env, sr=sr, hop_length=self.hop_length
            )
            ac_mean = np.mean(tempogram, axis=1)
            if len(ac_mean) > 1:
                periodicity = min(
                    float(np.max(ac_mean)) / (float(np.mean(ac_mean)) + 1e-10) / 5.0,
                    1.0,
                )
            else:
                periodicity = 0.0

            # ── 4. Tempo consistency — stable BPM across track thirds ─────────
            consistency = 1.0
            n = len(y)
            third = n // 3
            if third > sr:  # at least 1 second per segment
                local_bpms: list[float] = []
                for start in (0, third, 2 * third):
                    seg = y[start : start + third]
                    try:
                        lb, _ = librosa.beat.beat_track(y=seg, sr=sr)
                        local_bpms.append(
                            float(lb) if not isinstance(lb, np.ndarray) else float(lb.item())
                        )
                    except Exception:
                        pass
                if len(local_bpms) >= 2:
                    consistency = max(0.0, 1.0 - float(np.std(local_bpms)) / 10.0)

            # ── Weighted blend → 1–10 ─────────────────────────────────────────
            raw = (
                0.35 * regularity
                + 0.30 * beat_strength
                + 0.20 * periodicity
                + 0.15 * consistency
            )
            danceability = max(1, min(10, round(1 + raw * 9)))

            logger.info(
                f"Danceability: {danceability}/10  "
                f"(reg={regularity:.3f}, str={beat_strength:.3f}, "
                f"per={periodicity:.3f}, con={consistency:.3f})"
            )

            return {
                "danceability": danceability,
                "beat_regularity": float(regularity),
                "beat_strength": float(beat_strength),
                "periodicity": float(periodicity),
                "tempo_consistency": float(consistency),
            }

        except Exception as e:
            logger.error(f"Danceability analysis failed for {audio_path}: {e}")
            return {"danceability": 0}


class AudioAnalyzer:
    """Combined analyzer for BPM and Key detection."""

    # BPM range accepted from filename labels.
    _BPM_MIN = 60
    _BPM_MAX = 220

    def __init__(self, sr: int = 22050, hop_length: int = 512):
        """Initialize analyzer with both detectors."""
        self.bpm_detector = BPMDetector(sr=sr, hop_length=hop_length)
        self.key_detector = KeyDetector(sr=sr, hop_length=hop_length)
        self.energy_analyzer = EnergyAnalyzer(sr=sr, hop_length=hop_length)
        self.dance_analyzer = DanceabilityAnalyzer(sr=sr, hop_length=hop_length)

    @staticmethod
    def _parse_bpm_from_filename(filename: str) -> Optional[float]:
        """Extract a BPM value embedded in an audio filename.

        Recognises patterns used by most sample-pack producers:
          - Explicit tag:  "120bpm", "120 BPM", "BPM120", "BPM 120"
          - Parentheses:   "(120)", "[120]"
        Returns the first matching value in the range 60–220, or None.
        """
        stem = os.path.splitext(os.path.basename(filename))[0]

        # Priority 1 — explicit "bpm" keyword next to a number.
        m = re.search(
            r'(?<![\d])(\d{2,3})\s*bpm|bpm\s*(\d{2,3})(?![\d])',
            stem,
            re.IGNORECASE,
        )
        if m:
            raw = float(m.group(1) or m.group(2))
            if AudioAnalyzer._BPM_MIN <= raw <= AudioAnalyzer._BPM_MAX:
                return raw

        # Priority 2 — number enclosed in parentheses or brackets.
        m = re.search(r'[\(\[]\s*(\d{2,3})\s*[\)\]]', stem)
        if m:
            raw = float(m.group(1))
            if AudioAnalyzer._BPM_MIN <= raw <= AudioAnalyzer._BPM_MAX:
                return raw

        return None

    def analyze(self, audio_path: str) -> Dict[str, Any]:
        """
        Perform complete audio analysis.

        BPM resolution order:
          1. Filename label  — trusted; confidence = 1.0, source = "filename"
          2. Librosa engine  — rounded to nearest integer; source = "analysis"

        Args:
            audio_path: Path to audio file

        Returns:
            Dictionary containing BPM, key, and all metadata
        """
        logger.info(f"Starting comprehensive analysis for: {audio_path}")

        filename_bpm = self._parse_bpm_from_filename(audio_path)

        if filename_bpm is not None:
            logger.info(f"Filename BPM override: {filename_bpm} (from label)")
            bpm = filename_bpm
            bpm_meta = {
                'confidence': 1.0,
                'source': 'filename',
                'beats_count': 0,
                'onset_strength_mean': 0.0,
                'duration_seconds': 0.0,
            }
        else:
            bpm, bpm_meta = self.bpm_detector.detect(audio_path)
            bpm_meta['source'] = 'analysis'

        key, key_meta = self.key_detector.detect(audio_path)
        energy_meta = self.energy_analyzer.analyze(audio_path)
        dance_meta = self.dance_analyzer.analyze(audio_path)

        return {
            'file': audio_path,
            'bpm': bpm,
            'bpm_source': bpm_meta.get('source', 'analysis'),
            'key': key,
            'energy': energy_meta.get('energy_level', 0),
            'danceability': dance_meta.get('danceability', 0),
            'bpm_metadata': bpm_meta,
            'key_metadata': key_meta,
            'energy_metadata': energy_meta,
                    'dance_metadata': dance_meta,
        }
