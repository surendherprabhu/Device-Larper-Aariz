#!/usr/bin/env python3
"""
================================================================================
DEVICE LARPER AARIZ (DLA)
Simulated AI-Powered Transistor Optical Inspection System
--------------------------------------------------------------------------------
Cross-Platform Single-File Application: macOS (Apple Silicon) & Arch Linux (x86_64)

IMPORTANT NOTICE / DISCLAIMER:
This application is an educational simulation and demonstration tool.
Diagnostic results (PASS / FAIL) and defect classifications are manually
controlled simulation states designed for inspection workflow testing.
This software does NOT provide genuine electrical diagnosis or physical
fault verification of semiconductor components.
================================================================================
"""

import sys
import os
import time
import math
import random
import platform
import signal
from datetime import datetime

import cv2
import numpy as np

from PySide6.QtCore import (
    Qt, QThread, Signal, Slot, QTimer, QSize, QPoint, QRectF, QObject, QEvent
)
from PySide6.QtGui import (
    QImage, QPixmap, QColor, QFont, QPainter, QPen, QBrush,
    QLinearGradient, QIcon, QKeySequence, QKeyEvent, QShortcut
)
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QGridLayout, QSplitter, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView, QSlider, QComboBox,
    QCheckBox, QSizePolicy, QMessageBox, QAbstractItemView, QDialog
)


# ==============================================================================
# INDUSTRIAL COLOR PALETTE & CONSTANTS
# ==============================================================================

# Industrial Dark Theme (RGB & Hex)
COLOR_BG_DARK       = "#0B0E14"  # Deep Obsidian
COLOR_PANEL_BG      = "#141820"  # Dark Slate Panel
COLOR_PANEL_BORDER  = "#222938"  # Slate Border
COLOR_TEXT_PRIMARY  = "#F0F4F8"  # Crisp White
COLOR_TEXT_MUTED    = "#8290A4"  # Muted Steel
COLOR_ACCENT_CYAN   = "#38BDF8"  # Cyber Cyan

# Diagnostic States: Green (Healthy/Pass) & Red (Defect/Fail)
COLOR_PASS_NEON     = "#00FF88"  # Vibrant Emerald
COLOR_PASS_BG       = "#082F1D"  # Deep Forest Glow
COLOR_PASS_BORDER   = "#00E575"
COLOR_FAIL_NEON     = "#FF3344"  # Vibrant Crimson
COLOR_FAIL_BG       = "#360A10"  # Deep Crimson Glow
COLOR_FAIL_BORDER   = "#FF2B44"
COLOR_WARN_AMBER    = "#F59E0B"  # Searching / Warning Amber

# OpenCV Colors (BGR Tuples)
CV_COLOR_GREEN      = (136, 255, 0)   # #00FF88 in BGR
CV_COLOR_RED        = (68, 51, 255)   # #FF3344 in BGR
CV_COLOR_CYAN       = (248, 189, 56)  # #38BDF8 in BGR
CV_COLOR_AMBER      = (11, 158, 245)  # #F59E0B in BGR
CV_COLOR_WHITE      = (248, 244, 240)
CV_COLOR_DARK_MASK  = (16, 20, 26)

# System Metadata
APP_NAME    = "DEVICE LARPER AARIZ"
APP_SUBTITLE = "AI-POWERED OPTICAL TRANSISTOR INSPECTION SYSTEM"
APP_VERSION = "v1.0.0-PROD"

# Native Monospace Font Stack per platform (Zero alias lookup lag)
if sys.platform == "darwin":
    FONT_MONOSPACE = "Menlo, 'Courier New', monospace"
elif sys.platform in ("win32", "cygwin") or os.name == "nt":
    FONT_MONOSPACE = "Consolas, 'Courier New', monospace"
else:
    FONT_MONOSPACE = "'DejaVu Sans Mono', 'Liberation Mono', monospace"

# ==============================================================================
# CONFIGURABLE KEYBOARD SHORTCUTS
# ==============================================================================
# Modify key bindings here if desired. Supported Qt key codes can be added.
KEY_CONFIG = {
    "TOGGLE_STATE": [Qt.Key.Key_Space, Qt.Key.Key_F],
    "SET_PASS":     [Qt.Key.Key_1, Qt.Key.Key_P],
    "SET_FAIL":     [Qt.Key.Key_2, Qt.Key.Key_D],
    "LOG_RECORD":   [Qt.Key.Key_Return, Qt.Key.Key_Enter],
    "CYCLE_CAM":    [Qt.Key.Key_C],
    "SYNTHETIC":    [Qt.Key.Key_S],
    "RESET_STATS":  [Qt.Key.Key_R],
    "TOGGLE_HUD":   [Qt.Key.Key_H],
    "HELP":         [Qt.Key.Key_F1],
    "EXIT":         [Qt.Key.Key_Q, Qt.Key.Key_Escape],
}


# ==============================================================================
# VISION & TRACKING ENGINE
# ==============================================================================

class BoxSmoother:
    """Exponential Moving Average (EMA) filter for jitter-free tracking."""
    def __init__(self, alpha: float = 0.35, max_lost_frames: int = 12):
        self.alpha = alpha
        self.max_lost_frames = max_lost_frames
        self.box = None
        self.lost_frames = 0

    def update(self, new_box):
        """
        Update smoothed bounding box.
        new_box: (x, y, w, h) or None if target lost.
        Returns: ((x, y, w, h), is_tracking)
        """
        if new_box is None:
            self.lost_frames += 1
            if self.lost_frames > self.max_lost_frames:
                self.box = None
                return None, False
            # Hold lock during brief occlusion
            return [int(round(v)) for v in self.box], True

        self.lost_frames = 0
        if self.box is None:
            self.box = [float(v) for v in new_box]
        else:
            for i in range(4):
                self.box[i] = self.alpha * new_box[i] + (1.0 - self.alpha) * self.box[i]
        return [int(round(v)) for v in self.box], True

    def reset(self):
        self.box = None
        self.lost_frames = 0


class SyntheticBenchGenerator:
    """
    High-fidelity synthetic inspection test bench.
    Renders an animated electronic transistor on an AOI inspection platform.
    Allows full hardware-free demonstration on any system without a webcam.
    """
    def __init__(self, width: int = 1280, height: int = 720):
        self.width = width
        self.height = height
        self.start_time = time.time()
        self.last_defect_state = False

    def generate_frame(self, is_fault: bool):
        t = time.time() - self.start_time
        img = np.full((self.height, self.width, 3), 20, dtype=np.uint8)

        # 1. Industrial Inspection Mat with Grid
        grid_step = 40
        for x in range(0, self.width, grid_step):
            cv2.line(img, (x, 0), (x, self.height), (28, 33, 42), 1)
        for y in range(0, self.height, grid_step):
            cv2.line(img, (0, y), (self.width, y), (28, 33, 42), 1)

        # 2. Stage Center & Micro-Drift (simulating physical turntable micro-vibration)
        cx = self.width // 2
        cy = self.height // 2
        drift_x = int(math.sin(t * 1.4) * 8)
        drift_y = int(math.cos(t * 1.1) * 5)
        scx = cx + drift_x
        scy = cy + drift_y

        # White Inspection Stage Card
        pw, ph = 240, 200
        cv2.rectangle(img, (scx - pw, scy - ph), (scx + pw, scy + ph), (220, 224, 228), -1)
        cv2.rectangle(img, (scx - pw, scy - ph), (scx + pw, scy + ph), (160, 168, 178), 2)

        # Stage Alignment Marks (Fiducials)
        fid_len = 12
        for fx, fy in [
            (scx - pw + 20, scy - ph + 20),
            (scx + pw - 20, scy - ph + 20),
            (scx - pw + 20, scy + ph - 20),
            (scx + pw - 20, scy + ph - 20),
        ]:
            cv2.drawMarker(img, (fx, fy), (120, 128, 140), cv2.MARKER_CROSS, fid_len, 2)

        cv2.putText(
            img, "DLA AOI CALIBRATED BENCH #01",
            (scx - pw + 35, scy - ph + 26),
            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (100, 108, 120), 1, cv2.LINE_AA
        )

        # 3. Transistor Pins (Emitter, Base, Collector)
        pin_y_start = scy + 15
        pin_y_end = scy + 120
        pin_offsets = [-32, 0, 32]

        for i, offset in enumerate(pin_offsets):
            px = scx + offset
            if is_fault and i == 2:
                # FAULT STATE: Bent Collector lead!
                cv2.line(img, (px, pin_y_start), (px + 22, pin_y_start + 50), (100, 105, 115), 5)
                cv2.line(img, (px + 22, pin_y_start + 50), (px + 40, pin_y_end), (140, 145, 155), 5)
                # Defect indicator marker
                cv2.circle(img, (px + 22, pin_y_start + 50), 7, (0, 0, 255), 2)
            else:
                # Normal straight lead
                cv2.line(img, (px, pin_y_start), (px, pin_y_end), (140, 145, 155), 5)
                # Pin shine reflection
                cv2.line(img, (px - 1, pin_y_start), (px - 1, pin_y_end), (200, 205, 215), 1)

        # 4. Transistor Body (TO-92 Molded Plastic Package)
        bw, bh = 60, 65
        cv2.rectangle(img, (scx - bw, scy - bh), (scx + bw, scy + 20), (22, 24, 28), -1)
        cv2.ellipse(img, (scx, scy - bh), (bw, 32), 0, 180, 360, (22, 24, 28), -1)

        # Body Highlight / Specular Edge
        cv2.ellipse(img, (scx, scy - bh), (bw - 4, 28), 0, 200, 340, (50, 54, 62), 2)
        cv2.line(img, (scx - bw + 4, scy - bh), (scx - bw + 4, scy + 18), (50, 54, 62), 1)

        if is_fault:
            # Subtle chip/crack defect on body
            cv2.line(img, (scx - 20, scy - 30), (scx - 5, scy - 12), (180, 30, 40), 2)
            cv2.line(img, (scx - 5, scy - 12), (scx + 8, scy - 18), (180, 30, 40), 2)

        # Laser Marking / Component ID
        cv2.putText(
            img, "2N2222A",
            (scx - 38, scy - 15),
            cv2.FONT_HERSHEY_SIMPLEX, 0.48, (210, 215, 220), 1, cv2.LINE_AA
        )
        cv2.putText(
            img, "BJT-NPN",
            (scx - 32, scy + 8),
            cv2.FONT_HERSHEY_SIMPLEX, 0.40, (170, 175, 185), 1, cv2.LINE_AA
        )

        # Return synthesized frame
        return img


class TransistorDetector:
    """
    OpenCV computer vision detector for transistors and electronic packages.
    Implements multi-scale edge filtering, adaptive thresholding, and contour scoring.
    """
    def __init__(self):
        self.smoother = BoxSmoother(alpha=0.32, max_lost_frames=10)

    def detect(self, frame: np.ndarray, sensitivity: int = 50):
        """
        Detects transistor in frame.
        sensitivity: 0 to 100 slider value.
        Returns:
            (square_box, detected_flag, metrics_dict)
            square_box: (x, y, side, side)
        """
        h, w = frame.shape[:2]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)

        # Inspection Region of Interest (Center 75% of viewport)
        roi_margin_x = int(w * 0.12)
        roi_margin_y = int(h * 0.12)
        roi = blurred[roi_margin_y:h - roi_margin_y, roi_margin_x:w - roi_margin_x]

        # Dynamic sensitivity mapping
        # Sens 50 -> low=40, high=120
        # Sens 100 -> low=20, high=80 (more sensitive to faint edges)
        # Sens 0 -> low=70, high=160
        s_factor = (100 - sensitivity) / 100.0
        low_t = int(25 + 50 * s_factor)
        high_t = int(75 + 90 * s_factor)

        edges = cv2.Canny(roi, low_t, high_t)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (11, 11))
        closed_edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=1)

        contours, hierarchy = cv2.findContours(
            closed_edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE
        )

        target_candidates = []
        center_x, center_y = w // 2, h // 2

        for i, c in enumerate(contours):
            area = cv2.contourArea(c)
            # Area filter: components are typically 1,200 to 220,000 px^2 in ROI
            if 1200 < area < 240000:
                rx, ry, rw, rh = cv2.boundingRect(c)
                # Map back to global coordinates
                gx = rx + roi_margin_x
                gy = ry + roi_margin_y
                gcx = gx + rw / 2.0
                gcy = gy + rh / 2.0

                # Reject outer boundary if it matches the whole ROI or inspection pad exactly
                roi_area = (w - 2 * roi_margin_x) * (h - 2 * roi_margin_y)
                if area > 0.82 * roi_area:
                    continue

                # Aspect ratio check: Transistor body + pins ratio is usually 0.35 to 2.8
                aspect = float(rw) / float(rh) if rh > 0 else 1.0
                if 0.22 <= aspect <= 3.5:
                    # Score by proximity to center crosshairs and compactness
                    dist = math.hypot(gcx - center_x, gcy - center_y)
                    score = dist - (math.sqrt(area) * 0.4)
                    target_candidates.append((score, (gx, gy, rw, rh), area))

        # Select best candidate
        raw_box = None
        cand_area = 0
        if target_candidates:
            target_candidates.sort(key=lambda item: item[0])
            _, (bx, by, bw, bh), cand_area = target_candidates[0]

            # Enforce a square bounding box centered around the component
            side = int(max(bw, bh) * 1.30)
            cx = bx + bw // 2
            cy = by + bh // 2
            sq_x = max(0, min(w - side, cx - side // 2))
            sq_y = max(0, min(h - side, cy - side // 2))
            raw_box = (sq_x, sq_y, side, side)

        # Temporal smoothing
        smoothed_box, is_tracking = self.smoother.update(raw_box)

        metrics = {
            "area": cand_area,
            "center": (center_x, center_y),
            "tracking": is_tracking,
            "leads_detected": 3 if is_tracking else 0
        }

        return smoothed_box, is_tracking, metrics


class HUDOverlayRenderer:
    """Renders high-tech industrial AOI HUD elements directly onto the frame."""
    @staticmethod
    def render(frame: np.ndarray,
               bounding_box,
               is_tracking: bool,
               diagnostic_state: str,
               confidence: float,
               show_full_hud: bool = True,
               fps: float = 30.0,
               source_label: str = "CAM 0"):
        h, w = frame.shape[:2]
        is_healthy = (diagnostic_state == "HEALTHY")
        primary_color = CV_COLOR_GREEN if is_healthy else CV_COLOR_RED

        # 1. Viewport Outer Reticle Brackets (Inspection Viewfinder)
        corner_len = 36
        corner_thick = 2
        ret_color = (80, 90, 105)

        # Top-Left
        cv2.line(frame, (20, 20), (20 + corner_len, 20), ret_color, corner_thick)
        cv2.line(frame, (20, 20), (20, 20 + corner_len), ret_color, corner_thick)
        # Top-Right
        cv2.line(frame, (w - 20, 20), (w - 20 - corner_len, 20), ret_color, corner_thick)
        cv2.line(frame, (w - 20, 20), (w - 20, 20 + corner_len), ret_color, corner_thick)
        # Bottom-Left
        cv2.line(frame, (20, h - 20), (20 + corner_len, h - 20), ret_color, corner_thick)
        cv2.line(frame, (20, h - 20), (20, h - 20 - corner_len), ret_color, corner_thick)
        # Bottom-Right
        cv2.line(frame, (w - 20, h - 20), (w - 20 - corner_len, h - 20), ret_color, corner_thick)
        cv2.line(frame, (w - 20, h - 20), (w - 20, h - 20 - corner_len), ret_color, corner_thick)

        # 2. Central Inspection Reticle (Crosshair)
        cx, cy = w // 2, h // 2
        ch_len = 16
        cv2.line(frame, (cx - ch_len, cy), (cx + ch_len, cy), (60, 70, 85), 1)
        cv2.line(frame, (cx, cy - ch_len), (cx, cy + ch_len), (60, 70, 85), 1)
        cv2.circle(frame, (cx, cy), 45, (45, 55, 68), 1)

        # 3. Transistor Bounding Box (Square)
        if is_tracking and bounding_box is not None:
            bx, by, bw, bh = bounding_box
            # Ensure valid dimensions
            bw = max(20, min(w - bx, bw))
            bh = max(20, min(h - by, bh))

            # Main square outline
            cv2.rectangle(frame, (bx, by), (bx + bw, by + bh), primary_color, 1, cv2.LINE_AA)

            # High-tech corner bracket accents (thick corners)
            c_len = min(28, bw // 4)
            c_thick = 3
            # TL
            cv2.line(frame, (bx, by), (bx + c_len, by), primary_color, c_thick)
            cv2.line(frame, (bx, by), (bx, by + c_len), primary_color, c_thick)
            # TR
            cv2.line(frame, (bx + bw, by), (bx + bw - c_len, by), primary_color, c_thick)
            cv2.line(frame, (bx + bw, by), (bx + bw, by + c_len), primary_color, c_thick)
            # BL
            cv2.line(frame, (bx, by + bh), (bx + c_len, by + bh), primary_color, c_thick)
            cv2.line(frame, (bx, by + bh), (bx, by + bh - c_len), primary_color, c_thick)
            # BR
            cv2.line(frame, (bx + bw, by + bh), (bx + bw - c_len, by + bh), primary_color, c_thick)
            cv2.line(frame, (bx + bw, by + bh), (bx + bw, by + bh - c_len), primary_color, c_thick)

            # Center target pin
            tcx, tcy = bx + bw // 2, by + bh // 2
            cv2.drawMarker(frame, (tcx, tcy), primary_color, cv2.MARKER_CROSS, 12, 1)

            # Floating HUD Tag Bar
            status_text = "PASS" if is_healthy else "FAIL"
            tag_label = f"DLA-TO92 // {status_text} [{confidence:.1f}%]"
            (tw, th), _ = cv2.getTextSize(tag_label, cv2.FONT_HERSHEY_SIMPLEX, 0.48, 1)

            tag_y = max(28, by - 8)
            tag_bg_color = (12, 38, 22) if is_healthy else (38, 12, 16)
            cv2.rectangle(frame, (bx, tag_y - th - 6), (bx + tw + 14, tag_y), tag_bg_color, -1)
            cv2.rectangle(frame, (bx, tag_y - th - 6), (bx + tw + 14, tag_y), primary_color, 1)
            cv2.putText(
                frame, tag_label, (bx + 7, tag_y - 4),
                cv2.FONT_HERSHEY_SIMPLEX, 0.48, primary_color, 1, cv2.LINE_AA
            )

            # Coordinates Readout under box
            coord_text = f"LOC: ({tcx},{tcy}) | BOX: {bw}x{bh}px"
            cv2.putText(
                frame, coord_text, (bx, by + bh + 16),
                cv2.FONT_HERSHEY_SIMPLEX, 0.38, (160, 175, 190), 1, cv2.LINE_AA
            )
        else:
            # NO OBJECT DETECTED MESSAGE
            warn_color = CV_COLOR_AMBER
            msg_banner = "AWAITING COMPONENT PLACEMENT"
            msg_sub = "POSITION TRANSISTOR IN CENTRAL RETICLE"
            (mw, mh), _ = cv2.getTextSize(msg_banner, cv2.FONT_HERSHEY_SIMPLEX, 0.70, 2)
            (sw, sh), _ = cv2.getTextSize(msg_sub, cv2.FONT_HERSHEY_SIMPLEX, 0.42, 1)

            box_w = max(mw, sw) + 40
            box_h = mh + sh + 30
            bx = cx - box_w // 2
            by = cy - box_h // 2 - 80

            # Translucent dark banner
            cv2.rectangle(frame, (bx, by), (bx + box_w, by + box_h), (14, 18, 26), -1)
            cv2.rectangle(frame, (bx, by), (bx + box_w, by + box_h), warn_color, 1)

            cv2.putText(
                frame, msg_banner, (cx - mw // 2, by + mh + 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.70, warn_color, 2, cv2.LINE_AA
            )
            cv2.putText(
                frame, msg_sub, (cx - sw // 2, by + mh + sh + 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.42, (180, 195, 210), 1, cv2.LINE_AA
            )

        # 4. Viewport Telemetry Bars (if show_full_hud enabled)
        if show_full_hud:
            # Top-Left Telemetry
            cv2.putText(
                frame, "DEVICE LARPER AARIZ // OPTICAL AOI CORE",
                (32, 42), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (230, 235, 245), 1, cv2.LINE_AA
            )
            cv2.putText(
                frame, f"FEED: {source_label} | RESOLUTION: {w}x{h} | FPS: {fps:.1f}",
                (32, 62), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (130, 145, 165), 1, cv2.LINE_AA
            )

            # Bottom-Left Telemetry
            state_label = "HEALTHY [PASS]" if is_healthy else "DEFECT DETECTED [FAIL]"
            cv2.putText(
                frame, f"INFERENCE: {state_label} | AI CONF: {confidence:.1f}%",
                (32, h - 35), cv2.FONT_HERSHEY_SIMPLEX, 0.45, primary_color, 1, cv2.LINE_AA
            )
            cv2.putText(
                frame, "CLASSIFIER: REALTIME AOI | PROFILE: TO-92 BJT",
                (32, h - 18), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (120, 135, 150), 1, cv2.LINE_AA
            )

        return frame


# ==============================================================================
# CAMERA WORKER THREAD
# ==============================================================================

class SuppressStderr:
    """Context manager to suppress low-level C++ driver stderr noise during camera probe."""
    def __enter__(self):
        try:
            self.null_fd = os.open(os.devnull, os.O_RDWR)
            self.save_fd = os.dup(2)
            os.dup2(self.null_fd, 2)
        except Exception:
            self.null_fd = None
            self.save_fd = None
        return self

    def __exit__(self, *_):
        if hasattr(self, "save_fd") and self.save_fd is not None:
            try:
                os.dup2(self.save_fd, 2)
                os.close(self.save_fd)
            except Exception:
                pass
        if hasattr(self, "null_fd") and self.null_fd is not None:
            try:
                os.close(self.null_fd)
            except Exception:
                pass


def get_camera_backend():
    """Returns optimal OpenCV camera backend per platform."""
    if sys.platform == "darwin":
        return getattr(cv2, "CAP_AVFOUNDATION", cv2.CAP_ANY)
    elif sys.platform.startswith("linux"):
        return getattr(cv2, "CAP_V4L2", cv2.CAP_ANY)
    elif sys.platform in ("win32", "cygwin") or os.name == "nt":
        return getattr(cv2, "CAP_DSHOW", cv2.CAP_ANY)
    return cv2.CAP_ANY


def scan_available_cameras(max_probe: int = 4):
    """Detect available physical camera indices cross-platform."""
    available = []
    backend = get_camera_backend()
    with SuppressStderr():
        for idx in range(max_probe):
            cap = None
            try:
                cap = cv2.VideoCapture(idx, backend)
                if cap is None or not cap.isOpened():
                    cap = cv2.VideoCapture(idx, cv2.CAP_ANY)

                if cap is not None and cap.isOpened():
                    ret, _ = cap.read()
                    if ret:
                        available.append(idx)
                    cap.release()
            except Exception:
                if cap is not None:
                    try:
                        cap.release()
                    except Exception:
                        pass
    return available


class CameraThread(QThread):
    """
    Asynchronous Camera & Image Processing Thread.
    Never blocks the PySide6 GUI thread.
    Handles physical webcams and synthetic test bench fallback seamlessly.
    All camera open/read/release operations remain strictly on this thread.
    """
    frame_ready = Signal(QImage, dict)
    status_changed = Signal(str, bool)

    def __init__(self, camera_index: int = 0, parent=None):
        super().__init__(parent)
        self.camera_index = camera_index          # Active index
        self.target_camera_index = camera_index   # Requested index
        self.running = True
        self.sensitivity = 50
        self.show_hud = True
        self.diagnostic_state = "HEALTHY"

        self.detector = TransistorDetector()
        self.synthetic = SyntheticBenchGenerator()
        self.cap = None

    def set_camera_index(self, index: int):
        """Thread-safe request to switch camera."""
        self.target_camera_index = index

    def set_sensitivity(self, val: int):
        self.sensitivity = val

    def set_hud_visible(self, visible: bool):
        self.show_hud = visible

    def set_diagnostic_state(self, state: str):
        self.diagnostic_state = state

    def _init_camera(self):
        """Cross-platform camera initialization with fallbacks (worker thread only)."""
        if self.camera_index < 0:
            return True  # Synthetic mode

        self._release_camera()
        try:
            backend = get_camera_backend()
            self.cap = cv2.VideoCapture(self.camera_index, backend)

            if self.cap is None or not self.cap.isOpened():
                self.cap = cv2.VideoCapture(self.camera_index, cv2.CAP_ANY)

            if self.cap is not None and self.cap.isOpened():
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                self.cap.set(cv2.CAP_PROP_FPS, 30)
                return True
        except Exception as e:
            print(f"[DLA] Camera init exception: {e}")

        return False

    def _release_camera(self):
        """Releases camera capture strictly within worker thread."""
        if self.cap is not None:
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None

    def run(self):
        fps_tracker_time = time.time()
        frame_counter = 0
        current_fps = 30.0

        # Initial camera open
        self._init_camera()

        while self.running:
            # Check for camera switch request
            if self.target_camera_index != self.camera_index:
                self._release_camera()
                self.camera_index = self.target_camera_index
                if self.camera_index >= 0:
                    opened = self._init_camera()
                    if opened:
                        self.status_changed.emit(f"CAMERA {self.camera_index} CONNECTED", True)
                    else:
                        self.status_changed.emit(f"CAMERA {self.camera_index} NOT AVAILABLE", False)
                else:
                    self.status_changed.emit("SYNTHETIC BENCH ACTIVE", True)

            is_synthetic = (self.camera_index < 0)
            raw_frame = None

            if is_synthetic:
                is_fault = (self.diagnostic_state == "DEFECT")
                raw_frame = self.synthetic.generate_frame(is_fault=is_fault)
                time.sleep(0.033)  # ~30 FPS cadence
            else:
                if self.cap is None or not self.cap.isOpened():
                    opened = self._init_camera()
                    if not opened:
                        self.status_changed.emit(f"CAMERA {self.camera_index} NOT AVAILABLE", False)
                        raw_frame = np.full((720, 1280, 3), 18, dtype=np.uint8)
                        cv2.putText(
                            raw_frame, f"AWAITING CAMERA {self.camera_index}...",
                            (420, 360), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (180, 190, 205), 2
                        )
                        time.sleep(0.4)
                    else:
                        self.status_changed.emit(f"CAMERA {self.camera_index} CONNECTED", True)

                if self.cap is not None and self.cap.isOpened():
                    ret, frame = self.cap.read()
                    if ret and frame is not None:
                        raw_frame = frame
                    else:
                        self.status_changed.emit("CAMERA SIGNAL LOST - RECONNECTING...", False)
                        self._release_camera()
                        time.sleep(0.4)
                        continue

            if raw_frame is None or not self.running:
                continue

            # FPS Calculation
            frame_counter += 1
            now = time.time()
            if now - fps_tracker_time >= 1.0:
                current_fps = frame_counter / (now - fps_tracker_time)
                frame_counter = 0
                fps_tracker_time = now

            # Run Computer Vision Detection
            box, is_tracking, metrics = self.detector.detect(
                raw_frame, sensitivity=self.sensitivity
            )

            # Realistic simulated confidence with subtle organic jitter
            if is_tracking:
                if self.diagnostic_state == "HEALTHY":
                    jitter = random.uniform(-0.25, 0.25)
                    confidence = max(97.5, min(99.9, 99.2 + jitter))
                else:
                    jitter = random.uniform(-0.35, 0.35)
                    confidence = max(96.0, min(99.4, 98.6 + jitter))
            else:
                confidence = 0.0

            # Render Industrial HUD Graphics onto frame
            source_tag = "SYNTHETIC BENCH" if is_synthetic else f"CAM {self.camera_index}"
            hud_frame = HUDOverlayRenderer.render(
                raw_frame,
                bounding_box=box,
                is_tracking=is_tracking,
                diagnostic_state=self.diagnostic_state,
                confidence=confidence,
                show_full_hud=self.show_hud,
                fps=current_fps,
                source_label=source_tag
            )

            # Convert OpenCV BGR to contiguous RGB
            rgb = np.ascontiguousarray(cv2.cvtColor(hud_frame, cv2.COLOR_BGR2RGB))
            fh, fw, ch = rgb.shape
            bytes_per_line = ch * fw
            qimg = QImage(rgb.data, fw, fh, bytes_per_line, QImage.Format.Format_RGB888).copy()

            telemetry = {
                "tracking": is_tracking,
                "confidence": confidence,
                "box": box,
                "fps": current_fps,
                "source": source_tag,
                "diagnostic_state": self.diagnostic_state
            }

            self.frame_ready.emit(qimg, telemetry)

        # Release capture when thread terminates
        self._release_camera()

    def stop(self):
        """Signals thread to stop and waits for completion."""
        self.running = False
        self.wait(2000)


# ==============================================================================
# CUSTOM INDUSTRIAL UI WIDGETS
# ==============================================================================

class StatusLedWidget(QWidget):
    """Pulsing industrial status LED indicator."""
    def __init__(self, color_hex: str = COLOR_PASS_NEON, size: int = 14, parent=None):
        super().__init__(parent)
        self.color_hex = color_hex
        self.size_px = size
        self.setFixedSize(size + 4, size + 4)
        self.glow_alpha = 180
        self.growing = False

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._pulse)
        self.timer.start(80)

    def set_color(self, hex_code: str):
        self.color_hex = hex_code
        self.update()

    def _pulse(self):
        if self.growing:
            self.glow_alpha += 15
            if self.glow_alpha >= 240:
                self.growing = False
        else:
            self.glow_alpha -= 15
            if self.glow_alpha <= 120:
                self.growing = True
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        center = self.rect().center()
        radius = self.size_px / 2.0

        # Outer glow
        glow_color = QColor(self.color_hex)
        glow_color.setAlpha(self.glow_alpha)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(glow_color))
        painter.drawEllipse(center, radius, radius)

        # Core bright dot
        core_color = QColor(self.color_hex)
        core_color.setAlpha(255)
        painter.setBrush(QBrush(core_color))
        painter.drawEllipse(center, radius * 0.55, radius * 0.55)


class MetricTile(QFrame):
    """Industrial KPI Metric Box."""
    def __init__(self, label: str, value: str = "0", value_color: str = COLOR_TEXT_PRIMARY, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {COLOR_PANEL_BG};
                border: 1px solid {COLOR_PANEL_BORDER};
                border-radius: 6px;
                padding: 4px;
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(2)

        self.lbl_title = QLabel(label.upper())
        self.lbl_title.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 10px; font-weight: bold; letter-spacing: 1px;")

        self.lbl_value = QLabel(value)
        self.lbl_value.setStyleSheet(f"color: {value_color}; font-size: 22px; font-weight: bold; font-family: {FONT_MONOSPACE};")

        layout.addWidget(self.lbl_title)
        layout.addWidget(self.lbl_value)

    def set_value(self, val: str):
        self.lbl_value.setText(val)


class DiagnosticBanner(QFrame):
    """Primary high-impact PASS / FAIL glowing banner with integrated LED status indicator."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(128)
        self.current_state = "HEALTHY"
        self._init_ui()
        self.update_state("HEALTHY")

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 12, 18, 12)
        layout.setSpacing(4)

        # Top row: Result text + Status LED Indicator
        top_row = QHBoxLayout()
        self.lbl_result = QLabel("PASS")
        self.lbl_result.setStyleSheet("font-size: 38px; font-weight: 900; letter-spacing: 2px;")
        top_row.addWidget(self.lbl_result)

        top_row.addStretch()

        self.led_status = StatusLedWidget(COLOR_PASS_NEON, size=18)
        top_row.addWidget(self.led_status)

        layout.addLayout(top_row)

        self.lbl_status = QLabel("● COMPONENT HEALTHY")
        self.lbl_status.setStyleSheet("font-size: 13px; font-weight: bold; letter-spacing: 1px;")

        self.lbl_confidence = QLabel("AI INFERENCE CONFIDENCE: 99.2%")
        self.lbl_confidence.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 11px; font-family: {FONT_MONOSPACE};")

        layout.addWidget(self.lbl_status)
        layout.addWidget(self.lbl_confidence)

    def update_state(self, state: str, confidence: float = 99.2):
        self.current_state = state
        if state == "HEALTHY":
            self.setStyleSheet(f"""
                DiagnosticBanner {{
                    background-color: {COLOR_PASS_BG};
                    border: 2px solid {COLOR_PASS_BORDER};
                    border-radius: 8px;
                }}
            """)
            self.lbl_result.setText("PASS")
            self.lbl_result.setStyleSheet(f"color: {COLOR_PASS_NEON}; font-size: 38px; font-weight: 900; letter-spacing: 2px;")
            self.lbl_status.setText("● COMPONENT HEALTHY")
            self.lbl_status.setStyleSheet(f"color: {COLOR_PASS_NEON}; font-size: 13px; font-weight: bold; letter-spacing: 1px;")
            self.led_status.set_color(COLOR_PASS_NEON)
        else:
            self.setStyleSheet(f"""
                DiagnosticBanner {{
                    background-color: {COLOR_FAIL_BG};
                    border: 2px solid {COLOR_FAIL_BORDER};
                    border-radius: 8px;
                }}
            """)
            self.lbl_result.setText("FAIL")
            self.lbl_result.setStyleSheet(f"color: {COLOR_FAIL_NEON}; font-size: 38px; font-weight: 900; letter-spacing: 2px;")
            self.lbl_status.setText("▲ COMPONENT DEFECT DETECTED")
            self.lbl_status.setStyleSheet(f"color: {COLOR_FAIL_NEON}; font-size: 13px; font-weight: bold; letter-spacing: 1px;")
            self.led_status.set_color(COLOR_FAIL_NEON)

        self.lbl_confidence.setText(f"AI INFERENCE CONFIDENCE: {confidence:.1f}%")


class VideoViewport(QLabel):
    """Viewport label maintaining crisp aspect-ratio scaling."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(480, 270)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet(f"background-color: #05070A; border: 1px solid {COLOR_PANEL_BORDER}; border-radius: 6px;")
        self._pixmap = None

    def set_frame(self, qimage: QImage):
        pixmap = QPixmap.fromImage(qimage)
        self._pixmap = pixmap
        scaled = pixmap.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.setPixmap(scaled)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._pixmap is not None:
            scaled = self._pixmap.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.setPixmap(scaled)


class OperatorGuideDialog(QDialog):
    """
    Discreet Operator Command Reference Dialog (F1).
    Allows the operator to reference controls privately without displaying
    any spoilers on the main inspection dashboard.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("DLA — OPERATOR COMMAND REFERENCE")
        self.setFixedSize(500, 380)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: #11151F;
                border: 1px solid {COLOR_PANEL_BORDER};
                border-radius: 8px;
            }}
            QLabel {{
                color: {COLOR_TEXT_PRIMARY};
            }}
            QPushButton {{
                background-color: #1F2736;
                color: #FFFFFF;
                border: 1px solid {COLOR_PANEL_BORDER};
                border-radius: 4px;
                padding: 6px 16px;
            }}
            QPushButton:hover {{
                background-color: #2D3A50;
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 18, 22, 16)
        layout.setSpacing(10)

        hdr = QLabel("OPERATOR CONTROL REFERENCE")
        hdr.setStyleSheet(f"color: {COLOR_ACCENT_CYAN}; font-size: 13px; font-weight: bold; letter-spacing: 1px;")
        layout.addWidget(hdr)

        sub = QLabel("Coordinated keyboard triggers for testing & live demonstrations:")
        sub.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 11px;")
        layout.addWidget(sub)

        grid = QGridLayout()
        grid.setSpacing(8)

        commands = [
            ("[SPACE] / [F]", "Toggle Diagnostic State (Healthy <-> Defect)"),
            ("[1] / [P]",     "Force Component Healthy (PASS)"),
            ("[2] / [D]",     "Force Component Defect (FAIL)"),
            ("[ENTER]",       "Log Current Inspection Record"),
            ("[C]",           "Cycle Camera Source"),
            ("[S]",           "Engage Synthetic Turntable Test Bench"),
            ("[R]",           "Reset Statistical Counters"),
            ("[H]",           "Toggle On-Screen Reticle HUD Overlays"),
            ("[F1]",          "Toggle This Reference Window"),
            ("[Q] / [ESC]",   "Safe Application Exit"),
        ]

        for row, (k, desc) in enumerate(commands):
            lbl_k = QLabel(k)
            lbl_k.setStyleSheet(f"color: {COLOR_ACCENT_CYAN}; font-weight: bold; font-family: {FONT_MONOSPACE}; font-size: 11px;")
            lbl_d = QLabel(desc)
            lbl_d.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-size: 11px;")
            grid.addWidget(lbl_k, row, 0)
            grid.addWidget(lbl_d, row, 1)

        layout.addLayout(grid)
        layout.addStretch()

        btn_close = QPushButton("DISMISS [ESC]")
        btn_close.clicked.connect(self.close)
        layout.addWidget(btn_close, alignment=Qt.AlignmentFlag.AlignRight)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Escape, Qt.Key.Key_F1):
            self.close()
            event.accept()
        else:
            super().keyPressEvent(event)


class GlobalKeyFilter(QObject):
    """
    Application-wide event filter that intercepts all key presses globally
    before any child widget (button, table, slider, combo) can consume them.
    Guarantees 100% keyboard shortcut reliability across all platforms.
    """
    def __init__(self, window):
        super().__init__()
        self.win = window

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.KeyPress:
            key = event.key()

            if key in KEY_CONFIG["TOGGLE_STATE"]:
                self.win.toggle_diagnostic_state()
                return True
            elif key in KEY_CONFIG["SET_PASS"]:
                self.win.set_diagnostic_state("HEALTHY")
                return True
            elif key in KEY_CONFIG["SET_FAIL"]:
                self.win.set_diagnostic_state("DEFECT")
                return True
            elif key in KEY_CONFIG["LOG_RECORD"]:
                self.win.log_current_inspection()
                return True
            elif key in KEY_CONFIG["CYCLE_CAM"]:
                self.win.cycle_camera()
                return True
            elif key in KEY_CONFIG["SYNTHETIC"]:
                self.win.toggle_synthetic()
                return True
            elif key in KEY_CONFIG["RESET_STATS"]:
                self.win.reset_counters()
                return True
            elif key in KEY_CONFIG["TOGGLE_HUD"]:
                self.win.btn_toggle_hud.toggle()
                self.win._on_toggle_hud()
                return True
            elif key in KEY_CONFIG.get("HELP", [Qt.Key.Key_F1]):
                self.win.show_operator_guide()
                return True
            elif key in KEY_CONFIG["EXIT"]:
                self.win.close()
                return True

        return super().eventFilter(obj, event)


# ==============================================================================
# MAIN APPLICATION WINDOW
# ==============================================================================

class DLAInspectionWindow(QMainWindow):
    """
    DEVICE LARPER AARIZ (DLA) Main Industrial Dashboard Window.
    """
    def __init__(self, camera_override=None, sensitivity_override: int = 50, synthetic_mode: bool = False):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} — {APP_SUBTITLE}")
        self.resize(1340, 860)
        self.setMinimumSize(1024, 680)

        # Inspection Statistics Counters
        self.counter_total = 0
        self.counter_healthy = 0
        self.counter_defects = 0
        self.inspection_index = 1001

        # Current Diagnostic Override State
        self.current_diagnostic_state = "HEALTHY"

        # Apply Global Dark Industrial Stylesheet
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {COLOR_BG_DARK};
            }}
            QWidget {{
                color: {COLOR_TEXT_PRIMARY};
            }}
            QPushButton {{
                background-color: #1F2736;
                color: {COLOR_TEXT_PRIMARY};
                border: 1px solid {COLOR_PANEL_BORDER};
                border-radius: 5px;
                padding: 8px 14px;
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #2A3548;
                border: 1px solid {COLOR_ACCENT_CYAN};
            }}
            QPushButton:pressed {{
                background-color: #151D2A;
            }}
            QComboBox {{
                background-color: #161D28;
                border: 1px solid {COLOR_PANEL_BORDER};
                border-radius: 4px;
                padding: 5px 10px;
                color: {COLOR_TEXT_PRIMARY};
                font-size: 12px;
            }}
            QComboBox QAbstractItemView {{
                background-color: #161D28;
                selection-background-color: #263346;
                color: {COLOR_TEXT_PRIMARY};
            }}
            QSlider::groove:horizontal {{
                border: 1px solid {COLOR_PANEL_BORDER};
                height: 6px;
                background: #161C26;
                border-radius: 3px;
            }}
            QSlider::sub-page:horizontal {{
                background: {COLOR_ACCENT_CYAN};
                border-radius: 3px;
            }}
            QSlider::handle:horizontal {{
                background: #FFFFFF;
                border: 1px solid #778899;
                width: 14px;
                margin-top: -5px;
                margin-bottom: -5px;
                border-radius: 7px;
            }}
            QTableWidget {{
                background-color: #0E121A;
                border: 1px solid {COLOR_PANEL_BORDER};
                border-radius: 4px;
                gridline-color: #1B2230;
                font-size: 11px;
            }}
            QHeaderView::section {{
                background-color: #161C26;
                color: {COLOR_TEXT_MUTED};
                font-size: 10px;
                font-weight: bold;
                border: 1px solid {COLOR_PANEL_BORDER};
                padding: 4px;
            }}
        """)

        # Build UI Structure
        self._build_ui()

        # Scan cameras prior to launching thread
        initial_cam = self._populate_cameras()

        if synthetic_mode:
            initial_cam = -1
            self.toggle_synthetic()
        elif camera_override is not None:
            initial_cam = camera_override
            for i in range(self.combo_camera.count()):
                if self.combo_camera.itemData(i) == camera_override:
                    self.combo_camera.setCurrentIndex(i)
                    break

        if sensitivity_override != 50:
            self.slider_sens.setValue(sensitivity_override)

        # Initialize Camera Worker Thread
        self.camera_thread = CameraThread(camera_index=initial_cam, parent=self)
        self.camera_thread.set_sensitivity(self.slider_sens.value())
        self.camera_thread.frame_ready.connect(self._on_frame_ready)
        self.camera_thread.status_changed.connect(self._on_camera_status)
        self.camera_thread.start()

        # Install global application key filter (catches all hotkeys regardless of focus)
        self._guide_dialog = None
        self.key_filter = GlobalKeyFilter(self)
        QApplication.instance().installEventFilter(self.key_filter)

    def _build_ui(self):
        main_widget = QWidget(self)
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(14, 10, 14, 10)
        main_layout.setSpacing(10)

        # 1. Header Bar
        main_layout.addWidget(self._create_header_bar())

        # 2. Main Horizontal Splitter (Viewport vs Telemetry Sidebar)
        content_splitter = QSplitter(Qt.Orientation.Horizontal)
        content_splitter.setChildrenCollapsible(False)

        # Left Column: Video Viewport & Controls
        left_panel = self._create_viewport_panel()
        content_splitter.addWidget(left_panel)

        # Right Column: Diagnostics, Counters & Log Table
        right_panel = self._create_diagnostics_panel()
        content_splitter.addWidget(right_panel)

        content_splitter.setStretchFactor(0, 7)  # Viewport 70%
        content_splitter.setStretchFactor(1, 3)  # Sidebar 30%
        main_layout.addWidget(content_splitter, stretch=1)

        # 3. Bottom Status Footer
        main_layout.addWidget(self._create_footer_bar())

    def _create_header_bar(self) -> QWidget:
        header = QFrame(self)
        header.setFixedHeight(56)
        header.setStyleSheet(f"""
            QFrame {{
                background-color: {COLOR_PANEL_BG};
                border: 1px solid {COLOR_PANEL_BORDER};
                border-radius: 6px;
            }}
        """)
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(16, 8, 16, 8)

        # Title & Subtitle
        v_title = QVBoxLayout()
        v_title.setSpacing(1)

        title_lbl = QLabel(f"<b>{APP_NAME}</b> <span style='color:{COLOR_ACCENT_CYAN}; font-size:12px;'>{APP_VERSION}</span>")
        title_lbl.setStyleSheet("font-size: 16px; letter-spacing: 1px;")
        sub_lbl = QLabel(APP_SUBTITLE)
        sub_lbl.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 10px; font-weight: bold; letter-spacing: 1px;")

        v_title.addWidget(title_lbl)
        v_title.addWidget(sub_lbl)
        h_layout.addLayout(v_title)

        h_layout.addStretch()

        # Telemetry Status Pills
        # 1. System Online Pill
        self.led_system = StatusLedWidget(COLOR_PASS_NEON, size=12)
        h_layout.addWidget(self.led_system)
        lbl_online = QLabel("SYSTEM ONLINE")
        lbl_online.setStyleSheet(f"color: {COLOR_PASS_NEON}; font-size: 11px; font-weight: bold; margin-right: 15px;")
        h_layout.addWidget(lbl_online)

        # 2. Camera Status Pill
        self.lbl_camera_status = QLabel("CAM: INITIALIZING...")
        self.lbl_camera_status.setStyleSheet(f"""
            background-color: #1A2230;
            color: {COLOR_ACCENT_CYAN};
            border: 1px solid #2B374A;
            border-radius: 4px;
            padding: 4px 10px;
            font-size: 11px;
            font-family: {FONT_MONOSPACE};
            font-weight: bold;
        """)
        h_layout.addWidget(self.lbl_camera_status)

        # 3. Platform Badge
        if sys.platform == "darwin":
            os_name = "macOS (Apple Silicon)" if platform.machine() in ("arm64", "aarch64") else "macOS (Intel)"
        elif sys.platform.startswith("linux"):
            os_name = f"Linux ({platform.machine()})"
        elif sys.platform in ("win32", "cygwin") or os.name == "nt":
            os_name = f"Windows ({platform.machine()})"
        else:
            os_name = f"{platform.system()} ({platform.machine()})"

        lbl_platform = QLabel(os_name)
        lbl_platform.setStyleSheet(f"""
            background-color: #161A22;
            color: {COLOR_TEXT_MUTED};
            border: 1px solid {COLOR_PANEL_BORDER};
            border-radius: 4px;
            padding: 4px 10px;
            font-size: 11px;
            font-family: {FONT_MONOSPACE};
        """)
        h_layout.addWidget(lbl_platform)

        return header

    def _create_viewport_panel(self) -> QWidget:
        container = QFrame(self)
        container.setStyleSheet(f"""
            QFrame {{
                background-color: {COLOR_PANEL_BG};
                border: 1px solid {COLOR_PANEL_BORDER};
                border-radius: 6px;
            }}
        """)
        v_layout = QVBoxLayout(container)
        v_layout.setContentsMargins(12, 10, 12, 10)
        v_layout.setSpacing(8)

        # Viewport Top Bar
        top_bar = QHBoxLayout()
        feed_title = QLabel("LIVE OPTICAL INSPECTION VIEWPORT")
        feed_title.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 11px; font-weight: bold; letter-spacing: 1px;")
        top_bar.addWidget(feed_title)

        top_bar.addStretch()

        # Camera Source Selector
        lbl_source = QLabel("SOURCE:")
        lbl_source.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 11px; font-weight: bold;")
        top_bar.addWidget(lbl_source)

        self.combo_camera = QComboBox()
        self.combo_camera.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.combo_camera.setMinimumWidth(180)
        self.combo_camera.addItem("Synthetic Test Bench", -1)
        self.combo_camera.addItem("Camera 0 (Default)", 0)
        self.combo_camera.currentIndexChanged.connect(self._on_camera_selected)
        top_bar.addWidget(self.combo_camera)

        # HUD Toggle Button
        self.btn_toggle_hud = QPushButton("[H] HUD: ON")
        self.btn_toggle_hud.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_toggle_hud.setCheckable(True)
        self.btn_toggle_hud.setChecked(True)
        self.btn_toggle_hud.clicked.connect(self._on_toggle_hud)
        top_bar.addWidget(self.btn_toggle_hud)

        v_layout.addLayout(top_bar)

        # Video Display Viewport
        self.viewport = VideoViewport(self)
        v_layout.addWidget(self.viewport, stretch=1)

        # Viewport Bottom Controls
        bottom_bar = QHBoxLayout()
        bottom_bar.setContentsMargins(0, 4, 0, 0)

        lbl_sens = QLabel("DETECTION SENSITIVITY:")
        lbl_sens.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 11px; font-weight: bold;")
        bottom_bar.addWidget(lbl_sens)

        self.slider_sens = QSlider(Qt.Orientation.Horizontal)
        self.slider_sens.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.slider_sens.setRange(10, 95)
        self.slider_sens.setValue(50)
        self.slider_sens.setFixedWidth(160)
        self.slider_sens.valueChanged.connect(self._on_sensitivity_changed)
        bottom_bar.addWidget(self.slider_sens)

        self.lbl_sens_val = QLabel("50%")
        self.lbl_sens_val.setStyleSheet(f"color: {COLOR_ACCENT_CYAN}; font-size: 11px; font-family: {FONT_MONOSPACE};")
        bottom_bar.addWidget(self.lbl_sens_val)

        bottom_bar.addStretch()

        btn_refresh_cam = QPushButton("SCAN CAMERAS")
        btn_refresh_cam.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        btn_refresh_cam.clicked.connect(self._populate_cameras)
        bottom_bar.addWidget(btn_refresh_cam)

        v_layout.addLayout(bottom_bar)

        return container

    def _create_diagnostics_panel(self) -> QWidget:
        container = QFrame(self)
        container.setStyleSheet(f"""
            QFrame {{
                background-color: {COLOR_PANEL_BG};
                border: 1px solid {COLOR_PANEL_BORDER};
                border-radius: 6px;
            }}
        """)
        v_layout = QVBoxLayout(container)
        v_layout.setContentsMargins(12, 12, 12, 12)
        v_layout.setSpacing(12)

        # Section 1: Primary Diagnostic Banner
        sec_title_1 = QLabel("INSPECTION DIAGNOSTIC RESULT")
        sec_title_1.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 10px; font-weight: bold; letter-spacing: 1px;")
        v_layout.addWidget(sec_title_1)

        self.diagnostic_banner = DiagnosticBanner(self)
        v_layout.addWidget(self.diagnostic_banner)

        # Section 1.5: Component Identification
        card_id = QFrame(self)
        card_id.setStyleSheet(f"""
            QFrame {{
                background-color: #0F131C;
                border: 1px solid {COLOR_PANEL_BORDER};
                border-radius: 6px;
            }}
        """)
        id_layout = QVBoxLayout(card_id)
        id_layout.setContentsMargins(12, 10, 12, 10)
        id_layout.setSpacing(3)

        lbl_id_hdr = QLabel("COMPONENT IDENTIFICATION")
        lbl_id_hdr.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 10px; font-weight: bold; letter-spacing: 1px;")
        id_layout.addWidget(lbl_id_hdr)

        self.lbl_comp_name = QLabel("2N2222A NPN BJT TRANSISTOR")
        self.lbl_comp_name.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-size: 13px; font-weight: bold;")
        id_layout.addWidget(self.lbl_comp_name)

        self.lbl_comp_pkg = QLabel("PACKAGE: TO-92 (3-Lead Through-Hole Molded Plastic)")
        self.lbl_comp_pkg.setStyleSheet(f"color: {COLOR_ACCENT_CYAN}; font-size: 11px; font-family: {FONT_MONOSPACE};")
        id_layout.addWidget(self.lbl_comp_pkg)

        self.lbl_comp_pins = QLabel("PINOUT: Pin 1 (Emitter) | Pin 2 (Base) | Pin 3 (Collector)")
        self.lbl_comp_pins.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 10px; font-family: {FONT_MONOSPACE};")
        id_layout.addWidget(self.lbl_comp_pins)

        self.lbl_comp_defect = QLabel("ANALYSIS: NOMINAL SPECIFICATION [PASS]")
        self.lbl_comp_defect.setStyleSheet(f"color: {COLOR_PASS_NEON}; font-size: 11px; font-weight: bold;")
        id_layout.addWidget(self.lbl_comp_defect)

        v_layout.addWidget(card_id)

        # Section 2: Real-time Pin & Junction Geometry Matrix
        sec_title_2 = QLabel("GEOMETRIC TOLERANCE & LEAD INTEGRITY")
        sec_title_2.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 10px; font-weight: bold; letter-spacing: 1px;")
        v_layout.addWidget(sec_title_2)

        card_matrix = QFrame(self)
        card_matrix.setStyleSheet(f"""
            QFrame {{
                background-color: #0E121A;
                border: 1px solid {COLOR_PANEL_BORDER};
                border-radius: 6px;
            }}
        """)
        m_layout = QVBoxLayout(card_matrix)
        m_layout.setContentsMargins(10, 8, 10, 8)
        m_layout.setSpacing(4)

        self.lbl_lead1 = QLabel("PIN 1 (EMITTER)   :  0.00 mm  [NOMINAL]")
        self.lbl_lead1.setStyleSheet(f"color: {COLOR_PASS_NEON}; font-size: 11px; font-family: {FONT_MONOSPACE};")
        m_layout.addWidget(self.lbl_lead1)

        self.lbl_lead2 = QLabel("PIN 2 (BASE)      : +0.01 mm  [NOMINAL]")
        self.lbl_lead2.setStyleSheet(f"color: {COLOR_PASS_NEON}; font-size: 11px; font-family: {FONT_MONOSPACE};")
        m_layout.addWidget(self.lbl_lead2)

        self.lbl_lead3 = QLabel("PIN 3 (COLLECTOR) : -0.01 mm  [NOMINAL]")
        self.lbl_lead3.setStyleSheet(f"color: {COLOR_PASS_NEON}; font-size: 11px; font-family: {FONT_MONOSPACE};")
        m_layout.addWidget(self.lbl_lead3)

        self.lbl_encap = QLabel("ENCAPSULATION     : 100% VOID-FREE [PASS]")
        self.lbl_encap.setStyleSheet(f"color: {COLOR_PASS_NEON}; font-size: 11px; font-family: {FONT_MONOSPACE};")
        m_layout.addWidget(self.lbl_encap)

        v_layout.addWidget(card_matrix)

        # Section 3: Inspection Counters & KPI Tiles
        sec_title_3 = QLabel("PRODUCTION YIELD METRICS")
        sec_title_3.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 10px; font-weight: bold; letter-spacing: 1px;")
        v_layout.addWidget(sec_title_3)

        grid_metrics = QGridLayout()
        grid_metrics.setSpacing(6)

        self.tile_total = MetricTile("Total Inspected", "0", COLOR_TEXT_PRIMARY)
        self.tile_pass = MetricTile("Healthy (Pass)", "0", COLOR_PASS_NEON)
        self.tile_fail = MetricTile("Defects (Fail)", "0", COLOR_FAIL_NEON)
        self.tile_yield = MetricTile("Yield Rate", "100.0%", COLOR_ACCENT_CYAN)

        grid_metrics.addWidget(self.tile_total, 0, 0)
        grid_metrics.addWidget(self.tile_pass, 0, 1)
        grid_metrics.addWidget(self.tile_fail, 1, 0)
        grid_metrics.addWidget(self.tile_yield, 1, 1)

        v_layout.addLayout(grid_metrics)

        # Counter Action Buttons
        h_counter_btns = QHBoxLayout()
        btn_log = QPushButton("LOG INSPECTION")
        btn_log.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        btn_log.setStyleSheet(f"background-color: #1A2433; color: {COLOR_TEXT_PRIMARY}; border: 1px solid #2F3B4F;")
        btn_log.clicked.connect(self.log_current_inspection)
        h_counter_btns.addWidget(btn_log)

        btn_reset = QPushButton("RESET COUNTERS")
        btn_reset.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        btn_reset.setStyleSheet(f"background-color: #1A2433; color: {COLOR_TEXT_MUTED}; border: 1px solid #2F3B4F;")
        btn_reset.clicked.connect(self.reset_counters)
        h_counter_btns.addWidget(btn_reset)

        v_layout.addLayout(h_counter_btns)

        # Section 4: Inspection Event History Log Table
        sec_title_4 = QLabel("INSPECTION EVENT LOG")
        sec_title_4.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 10px; font-weight: bold; letter-spacing: 1px;")
        v_layout.addWidget(sec_title_4)

        self.table_log = QTableWidget(0, 4)
        self.table_log.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table_log.setHorizontalHeaderLabels(["TIME", "COMPONENT ID", "RESULT", "CONF"])
        self.table_log.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_log.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_log.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table_log.verticalHeader().setVisible(False)
        v_layout.addWidget(self.table_log, stretch=1)

        return container

    def _create_footer_bar(self) -> QWidget:
        footer = QFrame(self)
        footer.setFixedHeight(30)
        footer.setStyleSheet(f"""
            QFrame {{
                background-color: {COLOR_PANEL_BG};
                border: 1px solid {COLOR_PANEL_BORDER};
                border-radius: 4px;
            }}
        """)
        h_layout = QHBoxLayout(footer)
        h_layout.setContentsMargins(12, 2, 12, 2)

        # Left status
        lbl_status = QLabel("● SYSTEM OPERATIONAL • AOI CONTINUOUS SURVEILLANCE ACTIVE")
        lbl_status.setStyleSheet(f"color: {COLOR_PASS_NEON}; font-size: 11px; font-weight: bold;")
        h_layout.addWidget(lbl_status)

        h_layout.addStretch()

        # Center telemetry
        lbl_center = QLabel("NEURAL PIPELINE: REALTIME CONVOLUTIONAL AOI • LATENCY: 14ms")
        lbl_center.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 11px; font-family: {FONT_MONOSPACE};")
        h_layout.addWidget(lbl_center)

        h_layout.addStretch()

        # Right certification
        lbl_right = QLabel("PASS THRESHOLD: 95.0% • CALIBRATED [F1: GUIDE]")
        lbl_right.setStyleSheet(f"color: {COLOR_ACCENT_CYAN}; font-size: 11px; font-family: {FONT_MONOSPACE};")
        h_layout.addWidget(lbl_right)

        return footer

    # ==========================================================================
    # SLOTS & EVENT HANDLERS
    # ==========================================================================

    @Slot(QImage, dict)
    def _on_frame_ready(self, qimage: QImage, telemetry: dict):
        self.viewport.set_frame(qimage)

        confidence = telemetry.get("confidence", 99.2)
        # Update diagnostic banner confidence readout
        self.diagnostic_banner.lbl_confidence.setText(
            f"AI INFERENCE CONFIDENCE: {confidence:.1f}%"
        )

    @Slot(str, bool)
    def _on_camera_status(self, message: str, is_active: bool):
        color = COLOR_PASS_NEON if is_active else COLOR_WARN_AMBER
        self.lbl_camera_status.setText(message)
        self.lbl_camera_status.setStyleSheet(f"""
            background-color: #1A2230;
            color: {color};
            border: 1px solid #2B374A;
            border-radius: 4px;
            padding: 4px 10px;
            font-size: 11px;
            font-family: monospace;
            font-weight: bold;
        """)

    def _populate_cameras(self) -> int:
        """Scans for available cameras and updates the dropdown selector."""
        self.combo_camera.blockSignals(True)
        current_data = self.combo_camera.currentData()
        self.combo_camera.clear()

        # Always offer Synthetic Test Bench
        self.combo_camera.addItem("Synthetic Test Bench", -1)

        physical = scan_available_cameras(max_probe=3)
        if physical:
            for idx in physical:
                self.combo_camera.addItem(f"Camera {idx} (Hardware)", idx)
        else:
            self.combo_camera.addItem("No Physical Cameras Found", -2)

        idx_to_select = 0
        if current_data is not None:
            for i in range(self.combo_camera.count()):
                if self.combo_camera.itemData(i) == current_data:
                    idx_to_select = i
                    break
        elif physical:
            for i in range(self.combo_camera.count()):
                if self.combo_camera.itemData(i) == physical[0]:
                    idx_to_select = i
                    break

        self.combo_camera.setCurrentIndex(idx_to_select)
        self.combo_camera.blockSignals(False)

        selected_data = self.combo_camera.itemData(idx_to_select)
        cam_idx = -1 if (selected_data is None or selected_data == -2) else selected_data

        if hasattr(self, "camera_thread") and self.camera_thread is not None:
            self.camera_thread.set_camera_index(cam_idx)

        return cam_idx

    def _on_camera_selected(self, index: int):
        cam_idx = self.combo_camera.itemData(index)
        if cam_idx is None or cam_idx == -2:
            cam_idx = -1  # Fallback to synthetic
        if hasattr(self, "camera_thread") and self.camera_thread is not None:
            self.camera_thread.set_camera_index(cam_idx)

    def _on_sensitivity_changed(self, val: int):
        self.lbl_sens_val.setText(f"{val}%")
        self.camera_thread.set_sensitivity(val)

    def _on_toggle_hud(self):
        show = self.btn_toggle_hud.isChecked()
        self.btn_toggle_hud.setText("[H] HUD: ON" if show else "[H] HUD: OFF")
        self.camera_thread.set_hud_visible(show)

    def toggle_diagnostic_state(self):
        """Toggle between HEALTHY and DEFECT states."""
        if self.current_diagnostic_state == "HEALTHY":
            self.set_diagnostic_state("DEFECT")
        else:
            self.set_diagnostic_state("HEALTHY")

    def set_diagnostic_state(self, state: str):
        """Set diagnostic state immediately across all indicators."""
        self.current_diagnostic_state = state
        self.camera_thread.set_diagnostic_state(state)
        self.diagnostic_banner.update_state(state)

        if hasattr(self, "lbl_comp_defect"):
            if state == "HEALTHY":
                self.lbl_comp_defect.setText("ANALYSIS: NOMINAL SPECIFICATION [PASS]")
                self.lbl_comp_defect.setStyleSheet(f"color: {COLOR_PASS_NEON}; font-size: 11px; font-weight: bold;")
            else:
                self.lbl_comp_defect.setText("ANALYSIS: LEAD COPITY ANOMALY [FAIL]")
                self.lbl_comp_defect.setStyleSheet(f"color: {COLOR_FAIL_NEON}; font-size: 11px; font-weight: bold;")

        if hasattr(self, "lbl_lead3"):
            if state == "HEALTHY":
                self.lbl_lead3.setText("PIN 3 (COLLECTOR) : -0.01 mm  [NOMINAL]")
                self.lbl_lead3.setStyleSheet(f"color: {COLOR_PASS_NEON}; font-size: 11px; font-family: {FONT_MONOSPACE};")
                self.lbl_encap.setText("ENCAPSULATION     : 100% VOID-FREE [PASS]")
                self.lbl_encap.setStyleSheet(f"color: {COLOR_PASS_NEON}; font-size: 11px; font-family: {FONT_MONOSPACE};")
            else:
                self.lbl_lead3.setText("PIN 3 (COLLECTOR) : -0.42 mm  [BEND DEFECT]")
                self.lbl_lead3.setStyleSheet(f"color: {COLOR_FAIL_NEON}; font-size: 11px; font-family: {FONT_MONOSPACE}; font-weight: bold;")
                self.lbl_encap.setText("ENCAPSULATION     : CHIP VOID DETECTED [FAIL]")
                self.lbl_encap.setStyleSheet(f"color: {COLOR_FAIL_NEON}; font-size: 11px; font-family: {FONT_MONOSPACE}; font-weight: bold;")

    def show_operator_guide(self):
        """Displays discrete operator hotkey reference dialog."""
        if not hasattr(self, "_guide_dialog") or self._guide_dialog is None:
            self._guide_dialog = OperatorGuideDialog(self)
        if self._guide_dialog.isVisible():
            self._guide_dialog.hide()
        else:
            self._guide_dialog.show()
            self._guide_dialog.raise_()
            self._guide_dialog.activateWindow()

    def log_current_inspection(self):
        """Log current inspection to statistics and table."""
        self.counter_total += 1
        is_healthy = (self.current_diagnostic_state == "HEALTHY")

        if is_healthy:
            self.counter_healthy += 1
            result_str = "PASS"
            result_color = COLOR_PASS_NEON
        else:
            self.counter_defects += 1
            result_str = "FAIL"
            result_color = COLOR_FAIL_NEON

        # Update KPI tiles
        yield_rate = (self.counter_healthy / self.counter_total) * 100.0 if self.counter_total > 0 else 100.0
        self.tile_total.set_value(str(self.counter_total))
        self.tile_pass.set_value(str(self.counter_healthy))
        self.tile_fail.set_value(str(self.counter_defects))
        self.tile_yield.set_value(f"{yield_rate:.1f}%")

        # Insert table record
        time_str = datetime.now().strftime("%H:%M:%S")
        comp_id = f"TR-{self.inspection_index}"
        self.inspection_index += 1

        conf_str = "99.2%" if is_healthy else "98.6%"

        row = self.table_log.rowCount()
        self.table_log.insertRow(row)

        item_time = QTableWidgetItem(time_str)
        item_id = QTableWidgetItem(comp_id)
        item_result = QTableWidgetItem(result_str)
        item_conf = QTableWidgetItem(conf_str)

        item_result.setForeground(QColor(result_color))
        font = item_result.font()
        font.setBold(True)
        item_result.setFont(font)

        self.table_log.setItem(row, 0, item_time)
        self.table_log.setItem(row, 1, item_id)
        self.table_log.setItem(row, 2, item_result)
        self.table_log.setItem(row, 3, item_conf)
        self.table_log.scrollToBottom()

    def reset_counters(self):
        """Reset inspection statistics and logs."""
        self.counter_total = 0
        self.counter_healthy = 0
        self.counter_defects = 0
        self.tile_total.set_value("0")
        self.tile_pass.set_value("0")
        self.tile_fail.set_value("0")
        self.tile_yield.set_value("100.0%")
        self.table_log.setRowCount(0)

    def cycle_camera(self):
        """Cycle to next camera in dropdown."""
        count = self.combo_camera.count()
        if count > 1:
            next_idx = (self.combo_camera.currentIndex() + 1) % count
            self.combo_camera.setCurrentIndex(next_idx)

    def toggle_synthetic(self):
        """Force synthetic test bench mode."""
        for i in range(self.combo_camera.count()):
            if self.combo_camera.itemData(i) == -1:
                self.combo_camera.setCurrentIndex(i)
                break

    # ==========================================================================
    # KEYBOARD SHORTCUTS & WINDOW CLOSE
    # ==========================================================================

    def keyPressEvent(self, event: QKeyEvent):
        key = event.key()

        # Configurable key bindings via KEY_CONFIG dictionary
        if key in KEY_CONFIG["TOGGLE_STATE"]:
            self.toggle_diagnostic_state()
            event.accept()
        elif key in KEY_CONFIG["SET_PASS"]:
            self.set_diagnostic_state("HEALTHY")
            event.accept()
        elif key in KEY_CONFIG["SET_FAIL"]:
            self.set_diagnostic_state("DEFECT")
            event.accept()
        elif key in KEY_CONFIG["LOG_RECORD"]:
            self.log_current_inspection()
            event.accept()
        elif key in KEY_CONFIG["CYCLE_CAM"]:
            self.cycle_camera()
            event.accept()
        elif key in KEY_CONFIG["SYNTHETIC"]:
            self.toggle_synthetic()
            event.accept()
        elif key in KEY_CONFIG["RESET_STATS"]:
            self.reset_counters()
            event.accept()
        elif key in KEY_CONFIG["TOGGLE_HUD"]:
            self.btn_toggle_hud.toggle()
            self._on_toggle_hud()
            event.accept()
        elif key in KEY_CONFIG.get("HELP", [Qt.Key.Key_F1]):
            self.show_operator_guide()
            event.accept()
        elif key in KEY_CONFIG["EXIT"]:
            self.close()
            event.accept()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        """Clean shutdown of background threads and cameras."""
        if hasattr(self, "_guide_dialog") and self._guide_dialog is not None:
            try:
                self._guide_dialog.close()
            except Exception:
                pass
        if hasattr(self, "camera_thread") and self.camera_thread is not None:
            self.camera_thread.stop()
        event.accept()


# ==============================================================================
# ENTRY POINT
# ==============================================================================

def main():
    import argparse
    parser = argparse.ArgumentParser(
        description=f"{APP_NAME} - {APP_SUBTITLE}",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
KEYBOARD CONTROLS:
  [SPACE / F] : Toggle Diagnostic State (Healthy <-> Defect)
  [1 / P]     : Force Component Healthy (PASS)
  [2 / D]     : Force Defect Detected (FAIL)
  [ENTER]     : Log Inspection Record to Statistics
  [C]         : Cycle Camera Source
  [S]         : Force Synthetic Test Bench Mode
  [R]         : Reset Statistical Counters
  [H]         : Toggle HUD Overlays
  [Q / ESC]   : Clean Application Exit
        """
    )
    parser.add_argument("--camera", type=int, default=None, help="Target camera device index (e.g. 0, 1)")
    parser.add_argument("--synthetic", action="store_true", help="Force synthetic inspection test bench mode")
    parser.add_argument("--sensitivity", type=int, default=50, help="Initial detection sensitivity (10-95)")
    args = parser.parse_args()

    # Handle terminal Ctrl+C cleanly
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    # Enable High DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)

    # Periodic heartbeat timer so Python processes Ctrl+C on Windows
    sig_timer = QTimer()
    sig_timer.timeout.connect(lambda: None)
    sig_timer.start(500)

    window = DLAInspectionWindow(
        camera_override=args.camera,
        sensitivity_override=args.sensitivity,
        synthetic_mode=args.synthetic
    )
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
