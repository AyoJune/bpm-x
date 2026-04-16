"""BPM-X desktop GUI built with CustomTkinter."""

from __future__ import annotations

import csv
import json
import platform
import queue
import shutil
import subprocess
import threading
import tkinter as tk
from pathlib import Path
from tkinter import TclError, filedialog, messagebox
from typing import Any

import customtkinter as ctk

from core.engine import AudioAnalyzer
from core.translator import KeyTranslator
from modules.audio_finisher import AudioFinisher
from modules.file_auto import FileOrganizer
from modules.meta_tagger import MetaTagger

try:
    import winsound
    HAS_WINSOUND = True
except ImportError:
    HAS_WINSOUND = False


IS_MACOS = platform.system() == "Darwin"

try:
    from pydub import AudioSegment
    from pydub.playback import play as pydub_play
    HAS_PYDUB_PLAYBACK = True
except Exception:
    HAS_PYDUB_PLAYBACK = False

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    HAS_DND = True
except ImportError:
    try:
        from TkinterDnD2 import DND_FILES, TkinterDnD  # type: ignore
        HAS_DND = True
    except ImportError:
        DND_FILES = None
        TkinterDnD = None
        HAS_DND = False


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

ACCENT_CYAN = "#00CCFF"
PANEL_BG = "#0A0D14"
CARD_BG = "#111827"
TEXT_MUTED = "#8FA0B5"


# Camelot colors tuned for quick at-a-glance key recognition.
CAMELOT_COLORS = {
    "1A": "#2D7FF9", "2A": "#3C70F0", "3A": "#5862E6", "4A": "#7455DD",
    "5A": "#9048D3", "6A": "#D64545", "7A": "#DF6C45", "8A": "#E89444",
    "9A": "#D4B13E", "10A": "#ADC63D", "11A": "#7FBC4A", "12A": "#48B16D",
    "1B": "#24C7FF", "2B": "#20B8EA", "3B": "#1AA9D5", "4B": "#159AC0",
    "5B": "#108BAB", "6B": "#2C7CC3", "7B": "#5D6FD5", "8B": "#845FD6",
    "9B": "#AD52CC", "10B": "#C548AF", "11B": "#D6538E", "12B": "#DF6F75",
}


class HoverTip:
    """Minimal hover tooltip for dense result-table metadata."""

    def __init__(self, widget: tk.Widget, text: str) -> None:
        self.widget = widget
        self.text = text
        self.tip_window: tk.Toplevel | None = None
        self.widget.bind("<Enter>", self._show)
        self.widget.bind("<Leave>", self._hide)

    def _show(self, _event: tk.Event) -> None:
        if self.tip_window is not None:
            return

        self.tip_window = tk.Toplevel(self.widget)
        self.tip_window.wm_overrideredirect(True)
        self.tip_window.attributes("-topmost", True)

        x = self.widget.winfo_rootx() + 18
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
        self.tip_window.wm_geometry(f"+{x}+{y}")

        label = tk.Label(
            self.tip_window,
            text=self.text,
            justify="left",
            bg="#09111E",
            fg="#DCE8F5",
            bd=1,
            relief="solid",
            padx=8,
            pady=6,
            font=("Segoe UI", 9),
        )
        label.pack()

    def _hide(self, _event: tk.Event) -> None:
        if self.tip_window is not None:
            self.tip_window.destroy()
            self.tip_window = None


class BPMXGUI(ctk.CTk):
    """Desktop application for BPM-X batch analysis and tagging."""

    def __init__(self) -> None:
        super().__init__()

        self.title("BPM-X | Professional Audio Sniper")
        self.geometry("1120x720")
        self.minsize(940, 640)
        self.configure(fg_color=PANEL_BG)

        self.ui_queue: queue.Queue[tuple[str, object]] = queue.Queue()

        self.analyzer = AudioAnalyzer()
        self.translator = KeyTranslator()
        self.tagger = MetaTagger()
        self.finisher = AudioFinisher()
        self.organizer = FileOrganizer("data/library")

        self.selected_path: Path | None = None
        self.selected_paths: list[Path] = []
        self.is_running = False
        self._result_rows: list[ctk.CTkFrame] = []
        self._result_records: list[dict[str, Any]] = []
        self._dnd_status_text = "DnD: Unknown"
        self.btn_fix_dnd: ctk.CTkButton | None = None
        self.trimmed_count = 0
        self.normalized_count = 0
        self.lufs_count = 0
        self.copies_count = 0

        self._build_layout()
        self._start_ui_polling()

    @staticmethod
    def _ffmpeg_install_hint() -> str:
        if IS_MACOS:
            return "brew install ffmpeg"
        return "winget install ffmpeg"

    @staticmethod
    def _dnd_help_text() -> str:
        if IS_MACOS:
            return (
                "Drag-and-Drop Setup\n\n"
                "tkdnd (Tkinter drag-and-drop) may require extra system linkage on macOS.\n\n"
                "Option 1 - Use SELECT Button:\n"
                "Click 'Select Samples' above and choose one or more audio files directly.\n\n"
                "Option 2 - Fix tkdnd Linkage (Advanced):\n"
                "1. Install: pip install tkinterdnd2 TkinterDnD2-Universal\n"
                "2. Ensure Tcl/Tk is available to your Python build\n"
                "3. Restart the application after installation\n\n"
                "Note: Fallback mode is active and fully functional. No action is required to use BPM-X."
            )

        return (
            "Drag-and-Drop Setup\n\n"
            "tkdnd (Tkinter drag-and-drop) may require extra system linkage on Windows.\n\n"
            "Option 1 - Use SELECT Button:\n"
            "Click 'Select Samples' above and choose one or more audio files directly.\n\n"
            "Option 2 - Fix tkdnd Linkage (Advanced):\n"
            "1. Install: pip install tkinterdnd2 TkinterDnD2-Universal\n"
            "2. Download tkdnd binary from GitHub (tkdnd/tkdnd releases)\n"
            "3. Extract to: {Python}/tcl/tkdnd{version}\n"
            "4. Restart the application\n\n"
            "Note: Fallback mode is active and fully functional. No action is required to use BPM-X."
        )

    def _build_layout(self) -> None:
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar = ctk.CTkFrame(self, width=250, corner_radius=0, fg_color="#0E1525")
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)

        self.logo = ctk.CTkLabel(
            self.sidebar,
            text="BPM-X",
            font=("Orbitron", 30, "bold"),
            text_color=ACCENT_CYAN,
        )
        self.logo.pack(padx=24, pady=(26, 6), anchor="w")

        self.subtitle = ctk.CTkLabel(
            self.sidebar,
            text="Audio Sniper",
            text_color=TEXT_MUTED,
            font=("Orbitron", 13),
        )
        self.subtitle.pack(padx=24, pady=(0, 20), anchor="w")

        ffmpeg_row = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        ffmpeg_row.pack(padx=24, pady=(0, 18), anchor="w")

        ffmpeg_ok = shutil.which("ffmpeg") is not None
        ffmpeg_color = ACCENT_CYAN if ffmpeg_ok else "#E74C3C"
        ffmpeg_text = "FFmpeg: detected" if ffmpeg_ok else "FFmpeg: missing"
        self.ffmpeg_badge = ctk.CTkLabel(
            ffmpeg_row,
            text=ffmpeg_text,
            fg_color=ffmpeg_color,
            corner_radius=8,
            padx=10,
            pady=4,
            font=("Orbitron", 12, "bold"),
        )
        self.ffmpeg_badge.pack(side="left")

        self.ffmpeg_recheck_btn = ctk.CTkButton(
            ffmpeg_row,
            text="↻",
            width=28,
            height=28,
            corner_radius=8,
            fg_color="#1F2D45",
            hover_color="#2A3F62",
            text_color=TEXT_MUTED,
            font=("Segoe UI", 14),
            command=self._recheck_ffmpeg,
        )
        self.ffmpeg_recheck_btn.pack(side="left", padx=(8, 0))
        HoverTip(
            self.ffmpeg_recheck_btn,
            f"Re-check FFmpeg availability\n(run after: {self._ffmpeg_install_hint()})",
        )

        self.btn_select = ctk.CTkButton(
            self.sidebar,
            text="Select Samples",
            command=self.select_path,
            height=40,
            corner_radius=10,
            fg_color=ACCENT_CYAN,
            hover_color="#1EA5C7",
            text_color="#081018",
        )
        self.btn_select.pack(padx=24, pady=6, fill="x")

        self.btn_run = ctk.CTkButton(
            self.sidebar,
            text="Run Batch",
            command=self.start_batch,
            height=40,
            corner_radius=10,
            state="disabled",
            fg_color="#1F2D45",
            hover_color="#2A3F62",
        )
        self.btn_run.pack(padx=24, pady=6, fill="x")

        self.btn_export_csv = ctk.CTkButton(
            self.sidebar,
            text="Export CSV",
            command=self.export_csv,
            height=34,
            corner_radius=10,
            state="disabled",
            fg_color="#1F2D45",
            hover_color="#2A3F62",
        )
        self.btn_export_csv.pack(padx=24, pady=(10, 6), fill="x")

        self.btn_export_json = ctk.CTkButton(
            self.sidebar,
            text="Export JSON",
            command=self.export_json,
            height=34,
            corner_radius=10,
            state="disabled",
            fg_color="#1F2D45",
            hover_color="#2A3F62",
        )
        self.btn_export_json.pack(padx=24, pady=6, fill="x")

        self.move_var = ctk.BooleanVar(value=False)
        self.tag_var = ctk.BooleanVar(value=True)
        self.organize_var = ctk.BooleanVar(value=True)
        self.trim_var = ctk.BooleanVar(value=False)
        self.normalize_var = ctk.BooleanVar(value=False)
        self.lufs_var = ctk.BooleanVar(value=False)
        self.keep_originals_var = ctk.BooleanVar(value=False)
        self.tag_profile_var = ctk.StringVar(value="Universal")

        self.switch_move = ctk.CTkSwitch(self.sidebar, text="Move files", variable=self.move_var)
        self.switch_move.pack(padx=24, pady=(12, 4), anchor="w")

        self.switch_tag = ctk.CTkSwitch(self.sidebar, text="Write tags", variable=self.tag_var)
        self.switch_tag.pack(padx=24, pady=4, anchor="w")

        self.switch_organize = ctk.CTkSwitch(self.sidebar, text="Organize library", variable=self.organize_var)
        self.switch_organize.pack(padx=24, pady=4, anchor="w")

        self.switch_trim = ctk.CTkSwitch(self.sidebar, text="Auto-Trim Silence", variable=self.trim_var)
        self.switch_trim.pack(padx=24, pady=4, anchor="w")

        self.switch_normalize = ctk.CTkSwitch(self.sidebar, text="Normalize Peaks (-1 dB)", variable=self.normalize_var)
        self.switch_normalize.pack(padx=24, pady=4, anchor="w")

        self.switch_lufs = ctk.CTkSwitch(self.sidebar, text="LUFS Normalize (-14 LUFS)", variable=self.lufs_var)
        self.switch_lufs.pack(padx=24, pady=4, anchor="w")

        self.switch_keep_originals = ctk.CTkSwitch(
            self.sidebar,
            text="Keep Originals",
            variable=self.keep_originals_var,
        )
        self.switch_keep_originals.pack(padx=24, pady=4, anchor="w")

        self.profile_label = ctk.CTkLabel(
            self.sidebar,
            text="DAW Profile",
            text_color=TEXT_MUTED,
            font=("Segoe UI", 11, "bold"),
        )
        self.profile_label.pack(padx=24, pady=(8, 2), anchor="w")

        self.profile_menu = ctk.CTkOptionMenu(
            self.sidebar,
            values=["Universal", "DJ", "Ableton"],
            variable=self.tag_profile_var,
            fg_color="#1F2D45",
            button_color="#2A3F62",
            button_hover_color="#35517E",
            dropdown_fg_color="#172238",
            text_color="#DCE8F5",
            dropdown_text_color="#DCE8F5",
        )
        self.profile_menu.pack(padx=24, pady=(0, 4), fill="x")

        self.path_label = ctk.CTkLabel(
            self.sidebar,
            text="No input selected",
            wraplength=210,
            text_color=TEXT_MUTED,
            justify="left",
        )
        self.path_label.pack(padx=24, pady=(14, 0), anchor="w")

        self.dnd_status_label = ctk.CTkLabel(
            self.sidebar,
            text=self._dnd_status_text,
            wraplength=210,
            text_color=TEXT_MUTED,
            justify="left",
            font=("Segoe UI", 11, "bold"),
        )
        self.dnd_status_label.pack(padx=24, pady=(10, 0), anchor="w")

        self.main_frame = ctk.CTkFrame(self, corner_radius=16, fg_color=CARD_BG)
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(4, weight=1)

        self.drop_zone = ctk.CTkFrame(
            self.main_frame,
            corner_radius=16,
            border_width=2,
            border_color=ACCENT_CYAN,
            fg_color="#0C1424",
            height=140,
        )
        self.drop_zone.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        self.drop_zone.grid_propagate(False)

        self.drop_label = ctk.CTkLabel(
            self.drop_zone,
            text="Drop sample files or folders here",
            font=("Orbitron", 18, "bold"),
            text_color=ACCENT_CYAN,
        )
        self.drop_label.place(relx=0.5, rely=0.44, anchor="center")

        self.drop_hint = ctk.CTkLabel(
            self.drop_zone,
            text="Supported: .mp3 .wav .flac .ogg .m4a .aif .aiff",
            text_color=TEXT_MUTED,
            font=("Segoe UI", 13),
        )
        self.drop_hint.place(relx=0.5, rely=0.67, anchor="center")

        if HAS_DND and hasattr(self.drop_zone, "drop_target_register"):
            try:
                has_tkdnd = bool(self.tk.call("info", "commands", "tkdnd::drop_target"))
                if has_tkdnd:
                    self.drop_zone.drop_target_register(DND_FILES)
                    self.drop_zone.dnd_bind("<<Drop>>", self._on_drop)
                    self._dnd_status_text = "DnD: Active"
                else:
                    self.drop_hint.configure(
                        text="Drag-and-drop unavailable (tkdnd missing). Use Select File/Folder."
                    )
                    self._dnd_status_text = "DnD: System Linkage Required (Using Fallback)"
            except TclError:
                self.drop_hint.configure(
                    text="Drag-and-drop unavailable (tkdnd error). Use Select File/Folder."
                )
                self._dnd_status_text = "DnD: System Linkage Required (Using Fallback)"
        else:
            self._dnd_status_text = "DnD: System Linkage Required (Using Fallback)"

        self._update_dnd_status_ui()

        self.progress = ctk.CTkProgressBar(self.main_frame)
        self.progress.grid(row=1, column=0, sticky="ew", padx=20, pady=10)
        self.progress.configure(progress_color=ACCENT_CYAN, fg_color="#1E293B")
        self.progress.set(0.0)

        self.stats_row = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.stats_row.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 6))
        self.stats_row.grid_columnconfigure(0, weight=1)

        self.stats_label = ctk.CTkLabel(
            self.stats_row,
            text="Waiting for input",
            text_color=TEXT_MUTED,
            anchor="w",
        )
        self.stats_label.grid(row=0, column=0, sticky="w")

        self.master_stats_label = ctk.CTkLabel(
            self.stats_row,
            text="[ Trimmed: 0 | Normalized: 0 | LUFS: 0 | Copies: 0 ]",
            text_color="#8FB7D8",
            anchor="e",
            font=("Orbitron", 10, "bold"),
        )
        self.master_stats_label.grid(row=0, column=1, sticky="e")

        self.results_header = ctk.CTkFrame(self.main_frame, fg_color="#0F1A2D", corner_radius=10)
        self.results_header.grid(row=3, column=0, sticky="ew", padx=20, pady=(4, 6))
        self.results_header.grid_columnconfigure(0, weight=4)
        self.results_header.grid_columnconfigure(1, weight=1)
        self.results_header.grid_columnconfigure(2, weight=1)
        self.results_header.grid_columnconfigure(3, weight=1)
        self.results_header.grid_columnconfigure(4, weight=2)
        self.results_header.grid_columnconfigure(5, weight=1)
        self.results_header.grid_columnconfigure(6, weight=1)
        self.results_header.grid_columnconfigure(7, weight=1)
        self.results_header.grid_columnconfigure(8, weight=1)

        ctk.CTkLabel(self.results_header, text="FILE", text_color=TEXT_MUTED, font=("Orbitron", 11, "bold")).grid(
            row=0, column=0, sticky="w", padx=10, pady=8
        )
        ctk.CTkLabel(self.results_header, text="BPM", text_color=TEXT_MUTED, font=("Orbitron", 11, "bold")).grid(
            row=0, column=1, sticky="w", padx=10, pady=8
        )
        ctk.CTkLabel(self.results_header, text="KEY", text_color=TEXT_MUTED, font=("Orbitron", 11, "bold")).grid(
            row=0, column=2, sticky="w", padx=10, pady=8
        )
        ctk.CTkLabel(self.results_header, text="CAMELOT", text_color=TEXT_MUTED, font=("Orbitron", 11, "bold")).grid(
            row=0, column=3, sticky="w", padx=10, pady=8
        )
        ctk.CTkLabel(self.results_header, text="HARMONICS", text_color=TEXT_MUTED, font=("Orbitron", 11, "bold")).grid(
            row=0, column=4, sticky="w", padx=10, pady=8
        )
        ctk.CTkLabel(self.results_header, text="ENERGY", text_color=TEXT_MUTED, font=("Orbitron", 11, "bold")).grid(
            row=0, column=5, sticky="w", padx=10, pady=8
        )
        ctk.CTkLabel(self.results_header, text="DANCE", text_color=TEXT_MUTED, font=("Orbitron", 11, "bold")).grid(
            row=0, column=6, sticky="w", padx=10, pady=8
        )
        ctk.CTkLabel(self.results_header, text="CONF", text_color=TEXT_MUTED, font=("Orbitron", 11, "bold")).grid(
            row=0, column=7, sticky="w", padx=10, pady=8
        )
        ctk.CTkLabel(self.results_header, text="PREVIEW", text_color=TEXT_MUTED, font=("Orbitron", 11, "bold")).grid(
            row=0, column=8, sticky="w", padx=10, pady=8
        )

        self.results_frame = ctk.CTkScrollableFrame(
            self.main_frame,
            corner_radius=12,
            fg_color="#0B1221",
        )
        self.results_frame.grid(row=4, column=0, sticky="nsew", padx=20, pady=(0, 12))
        self.results_frame.grid_columnconfigure(0, weight=1)
        self._add_info_row("BPM-X ready. Select or drop files to begin.")

        self.camelot_strip = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.camelot_strip.grid(row=5, column=0, sticky="ew", padx=20, pady=(0, 18))
        self._render_camelot_palette()

    def _render_camelot_palette(self) -> None:
        for idx, key in enumerate(sorted(CAMELOT_COLORS.keys(), key=self._camelot_sort)):
            badge = ctk.CTkLabel(
                self.camelot_strip,
                text=key,
                fg_color=CAMELOT_COLORS[key],
                text_color="#061018",
                corner_radius=7,
                width=42,
                height=24,
                font=("Orbitron", 11, "bold"),
            )
            badge.grid(row=0, column=idx, padx=3, pady=3)

    def _update_dnd_status_ui(self) -> None:
        dnd_active = self._dnd_status_text == "DnD: Active"
        dnd_color = "#2ECC71" if dnd_active else "#F39C12"
        self.dnd_status_label.configure(text=self._dnd_status_text, text_color=dnd_color)

        needs_fix_help = not dnd_active
        if needs_fix_help and self.btn_fix_dnd is None:
            self.btn_fix_dnd = ctk.CTkButton(
                self.sidebar,
                text="? Fix DnD",
                command=self.show_dnd_help,
                height=30,
                corner_radius=8,
                fg_color="#F39C12",
                hover_color="#E67E22",
                text_color="#081018",
                font=("Segoe UI", 11, "bold"),
            )
            self.btn_fix_dnd.pack(padx=24, pady=(8, 0), fill="x")
        elif not needs_fix_help and self.btn_fix_dnd is not None:
            self.btn_fix_dnd.destroy()
            self.btn_fix_dnd = None

    def _recheck_ffmpeg(self) -> None:
        """Live-recheck FFmpeg availability without restarting the app."""
        # Invalidate shutil's which() cache for ffmpeg between calls.
        shutil._which_cache.clear() if hasattr(shutil, "_which_cache") else None
        ffmpeg_ok = shutil.which("ffmpeg") is not None
        self.ffmpeg_badge.configure(
            text="FFmpeg: detected" if ffmpeg_ok else "FFmpeg: missing",
            fg_color=ACCENT_CYAN if ffmpeg_ok else "#E74C3C",
        )
        status = (
            "FFmpeg detected — MP3 preview enabled."
            if ffmpeg_ok
            else f"FFmpeg not found. Run: {self._ffmpeg_install_hint()}"
        )
        self.ui_queue.put(("log", status))

    @staticmethod
    def _camelot_sort(value: str) -> tuple[int, int]:
        num = int(value[:-1])
        mode = 0 if value.endswith("A") else 1
        return num, mode

    def _add_info_row(self, message: str, error: bool = False) -> None:
        row = ctk.CTkFrame(self.results_frame, fg_color="#101A30", corner_radius=8)
        row.grid(row=len(self._result_rows), column=0, sticky="ew", padx=6, pady=4)
        row.grid_columnconfigure(0, weight=1)
        color = "#FF7A7A" if error else "#B4C3D6"
        ctk.CTkLabel(row, text=message, text_color=color, anchor="w").grid(
            row=0, column=0, sticky="ew", padx=10, pady=8
        )
        self._result_rows.append(row)

    def _add_result_row(self, payload: dict[str, Any]) -> None:
        file_name = str(payload.get("file", "Unknown"))
        file_path = str(payload.get("path", ""))
        bpm_text = str(payload.get("bpm", "--"))
        bpm_source = str(payload.get("bpm_source", "analysis"))
        key_text = str(payload.get("key", "--"))
        camelot = str(payload.get("camelot", "--"))
        is_error = bool(payload.get("error", False))
        confidence_value = payload.get("confidence")
        finish_tags = payload.get("finish_tags", [])
        top_candidates = payload.get("top_candidates", [])

        tag_set = {str(tag).upper() for tag in finish_tags} if isinstance(finish_tags, list) else set()
        if "TRIMMED" in tag_set:
            self.trimmed_count += 1
        if "NORM" in tag_set:
            self.normalized_count += 1
        if "LUFS" in tag_set:
            self.lufs_count += 1
        if "COPY" in tag_set:
            self.copies_count += 1
        if tag_set:
            self._update_master_stats_label()

        # Compute harmonic neighbors
        harmonics_text = "--"
        if not is_error and key_text != "--" and camelot != "--":
            try:
                compat = self.translator.get_compatible_keys(camelot)
                # Show adjacent keys + relative major/minor
                neighbors = compat.get("same_mode", []) + [compat.get("relative_major_minor", "")]
                neighbors = [n for n in neighbors if n and n != camelot][:3]
                harmonics_text = ", ".join(neighbors)
            except Exception:
                harmonics_text = "--"

        row_fg = "#161F33" if not is_error else "#2A1520"
        row = ctk.CTkFrame(self.results_frame, fg_color=row_fg, corner_radius=8)
        row.grid(row=len(self._result_rows), column=0, sticky="ew", padx=6, pady=4)
        row.grid_columnconfigure(0, weight=4)
        row.grid_columnconfigure(1, weight=1)
        row.grid_columnconfigure(2, weight=1)
        row.grid_columnconfigure(3, weight=1)
        row.grid_columnconfigure(4, weight=2)
        row.grid_columnconfigure(5, weight=1)
        row.grid_columnconfigure(6, weight=1)
        row.grid_columnconfigure(7, weight=1)
        row.grid_columnconfigure(8, weight=1)

        name_color = "#E4EEF7" if not is_error else "#FF9AA2"
        name_cell = ctk.CTkFrame(row, fg_color="transparent")
        name_cell.grid(row=0, column=0, sticky="w", padx=10, pady=8)
        ctk.CTkLabel(name_cell, text=file_name, text_color=name_color, anchor="w").pack(side="left")

        # Finisher chips: quick visual confirmation that cleanup ran.
        if isinstance(finish_tags, list):
            for tag in finish_tags:
                tag_text = str(tag).upper()
                if tag_text == "TRIMMED":
                    tag_color = "#2ED8A3"
                elif tag_text == "NORM":
                    tag_color = "#00CCFF"
                elif tag_text == "LUFS":
                    tag_color = "#F4C542"
                elif tag_text == "COPY":
                    tag_color = "#A78BFA"
                else:
                    tag_color = "#6B7C93"
                ctk.CTkLabel(
                    name_cell,
                    text=tag_text,
                    fg_color=tag_color,
                    text_color="#061018",
                    corner_radius=6,
                    padx=6,
                    pady=1,
                    font=("Orbitron", 9, "bold"),
                ).pack(side="left", padx=(6, 0))
        # BPM — pin indicator when value was read from the filename label.
        bpm_color = ACCENT_CYAN if bpm_source == "filename" else "#B8D7FF"
        bpm_display = f"{bpm_text} ✦" if bpm_source == "filename" else bpm_text
        bpm_label = ctk.CTkLabel(row, text=bpm_display, text_color=bpm_color, anchor="w")
        bpm_label.grid(row=0, column=1, sticky="w", padx=10, pady=8)
        if bpm_source == "filename":
            HoverTip(bpm_label, "BPM read from filename label\n(100% confidence — human-tagged)")
        ctk.CTkLabel(row, text=key_text, text_color="#D1D9E6", anchor="w").grid(
            row=0, column=2, sticky="w", padx=10, pady=8
        )

        chip_color = CAMELOT_COLORS.get(camelot, "#405070")
        ctk.CTkLabel(
            row,
            text=camelot,
            fg_color=chip_color,
            text_color="#081018",
            font=("Orbitron", 11, "bold"),
            corner_radius=7,
            width=64,
            height=24,
        ).grid(row=0, column=3, sticky="w", padx=10, pady=8)

        # Harmonics display
        harmonics_color = "#B8D7FF" if not is_error else "#999999"
        ctk.CTkLabel(row, text=harmonics_text, text_color=harmonics_color, anchor="w", font=("Segoe UI", 10)).grid(
            row=0, column=4, sticky="w", padx=10, pady=8
        )

        # Energy level (1–10) — color-graded like a heat map.
        energy_value = payload.get("energy", 0)
        if isinstance(energy_value, int) and energy_value > 0:
            # 1–3: cool blue, 4–6: amber, 7–10: hot red-orange
            if energy_value <= 3:
                energy_color = "#4A90D9"
            elif energy_value <= 6:
                energy_color = "#F4C542"
            else:
                energy_color = "#FF6B35"
            energy_label = ctk.CTkLabel(
                row,
                text=f"{energy_value}/10",
                text_color=energy_color,
                anchor="w",
                font=("Orbitron", 11, "bold"),
            )
            energy_label.grid(row=0, column=5, sticky="w", padx=10, pady=8)
            energy_meta = payload.get("energy_metadata", {})
            if energy_meta:
                tip = (
                    f"Energy Level: {energy_value}/10\n"
                    f"RMS loudness:  {energy_meta.get('rms_mean', 0):.4f}\n"
                    f"Brightness:    {energy_meta.get('centroid_norm', 0):.3f}\n"
                    f"Onset density: {energy_meta.get('onset_density', 0):.3f}\n"
                    f"Bass weight:   {energy_meta.get('low_ratio', 0):.3f}"
                )
                HoverTip(energy_label, tip)
        else:
            ctk.CTkLabel(row, text="--", text_color="#7E8A9E", anchor="w").grid(
                row=0, column=5, sticky="w", padx=10, pady=8
            )

        # Danceability (1–10) — rhythmic regularity / beat grid tightness.
        dance_value = payload.get("danceability", 0)
        if isinstance(dance_value, int) and dance_value > 0:
            if dance_value <= 3:
                dance_color = "#7E8A9E"   # grey — low rhythmic drive
            elif dance_value <= 6:
                dance_color = "#A78BFA"   # purple — moderate groove
            else:
                dance_color = "#36E874"   # green — high danceability
            dance_label = ctk.CTkLabel(
                row,
                text=f"{dance_value}/10",
                text_color=dance_color,
                anchor="w",
                font=("Orbitron", 11, "bold"),
            )
            dance_label.grid(row=0, column=6, sticky="w", padx=10, pady=8)
            dance_meta = payload.get("dance_metadata", {})
            if dance_meta:
                tip = (
                    f"Danceability: {dance_value}/10\n"
                    f"Beat regularity:   {dance_meta.get('beat_regularity', 0):.3f}\n"
                    f"Beat strength:     {dance_meta.get('beat_strength', 0):.3f}\n"
                    f"Periodicity:       {dance_meta.get('periodicity', 0):.3f}\n"
                    f"Tempo consistency: {dance_meta.get('tempo_consistency', 0):.3f}"
                )
                HoverTip(dance_label, tip)
        else:
            ctk.CTkLabel(row, text="--", text_color="#7E8A9E", anchor="w").grid(
                row=0, column=6, sticky="w", padx=10, pady=8
            )

        confidence_text = "--"
        confidence_color = "#7E8A9E"
        if isinstance(confidence_value, (int, float)):
            confidence_pct = int(round(float(confidence_value) * 100))
            confidence_text = f"{confidence_pct}%"
            if confidence_pct >= 75:
                confidence_color = "#36E874"
            elif confidence_pct >= 60:
                confidence_color = "#F4C542"
            else:
                confidence_color = "#FF7A7A"

        confidence_label = ctk.CTkLabel(
            row,
            text=confidence_text,
            text_color=confidence_color,
            anchor="w",
            font=("Orbitron", 11, "bold"),
        )
        confidence_label.grid(row=0, column=7, sticky="w", padx=10, pady=8)

        if top_candidates:
            tooltip_lines = [f"Confidence: {confidence_text}", "Top key candidates:"]
            for idx, candidate in enumerate(top_candidates[:3], start=1):
                candidate_key = str(candidate.get("key", "Unknown"))
                candidate_score = float(candidate.get("score", 0.0))
                tooltip_lines.append(f"{idx}. {candidate_key} ({candidate_score:.3f})")
            HoverTip(confidence_label, "\n".join(tooltip_lines))

        play_btn = ctk.CTkButton(
            row,
            text="Play",
            width=62,
            height=24,
            corner_radius=8,
            fg_color="#1E3A5F",
            hover_color="#2A4E7F",
            state="disabled" if is_error or not file_path else "normal",
            command=lambda p=file_path: self.preview_audio(p),
        )
        play_btn.grid(row=0, column=8, sticky="w", padx=10, pady=8)

        self._result_rows.append(row)
        self._result_records.append(
            {
                "file": file_name,
                "path": file_path,
                "bpm": bpm_text,
                "key": key_text,
                "camelot": camelot,
                "confidence": confidence_text,
                "error": is_error,
            }
        )
        self._update_export_buttons()

    def _clear_result_rows(self) -> None:
        for row in self._result_rows:
            row.destroy()
        self._result_rows.clear()
        self._result_records.clear()
        self._reset_master_stats()
        self._update_export_buttons()

    def _reset_master_stats(self) -> None:
        self.trimmed_count = 0
        self.normalized_count = 0
        self.lufs_count = 0
        self.copies_count = 0
        self._update_master_stats_label()

    def _update_master_stats_label(self) -> None:
        self.master_stats_label.configure(
            text=(
                f"[ Trimmed: {self.trimmed_count} | Normalized: {self.normalized_count} "
                f"| LUFS: {self.lufs_count} | Copies: {self.copies_count} ]"
            )
        )

    def _update_export_buttons(self) -> None:
        state = "normal" if self._result_records else "disabled"
        self.btn_export_csv.configure(state=state)
        self.btn_export_json.configure(state=state)

    def _set_progress(self, value: float) -> None:
        value = max(0.0, min(1.0, value))
        if value < 0.7:
            color = ACCENT_CYAN
        elif value < 0.9:
            color = "#2ED8A3"
        else:
            color = "#36E874"
        self.progress.configure(progress_color=color)
        self.progress.set(value)

    def export_csv(self) -> None:
        if not self._result_records:
            messagebox.showinfo("BPM-X", "No results available to export yet.")
            return

        save_path = filedialog.asksaveasfilename(
            title="Export Results to CSV",
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
            initialfile="bpmx_results.csv",
        )
        if not save_path:
            return

        fields = ["file", "path", "bpm", "key", "camelot", "confidence", "error"]
        with open(save_path, "w", newline="", encoding="utf-8") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=fields)
            writer.writeheader()
            writer.writerows(self._result_records)

        self._add_info_row(f"Exported CSV: {save_path}")

    def export_json(self) -> None:
        if not self._result_records:
            messagebox.showinfo("BPM-X", "No results available to export yet.")
            return

        save_path = filedialog.asksaveasfilename(
            title="Export Results to JSON",
            defaultextension=".json",
            filetypes=[("JSON", "*.json")],
            initialfile="bpmx_results.json",
        )
        if not save_path:
            return

        with open(save_path, "w", encoding="utf-8") as json_file:
            json.dump(self._result_records, json_file, indent=2)

        self._add_info_row(f"Exported JSON: {save_path}")

    def preview_audio(self, file_path: str) -> None:
        path = Path(file_path)
        if not path.exists():
            self._add_info_row(f"Preview failed: file missing ({file_path})", error=True)
            return
        threading.Thread(target=self._play_audio_worker, args=(path,), daemon=True).start()

    def _play_audio_worker(self, path: Path) -> None:
        try:
            if HAS_WINSOUND and path.suffix.lower() == ".wav":
                winsound.PlaySound(str(path), winsound.SND_FILENAME | winsound.SND_ASYNC)
                self.ui_queue.put(("log", f"Previewing: {path.name}"))
                return

            if IS_MACOS and shutil.which("afplay") is not None:
                self.ui_queue.put(("log", f"Previewing: {path.name}"))
                subprocess.run(["afplay", str(path)], check=False)
                return

            if HAS_PYDUB_PLAYBACK:
                segment = AudioSegment.from_file(str(path))
                self.ui_queue.put(("log", f"Previewing: {path.name}"))
                pydub_play(segment)
                return

            self.ui_queue.put(("log", "Preview unavailable: install an audio backend or FFmpeg."))
        except Exception as exc:
            self.ui_queue.put(("log", f"Preview failed for {path.name}: {exc}"))

    def show_dnd_help(self) -> None:
        """Display tkdnd installation and linkage instructions."""
        messagebox.showinfo("BPM-X | DnD Help", self._dnd_help_text())

    def _start_ui_polling(self) -> None:
        self.after(100, self._process_ui_queue)

    def _process_ui_queue(self) -> None:
        while not self.ui_queue.empty():
            event, payload = self.ui_queue.get_nowait()
            if event == "log":
                self._add_info_row(str(payload))
            elif event == "result":
                self._add_result_row(payload if isinstance(payload, dict) else {})
            elif event == "progress":
                self._set_progress(float(payload))
            elif event == "stats":
                self.stats_label.configure(text=str(payload))
            elif event == "done":
                self.is_running = False
                self.btn_run.configure(state="normal")
        self.after(100, self._process_ui_queue)

    def _on_drop(self, event) -> None:
        raw = event.data.strip()
        if not raw:
            return

        parsed = [Path(p) for p in self.tk.splitlist(raw) if p.strip()]
        valid = [p for p in parsed if p.exists()]
        if valid:
            self.set_selected_paths(valid)

    def select_path(self) -> None:
        file_paths = filedialog.askopenfilenames(
            title="BPM-X | Select Samples for Sniper Analysis",
            filetypes=[
                ("Audio Files", "*.wav *.mp3 *.flac *.aif *.aiff *.ogg *.m4a"),
                ("All Files", "*.*"),
            ],
        )
        if file_paths:
            self.set_selected_paths([Path(p) for p in file_paths])

    def set_selected_path(self, path: Path) -> None:
        self.set_selected_paths([path])

    def set_selected_paths(self, paths: list[Path]) -> None:
        self.selected_paths = paths
        self.selected_path = paths[0] if paths else None
        if len(paths) == 1:
            label = f"Input: {paths[0]}"
        else:
            label = f"Loaded: {len(paths)} samples"
        self.path_label.configure(text=label)
        self.btn_run.configure(state="normal")
        if len(paths) == 1:
            self.ui_queue.put(("log", label))
        else:
            self.ui_queue.put(("log", f"Sniper ready. {len(paths)} targets locked."))

    def start_batch(self) -> None:
        if self.is_running or not self.selected_paths:
            return
        self.is_running = True
        self.btn_run.configure(state="disabled")
        self._clear_result_rows()
        self._set_progress(0.0)
        self.ui_queue.put(("log", "Starting batch analysis..."))

        worker = threading.Thread(target=self._run_batch, daemon=True)
        worker.start()

    def _run_batch(self) -> None:
        try:
            files = self._collect_audio_files(self.selected_paths)
            total = len(files)
            if total == 0:
                self.ui_queue.put(("log", "No audio files found."))
                self.ui_queue.put(("done", None))
                return

            self.ui_queue.put(("stats", f"Processing {total} file(s)..."))
            success = 0
            failed = 0
            selected_profile = self.tag_profile_var.get().strip().lower()
            profile_forces_lufs = selected_profile == "universal"
            if profile_forces_lufs and not self.lufs_var.get():
                self.ui_queue.put(("log", "Universal profile active: LUFS normalization auto-enabled (-14 LUFS)."))

            for idx, audio_path in enumerate(files, start=1):
                try:
                    preview_path = audio_path
                    finish_tags: list[str] = []
                    apply_lufs = self.lufs_var.get() or profile_forces_lufs

                    analysis = self.analyzer.analyze(str(audio_path))
                    camelot = self.translator.to_camelot(analysis["key"])

                    # Organize first so finishing runs on the final file path.
                    # This keeps the Play button and destructive edits aligned.
                    if self.organize_var.get():
                        organized_path = self.organizer.organize_file(
                            str(audio_path),
                            analysis["bpm"],
                            analysis["key"],
                            camelot,
                            move=self.move_var.get(),
                        )
                        if organized_path is not None:
                            preview_path = organized_path
                        elif self.move_var.get():
                            self.ui_queue.put((
                                "log",
                                f"Warning: organize failed for {audio_path.name}; preview will use original path.",
                            ))

                    if self.trim_var.get() or self.normalize_var.get() or apply_lufs:
                        finish_info = self.finisher.finish(
                            preview_path,
                            trim=self.trim_var.get(),
                            normalize=self.normalize_var.get(),
                            lufs_normalize=apply_lufs,
                            keep_originals=self.keep_originals_var.get(),
                        )
                        preview_path = Path(str(finish_info["path"]))
                        finish_tags = [str(tag) for tag in finish_info.get("tags", [])]
                        self.ui_queue.put((
                            "log",
                            f"Finisher [{Path(str(finish_info['path'])).name}]: {finish_info['summary']}",
                        ))

                    if self.tag_var.get():
                        self.tagger.tag_file(
                            str(preview_path),
                            analysis["bpm"],
                            analysis["key"],
                            camelot,
                            overwrite=True,
                            profile=selected_profile,
                        )

                    self.ui_queue.put((
                        "result",
                        {
                            "file": audio_path.name,
                            "path": str(preview_path),
                            "bpm": f"{analysis['bpm']:.0f}",
                            "bpm_source": analysis.get("bpm_source", "analysis"),
                            "key": analysis["key"],
                            "camelot": camelot,
                            "energy": analysis.get("energy", 0),
                            "energy_metadata": analysis.get("energy_metadata", {}),
                            "danceability": analysis.get("danceability", 0),
                            "dance_metadata": analysis.get("dance_metadata", {}),
                            "confidence": analysis["key_metadata"].get("confidence"),
                            "finish_tags": finish_tags,
                            "top_candidates": analysis["key_metadata"].get("top_candidates", []),
                            "error": False,
                        },
                    ))
                    success += 1
                except Exception as exc:
                    failed += 1
                    self.ui_queue.put((
                        "result",
                        {
                            "file": audio_path.name,
                            "path": str(audio_path),
                            "bpm": "--",
                            "key": str(exc),
                            "camelot": "ERR",
                            "error": True,
                        },
                    ))

                self.ui_queue.put(("progress", idx / total))
                self.ui_queue.put(("stats", f"Processed {idx}/{total} | Success: {success} | Failed: {failed}"))

            self.ui_queue.put(("log", "Batch complete."))
            self.ui_queue.put(("stats", f"Done | Success: {success} | Failed: {failed}"))
        finally:
            self.ui_queue.put(("done", None))

    @staticmethod
    def _collect_audio_files(paths: list[Path]) -> list[Path]:
        audio_exts = {".mp3", ".wav", ".flac", ".ogg", ".m4a", ".aif", ".aiff"}
        collected: list[Path] = []
        for path in paths:
            if path.is_file() and path.suffix.lower() in audio_exts:
                collected.append(path)
            elif path.is_dir():
                collected.extend(p for p in path.rglob("*") if p.suffix.lower() in audio_exts)

        # Keep stable order while removing duplicates.
        deduped = list(dict.fromkeys(collected))
        return deduped


def run_gui() -> None:
    """Launch BPM-X desktop GUI."""
    if HAS_DND and TkinterDnD is not None:
        class BPMXDnDGUI(TkinterDnD.DnDWrapper, BPMXGUI):
            pass

        app = BPMXDnDGUI()
        app.mainloop()
        return

    app = BPMXGUI()
    app.mainloop()


if __name__ == "__main__":
    run_gui()
