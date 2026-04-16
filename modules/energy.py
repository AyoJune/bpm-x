"""
Energy Analyzer - Analyzes perceived energy level of tracks (1-10)
Based on loudness, frequency distribution, and spectral centroid
"""

import logging
from typing import Tuple, Dict, Any

try:
    import librosa
    import numpy as np
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False

logger = logging.getLogger(__name__)


class EnergyAnalyzer:
    """Analyzes perceived energy level of audio tracks."""
    
    def __init__(self, sr: int = 22050):
        """
        Initialize energy analyzer.
        
        Args:
            sr: Sample rate (Hz)
        """
        if not LIBROSA_AVAILABLE:
            logger.warning("librosa not available for energy analysis")
        
        self.sr = sr
    
    def analyze(self, audio_path: str) -> Tuple[int, Dict[str, Any]]:
        """
        Analyze perceived energy level of track.
        
        Returns:
            Tuple of (energy_level [1-10], metadata_dict)
        """
        if not LIBROSA_AVAILABLE:
            logger.warning("Cannot analyze energy: librosa not installed")
            return 5, {'error': 'librosa not available'}
        
        try:
            # Load audio
            y, sr = librosa.load(audio_path, sr=self.sr)
            logger.info(f"Analyzing energy for: {audio_path}")
            
            # 1. Loudness (RMS energy)
            S = librosa.feature.melspectrogram(y=y, sr=sr)
            log_S = librosa.power_to_db(S, ref=np.max)
            loudness = np.mean(log_S)
            loudness_normalized = (loudness + 80) / 80  # Normalize to [0, 1]
            loudness_normalized = max(0, min(1, loudness_normalized))
            
            # 2. Dynamic range (percussiveness)
            onset_env = librosa.onset.onset_strength(y=y, sr=sr)
            percussiveness = np.std(onset_env)
            percussiveness_normalized = min(percussiveness / 0.15, 1.0)
            
            # 3. Spectral centroid (brightness)
            centroid = librosa.feature.spectral_centroid(y=y, sr=sr)
            centroid_mean = np.mean(centroid)
            spectral_normalized = centroid_mean / (sr / 2)  # Norm to [0, 1]
            
            # 4. Zero crossing rate (clarity/attack)
            zcr = librosa.feature.zero_crossing_rate(y)[0]
            zcr_mean = np.mean(zcr)
            zcr_normalized = min(zcr_mean * 20, 1.0)
            
            # Combine metrics with weights
            weights = {
                'loudness': 0.35,
                'percussiveness': 0.30,
                'spectral': 0.20,
                'zcr': 0.15
            }
            
            energy_score = (
                loudness_normalized * weights['loudness'] +
                percussiveness_normalized * weights['percussiveness'] +
                spectral_normalized * weights['spectral'] +
                zcr_normalized * weights['zcr']
            )
            
            # Convert to 1-10 scale
            energy_level = max(1, min(10, int(round(energy_score * 10))))
            
            logger.info(f"Detected energy level: {energy_level}/10")
            
            return energy_level, {
                'energy_level': energy_level,
                'loudness': float(loudness),
                'percussiveness': float(percussiveness),
                'spectral_centroid_hz': float(centroid_mean),
                'zero_crossing_rate': float(zcr_mean),
                'scores': {
                    'loudness': float(loudness_normalized),
                    'percussiveness': float(percussiveness_normalized),
                    'spectral': float(spectral_normalized),
                    'zcr': float(zcr_normalized)
                }
            }
        
        except Exception as e:
            logger.error(f"Energy analysis failed: {e}")
            return 5, {'error': str(e)}
    
    def analyze_batch(self, audio_paths: list) -> Dict[str, Tuple[int, Dict]]:
        """
        Analyze energy levels for multiple files.
        
        Args:
            audio_paths: List of file paths
            
        Returns:
            Dictionary mapping file paths to (energy_level, metadata)
        """
        results = {}
        for path in audio_paths:
            try:
                energy, meta = self.analyze(path)
                results[path] = (energy, meta)
            except Exception as e:
                logger.error(f"Batch analysis failed for {path}: {e}")
                results[path] = (5, {'error': str(e)})
        
        return results
