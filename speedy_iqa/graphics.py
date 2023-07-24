"""
graphics.py: Custom graphics items for the Speedy IQA Package.

This module defines custom graphics items for the Speedy IQA Package.

Classes:
    - CustomGraphicsView.
"""

from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtWidgets import *
from typing import Optional, Dict, List
from speedy_iqa.utils import ConnectionManager
import math
from qt_material import get_theme


class CustomGraphicsView(QGraphicsView):
    """
    Custom graphics view to handle zooming, panning, resizing. This class is used to display
    the images and is the central widget of the main window.

    Methods:
        - zoom_in (self): Zoom in by a factor of 1.2 (20%).
        - zoom_out (self): Zoom out by a factor of 0.8 (20%).
        - on_main_window_resized (self): Resize the image and maintain the same zoom when the main window is resized.
    """
    def __init__(self, parent: Optional[QWidget] = None, main_window: bool = False, label: Optional[str] = None):
        """
        Initialize the custom graphics view.
        """
        super().__init__()
        # self.connections = {}
        self.connection_manager = ConnectionManager()

        if label is not None:
            self.label = QLabel(label.upper(), self)
            self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.label.setStyleSheet(
                f"background-color: {get_theme('dark_blue.xml')['primaryLightColor']}; margin: 3px; padding: 3px; "
                f"font-size: 16px; font-weight: bold; color: {get_theme('dark_blue.xml')['secondaryDarkColor']};"
            )
            self.label.move(5, 5)  # Place label at the top-left corner with 5px offset from the border.

        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setOptimizationFlag(QGraphicsView.OptimizationFlag.DontAdjustForAntialiasing, True)
        self.setOptimizationFlag(QGraphicsView.OptimizationFlag.DontSavePainterState, True)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.zoom = 1.0
        self.start_rect = None
        self.current_finding = None
        self.current_color = None
        self.label = label
        # self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        self.touch_points = []
        self.rect_items = {}

        if main_window:
            self.connection_manager.connect(parent.resized, self.on_main_window_resized)

    def zoom_in(self):
        """
        Zoom in by a factor of 1.2 (20%).
        """
        factor = 1.2
        self.zoom *= factor
        self.scale(factor, factor)

    def zoom_out(self):
        """
        Zoom out by a factor of 0.8 (20%).
        """
        factor = 0.8
        self.zoom /= factor
        self.scale(factor, factor)

    def on_main_window_resized(self):
        """
        Resize the images and maintain the same zoom when the main window is resized.
        """
        if self.scene() and self.scene().items():
            self.fitInView(self.scene().items()[-1].boundingRect(), Qt.AspectRatioMode.KeepAspectRatio)
            self.scale(self.zoom, self.zoom)
