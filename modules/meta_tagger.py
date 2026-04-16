"""
Metadata Tagger - Injects BPM and Key into audio file metadata
Uses mutagen to write ID3 tags (MP3), Vorbis comments (OGG), etc.
FL Studio automatically reads these tags for project sync.
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional

try:
    from mutagen.id3 import COMM, ID3, TBPM, TCON, TKEY, TIT1, TXXX
    from mutagen.wave import WAVE
    from mutagen.oggvorbis import OggVorbis
    from mutagen.flac import FLAC
    MUTAGEN_AVAILABLE = True
except ImportError:
    MUTAGEN_AVAILABLE = False

logger = logging.getLogger(__name__)


class MetaTagger:
    """Injects BPM, Key, and custom metadata into audio files."""

    PROFILES = {"universal", "dj", "ableton"}
    
    def __init__(self):
        """Initialize metadata tagger."""
        if not MUTAGEN_AVAILABLE:
            logger.warning(
                "mutagen not available. Metadata tagging will fail. "
                "Install with: pip install mutagen"
            )
    
    def get_file_type(self, file_path: str) -> Optional[str]:
        """
        Detect audio file type for tagging.
        
        Args:
            file_path: Path to audio file
            
        Returns:
            File type ('mp3', 'wav', 'ogg', 'flac') or None
        """
        ext = Path(file_path).suffix.lower()
        type_map = {
            '.mp3': 'mp3',
            '.wav': 'wav',
            '.ogg': 'ogg',
            '.flac': 'flac',
            '.m4a': 'm4a',
        }
        return type_map.get(ext)
    
    def tag_file(
        self,
        file_path: str,
        bpm: float,
        key: str,
        camelot: Optional[str] = None,
        extra_tags: Optional[Dict[str, str]] = None,
        overwrite: bool = False,
        profile: str = "universal",
    ) -> bool:
        """
        Inject BPM and Key metadata into audio file.
        
        Args:
            file_path: Path to audio file
            bpm: Tempo in BPM
            key: Musical key (e.g., "C Major")
            camelot: Camelot wheel notation (e.g., "8B")
            extra_tags: Additional custom tags
            overwrite: Whether to overwrite existing tags
            profile: Tag profile ('universal', 'dj', 'ableton')
            
        Returns:
            True if successful, False otherwise
        """
        if not MUTAGEN_AVAILABLE:
            logger.error("Cannot tag file: mutagen not installed")
            return False
        
        file_path = Path(file_path)
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return False
        
        file_type = self.get_file_type(str(file_path))
        if not file_type:
            logger.warning(f"Unsupported file type: {file_path.suffix}")
            return False

        profile = (profile or "universal").strip().lower()
        if profile not in self.PROFILES:
            logger.warning(f"Unknown tag profile '{profile}', falling back to 'universal'")
            profile = "universal"
        
        try:
            if file_type == 'mp3':
                return self._tag_mp3(file_path, bpm, key, camelot, extra_tags, overwrite, profile)
            elif file_type == 'wav':
                return self._tag_wav(file_path, bpm, key, camelot, extra_tags, overwrite, profile)
            elif file_type == 'ogg':
                return self._tag_ogg(file_path, bpm, key, camelot, extra_tags, overwrite, profile)
            elif file_type == 'flac':
                return self._tag_flac(file_path, bpm, key, camelot, extra_tags, overwrite, profile)
            else:
                logger.warning(f"Tagging not implemented for: {file_type}")
                return False
        
        except Exception as e:
            logger.error(f"Failed to tag {file_path}: {e}")
            return False
    
    def _tag_mp3(
        self,
        file_path: Path,
        bpm: float,
        key: str,
        camelot: Optional[str],
        extra_tags: Optional[Dict[str, str]],
        overwrite: bool,
        profile: str,
    ) -> bool:
        """Tag MP3 file using ID3."""
        try:
            # Try to load existing tags, or create new ones
            try:
                tags = ID3(str(file_path))
                if overwrite:
                    tags.delete(str(file_path))
                    tags = ID3()
            except:
                tags = ID3()

            bpm_int = int(round(bpm))

            self._write_id3_common(tags, bpm_int, key, camelot, profile)

            # Add extra tags
            if extra_tags:
                for key_name, value in extra_tags.items():
                    self._discard_txxx(tags, key_name.upper())
                    tags.add(TXXX(desc=key_name.upper(), text=[str(value)]))

            tags.save(str(file_path), v2_version=4)
            logger.info(f"Tagged MP3: {file_path.name} (BPM: {bpm_int}, Key: {key}, Profile: {profile})")
            return True
        
        except Exception as e:
            logger.error(f"MP3 tagging failed: {e}")
            return False
    
    def _tag_wav(
        self,
        file_path: Path,
        bpm: float,
        key: str,
        camelot: Optional[str],
        extra_tags: Optional[Dict[str, str]],
        overwrite: bool,
        profile: str,
    ) -> bool:
        """Tag WAV file using ID3 in INFO chunk."""
        try:
            # WAV files can use ID3 tags
            try:
                tags = ID3(str(file_path))
                if overwrite:
                    tags.delete(str(file_path))
                    tags = ID3()
            except:
                tags = ID3()

            bpm_int = int(round(bpm))

            self._write_id3_common(tags, bpm_int, key, camelot, profile)

            # Add extra tags
            if extra_tags:
                for key_name, value in extra_tags.items():
                    self._discard_txxx(tags, key_name.upper())
                    tags.add(TXXX(desc=key_name.upper(), text=[str(value)]))

            tags.save(str(file_path), v2_version=4)
            logger.info(f"Tagged WAV: {file_path.name} (BPM: {bpm_int}, Key: {key}, Profile: {profile})")
            return True
        
        except Exception as e:
            logger.error(f"WAV tagging failed: {e}")
            return False
    
    def _tag_ogg(
        self,
        file_path: Path,
        bpm: float,
        key: str,
        camelot: Optional[str],
        extra_tags: Optional[Dict[str, str]],
        overwrite: bool,
        profile: str,
    ) -> bool:
        """Tag OGG file using Vorbis comments."""
        try:
            tags = OggVorbis(str(file_path))

            bpm_int = int(round(bpm))
            self._write_vorbis_common(tags, bpm_int, key, camelot, profile)

            # Add extra tags
            if extra_tags:
                for key_name, value in extra_tags.items():
                    tags[key_name.upper()] = str(value)

            tags.save()
            logger.info(f"Tagged OGG: {file_path.name} (BPM: {bpm_int}, Key: {key}, Profile: {profile})")
            return True
        
        except Exception as e:
            logger.error(f"OGG tagging failed: {e}")
            return False
    
    def _tag_flac(
        self,
        file_path: Path,
        bpm: float,
        key: str,
        camelot: Optional[str],
        extra_tags: Optional[Dict[str, str]],
        overwrite: bool,
        profile: str,
    ) -> bool:
        """Tag FLAC file using Vorbis comments."""
        try:
            tags = FLAC(str(file_path))

            bpm_int = int(round(bpm))
            self._write_vorbis_common(tags, bpm_int, key, camelot, profile)

            # Add extra tags
            if extra_tags:
                for key_name, value in extra_tags.items():
                    tags[key_name.upper()] = str(value)

            tags.save()
            logger.info(f"Tagged FLAC: {file_path.name} (BPM: {bpm_int}, Key: {key}, Profile: {profile})")
            return True
        
        except Exception as e:
            logger.error(f"FLAC tagging failed: {e}")
            return False
    
    def read_tags(self, file_path: str) -> Dict[str, Any]:
        """
        Read existing metadata from audio file.
        
        Args:
            file_path: Path to audio file
            
        Returns:
            Dictionary of metadata tags
        """
        if not MUTAGEN_AVAILABLE:
            logger.error("Cannot read tags: mutagen not installed")
            return {}

    @staticmethod
    def _discard_frames(tags: ID3, frame_id: str) -> None:
        for frame in tags.getall(frame_id):
            tags.discard(frame)

    @staticmethod
    def _discard_txxx(tags: ID3, desc: str) -> None:
        target = desc.upper()
        for frame in tags.getall('TXXX'):
            if getattr(frame, 'desc', '').upper() == target:
                tags.discard(frame)

    def _write_id3_common(self, tags: ID3, bpm_int: int, key: str, camelot: Optional[str], profile: str) -> None:
        key_with_cam = f"{key} ({camelot or 'Unknown'})"
        cam = camelot or ""

        # Universal core frames used broadly across players and DAWs.
        self._discard_frames(tags, 'TBPM')
        self._discard_frames(tags, 'TKEY')
        self._discard_frames(tags, 'TIT1')
        self._discard_frames(tags, 'COMM')
        self._discard_frames(tags, 'TCON')

        self._discard_txxx(tags, 'INITIAL_KEY')
        self._discard_txxx(tags, 'CAMELOT')
        self._discard_txxx(tags, 'KEY')
        self._discard_txxx(tags, 'BPMX_PROFILE')
        self._discard_txxx(tags, 'DJ_KEY')

        tags.add(TBPM(text=[str(bpm_int)]))
        tags.add(TKEY(text=[key]))
        tags.add(TXXX(desc='INITIAL_KEY', text=[key_with_cam]))
        tags.add(TXXX(desc='KEY', text=[key]))
        tags.add(TXXX(desc='CAMELOT', text=[cam]))
        tags.add(TXXX(desc='BPMX_PROFILE', text=[profile]))

        if profile in {'universal', 'dj'}:
            # Rekordbox/Serato compatibility hints commonly mirrored in TIT1/COMM.
            tags.add(TIT1(text=[f"{key} | {cam}".strip(" |")]))
            tags.add(COMM(encoding=3, lang='eng', desc='BPM-X', text=[f"KEY={key}; CAMELOT={cam}; BPM={bpm_int}"]))
            tags.add(TXXX(desc='DJ_KEY', text=[cam or key]))

        if profile == 'ableton':
            # Keep Ableton-focused profile cleaner and standards-first.
            tags.add(TCON(text=['BPM-X']))

    @staticmethod
    def _write_vorbis_common(tags: Any, bpm_int: int, key: str, camelot: Optional[str], profile: str) -> None:
        key_with_cam = f"{key} ({camelot or 'Unknown'})"
        cam = camelot or ""

        tags['BPM'] = str(bpm_int)
        tags['INITIAL_KEY'] = key_with_cam
        tags['KEY'] = key
        tags['CAMELOT'] = cam
        tags['BPMX_PROFILE'] = profile

        if profile in {'universal', 'dj'}:
            tags['GROUPING'] = f"{key} | {cam}".strip(" |")
            tags['COMMENT'] = f"KEY={key}; CAMELOT={cam}; BPM={bpm_int}"
            tags['DJ_KEY'] = cam or key
        
        file_path = Path(file_path)
        file_type = self.get_file_type(str(file_path))
        
        try:
            if file_type == 'mp3':
                tags = ID3(str(file_path))
            elif file_type == 'ogg':
                tags = OggVorbis(str(file_path))
            elif file_type == 'flac':
                tags = FLAC(str(file_path))
            else:
                logger.warning(f"Tag reading not supported for: {file_type}")
                return {}
            
            result = {}
            
            # Extract common fields
            if hasattr(tags, 'get'):
                for key in ['BPM', 'INITIAL_KEY', 'CAMELOT', 'TIT2', 'TPE1']:
                    if key in tags:
                        result[key] = str(tags[key])
            
            logger.info(f"Read tags from {file_path.name}: {result}")
            return result
        
        except Exception as e:
            logger.warning(f"Could not read tags: {e}")
            return {}
