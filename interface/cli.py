"""
Command-Line Interface for BPM-X
Fast, scriptable interface for batch operations and quick analysis.
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

from utils.logger import setup_logger, get_logger
from utils.config_loader import ConfigLoader
from core import BPMDetector, KeyDetector, AudioAnalyzer
from core.translator import KeyTranslator
from modules import MetaTagger, FileOrganizer, EnergyAnalyzer


def setup_commands(parser: argparse.ArgumentParser) -> None:
    """Configure CLI subcommands."""
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Analyze command
    analyze_parser = subparsers.add_parser(
        'analyze',
        help='Analyze BPM and Key from audio file(s)'
    )
    analyze_parser.add_argument(
        'files',
        nargs='+',
        help='Audio file(s) to analyze'
    )
    analyze_parser.add_argument(
        '--format',
        choices=['json', 'table', 'simple'],
        default='table',
        help='Output format'
    )
    
    # Tag command
    tag_parser = subparsers.add_parser(
        'tag',
        help='Tag audio file(s) with BPM/Key metadata'
    )
    tag_parser.add_argument(
        'files',
        nargs='+',
        help='Audio file(s) to tag'
    )
    tag_parser.add_argument(
        '--bpm',
        type=float,
        help='Manual BPM (auto-detect if not provided)'
    )
    tag_parser.add_argument(
        '--key',
        help='Manual key (auto-detect if not provided)'
    )
    tag_parser.add_argument(
        '--overwrite',
        action='store_true',
        help='Overwrite existing tags'
    )
    
    # Organize command
    org_parser = subparsers.add_parser(
        'organize',
        help='Organize audio file(s) into library structure'
    )
    org_parser.add_argument(
        'path',
        help='File or directory to organize'
    )
    org_parser.add_argument(
        '--dest',
        default='data/library',
        help='Library destination directory'
    )
    org_parser.add_argument(
        '--move',
        action='store_true',
        help='Move instead of copy'
    )
    org_parser.add_argument(
        '--template',
        help='Custom naming template'
    )
    
    # Batch command
    batch_parser = subparsers.add_parser(
        'batch',
        help='Batch process directory: analyze, tag, and organize'
    )
    batch_parser.add_argument(
        'source',
        help='Source directory with audio files'
    )
    batch_parser.add_argument(
        '--dest',
        default='data/library',
        help='Library destination'
    )
    batch_parser.add_argument(
        '--move',
        action='store_true',
        help='Move files instead of copy'
    )
    batch_parser.add_argument(
        '--skip-tag',
        action='store_true',
        help='Skip metadata tagging'
    )
    batch_parser.add_argument(
        '--skip-organize',
        action='store_true',
        help='Skip file organization'
    )

    # GUI command
    subparsers.add_parser(
        'gui',
        help='Launch BPM-X desktop GUI'
    )


def format_analysis_output(analysis: dict, format: str = 'table') -> str:
    """Format analysis results for display."""
    if format == 'json':
        import json
        return json.dumps(analysis, indent=2, default=str)
    
    elif format == 'simple':
        return f"{Path(analysis['file']).name}: {analysis['bpm']:.1f} BPM, {analysis['key']}"
    
    else:  # table
        return (
            f"\nFile: {analysis['file']}\n"
            f"  BPM: {analysis['bpm']:.1f}\n"
            f"  Key: {analysis['key']}\n"
            f"  Confidence (BPM): {analysis['bpm_metadata'].get('confidence', 'N/A')}\n"
            f"  Confidence (Key): {analysis['key_metadata'].get('confidence', 'N/A')}\n"
        )


def cmd_analyze(args) -> int:
    """Handle analyze command."""
    logger = get_logger(__name__)
    analyzer = AudioAnalyzer()
    translator = KeyTranslator()
    
    results = []
    for file_path in args.files:
        try:
            logger.info(f"Analyzing: {file_path}")
            analysis = analyzer.analyze(file_path)
            camelot = translator.to_camelot(analysis['key'])
            analysis['camelot'] = camelot
            results.append(analysis)
            print(format_analysis_output(analysis, args.format))
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            return 1
    
    return 0


def cmd_tag(args) -> int:
    """Handle tag command."""
    logger = get_logger(__name__)
    analyzer = AudioAnalyzer()
    tagger = MetaTagger()
    translator = KeyTranslator()
    
    for file_path in args.files:
        try:
            logger.info(f"Processing: {file_path}")
            
            # Auto-detect or use manual values
            if args.bpm and args.key:
                bpm = args.bpm
                key = args.key
            else:
                analysis = analyzer.analyze(file_path)
                bpm = analysis['bpm']
                key = analysis['key']
            
            camelot = translator.to_camelot(key)
            
            # Tag file
            success = tagger.tag_file(
                file_path,
                bpm,
                key,
                camelot,
                overwrite=args.overwrite
            )
            
            if success:
                print(f"✓ Tagged: {Path(file_path).name}")
            else:
                print(f"✗ Failed to tag: {Path(file_path).name}")
                return 1
        
        except Exception as e:
            logger.error(f"Tagging failed: {e}")
            return 1
    
    return 0


def cmd_organize(args) -> int:
    """Handle organize command."""
    logger = get_logger(__name__)
    analyzer = AudioAnalyzer()
    organizer = FileOrganizer(args.dest)
    translator = KeyTranslator()
    
    path = Path(args.path)
    
    if path.is_file():
        # Single file
        try:
            logger.info(f"Organizing: {path.name}")
            analysis = analyzer.analyze(str(path))
            camelot = translator.to_camelot(analysis['key'])
            
            result = organizer.organize_file(
                str(path),
                analysis['bpm'],
                analysis['key'],
                camelot,
                filename_template=args.template,
                move=args.move
            )
            
            if result:
                print(f"✓ Organized: {result.relative_to(Path(args.dest).parent)}")
            else:
                print(f"✗ Failed to organize: {path.name}")
                return 1
        
        except Exception as e:
            logger.error(f"Organization failed: {e}")
            return 1
    
    elif path.is_dir():
        # Directory of files
        stats = organizer.organize_directory(
            str(path),
            analyzer,
            move=args.move,
            filename_template=args.template
        )
        print(
            f"\nOrganization complete:\n"
            f"  Success: {stats['success']}\n"
            f"  Failed: {stats['failed']}\n"
            f"  Skipped: {stats['skipped']}"
        )
    
    else:
        logger.error(f"Not a file or directory: {path}")
        return 1
    
    return 0


def cmd_batch(args) -> int:
    """Handle batch command."""
    logger = get_logger(__name__)
    analyzer = AudioAnalyzer()
    tagger = MetaTagger()
    organizer = FileOrganizer(args.dest)
    translator = KeyTranslator()
    
    source = Path(args.source)
    if not source.is_dir():
        logger.error(f"Source is not a directory: {source}")
        return 1
    
    audio_exts = {'.mp3', '.wav', '.flac', '.ogg', '.m4a'}
    audio_files = [
        f for f in source.rglob('*')
        if f.suffix.lower() in audio_exts
    ]
    
    logger.info(f"Found {len(audio_files)} audio files")
    
    success_count = 0
    failed_count = 0
    
    for audio_file in audio_files:
        try:
            logger.info(f"Processing: {audio_file.name}")
            analysis = analyzer.analyze(str(audio_file))
            camelot = translator.to_camelot(analysis['key'])
            
            # Tag
            if not args.skip_tag:
                tagger.tag_file(
                    str(audio_file),
                    analysis['bpm'],
                    analysis['key'],
                    camelot
                )
            
            # Organize
            if not args.skip_organize:
                organizer.organize_file(
                    str(audio_file),
                    analysis['bpm'],
                    analysis['key'],
                    camelot,
                    move=args.move
                )
            
            success_count += 1
            print(f"✓ {audio_file.name}: {analysis['bpm']:.0f} BPM, {camelot}")
        
        except Exception as e:
            logger.warning(f"Failed to process {audio_file.name}: {e}")
            failed_count += 1
    
    print(f"\nBatch complete: {success_count} processed, {failed_count} failed")
    return 0 if failed_count == 0 else 1


def run_cli():
    """Run CLI interface."""
    parser = argparse.ArgumentParser(
        description='BPM-X: Professional music library organizer',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  bpm-x analyze track.mp3
  bpm-x tag *.mp3
  bpm-x organize /path/to/samples --move
  bpm-x batch data/workspace --dest data/library --move
    bpm-x gui
        """
    )
    
    parser.add_argument(
        '--config',
        help='Config file path'
    )
    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help='Verbose logging'
    )
    
    setup_commands(parser)
    args = parser.parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    setup_logger(level=log_level)
    logger = get_logger(__name__)
    
    # Load config
    if args.config:
        config = ConfigLoader(args.config)
    else:
        config = ConfigLoader()
    
    logger.info(f"BPM-X started with config from: {config.config_file}")
    
    # Route commands
    if args.command == 'analyze':
        return cmd_analyze(args)
    elif args.command == 'tag':
        return cmd_tag(args)
    elif args.command == 'organize':
        return cmd_organize(args)
    elif args.command == 'batch':
        return cmd_batch(args)
    elif args.command == 'gui':
        from interface.gui import run_gui
        run_gui()
        return 0
    else:
        parser.print_help()
        return 0


if __name__ == '__main__':
    sys.exit(run_cli())
