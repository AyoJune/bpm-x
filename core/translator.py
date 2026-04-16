"""
Key Translator - Converts standard musical keys to Camelot Wheel format
For DJ/Producer workflow (e.g., "A Minor" -> "12A")
"""

import logging
from typing import Dict, Tuple

logger = logging.getLogger(__name__)


class KeyTranslator:
    """Translates musical keys to Camelot Wheel notation."""
    
    # Camelot Wheel mapping
    # Major keys: 1B-12B (clockwise)
    # Minor keys: 1A-12A (clockwise)
    CAMELOT_MAP = {
        # Format: "Root Mode" -> "CamelotNumber+Mode"
        # Major keys (B side)
        "B Major": "1B",
        "F# Major": "2B",
        "C# Major": "3B",
        "G# Major": "4B",
        "D# Major": "5B",
        "A# Major": "6B",
        "F Major": "7B",
        "C Major": "8B",
        "G Major": "9B",
        "D Major": "10B",
        "A Major": "11B",
        "E Major": "12B",
        
        # Minor keys (A side)
        "G# Minor": "1A",
        "D# Minor": "2A",
        "A# Minor": "3A",
        "F Minor": "4A",
        "C Minor": "5A",
        "G Minor": "6A",
        "D Minor": "7A",
        "A Minor": "8A",
        "E Minor": "9A",
        "B Minor": "10A",
        "F# Minor": "11A",
        "C# Minor": "12A",
    }
    
    # Enharmonic equivalents (alternate spellings)
    ENHARMONIC_MAP = {
        "Db": "C#",
        "Eb": "D#",
        "Gb": "F#",
        "Ab": "G#",
        "Bb": "A#",
    }
    
    def __init__(self):
        """Initialize the translator."""
        self.camelot_reverse = {v: k for k, v in self.CAMELOT_MAP.items()}
    
    def normalize_key_name(self, key: str) -> str:
        """
        Normalize key name to standard format.
        Handles enharmonic equivalents and case variations.
        
        Args:
            key: Key name (e.g., "C Major", "Db Major", "a minor")
            
        Returns:
            Normalized key name (e.g., "C Major", "C# Major", "A Minor")
        """
        key = key.strip()
        parts = key.split()
        
        if len(parts) < 2:
            raise ValueError(f"Invalid key format: {key}. Expected 'Note Mode' (e.g., 'C Major')")
        
        note = parts[0]
        mode = parts[1].capitalize()
        
        # Replace enharmonic equivalents
        if note in self.ENHARMONIC_MAP:
            note = self.ENHARMONIC_MAP[note]
        
        normalized = f"{note} {mode}"
        return normalized
    
    def to_camelot(self, key: str) -> str:
        """
        Convert musical key to Camelot Wheel notation.
        
        Args:
            key: Musical key (e.g., "C Major", "A Minor")
            
        Returns:
            Camelot notation (e.g., "8B", "8A")
            
        Raises:
            ValueError: If key is not recognized
        """
        try:
            normalized_key = self.normalize_key_name(key)
            
            if normalized_key not in self.CAMELOT_MAP:
                raise ValueError(
                    f"Key '{key}' not found in Camelot map. "
                    f"Valid keys: {list(self.CAMELOT_MAP.keys())}"
                )
            
            camelot = self.CAMELOT_MAP[normalized_key]
            logger.info(f"Translated '{key}' -> '{camelot}'")
            return camelot
        
        except Exception as e:
            logger.error(f"Translation failed for key '{key}': {e}")
            raise
    
    def from_camelot(self, camelot: str) -> str:
        """
        Convert Camelot notation back to musical key.
        
        Args:
            camelot: Camelot notation (e.g., "8B", "8A")
            
        Returns:
            Musical key (e.g., "C Major", "A Minor")
            
        Raises:
            ValueError: If camelot notation is invalid
        """
        camelot = camelot.upper().strip()
        
        if camelot not in self.camelot_reverse:
            raise ValueError(
                f"Camelot notation '{camelot}' not recognized. "
                f"Valid formats: 1A-12A, 1B-12B"
            )
        
        key = self.camelot_reverse[camelot]
        logger.info(f"Translated '{camelot}' -> '{key}'")
        return key
    
    def get_compatible_keys(self, camelot: str) -> Dict[str, str]:
        """
        Get DJ-compatible keys for harmonic mixing.
        
        Keys are compatible if they're adjacent on the Camelot wheel
        or transitions between major and minor on same number.
        
        Args:
            camelot: Reference Camelot notation (e.g., "8B")
            
        Returns:
            Dict with 'same_mode' and 'relative_minor/major' compatible keys
        """
        camelot = camelot.upper().strip()
        if camelot not in self.camelot_reverse:
            raise ValueError(f"Invalid Camelot notation: {camelot}")
        
        # Parse the camelot code
        num = int(camelot[:-1])
        mode = camelot[-1]
        
        # Adjacent positions (harmonic shift)
        prev_num = ((num - 2) % 12) + 1
        next_num = (num % 12) + 1
        
        compatible = {
            'current': camelot,
            'same_mode': [
                f"{prev_num}{mode}",
                f"{next_num}{mode}"
            ],
            'relative_major_minor': f"{num}{'A' if mode == 'B' else 'B'}"
        }
        
        return compatible


# Convenience functions
def key_to_camelot(key: str) -> str:
    """Quick conversion from key to Camelot."""
    translator = KeyTranslator()
    return translator.to_camelot(key)


def camelot_to_key(camelot: str) -> str:
    """Quick conversion from Camelot to key."""
    translator = KeyTranslator()
    return translator.from_camelot(camelot)
