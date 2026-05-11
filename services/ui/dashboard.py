#!/usr/bin/env python3
"""
Smartfield — Field Operations Dashboard
────────────────────────────────────────
PyQt6 + python-vlc  ·  ICICLE · AI Institute

Run:
  python3 dashboard.py

Environment overrides:
  CONFIG_PATH     path to config.toml        (default: ../../config.toml)
  LOGS_DIR        path to logs/mission        (default: ../../logs/mission)
  SMARTFIELD_URL  smartfield REST API         (default: http://localhost:9988)
  SUBSCRIBER_URL  mqtt_subscriber REST API    (default: http://localhost:9987)
  RTSP_URL        default camera RTSP URL     (default: rtsp://192.168.53.1/live)
"""

import os
import re
import sys
import html as _html
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass

import requests
import psutil
import toml

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QFrame, QLineEdit, QPushButton, QComboBox, QProgressBar,
    QSplitter, QTextEdit, QGroupBox, QFormLayout, QStatusBar, QSizePolicy,
)
from PyQt6.QtCore import (
    Qt, QTimer, QThread, pyqtSignal, QPropertyAnimation,
    QEasingCurve, pyqtProperty,
)
from PyQt6.QtGui import (
    QFont, QColor, QTextCursor, QPainter, QPen, QBrush,
    QImage, QPixmap,
)

# ── paths ─────────────────────────────────────────────────────────────────────

_HERE = Path(__file__).parent
_ROOT = _HERE.parent.parent

CONFIG_PATH  = Path(os.environ.get("CONFIG_PATH",  str(_ROOT / "config.toml")))
LOGS_DIR     = Path(os.environ.get("LOGS_DIR",     str(_ROOT / "logs" / "mission")))
SF_URL       = os.environ.get("SMARTFIELD_URL",    "http://localhost:9988")
SUB_URL      = os.environ.get("SUBSCRIBER_URL",    "http://localhost:9987")
RTSP_DEFAULT = os.environ.get("RTSP_URL",          "rtsp://192.168.53.1/live")

# ── palette ───────────────────────────────────────────────────────────────────

BG_BASE    = "#f4f1eb"
BG_CARD    = "#ffffff"
BG_PANEL   = "#f9f7f2"
BG_INPUT   = "#d8d4c8"
BORDER     = "#ddd9cf"
BORDER_LIT = "#4e7c34"

GREEN      = "#3d7a28"
GREEN_DIM  = "#4e7c34"
GREEN_BG   = "#eaf4e4"

AMBER      = "#b5720a"
AMBER_BG   = "#fdf3e0"

RED        = "#c0392b"
RED_BG     = "#fce8e6"

BLUE       = "#2176ae"
BLUE_BG    = "#e3f0f9"

TEXT       = "#1c2414"
TEXT_DIM   = "#4a5e38"
TEXT_MUTED = "#8a9e78"

FONT_UI    = "'DM Sans', 'Inter', 'Segoe UI', Arial, sans-serif"
FONT_MONO  = "'DM Mono', 'Fira Code', 'JetBrains Mono', 'Courier New', monospace"

# ── stylesheet ────────────────────────────────────────────────────────────────

STYLESHEET = f"""
* {{
    font-family: {FONT_UI};
    font-size: 13px;
    line-height: 1.5;
}}
QMainWindow, QWidget {{
    background-color: {BG_BASE};
    color: {TEXT};
}}

/* ── cards ── */
QGroupBox {{
    background-color: {BG_CARD};
    border: 1px solid {BORDER};
    border-radius: 8px;
    margin-top: 6px;
    padding-top: 4px;
    font-family: {FONT_MONO};
    font-weight: 500;
    font-size: 10px;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: {TEXT_DIM};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 2px 10px;
    left: 12px;
    background-color: {BG_CARD};
}}

/* ── inputs ── */
QLineEdit {{
    background-color: {BG_INPUT};
    border: 1px solid {BORDER};
    border-radius: 5px;
    padding: 6px 10px;
    font-family: {FONT_MONO};
    font-size: 12px;
    color: {TEXT};
}}
QLineEdit:focus {{ border: 1px solid {BORDER_LIT}; background-color: {BG_CARD}; }}
QLineEdit:disabled {{ color: {TEXT_MUTED}; }}

/* ── combo ── */
QComboBox {{
    background-color: {BG_INPUT};
    border: 1px solid {BORDER};
    border-radius: 5px;
    padding: 6px 10px;
    font-family: {FONT_MONO};
    font-size: 12px;
    color: {TEXT};
    min-width: 120px;
}}
QComboBox:focus {{ border: 1px solid {BORDER_LIT}; }}
QComboBox::drop-down {{ border: none; width: 0; }}
QComboBox QAbstractItemView {{
    background-color: {BG_CARD};
    border: 1px solid {BORDER};
    color: {TEXT};
    selection-background-color: {GREEN_BG};
    outline: none;
    padding: 2px;
}}

/* ── buttons ── */
QPushButton {{
    background-color: {GREEN_DIM};
    color: #ffffff;
    border: none;
    border-radius: 5px;
    padding: 7px 16px;
    font-weight: 600;
    font-size: 13px;
    min-height: 32px;
}}
QPushButton:hover  {{ background-color: {GREEN}; }}
QPushButton:pressed {{ background-color: #2d5c1e; }}

QPushButton#secondary {{
    background-color: {BG_PANEL};
    border: 1px solid {BORDER};
    color: {TEXT_DIM};
}}
QPushButton#secondary:hover {{
    background-color: {BG_INPUT};
    border-color: {BORDER_LIT};
    color: {TEXT};
}}

QPushButton#logtab {{
    background-color: transparent;
    border: none;
    border-bottom: 2px solid transparent;
    border-radius: 0px;
    color: {TEXT_MUTED};
    font-family: {FONT_MONO};
    font-size: 9px;
    font-weight: 500;
    letter-spacing: 0.08em;
    padding: 4px 10px;
    min-height: 24px;
}}
QPushButton#logtab:hover {{ color: {TEXT_DIM}; }}
QPushButton#logtab_active {{
    background-color: transparent;
    border: none;
    border-bottom: 2px solid {GREEN_DIM};
    border-radius: 0px;
    color: {GREEN_DIM};
    font-family: {FONT_MONO};
    font-size: 9px;
    font-weight: 600;
    letter-spacing: 0.08em;
    padding: 4px 10px;
    min-height: 24px;
}}

/* ── progress bars ── */
QProgressBar {{
    background-color: {BG_INPUT};
    border: none;
    border-radius: 3px;
    height: 6px;
    text-align: center;
}}
QProgressBar::chunk {{ border-radius: 3px; background-color: {GREEN_DIM}; }}

/* ── text edit (log terminal) ── */
QTextEdit {{
    background-color: {BG_PANEL};
    border: none;
    color: {TEXT};
    font-family: {FONT_MONO};
    font-size: 11px;
    padding: 8px 6px;
    selection-background-color: {GREEN_BG};
}}

/* ── scrollbars ── */
QScrollBar:vertical {{
    background: {BG_PANEL};
    width: 6px;
    border-radius: 3px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {BORDER};
    border-radius: 3px;
    min-height: 20px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}

/* ── status bar ── */
QStatusBar {{
    background-color: {BG_CARD};
    color: {TEXT_MUTED};
    border-top: 1px solid {BORDER};
    font-family: {FONT_MONO};
    font-size: 11px;
    padding: 0 12px;
}}

/* ── splitter ── */
QSplitter::handle {{
    background-color: {BORDER};
    margin: 2px;
}}

/* ── misc labels ── */
QLabel#muted {{
    color: {TEXT_MUTED};
    font-size: 12px;
}}
QLabel#dim {{
    color: {TEXT_DIM};
    font-size: 12px;
}}
"""

# ── pipeline stages ───────────────────────────────────────────────────────────

STAGES = [
    ("camera",    "Camera Trap Triggered",  "Motion detected — MQTT event published"),
    ("mqtt",      "Event Received",         "Subscriber relays detection to pipeline"),
    ("ltt",       "Navigate to Site",       "Drone airborne — LTT mission executing"),
    ("wildwings", "Aerial Tracking",        "YOLO active — WildWings tracking animal"),
    ("rtb",       "Return to Base",         "Footage saved — RTB mission executing"),
]

LOG_STAGE_MAP = {
    "mission started":       "mqtt",
    "initiating takeoff":    "ltt",
    "navigating to target":  "ltt",
    "ltt mission completed": "wildwings",
    "tracker starting":      "wildwings",
    "recording started":     "wildwings",
    "rtb":                   "rtb",
    "mission complete":      "__done__",
    "mission failed":        "__error__",
}

# ── workers ───────────────────────────────────────────────────────────────────

class MetricsWorker(QThread):
    updated = pyqtSignal(float, float)

    def run(self):
        psutil.cpu_percent()  # prime — first call always returns 0.0
        while not self.isInterruptionRequested():
            for _ in range(30):  # 3 s in 100 ms chunks
                if self.isInterruptionRequested():
                    return
                self.msleep(100)
            cpu = psutil.cpu_percent()  # non-blocking: measures since last call
            ram = psutil.virtual_memory().percent
            self.updated.emit(cpu, ram)


class HealthWorker(QThread):
    updated = pyqtSignal(dict)

    def run(self):
        def _check(name: str, url: str) -> tuple[str, bool]:
            try:
                r = requests.get(f"{url}/health", timeout=3)
                return name, (
                    r.status_code == 200
                    and r.json().get("data", {}).get("status") == "ok"
                )
            except Exception:
                return name, False

        while not self.isInterruptionRequested():
            with ThreadPoolExecutor(max_workers=2) as ex:
                sf  = ex.submit(_check, "smartfield", SF_URL)
                sub = ex.submit(_check, "subscriber", SUB_URL)
                result = dict([sf.result(), sub.result()])
            self.updated.emit(result)
            for _ in range(50):  # 5 s in 100 ms chunks
                if self.isInterruptionRequested():
                    return
                self.msleep(100)


class LogWatcher(QThread):
    new_lines = pyqtSignal(list)
    stage_hit = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._last_file: Path | None = None
        self._last_pos = 0

    def run(self):
        while not self.isInterruptionRequested():
            self._poll()
            self.msleep(800)

    def _poll(self):
        logs = sorted(LOGS_DIR.glob("mission_*/mission.log"))
        if not logs:
            return
        latest = logs[-1]
        if latest != self._last_file:
            self._last_file = latest
            self._last_pos  = 0
        try:
            with open(latest) as fh:
                fh.seek(self._last_pos)
                lines = fh.readlines()
                self._last_pos = fh.tell()
            if not lines:
                return
            self.new_lines.emit([ln.rstrip() for ln in lines])
            for line in lines:
                low = line.lower()
                for kw, stage in LOG_STAGE_MAP.items():
                    if kw in low:
                        self.stage_hit.emit(stage)
                        break
        except Exception:
            pass

class MissionWorker(QThread):
    done  = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, url: str, mode: str):
        super().__init__()
        self._url  = url
        self._mode = mode

    def run(self):
        try:
            r = requests.post(
                f"{self._url}/api/v1/mission/run",
                json={"mode_type": self._mode},
                timeout=(5, 300),
            )
            self.done.emit(r.json())
        except requests.exceptions.ConnectionError:
            self.error.emit("Cannot reach smartfield — is the service running?")
        except Exception as e:
            self.error.emit(f"Error: {e}")


class VideoWorker(QThread):
    frame_ready = pyqtSignal(QImage)
    error       = pyqtSignal(str)

    def __init__(self, url: str):
        super().__init__()
        self._url = url

    def run(self):
        try:
            import cv2
        except ImportError:
            self.error.emit("OpenCV (cv2) is not installed.")
            return
        os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;udp"
        cap = cv2.VideoCapture(self._url, cv2.CAP_FFMPEG)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        if not cap.isOpened():
            self.error.emit(f"Cannot open stream: {self._url}")
            return
        while not self.isInterruptionRequested():
            ret, frame = cap.read()
            if not ret:
                self.error.emit("Stream ended or lost.")
                break
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb.shape
            img = QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888)
            self.frame_ready.emit(img.copy())
            self.msleep(66)  # ~15 fps cap — keeps main thread free
        cap.release()


# ── custom widgets ────────────────────────────────────────────────────────────

class PulseDot(QWidget):
    """Painted circle dot with optional animated glow ring (for service health)."""

    def __init__(self, size: int = 8):
        super().__init__()
        self._online = False
        self._glow   = 0.0
        self._sz     = size
        self.setFixedSize(size + 14, size + 14)

        self._anim = QPropertyAnimation(self, b"glow", self)
        self._anim.setDuration(1600)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setLoopCount(-1)
        self._anim.setEasingCurve(QEasingCurve.Type.SineCurve)

    def get_glow(self) -> float:
        return self._glow

    def set_glow(self, val: float):
        self._glow = val
        self.update()

    glow = pyqtProperty(float, get_glow, set_glow)

    def set_online(self, ok: bool):
        self._online = ok
        if ok:
            self._anim.start()
        else:
            self._anim.stop()
            self._glow = 0.0
        self.update()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        cx = self.width() // 2
        cy = self.height() // 2
        r  = self._sz // 2

        if self._online and self._glow > 0:
            ring_r = r + 2 + int(self._glow * 5)
            ring_c = QColor(GREEN_DIM)
            ring_c.setAlpha(int((1.0 - self._glow) * 80))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(ring_c))
            p.drawEllipse(cx - ring_r, cy - ring_r, ring_r * 2, ring_r * 2)

        color = QColor(GREEN if self._online else RED)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(color))
        p.drawEllipse(cx - r, cy - r, r * 2, r * 2)
        p.end()


class PipelineConnector(QWidget):
    """Animated vertical connector between pipeline steps."""

    def __init__(self):
        super().__init__()
        self._active   = False
        self._slug_pos = 0.0
        self.setFixedHeight(22)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self._anim = QPropertyAnimation(self, b"slug_pos", self)
        self._anim.setDuration(900)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setLoopCount(-1)
        self._anim.setEasingCurve(QEasingCurve.Type.Linear)

    def get_slug(self) -> float:
        return self._slug_pos

    def set_slug(self, val: float):
        self._slug_pos = val
        self.update()

    slug_pos = pyqtProperty(float, get_slug, set_slug)

    def set_active(self, active: bool):
        self._active = active
        if active:
            self._anim.start()
        else:
            self._anim.stop()
            self._slug_pos = 0.0
        self.update()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        cx = self.width() // 2
        h  = self.height()

        line_pen = QPen(QColor(BORDER))
        line_pen.setWidth(2)
        p.setPen(line_pen)
        p.drawLine(cx, 0, cx, h)

        if self._active:
            slug_h  = 10
            slug_y0 = int(self._slug_pos * (h + slug_h)) - slug_h
            y0 = max(0, slug_y0)
            y1 = min(h, slug_y0 + slug_h)
            if y1 > y0:
                slug_pen = QPen(QColor(AMBER))
                slug_pen.setWidth(3)
                slug_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                p.setPen(slug_pen)
                p.drawLine(cx, y0, cx, y1)
        p.end()


class PipelineStep(QWidget):
    """Single stage card in the detection-to-documentation pipeline."""

    IDLE   = "idle"
    ACTIVE = "active"
    DONE   = "done"
    ERROR  = "error"

    _CONFIG = {
        IDLE:   (BG_PANEL,  BORDER,    TEXT_MUTED, "○", TEXT_MUTED, TEXT_DIM),
        ACTIVE: (AMBER_BG,  AMBER,     AMBER,      "◉", AMBER,      TEXT),
        DONE:   (GREEN_BG,  GREEN_DIM, GREEN,      "✓", GREEN,      TEXT),
        ERROR:  (RED_BG,    RED,       RED,        "✕", RED,        TEXT),
    }

    def __init__(self, title: str, subtitle: str):
        super().__init__()
        self._state = self.IDLE
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMinimumHeight(60)

        row = QHBoxLayout(self)
        row.setContentsMargins(14, 10, 14, 10)
        row.setSpacing(12)

        self._bubble = QLabel("○")
        self._bubble.setFixedSize(26, 26)
        self._bubble.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._bubble.setFont(QFont("", 12, QFont.Weight.Bold))

        col = QVBoxLayout()
        col.setSpacing(2)
        self._title_lbl = QLabel(title)
        self._title_lbl.setFont(QFont("", 13, QFont.Weight.DemiBold))
        self._sub_lbl = QLabel(subtitle)
        self._sub_lbl.setFont(QFont("", 11))

        col.addWidget(self._title_lbl)
        col.addWidget(self._sub_lbl)
        row.addWidget(self._bubble)
        row.addLayout(col)
        row.addStretch()
        self._refresh()

    def set_state(self, state: str):
        self._state = state
        self._refresh()

    def _refresh(self):
        bg, border, icon_c, icon, title_c, sub_c = self._CONFIG[self._state]
        self._bubble.setText(icon)
        self._bubble.setStyleSheet(
            f"background:{bg}; color:{icon_c};"
            f" border:1.5px solid {border}; border-radius:13px;"
        )
        self._title_lbl.setStyleSheet(f"color:{title_c};")
        self._sub_lbl.setStyleSheet(f"color:{sub_c}; font-size:11px;")
        self.setStyleSheet(
            f"PipelineStep {{"
            f"  background-color:{bg};"
            f"  border:1px solid {border};"
            f"  border-radius:7px;"
            f"}}"
        )


class MetricBar(QWidget):
    def __init__(self, label: str, base_color: str = GREEN_DIM):
        super().__init__()
        self._base = base_color
        self._current_color = base_color
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 4, 0, 4)
        row.setSpacing(10)

        lbl = QLabel(label)
        lbl.setFixedWidth(34)
        lbl.setFont(QFont("", 10))
        lbl.setStyleSheet(f"font-family:{FONT_MONO}; color:{TEXT_MUTED};")

        self._bar = QProgressBar()
        self._bar.setRange(0, 100)
        self._bar.setTextVisible(False)
        self._bar.setFixedHeight(6)

        self._pct = QLabel("—")
        self._pct.setFixedWidth(38)
        self._pct.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._pct.setFont(QFont("", 10))
        self._pct.setStyleSheet(f"font-family:{FONT_MONO}; color:{TEXT_MUTED};")

        row.addWidget(lbl)
        row.addWidget(self._bar, 1)
        row.addWidget(self._pct)
        self._set_color(base_color)

    def update_value(self, value: float):
        if value < 0:
            self._pct.setText("N/A")
            self._bar.setValue(0)
            return
        v = int(value)
        self._bar.setValue(v)
        self._pct.setText(f"{v}%")
        new_color = RED if v > 85 else AMBER if v > 65 else self._base
        if new_color != self._current_color:
            self._set_color(new_color)
            self._current_color = new_color

    def _set_color(self, c: str):
        self._bar.setStyleSheet(
            f"QProgressBar {{ background:{BG_INPUT}; border:none; border-radius:3px; }}"
            f"QProgressBar::chunk {{ background:{c}; border-radius:3px; }}"
        )


@dataclass
class LogEntry:
    ts:      str
    level:   str
    message: str


class LogTerminal(QWidget):
    """Scrollable log viewer with ALL / INFO / WARNING / ERROR filter tabs."""

    _LEVEL_COLOR = {
        "INFO":    GREEN,
        "WARNING": AMBER,
        "ERROR":   RED,
        "DEBUG":   TEXT_DIM,
    }
    _TS_COLOR  = TEXT_MUTED
    _MSG_COLOR = TEXT

    def __init__(self):
        super().__init__()
        self._filter = "ALL"
        self._build()

    def _build(self):
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        # filter tabs row
        tab_bar = QWidget()
        tab_bar.setStyleSheet(
            f"background:{BG_INPUT}; border-bottom:1px solid {BORDER};"
        )
        tab_row = QHBoxLayout(tab_bar)
        tab_row.setContentsMargins(8, 0, 8, 0)
        tab_row.setSpacing(0)

        self._tabs: dict[str, QPushButton] = {}
        for label in ("ALL", "INFO", "WARNING", "ERROR"):
            btn = QPushButton(label)
            btn.clicked.connect(lambda _, l=label: self._set_filter(l))
            self._tabs[label] = btn
            tab_row.addWidget(btn)
        tab_row.addStretch()

        clear_btn = QPushButton("Clear")
        clear_btn.setFixedWidth(54)
        clear_btn.setFixedHeight(24)
        clear_btn.setFont(QFont("", 10))
        clear_btn.setStyleSheet(
            f"background:{BG_PANEL}; border:1px solid {BORDER}; color:{TEXT_MUTED};"
            " border-radius:4px; font-size:10px;"
            " padding:0px;"
        )
        clear_btn.clicked.connect(self._clear)
        tab_row.addWidget(clear_btn)

        v.addWidget(tab_bar)

        self._view = QTextEdit()
        self._view.setReadOnly(True)
        self._view.document().setMaximumBlockCount(2000)
        self._view.setPlaceholderText("Waiting for mission activity…")
        v.addWidget(self._view)

        self._update_tabs()

    def _set_filter(self, f: str):
        self._filter = f
        self._update_tabs()
        self._view.clear()

    def _update_tabs(self):
        for label, btn in self._tabs.items():
            if label == self._filter:
                btn.setObjectName("logtab_active")
            else:
                btn.setObjectName("logtab")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def _clear(self):
        self._view.clear()

    def add_lines(self, lines: list[str]):
        for entry in (self._parse(line) for line in lines):
            if self._filter == "ALL" or entry.level == self._filter:
                self._append_entry(entry)
        self._view.moveCursor(QTextCursor.MoveOperation.End)

    def _parse(self, line: str) -> LogEntry:
        m_ts  = re.match(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", line)
        m_lvl = re.search(r"\[(INFO|WARNING|ERROR|DEBUG)\]", line)
        ts    = m_ts.group(1) if m_ts else ""
        level = m_lvl.group(1) if m_lvl else "INFO"

        # strip prefix up to level badge for the message part
        msg = line
        if m_lvl:
            msg = line[m_lvl.end():].strip().lstrip(":").strip()
            msg = re.sub(r"^\S+:\s*", "", msg)   # strip logger name

        return LogEntry(ts=ts, level=level, message=msg)

    def _entry_html(self, entry: LogEntry) -> str:
        lvl_color = self._LEVEL_COLOR.get(entry.level, self._TS_COLOR)
        msg = _html.escape(entry.message)
        return (
            f'<span style="color:{self._TS_COLOR}; font-family:monospace; font-size:10px;">{entry.ts}</span>'
            f'&nbsp;<span style="color:{lvl_color}; font-family:monospace; font-size:10px; font-weight:600;">{entry.level}</span>'
            f'&nbsp;<span style="color:{self._MSG_COLOR}; font-family:monospace; font-size:11px;">{msg}</span>'
        )

    def _append_entry(self, entry: LogEntry):
        self._view.moveCursor(QTextCursor.MoveOperation.End)
        self._view.insertHtml(self._entry_html(entry))
        self._view.insertHtml("<br>")

# ── main window ───────────────────────────────────────────────────────────────

class SmartfieldDashboard(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Smartfield — Field Operations Dashboard")
        self.setMinimumSize(1320, 840)

        self._video_worker: VideoWorker | None = None
        self._stage_keys  = [s[0] for s in STAGES]
        self._stage_index = -1
        self._connectors: list[PipelineConnector] = []

        self._build_ui()
        self._load_config()
        self._start_workers()

        self._clock = QTimer(self)
        self._clock.timeout.connect(self._tick_clock)
        self._clock.start(1000)
        self._tick_clock()

    # ── layout ────────────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)

        vbox = QVBoxLayout(root)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(0)

        vbox.addWidget(self._make_header())

        body = QWidget()
        body.setStyleSheet(f"background:{BG_BASE};")
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(10, 10, 10, 10)
        body_layout.setSpacing(0)

        split = QSplitter(Qt.Orientation.Horizontal)
        split.setHandleWidth(10)
        split.addWidget(self._make_left())
        split.addWidget(self._make_right())
        split.setSizes([660, 600])
        body_layout.addWidget(split)

        vbox.addWidget(body, 1)

        sb = QStatusBar()
        sb.setFixedHeight(28)
        self._status_lbl = QLabel("Ready.")
        self._clock_lbl  = QLabel()
        sb.addWidget(self._status_lbl)
        sb.addPermanentWidget(self._clock_lbl)
        self.setStatusBar(sb)

    # ── header ────────────────────────────────────────────────────────────────

    def _make_header(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(56)
        bar.setStyleSheet(
            f"background:{BG_CARD}; border-bottom:1px solid {BORDER};"
        )

        row = QHBoxLayout(bar)
        row.setContentsMargins(16, 0, 20, 0)
        row.setSpacing(0)

        # logo box
        logo_box = QLabel("🎒")
        logo_box.setFixedSize(34, 34)
        logo_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_box.setFont(QFont("", 18))
        logo_box.setStyleSheet(
            "background: qlineargradient(x1:0,y1:0,x2:1,y2:1,"
            f" stop:0 {GREEN_DIM}, stop:1 #2d5c1e);"
            " border-radius: 7px;"
        )

        # wordmark
        words_col = QVBoxLayout()
        words_col.setSpacing(1)
        words_col.setContentsMargins(0, 0, 0, 0)

        wordmark = QLabel("SMARTFIELD BACKPACK")
        wordmark.setFont(QFont("", 13, QFont.Weight.Bold))
        wordmark.setStyleSheet(
            f"font-family:{FONT_UI}; color:{TEXT};"
            " letter-spacing:0.12em; font-size:13px;"
        )

        subline = QLabel("ICICLE · AI INSTITUTE  —  FIELD OPERATIONS")
        subline.setFont(QFont("", 9))
        subline.setStyleSheet(
            f"font-family:{FONT_MONO}; color:{TEXT_MUTED};"
            " font-size:9px; letter-spacing:0.06em;"
        )

        words_col.addWidget(wordmark)
        words_col.addWidget(subline)

        row.addWidget(logo_box)
        row.addSpacing(12)
        row.addLayout(words_col)
        row.addStretch()

        # service health indicators
        self._sf_dot  = PulseDot(7)
        self._sub_dot = PulseDot(7)

        for dot, name in [(self._sf_dot, "smartfield"), (self._sub_dot, "mqtt_subscriber")]:
            sep = QFrame()
            sep.setFrameShape(QFrame.Shape.VLine)
            sep.setStyleSheet(f"color:{BORDER}; max-width:1px;")
            row.addWidget(sep)

            indicator = QWidget()
            ind_row = QHBoxLayout(indicator)
            ind_row.setContentsMargins(12, 0, 8, 0)
            ind_row.setSpacing(4)
            ind_row.addWidget(dot)
            lbl = QLabel(name)
            lbl.setFont(QFont("", 11))
            lbl.setStyleSheet(f"font-family:{FONT_MONO}; color:{TEXT_MUTED}; font-size:11px;")
            ind_row.addWidget(lbl)
            row.addWidget(indicator)

        return bar

    # ── left column ───────────────────────────────────────────────────────────

    def _make_left(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 5, 0)
        v.setSpacing(10)
        v.addWidget(self._make_camera_panel(), 3)
        v.addWidget(self._make_logs_panel(), 2)
        return w

    def _make_camera_panel(self) -> QGroupBox:
        box = QGroupBox("  📡  RTSP Camera Feed")
        box.setStyleSheet(
            f"QGroupBox {{ background-color: #f4f1eb; border: 1px solid {BORDER}; border-radius: 8px; }}"
            f"QGroupBox::title {{ background-color: #f4f1eb; }}"
        )
        v = QVBoxLayout(box)
        v.setContentsMargins(14, 20, 14, 14)
        v.setSpacing(10)

        self._video_label = QLabel()
        self._video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._video_label.setStyleSheet(
            "background:#0e1108; border-radius:6px; border:1px solid #ddd9cf;"
        )
        self._video_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self._video_label.setMinimumHeight(260)

        self._no_signal = QLabel("NO SIGNAL")
        self._no_signal.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._no_signal.setStyleSheet(
            f"color:{TEXT_MUTED}; font-size:14px; font-weight:600;"
            " letter-spacing:4px; background:transparent;"
            f" font-family:{FONT_MONO};"
        )
        ph = QVBoxLayout(self._video_label)
        ph.addWidget(self._no_signal)

        v.addWidget(self._video_label, 1)

        ctrl = QHBoxLayout()
        ctrl.setSpacing(8)
        self._rtsp_field = QLineEdit()
        self._rtsp_field.setPlaceholderText("rtsp://host/stream")
        self._rtsp_field.setText(RTSP_DEFAULT)
        self._rtsp_field.returnPressed.connect(self._stream_connect)

        btn_conn = QPushButton("▶  Connect")
        btn_conn.setFixedWidth(110)
        btn_conn.clicked.connect(self._stream_connect)

        btn_stop = QPushButton("■")
        btn_stop.setObjectName("secondary")
        btn_stop.setFixedWidth(50)
        btn_stop.setToolTip("Stop stream")
        btn_stop.clicked.connect(self._stream_stop)

        ctrl.addWidget(self._rtsp_field)
        ctrl.addWidget(btn_conn)
        ctrl.addWidget(btn_stop)
        v.addLayout(ctrl)
        return box

    def _make_logs_panel(self) -> QGroupBox:
        box = QGroupBox("  📋  Mission Logs")
        box.setStyleSheet(
            f"QGroupBox {{ background-color: #f4f1eb; border: 1px solid {BORDER}; border-radius: 8px; }}"
            f"QGroupBox::title {{ background-color: #f4f1eb; }}"
        )
        v = QVBoxLayout(box)
        v.setContentsMargins(0, 14, 0, 0)
        v.setSpacing(0)
        self._log_terminal = LogTerminal()
        v.addWidget(self._log_terminal)
        return box

    # ── right column ──────────────────────────────────────────────────────────

    def _make_right(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(5, 0, 0, 0)
        v.setSpacing(10)
        v.addWidget(self._make_pipeline_panel(), 4)
        v.addWidget(self._make_metrics_panel(), 1)
        v.addWidget(self._make_config_panel(), 3)
        return w

    def _make_pipeline_panel(self) -> QGroupBox:
        box = QGroupBox("  🦌  Detection-to-Documentation Pipeline")
        box.setStyleSheet(
            f"QGroupBox {{ background-color: #f4f1eb; border: 1px solid {BORDER}; border-radius: 8px; }}"
            f"QGroupBox::title {{ background-color: #f4f1eb; }}"
        )
        v = QVBoxLayout(box)
        v.setContentsMargins(16, 20, 16, 14)
        v.setSpacing(0)

        self._steps: dict[str, PipelineStep] = {}
        self._connectors = []

        for i, (key, title, subtitle) in enumerate(STAGES):
            step = PipelineStep(title, subtitle)
            self._steps[key] = step
            v.addWidget(step)

            if i < len(STAGES) - 1:
                conn = PipelineConnector()
                self._connectors.append(conn)
                v.addWidget(conn)

        v.addStretch()

        reset_btn = QPushButton("Reset Pipeline")
        reset_btn.setObjectName("secondary")
        reset_btn.setFixedWidth(138)
        reset_btn.setFixedHeight(30)
        reset_btn.clicked.connect(self._pipeline_reset)
        v.addWidget(reset_btn, alignment=Qt.AlignmentFlag.AlignRight)
        return box

    def _make_metrics_panel(self) -> QGroupBox:
        box = QGroupBox("  💻  System Metrics")
        box.setStyleSheet(
            f"QGroupBox {{ background-color: #f4f1eb; border: 1px solid {BORDER}; border-radius: 8px; }}"
            f"QGroupBox::title {{ background-color: #f4f1eb; }}"
        )
        v = QVBoxLayout(box)
        v.setContentsMargins(18, 18, 18, 12)
        v.setSpacing(0)
        self._cpu_bar = MetricBar("CPU", GREEN_DIM)
        self._ram_bar = MetricBar("RAM", BLUE)
        for bar in (self._cpu_bar, self._ram_bar):
            v.addWidget(bar)
        return box

    def _make_config_panel(self) -> QGroupBox:
        box = QGroupBox("  ⚙️   Mission Configuration")
        box.setStyleSheet(
            f"QGroupBox {{ background-color: #f4f1eb; border: 1px solid {BORDER}; border-radius: 8px; }}"
            f"QGroupBox::title {{ background-color: #f4f1eb; }}"
        )
        v = QVBoxLayout(box)
        v.setContentsMargins(18, 20, 18, 16)
        v.setSpacing(12)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        form.setSpacing(8)
        form.setHorizontalSpacing(14)

        self._lat_field  = QLineEdit()
        self._long_field = QLineEdit()
        self._mode_box   = QComboBox()
        self._mode_box.addItems(["live", "test"])

        self._lat_field.setPlaceholderText("e.g.  40.008278")
        self._long_field.setPlaceholderText("e.g.  -83.017514")

        for text, field in [("Latitude", self._lat_field), ("Longitude", self._long_field)]:
            lbl = QLabel(text)
            lbl.setStyleSheet(f"color:{TEXT_DIM}; font-weight:600; font-size:12px;")
            form.addRow(lbl, field)

        mode_lbl = QLabel("Mode")
        mode_lbl.setStyleSheet(f"color:{TEXT_DIM}; font-weight:600; font-size:12px;")
        form.addRow(mode_lbl, self._mode_box)
        v.addLayout(form)

        hint = QLabel("live = full autonomous flight   ·   test = YOLO runs, drone stays grounded")
        hint.setObjectName("muted")
        hint.setWordWrap(True)
        hint.setFont(QFont("", 11))
        v.addWidget(hint)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        save_btn = QPushButton("💾  Save Config")
        run_btn  = QPushButton("🚀  Trigger Mission")
        save_btn.clicked.connect(self._save_config)
        run_btn.clicked.connect(self._trigger_mission)
        btn_row.addWidget(save_btn)
        btn_row.addWidget(run_btn)
        v.addLayout(btn_row)
        return box

    # ── stream ────────────────────────────────────────────────────────────────

    def _stream_connect(self):
        url = self._rtsp_field.text().strip()
        if not url:
            self._set_status("Enter an RTSP URL first.", error=True)
            return
        self._stream_stop()
        self._no_signal.hide()
        self._video_worker = VideoWorker(url)
        self._video_worker.frame_ready.connect(self._on_frame)
        self._video_worker.error.connect(self._on_stream_error)
        self._video_worker.start()
        self._set_status(f"Connecting: {url}")

    def _on_frame(self, img: QImage):
        pix = QPixmap.fromImage(img).scaled(
            self._video_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.FastTransformation,
        )
        self._video_label.setPixmap(pix)

    def _on_stream_error(self, msg: str):
        self._stream_stop()
        self._set_status(msg, error=True)

    def _stream_stop(self):
        if self._video_worker:
            self._video_worker.requestInterruption()
            self._video_worker.quit()
            self._video_worker.wait(1000)
            self._video_worker = None
        self._video_label.setPixmap(QPixmap())
        self._no_signal.show()

    # ── config ────────────────────────────────────────────────────────────────

    def _load_config(self):
        try:
            cfg = toml.load(CONFIG_PATH).get("mission", {})
            self._lat_field.setText(str(cfg.get("lat", "")))
            self._long_field.setText(str(cfg.get("long", "")))
            idx = self._mode_box.findText(cfg.get("mode_type", "live"))
            if idx >= 0:
                self._mode_box.setCurrentIndex(idx)
        except Exception as exc:
            self._set_status(f"Cannot read config.toml: {exc}", error=True)

    def _save_config(self):
        try:
            lat  = float(self._lat_field.text())
            long = float(self._long_field.text())
        except ValueError:
            self._set_status("Invalid coordinates — use decimal format.", error=True)
            return
        try:
            cfg = toml.load(CONFIG_PATH)
            cfg.setdefault("mission", {})
            cfg["mission"]["lat"]       = lat
            cfg["mission"]["long"]      = long
            cfg["mission"]["mode_type"] = self._mode_box.currentText()
            with open(CONFIG_PATH, "w") as fh:
                toml.dump(cfg, fh)
            self._set_status(
                f"Saved — lat={lat}  long={long}  mode={self._mode_box.currentText()}"
            )
        except Exception as exc:
            self._set_status(f"Config write error: {exc}", error=True)

    # ── mission trigger ───────────────────────────────────────────────────────

    def _trigger_mission(self):
        if hasattr(self, "_mission_w") and self._mission_w.isRunning():
            self._set_status("Mission already in progress.", error=True)
            return
        self._set_status("Triggering mission…")
        self._mission_w = MissionWorker(SF_URL, self._mode_box.currentText())
        self._mission_w.done.connect(self._on_mission_response)
        self._mission_w.error.connect(lambda msg: self._set_status(msg, error=True))
        self._mission_w.start()

    def _on_mission_response(self, data: dict):
        if data.get("success"):
            self._set_status(f"Mission started: {data['data'].get('mission_id', '—')}")
            self._pipeline_reset()
            self._pipeline_advance("camera")
        else:
            self._set_status(f"Rejected: {data.get('error')}", error=True)

    # ── pipeline ──────────────────────────────────────────────────────────────

    def _pipeline_advance(self, stage: str):
        if stage == "__done__":
            for key in self._stage_keys:
                self._steps[key].set_state(PipelineStep.DONE)
            for conn in self._connectors:
                conn.set_active(False)
            self._stage_index = len(self._stage_keys) - 1
            self._set_status("Mission complete.")
            return

        if stage == "__error__":
            idx = max(self._stage_index, 0)
            if idx < len(self._stage_keys):
                self._steps[self._stage_keys[idx]].set_state(PipelineStep.ERROR)
            self._set_status("Mission failed — check logs.", error=True)
            return

        if stage not in self._stage_keys:
            return
        new_idx = self._stage_keys.index(stage)
        if new_idx <= self._stage_index:
            return

        for i in range(self._stage_index + 1, new_idx):
            self._steps[self._stage_keys[i]].set_state(PipelineStep.DONE)
            if i < len(self._connectors):
                self._connectors[i].set_active(False)

        self._steps[stage].set_state(PipelineStep.ACTIVE)

        # animate the connector leading into this step
        if new_idx > 0 and (new_idx - 1) < len(self._connectors):
            self._connectors[new_idx - 1].set_active(True)

        self._stage_index = new_idx

    def _pipeline_reset(self):
        for step in self._steps.values():
            step.set_state(PipelineStep.IDLE)
        for conn in self._connectors:
            conn.set_active(False)
        self._stage_index = -1

    # ── workers ───────────────────────────────────────────────────────────────

    def _start_workers(self):
        self._metrics_w = MetricsWorker()
        self._metrics_w.updated.connect(self._on_metrics)
        self._metrics_w.start()

        self._health_w = HealthWorker()
        self._health_w.updated.connect(self._on_health)
        self._health_w.start()

        self._log_w = LogWatcher()
        self._log_w.new_lines.connect(self._log_terminal.add_lines)
        self._log_w.stage_hit.connect(self._pipeline_advance)
        self._log_w.start()

    def _on_metrics(self, cpu: float, ram: float):
        self._cpu_bar.update_value(cpu)
        self._ram_bar.update_value(ram)

    def _on_health(self, status: dict):
        self._sf_dot.set_online(status.get("smartfield", False))
        self._sub_dot.set_online(status.get("subscriber", False))

    def _tick_clock(self):
        self._clock_lbl.setText(
            datetime.now().strftime("  %Y-%m-%d   %H:%M:%S  ")
        )

    def _set_status(self, msg: str, error: bool = False):
        self._status_lbl.setStyleSheet(
            f"color:{'#c0392b' if error else '#3d7a28'};"
            f" font-family:{FONT_MONO}; font-size:11px;"
        )
        self._status_lbl.setText(msg)

    def closeEvent(self, event):
        self._stream_stop()
        if hasattr(self, "_mission_w") and self._mission_w.isRunning():
            self._mission_w.done.disconnect()
            self._mission_w.error.disconnect()
            self._mission_w.wait(2000)
        for w in (self._metrics_w, self._health_w, self._log_w):
            w.requestInterruption()
            w.quit()
            w.wait(1000)
        event.accept()



# ── entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import traceback
    from PyQt6.QtWidgets import QMessageBox

    def _excepthook(exc_type, exc_value, exc_tb):
        text = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        dlg = QMessageBox()
        dlg.setIcon(QMessageBox.Icon.Critical)
        dlg.setWindowTitle("Smartfield — Fatal Error")
        dlg.setText("An unexpected error occurred and the dashboard must close.")
        dlg.setDetailedText(text)
        dlg.exec()
        sys.exit(1)

    sys.excepthook = _excepthook

    app = QApplication(sys.argv)
    app.setStyleSheet(STYLESHEET)
    app.setApplicationName("Smartfield Dashboard")
    window = SmartfieldDashboard()
    window.show()
    window.raise_()
    window.activateWindow()
    sys.exit(app.exec())
