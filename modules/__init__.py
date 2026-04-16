"""
Modules Package - Higher-level functionality for tagging, organization, and analysis
"""

from .meta_tagger import MetaTagger
from .file_auto import FileOrganizer
from .energy import EnergyAnalyzer
from .audio_finisher import AudioFinisher

__all__ = ['MetaTagger', 'FileOrganizer', 'EnergyAnalyzer', 'AudioFinisher']
