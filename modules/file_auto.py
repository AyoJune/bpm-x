"""
File Organizer - Smart file renaming and directory organization
Moves files to library structure based on BPM/Key/Genre
"""

import logging
from pathlib import Path
from typing import Optional, Dict
import re

logger = logging.getLogger(__name__)


class FileOrganizer:
    """Organizes audio files into sorted library structure."""
    
    def __init__(self, library_root: str = "data/library"):
        """
        Initialize file organizer.
        
        Args:
            library_root: Root directory for organized library
        """
        self.library_root = Path(library_root)
        self.library_root.mkdir(parents=True, exist_ok=True)
        logger.info(f"Library root: {self.library_root}")
    
    def generate_filename(
        self,
        original_name: str,
        bpm: float,
        key: str,
        camelot: str,
        template: Optional[str] = None
    ) -> str:
        """
        Generate organized filename from metadata.
        
        Args:
            original_name: Original filename
            bpm: Tempo in BPM
            key: Musical key
            camelot: Camelot notation
            template: Custom naming template
                Supported placeholders: {BPM}, {KEY}, {CAMELOT}, {ORIGINAL}
                
        Returns:
            Formatted filename
        """
        if template is None:
            # Default template: "BPM - Key - Original"
            template = "{BPM} - {CAMELOT} - {ORIGINAL}"
        
        # Extract base name without extension
        base_name = Path(original_name).stem
        
        # Replace placeholders
        filename = template.format(
            BPM=int(round(bpm)),
            KEY=key,
            CAMELOT=camelot,
            ORIGINAL=base_name
        )
        
        # Clean up filename
        filename = self._sanitize_filename(filename)
        
        return filename
    
    def _sanitize_filename(self, filename: str) -> str:
        """Remove invalid characters from filename."""
        # Remove/replace invalid characters
        invalid_chars = r'[<>:"/\\|?*]'
        filename = re.sub(invalid_chars, '', filename)
        
        # Replace multiple spaces with single space
        filename = re.sub(r'\s+', ' ', filename)
        
        # Trim to reasonable length
        if len(filename) > 200:
            filename = filename[:200]
        
        return filename.strip()
    
    def organize_file(
        self,
        file_path: str,
        bpm: float,
        key: str,
        camelot: str,
        energy_level: Optional[int] = None,
        genre: Optional[str] = None,
        filename_template: Optional[str] = None,
        move: bool = False
    ) -> Optional[Path]:
        """
        Move/copy file to organized library structure.
        
        Directory structure:
            library/
            ├── [GENRE]/
            │   ├── [CAMELOT_NUM]/
            │   │   └── {BPM} - {CAMELOT} - {ORIGINAL}.{ext}
            
        Args:
            file_path: Source file path
            bpm: Tempo
            key: Musical key
            camelot: Camelot notation
            energy_level: Energy level (1-10)
            genre: Music genre
            filename_template: Custom naming template
            move: If True, move file; if False, copy file
            
        Returns:
            Path to organized file, or None if failed
        """
        source = Path(file_path)
        if not source.exists():
            logger.error(f"Source file not found: {source}")
            return None
        
        try:
            # Parse camelot number
            camelot_num = camelot.replace('A', '').replace('B', '')
            
            # Build directory structure
            if genre:
                org_dir = self.library_root / genre / camelot_num
            else:
                org_dir = self.library_root / camelot_num
            
            org_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate organized filename
            new_filename = self.generate_filename(
                source.name,
                bpm,
                key,
                camelot,
                filename_template
            )
            new_filename = f"{new_filename}{source.suffix}"
            
            dest = org_dir / new_filename
            
            # Handle duplicate filenames
            counter = 1
            while dest.exists():
                stem, ext = new_filename.rsplit('.', 1) if '.' in new_filename else (new_filename, '')
                new_filename = f"{stem}_{counter}.{ext}"
                dest = org_dir / new_filename
                counter += 1
            
            # Move or copy
            if move:
                source.rename(dest)
                logger.info(f"Moved: {source.name} -> {dest.relative_to(self.library_root)}")
            else:
                import shutil
                shutil.copy2(source, dest)
                logger.info(f"Copied: {source.name} -> {dest.relative_to(self.library_root)}")
            
            return dest
        
        except Exception as e:
            logger.error(f"Organization failed for {source.name}: {e}")
            return None
    
    def organize_directory(
        self,
        source_dir: str,
        analyzer,  # AudioAnalyzer instance
        move: bool = False,
        filename_template: Optional[str] = None
    ) -> Dict[str, int]:
        """
        Organize all audio files in a directory.
        
        Args:
            source_dir: Directory containing audio files
            analyzer: AudioAnalyzer instance for BPM/Key detection
            move: If True, move files; if False, copy
            filename_template: Custom naming template
            
        Returns:
            Stats dict {'success': int, 'failed': int, 'skipped': int}
        """
        source_dir = Path(source_dir)
        if not source_dir.is_dir():
            logger.error(f"Not a directory: {source_dir}")
            return {'success': 0, 'failed': 0, 'skipped': 0}
        
        stats = {'success': 0, 'failed': 0, 'skipped': 0}
        
        # Audio extensions
        audio_exts = {'.mp3', '.wav', '.flac', '.ogg', '.m4a'}
        
        for audio_file in source_dir.rglob('*'):
            if audio_file.suffix.lower() not in audio_exts:
                continue
            
            try:
                # Analyze file
                logger.info(f"Analyzing: {audio_file.name}")
                analysis = analyzer.analyze(str(audio_file))
                
                # Import translator for key conversion
                from core.translator import KeyTranslator
                translator = KeyTranslator()
                camelot = translator.to_camelot(analysis['key'])
                
                # Organize file
                if self.organize_file(
                    str(audio_file),
                    analysis['bpm'],
                    analysis['key'],
                    camelot,
                    filename_template=filename_template,
                    move=move
                ):
                    stats['success'] += 1
                else:
                    stats['failed'] += 1
            
            except Exception as e:
                logger.warning(f"Skipped {audio_file.name}: {e}")
                stats['skipped'] += 1
        
        logger.info(f"Organization complete: {stats}")
        return stats
