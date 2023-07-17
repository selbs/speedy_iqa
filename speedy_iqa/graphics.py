"""
graphics.py: Custom graphics items for the Speedy IQA Package.

This module defines custom graphics items for the Speedy IQA Package to allow for drawing bounding boxes on images.

Classes:
    - CustomGraphicsView: Custom graphics view to handle drawing bounding boxes on images.
"""

from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtWidgets import *
from typing import Optional, Dict, List
from speedy_iqa.utils import ConnectionManager
import math


class CustomGraphicsView(QGraphicsView):
    """
    Custom graphics view to handle zooming, panning, resizing and drawing bounding boxes. This class is used to display
    the images and is the central widget of the main window.

    Methods:
        - zoom_in (self): Zoom in by a factor of 1.2 (20%).
        - zoom_out (self): Zoom out by a factor of 0.8 (20%).
        - on_main_window_resized (self): Resize the image and maintain the same zoom when the main window is resized.
    """
    def __init__(self, parent: Optional[QWidget] = None, main_window = False):
        """
        Initialize the custom graphics view.
        """
        super().__init__()
        # self.connections = {}
        self.connection_manager = ConnectionManager()
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setOptimizationFlag(QGraphicsView.OptimizationFlag.DontAdjustForAntialiasing, True)
        self.setOptimizationFlag(QGraphicsView.OptimizationFlag.DontSavePainterState, True)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.zoom = 1.0
        self.start_rect = None
        self.current_finding = None
        self.current_color = None
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
