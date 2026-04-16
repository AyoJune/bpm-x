"""
Audio Loader - Handles file format conversions and audio file I/O
Supports MP3, WAV, FLAC, OGG and automatic conversion to WAV.
"""

import os
import logging
from pathlib import Path
from typing import Tuple, Optional
import shutil

try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False

logger = logging.getLogger(__name__)


class AudioLoader:
    """Loads and converts audio files to standard format."""
    
    SUPPORTED_FORMATS = {
        '.mp3': 'mp3',
        '.wav': 'wav',
        '.flac': 'flac',
        '.ogg': 'ogg',
        '.m4a': 'm4a',
    }
    
    def __init__(self, output_format: str = 'wav', temp_dir: Optional[str] = None):
        """
        Initialize audio loader.
        
        Args:
            output_format: Target format for conversions ('wav', 'mp3', etc.)
            temp_dir: Directory for temporary files (defaults to system temp)
        """
        self.output_format = output_format.lower()
        self.temp_dir = temp_dir or Path.home() / '.bpm-x' / 'temp'
        
        # Create temp directory if needed
        Path(self.temp_dir).mkdir(parents=True, exist_ok=True)
        
        if not PYDUB_AVAILABLE:
            logger.warning(
                "pydub not available. Only loading supported—conversions will fail. "
                "Install pydub for format conversion: pip install pydub"
            )
    
    def get_file_format(self, file_path: str) -> Optional[str]:
        """
        Detect audio file format.
        
        Args:
            file_path: Path to audio file
            
        Returns:
            Format string (e.g., 'mp3') or None if unsupported
        """
        ext = Path(file_path).suffix.lower()
        return self.SUPPORTED_FORMATS.get(ext)
    
    def is_supported(self, file_path: str) -> bool:
        """Check if file format is supported."""
        return self.get_file_format(file_path) is not None
    
    def convert(self, input_path: str, output_path: Optional[str] = None) -> str:
        """
        Convert audio file to target format.
        
        Args:
            input_path: Path to source audio file
            output_path: Path for output file (auto-generated if None)
            
        Returns:
            Path to converted file
            
        Raises:
            ValueError: If format unsupported or conversion fails
        """
        if not PYDUB_AVAILABLE:
            raise RuntimeError(
                "Audio conversion requires pydub. "
                "Install with: pip install pydub"
            )
        
        input_path = Path(input_path)
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")
        
        in_format = self.get_file_format(str(input_path))
        if not in_format:
            raise ValueError(
                f"Unsupported format: {input_path.suffix}. "
                f"Supported: {list(self.SUPPORTED_FORMATS.keys())}"
            )
        
        # Generate output path if not provided
        if output_path is None:
            output_path = input_path.with_suffix(f'.{self.output_format}')
        
        output_path = Path(output_path)
        
        try:
            logger.info(f"Converting {input_path.name} to {self.output_format}...")
            
            # Load and export
            audio = AudioSegment.from_file(str(input_path), format=in_format)
            audio.export(str(output_path), format=self.output_format)
            
            logger.info(f"Conversion complete: {output_path}")
            return str(output_path)
        
        except Exception as e:
            logger.error(f"Conversion failed: {e}")
            raise
    
    def load_or_convert(self, file_path: str, target_format: str = 'wav') -> str:
        """
        Load audio file, converting if necessary.
        
        Args:
            file_path: Path to audio file
            target_format: Desired output format
            
        Returns:
            Path to usable audio file (original or converted)
        """
        file_path = Path(file_path)
        current_format = self.get_file_format(str(file_path))
        
        if current_format == target_format:
            logger.info(f"File already in {target_format} format")
            return str(file_path)
        
        logger.info(f"File needs conversion: {current_format} -> {target_format}")
        self.output_format = target_format
        return self.convert(str(file_path))
    
    def get_audio_duration(self, file_path: str) -> float:
        """
        Get audio file duration in seconds.
        
        Args:
            file_path: Path to audio file
            
        Returns:
            Duration in seconds
        """
        if not PYDUB_AVAILABLE:
            logger.warning("Cannot determine duration without pydub")
            return 0.0
        
        try:
            file_path = Path(file_path)
            fmt = self.get_file_format(str(file_path))
            audio = AudioSegment.from_file(str(file_path), format=fmt)
            duration = len(audio) / 1000.0  # pydub uses milliseconds
            return duration
        except Exception as e:
            logger.error(f"Failed to get duration: {e}")
            return 0.0
    
    def cleanup_temp_files(self) -> int:
        """
        Clean up temporary files.
        
        Returns:
            Number of files deleted
        """
        temp_path = Path(self.temp_dir)
        if not temp_path.exists():
            return 0
        
        deleted = 0
        try:
            for file in temp_path.glob('*'):
                try:
                    file.unlink()
                    deleted += 1
                except Exception as e:
                    logger.warning(f"Failed to delete {file}: {e}")
            
            logger.info(f"Cleaned up {deleted} temporary files")
            return deleted
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
            return deleted
