"""
main_app.py

This module contains the main window of the application.

Classes:
    - MainApp: Main window of the application.
"""

import os
import pydicom
import numpy as np
import pandas as pd
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtWidgets import *
from pydicom.pixel_data_handlers.util import apply_modality_lut, apply_voi_lut
from qimage2ndarray import array2qimage
from qt_material import get_theme, apply_stylesheet
import qtawesome as qta
from PyQt6.QtCore import QTimer
import datetime
import json
from typing import Dict, List, Optional
import matplotlib.pyplot as plt
import sys
from math import ceil
import imageio as iio
from functools import partial
from random import Random

from speedy_iqa.windows import AboutMessageBox, FileSelectionDialog
from speedy_iqa.utils import ConnectionManager, open_yml_file, setup_logging, bytescale
from speedy_iqa.utils import convert_to_checkstate, find_relative_image_path, invert_grayscale
from speedy_iqa.utils import make_column_categorical, expand_dict_column
from speedy_iqa.graphics import CustomGraphicsView

if hasattr(sys, '_MEIPASS'):
    # This is a py2app executable
    resource_dir = sys._MEIPASS
elif 'main.py' in os.listdir(os.path.dirname(os.path.realpath(__file__))):
    resource_dir = os.path.dirname(os.path.realpath(__file__))
elif 'main.py' in os.listdir(os.path.dirname(os.path.abspath("__main__"))):
    # This is a regular Python script
    resource_dir = os.path.dirname(os.path.abspath("__main__"))
elif 'main.py' in os.listdir(os.path.join(os.path.dirname(os.path.abspath("__main__")), 'speedy_iqa')):
    resource_dir = os.path.join(os.path.dirname(os.path.abspath("__main__")), 'speedy_iqa')
else:
    raise(FileNotFoundError(f"Resource directory not found from {os.path.dirname(os.path.abspath('__main__'))}"))

resource_dir = os.path.normpath(os.path.abspath(resource_dir))

outer_setting = QSettings('SpeedyIQA', 'ImageViewer')
config_file = os.path.abspath(os.path.abspath(
    outer_setting.value("last_config_file", os.path.join(resource_dir, "config.yml"))
))
config = open_yml_file(config_file)
logger, console_msg = setup_logging(
    os.path.normpath(os.path.expanduser(os.path.abspath(config['log_dir']))),
)


class ClickableWidget(QWidget):
    clicked = pyqtSignal()

    def mouseReleaseEvent(self, QMouseEvent):
        self.clicked.emit()


class MainApp(QMainWindow):
    """
    Main window of the application.

    :param settings: The loaded app settings.
    :type settings: QSettings
    """
    resized = pyqtSignal()

    def __init__(self, app, settings):
        """
        Initialize the main window.

        :param settings: The loaded app settings.
        :type settings: QSettings
        """
        super().__init__()
        # Initialize UI
        self.app = app
        self.should_quit = False
        self.settings = settings
        self.connection_manager = ConnectionManager()
        self.about_box = AboutMessageBox()
        self.setMouseTracking(True)
        self.setAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents, True)

        # Initialize variables
        self.current_index = 0
        self.checkboxes = {}
        self.radiobuttons = {}
        self.radiobuttons_boxes = {}
        self.colors = {}
        self.viewed_values = {}
        self.rotation = {}
        self.notes = {}
        self.checkbox_values = {}
        self.radiobutton_values = {}
        self.file_list = []
        self.default_groupbox_color = None
        self.highlighted_groupbox_color = None
        self.highlighted_opacity = 0.15
        self.highlighted_radiogroup = None

        # Load the configuration file
        config = self.open_config_yml()
        self.findings = config.get('checkboxes', [])
        self.radiobutton_groups1 = config.get('radiobuttons_page1', {})
        self.radiobutton_groups2 = config.get('radiobuttons_page2', {})
        # self.task = "medical diagnosis"
        self.tristate_checkboxes = config.get('tristate_checkboxes', False)
        self.max_backups = config.get('max_backups', 10)
        self.backup_dir = os.path.normpath(os.path.expanduser(config.get('backup_dir', '~/speedy_iqa/backups')))
        self.backup_interval = config.get('backup_interval', 5)
        self.task = config.get('task', 'General use')

        self.json_path = self.settings.value("json_path", "")
        self.loaded = self.load_from_json()

        if not self.loaded:

            self.dir_path = os.path.normpath(os.path.abspath(self.settings.value("image_path", ".")))
            if not os.path.isdir(self.dir_path):
                if os.path.isdir(os.path.dirname(self.dir_path)):
                    self.dir_path = os.path.dirname(self.dir_path)
                else:
                    raise FileNotFoundError(f"Directory {self.dir_path} not found, nor was the parent directory found.")

            self.file_list = sorted(find_relative_image_path(self.dir_path))
            Random(4).shuffle(self.file_list)

            self.reference_dir_path = os.path.normpath(
                os.path.abspath(self.settings.value("reference_path", "."))
            )
            self.reference_delimiter = self.settings.value("reference_delimiter", "__")

            imgs_wout_ref = self.check_no_of_images_wout_ref()

            if imgs_wout_ref:
                self.show_imgs_wout_ref_warning(imgs_wout_ref)
            if self.should_quit:
                return

            self.viewed_values = {f: False for f in self.file_list}
            self.rotation = {f: 0 for f in self.file_list}
            self.notes = {f: "" for f in self.file_list}
            if bool(self.findings):
                self.checkbox_values = {f: {finding: 0 for finding in self.findings} for f in self.file_list}
            else:
                self.checkbox_values = {f: {} for f in self.file_list}
            if bool(self.radiobutton_groups1):
                self.radiobutton_values = {f: {group['title']: None for group in self.radiobutton_groups1} for f in
                                           self.file_list}
            if bool(self.radiobutton_groups2):
                self.radiobutton_values = {f: {group['title']: None for group in self.radiobutton_groups2} for f in
                                           self.file_list}
            if not bool(self.radiobutton_groups1) and not bool(self.radiobutton_groups2):
                self.radiobutton_values = {f: {} for f in self.file_list}

        self.backup_interval = self.settings.value("backup_interval", 5, type=int)
        self.image = None
        self.reference_image = None

        # Set the initial window size
        self.resize(self.settings.value('window_size', QSize(800, 600)))

        # Set the default colors for the icons
        qta.set_defaults(
            color=get_theme("dark_blue.xml")['primaryLightColor'],
            color_disabled=get_theme("dark_blue.xml")['secondaryDarkColor'],
            color_active=get_theme("dark_blue.xml")['primaryColor'],
        )

        # Set the icons dictionary used in the main window
        self.icons = {}
        self.set_icons()

        # Set the window icon
        icon_path = os.path.normpath(os.path.abspath(os.path.join(resource_dir, 'assets/logo.icns')))
        self.setWindowIcon(QIcon(icon_path))

        # Set the central widget to the image viewer
        self.image_view = CustomGraphicsView(self, main_window=True, label="Assessment")
        self.reference_view = CustomGraphicsView(self, main_window=True, label="Reference")

        # Assign colors to findings
        self.assign_colors_to_findings()

        # Load the checkbox values from json file
        if self.loaded:
            self.restore_from_saved_state()

        # Now set up the main window layout and toolbars
        self.main_layout = QHBoxLayout()
        # print("INITIAL CURRENT INDEX", self.current_index)
        self.current_index = 0
        self.setWindowTitle(f"Speedy IQA - File: {self.file_list[self.current_index]}")

        # Create the image scene and set as the central widget
        self.image_scene = QGraphicsScene(self)
        self.reference_scene = QGraphicsScene(self)
        self.pixmap_item = QGraphicsPixmapItem()
        self.reference_pixmap_item = QGraphicsPixmapItem()
        self.load_file()
        if self.should_quit:
            return
        self.load_image()
        self.image_scene.addItem(self.pixmap_item)
        self.reference_scene.addItem(self.reference_pixmap_item)
        self.image_view.setScene(self.image_scene)
        self.reference_view.setScene(self.reference_scene)
        self.main_layout.addWidget(self.reference_view)
        self.main_layout.addWidget(self.image_view)
        self.apply_stored_rotation()    # Apply any rotation previously applied to the image
        self.central_widget = QWidget(self)
        self.central_widget.setLayout(self.main_layout)
        self.setCentralWidget(self.central_widget)

        # Create the navigation toolbar
        self.file_tool_bar = QToolBar(self)

        # Create the logo action
        logo_path = os.path.normpath(os.path.abspath(os.path.join(resource_dir, 'assets/logo.png')))
        img = iio.imread(logo_path)
        # Pad the logo to make it square for QIcon, otherwise it will be stretched
        height, width, _ = img.shape
        size = max(height, width)
        y_pad = (size - height) // 2
        x_pad = (size - width) // 2
        padded_logo = np.pad(img, [
                (y_pad, size - height - y_pad), (x_pad, size - width - x_pad), (0, 0)
        ], mode='constant', constant_values=0)
        logo_pixmap = QPixmap(array2qimage(padded_logo))
        self.logoAction = QAction(QIcon(logo_pixmap), "About", self)
        self.file_tool_bar.addAction(self.logoAction)
        # Create exit and save action buttons
        self.exitAction = QAction(self.icons['exit'], "Exit", self)
        self.exitAction.setShortcuts([
            QKeySequence(Qt.KeyboardModifier.ControlModifier | Qt.Key.Key_Q),
            QKeySequence.StandardKey.Quit
        ])
        self.file_tool_bar.addAction(self.exitAction)
        self.saveAction = QAction(self.icons['save'], "Save", self)
        self.saveAction.setShortcuts([
            Qt.Key.Key_S,
            QKeySequence.StandardKey.Save
        ])
        self.file_tool_bar.addAction(self.saveAction)
        self.exportAction = QAction(self.icons['export'], "Export to CSV File", self)
        self.file_tool_bar.addAction(self.exportAction)
        self.exportAction.setShortcut(QKeySequence(Qt.KeyboardModifier.ControlModifier | Qt.Key.Key_E))
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.file_tool_bar)

        # Create the labelling toolbar
        self.labelling_toolbar = QToolBar(self)
        self.viewed_label = QLabel(self)
        self.viewed_icon = QLabel(self)

        for page in [1, 2]:
            self.radiobuttons[page] = {}
            self.radiobuttons_boxes[page] = {}
        if bool(self.findings):
            self.create_checkboxes()
        if bool(self.radiobutton_groups1):
            for group in self.radiobutton_groups1:
                self.create_radiobuttons(1, group['title'], group['labels'])
        if bool(self.radiobutton_groups2):
            for group in self.radiobutton_groups2:
                self.create_radiobuttons(2, group['title'], group['labels'])
        self.textbox_label = QLabel(self)
        self.textbox = QTextEdit(self)
        self.stack = QStackedWidget()
        # self.stack = QStackedLayout(self)
        self.page1 = QWidget()
        self.page1_layout = QVBoxLayout(self.page1)
        self.page2 = QWidget()
        self.page2_layout = QVBoxLayout(self.page2)
        self.set_labelling_toolbar()

        # Create the image toolbar for image manipulation
        self.image_toolbar = QToolBar(self)
        # self.invert_action = QAction(self.icons['inv'], "Invert", self)
        # self.image_toolbar.addAction(self.invert_action)
        self.rotate_left_action = QAction(self.icons['rot_left'], "Rotate 90° Left", self)
        self.rotate_left_action.setShortcut(Qt.Key.Key_L)
        self.image_toolbar.addAction(self.rotate_left_action)
        self.rotate_right_action = QAction(self.icons['rot_right'], "Rotate 90° Right", self)
        self.rotate_right_action.setShortcut(Qt.Key.Key_R)
        self.image_toolbar.addAction(self.rotate_right_action)

        # Create zoom buttons
        self.zoom_in_action = QAction(self.icons['zoom_in'], "Zoom In", self)
        self.zoom_in_action.setShortcuts([Qt.Key.Key_Plus, Qt.Key.Key_Equal])
        self.zoom_out_action = QAction(self.icons['zoom_out'], "Zoom Out", self)
        self.zoom_out_action.setShortcuts([Qt.Key.Key_Minus, Qt.Key.Key_Underscore])
        self.image_toolbar.addAction(self.zoom_in_action)
        self.image_toolbar.addAction(self.zoom_out_action)

        # Set scrollbar style (too dark with qt material dark theme...)
        self.set_scroll_bar_colors()

        # Create sliders for windowing
        self.window_center_label = QAction(self.icons['wc'], "Brightness", self)
        self.window_width_label = QAction(self.icons['ww'], "Contrast", self)
        self.window_center_slider = QSlider(Qt.Orientation.Horizontal)
        self.window_width_slider = QSlider(Qt.Orientation.Horizontal)

        self.window_center_slider.setRange(1, 255)
        self.window_center_slider.setValue(127)
        self.window_width_slider.setRange(1, 450)
        self.window_width_slider.setValue(255)
        self.window_center_slider.setInvertedAppearance(True)
        self.window_width_slider.setInvertedAppearance(True)

        # Create a space between the windowing sliders and the next button
        spacer = QSpacerItem(0, 0, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum)
        spacer_layout = QHBoxLayout()
        spacer_widget = QWidget()
        spacer_widget.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        spacer_widget.setLayout(spacer_layout)
        spacer_widget.layout().addItem(spacer)

        # Create a reset window button and label the window sliders
        self.image_toolbar.addSeparator()
        # self.reset_window_action = QAction(self.icons['reset_win'], "Reset Brightness and Contrast", self)
        # self.auto_window_action = QAction(self.icons['auto_win'], "Auto-adjust", self)
        # self.image_toolbar.addAction(self.reset_window_action)
        # self.image_toolbar.addAction(self.auto_window_action)
        # self.image_toolbar.addAction(self.window_center_label)
        # self.image_toolbar.addWidget(self.window_center_slider)
        # self.image_toolbar.addAction(self.window_width_label)
        # self.image_toolbar.addWidget(self.window_width_slider)
        # self.image_toolbar.addWidget(spacer_widget)
        # self.image_toolbar.addSeparator()
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.image_toolbar)

        self.nav_toolbar = QToolBar(self)
        self.nav_spacer = QWidget()
        self.line_color = get_theme("dark_blue.xml")['secondaryLightColor']
        self.nav_spacer.setStyleSheet(f"border-bottom: 1px solid {self.line_color};")
        self.nav_spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.nav_toolbar.addWidget(self.nav_spacer)
        self.nav_toolbar.setMovable(False)
        self.nav_toolbar.addSeparator()
        # Add buttons to the navigator toolbar to navigate to previous and next image
        self.prevAction = QAction(self.icons['prev'], "Previous Image", self)
        self.prevAction.setShortcuts([
            Qt.Key.Key_Left,
            Qt.Key.Key_B,
            Qt.Key.Key_Back,
            Qt.Key.Key_Backspace
        ])
        self.goToAction = QAction(self.icons['goto'], "Go To Image...", self)
        self.goToAction.setShortcuts([
            QKeySequence(Qt.KeyboardModifier.ControlModifier | Qt.Key.Key_F),
            QKeySequence.StandardKey.Open
        ])
        self.nextAction = QAction(self.icons['next'], "Next Image", self)
        self.nextAction.setShortcuts([
            Qt.Key.Key_Right,
            Qt.Key.Key_Space,
            Qt.Key.Key_N,
            # Qt.Key.Key_Enter,
            # Qt.Key.Key_Return
        ])
        self.nextUnratedAction = QAction(self.icons['next_unrated'], "Next Unrated Image", self)
        self.nextUnratedAction.setShortcuts([
            QKeySequence(Qt.KeyboardModifier.ControlModifier | Qt.Key.Key_Right),
            QKeySequence(Qt.KeyboardModifier.ControlModifier | Qt.Key.Key_Space),
            QKeySequence(Qt.KeyboardModifier.ControlModifier | Qt.Key.Key_N),
            # QKeySequence(Qt.KeyboardModifier.ControlModifier | Qt.Key.Key_Enter),
            # QKeySequence(Qt.KeyboardModifier.ControlModifier | Qt.Key.Key_Return),
        ])

        action_width = self.labelling_toolbar.sizeHint().width() // 4

        try:
            nav_bg_color1 = get_theme(self.settings.value("theme", 'dark_blue.xml'))['primaryLightColor']
        except KeyError:
            nav_bg_color1 = get_theme(self.settings.value("theme", 'dark_blue.xml'))['primaryColor']
        try:
            nav_bg_color2 = get_theme(self.settings.value("theme", 'dark_blue.xml'))['secondaryLightColor']
        except KeyError:
            nav_bg_color2 = get_theme(self.settings.value("theme", 'dark_blue.xml'))['secondaryColor']

        self.prevButton = QToolButton()
        self.prevButton.setDefaultAction(self.prevAction)
        self.prevButton.setFixedWidth(action_width)
        # self.prevButton.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.prevButton.setStyleSheet(f"""
                    QToolButton {{background-color: {nav_bg_color1}; border: none; border-radius: 5px;}}
                    QToolButton:hover {{border: none; border-radius: 5px; background-color: {nav_bg_color2};}}
                """)
        self.nav_toolbar.addWidget(self.prevButton)

        self.goToButton = QToolButton()
        self.goToButton.setDefaultAction(self.goToAction)
        self.goToButton.setFixedWidth(action_width)
        self.goToButton.setStyleSheet(f"""
                    QToolButton {{border: none; border-radius: 5px;}}
                    QToolButton:hover {{border: none; border-radius: 5px;}}
                """)
        self.nav_toolbar.addWidget(self.goToButton)

        self.nextUnratedButton = QToolButton()
        self.nextUnratedButton.setDefaultAction(self.nextUnratedAction)
        self.nextUnratedButton.setFixedWidth(action_width)
        # self.nextButton.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        # self.nextUnratedButton.setStyleSheet(f"""
        #     QToolButton {{background-color: {nav_bg_color1}; border: none; border-radius: 5px;}}
        #     QToolButton:hover {{border: none; border-radius: 5px; background-color: {nav_bg_color2};}}
        # """)
        self.nextUnratedButton.setStyleSheet(f"""
                            QToolButton {{border: none; border-radius: 5px;}}
                            QToolButton:hover {{border: none; border-radius: 5px;}}
                        """)
        self.nav_toolbar.addWidget(self.nextUnratedButton)

        self.nextButton = QToolButton()
        self.nextButton.setDefaultAction(self.nextAction)
        self.nextButton.setFixedWidth(action_width)
        # self.nextButton.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.nextButton.setStyleSheet(f"""
            QToolButton {{background-color: {nav_bg_color1}; border: none; border-radius: 5px;}}
            QToolButton:hover {{border: none; border-radius: 5px; background-color: {nav_bg_color2};}}
        """)
        self.nav_toolbar.addWidget(self.nextButton)

        self.nav_toolbar.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.nav_toolbar)

        # Initiate connections between buttons / sliders and their functions
        self.init_connections()

        # Initiate window menus
        self.init_menus()

        # Backup progress... just in case...
        self.backup_files = None
        self.timer = QTimer()
        self.timer.setInterval(self.backup_interval * 60 * 1000)  # convert minutes to milliseconds
        self.connection_manager.connect(self.timer.timeout, self.backup_file)
        self.timer.start()

        # create a progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMinimumWidth(self.width())
        self.progress_bar.setFixedHeight(5)
        self.set_progress_bar_colors()
        # add the progress bar to the status bar at the bottom of the window
        self.progress_text = QLabel()
        self.progress_text.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        self.statusBar().addPermanentWidget(self.progress_text)
        self.statusBar().addPermanentWidget(self.progress_bar)
        percent_viewed = 100 * len([value for value in self.viewed_values.values() if value]) / len(self.file_list)
        self.update_progress_text()
        self.update_progress_bar(percent_viewed)
        self.change_theme(self.settings.value("theme", "dark_blue.xml"))

        self.highlighted_radiogroup = list(self.radiobuttons_boxes[self.stack.currentIndex()+1].keys())[0]
        self.highlight_radiogroup()

        QTimer.singleShot(0, self.set_items_on_initial_size)

        self.central_resize_timer = QTimer()
        self.central_resize_timer.setSingleShot(True)
        self.connection_manager.connect(self.resized, self.start_central_resize_timer)
        self.connection_manager.connect(self.central_resize_timer.timeout, self.determine_layout)

    def set_items_on_initial_size(self):
        self.determine_layout()
        self.image_view.fitInView(self.image_scene.items()[-1].boundingRect(), Qt.AspectRatioMode.KeepAspectRatio)
        self.reference_view.fitInView(self.reference_scene.items()[-1].boundingRect(), Qt.AspectRatioMode.KeepAspectRatio)
        self.delayed_visibility_update()

    def start_central_resize_timer(self):
        self.central_resize_timer.start(200)

    def determine_layout(self):
        image_aspect_ratio = self.pixmap.size().width() / self.pixmap.size().height()

        window_height = self.height()  # height of window
        # Estimate central widget width as window width - labelling toolbar width - 100 pixels for padding
        labelling_toolbar_width = self.labelling_toolbar.sizeHint().width()
        window_width = self.width() - labelling_toolbar_width - 100
        window_aspect_ratio = window_width / window_height

        screen_aspect_ratio = self.screen().size().width() / self.screen().size().height()

        if (
                window_aspect_ratio >= screen_aspect_ratio and image_aspect_ratio >= screen_aspect_ratio
        ) or (
                window_aspect_ratio < screen_aspect_ratio and image_aspect_ratio < screen_aspect_ratio
        ):
            # Both the window and the image are landscape, or both are portrait
            layout = QHBoxLayout()
        else:
            # The window and the image have different orientations
            layout = QVBoxLayout()

        layout.addWidget(self.reference_view)
        layout.addWidget(self.image_view)

        central_widget = QWidget(self)
        central_widget.setLayout(layout)

        self.setCentralWidget(central_widget)

        QTimer.singleShot(0, self.fit_to_view)

    def fit_to_view(self):
        self.image_view.fitInView(self.image_scene.items()[-1].boundingRect(), Qt.AspectRatioMode.KeepAspectRatio)
        self.image_view.scale(self.image_view.zoom, self.image_view.zoom)
        self.reference_view.fitInView(self.reference_scene.items()[-1].boundingRect(),
                                      Qt.AspectRatioMode.KeepAspectRatio)
        self.reference_view.scale(self.reference_view.zoom, self.reference_view.zoom)

    def update_progress_bar(self, progress: float):
        """
        Update the progress bar with the current progress

        :param progress: the current progress
        :type progress: float
        """
        self.progress_bar.setValue(int(progress))

    def update_progress_text(self):
        """
        Update the progress bar with the current progress
        """
        viewed_no = len([value for value in self.viewed_values.values() if value])
        total_no = len(self.file_list)
        self.progress_text.setText(f"Progress: {viewed_no}/{total_no}")

    def init_connections(self):
        """
        Initiate connections between buttons / sliders and their functions
        """
        self.connection_manager.connect(self.textbox.textChanged, self.on_text_changed)
        # self.connection_manager.connect(self.invert_action.triggered, self.invert_colours)
        self.connection_manager.connect(self.rotate_left_action.triggered, self.rotate_image_left)
        self.connection_manager.connect(self.rotate_right_action.triggered, self.rotate_image_right)
        self.connection_manager.connect(self.zoom_in_action.triggered, self.zoom_in)
        self.connection_manager.connect(self.zoom_out_action.triggered, self.zoom_out)
        # self.connection_manager.connect(self.reset_window_action.triggered, self.reset_window_sliders)
        # self.connection_manager.connect(self.auto_window_action.triggered, self.auto_window_sliders)
        # self.connection_manager.connect(self.window_center_slider.valueChanged, self.update_image)
        # self.connection_manager.connect(self.window_width_slider.valueChanged, self.update_image)
        self.connection_manager.connect(self.nextAction.triggered, self.reset_window_sliders)
        self.connection_manager.connect(self.nextUnratedAction.triggered, self.reset_window_sliders)
        self.connection_manager.connect(self.prevAction.triggered, self.reset_window_sliders)
        self.connection_manager.connect(self.prevAction.triggered, self.previous_image)
        self.connection_manager.connect(self.goToAction.triggered, self.go_to_image)
        self.connection_manager.connect(self.nextAction.triggered, self.next_image)
        self.connection_manager.connect(self.nextUnratedAction.triggered, self.next_unrated_image)
        self.connection_manager.connect(self.saveAction.triggered, self.save_to_json)
        self.connection_manager.connect(self.exitAction.triggered, self.quit_app)
        self.connection_manager.connect(self.logoAction.triggered, self.show_about)
        self.connection_manager.connect(self.exportAction.triggered, self.export_to_csv)
        self.connection_manager.connect(self.next_unviewed_button.clicked, self.nextUnratedAction.trigger)

        self.connection_manager.connect(self.image_view.horizontalScrollBar().valueChanged,
                                        self.sync_horizontal_scrollbars)
        self.connection_manager.connect(self.reference_view.horizontalScrollBar().valueChanged,
                                        self.sync_horizontal_scrollbars)

        self.connection_manager.connect(self.image_view.verticalScrollBar().valueChanged,
                                        self.sync_vertical_scrollbars)
        self.connection_manager.connect(self.reference_view.verticalScrollBar().valueChanged,
                                        self.sync_vertical_scrollbars)

    def go_to_image(self):
        """
        Open a dialog to go to a specific image
        """
        dialog = FileSelectionDialog(self.file_list, self)
        result = dialog.exec()
        if result == QDialog.DialogCode.Accepted:
            self.reset_window_sliders()
            index = self.file_list.index(dialog.selected_file)
            self.change_image("go_to", index)

    def sync_horizontal_scrollbars(self, value):
        """
        Sync the horizontal scrollbars of the image and reference views

        :param value: the value of the scrollbar
        :type value: int
        """
        self.image_view.horizontalScrollBar().setValue(value)
        self.reference_view.horizontalScrollBar().setValue(value)

    def sync_vertical_scrollbars(self, value):
        """
        Sync the vertical scrollbars of the image and reference views

        :param value: the value of the scrollbar
        :type value: int
        """
        self.image_view.verticalScrollBar().setValue(value)
        self.reference_view.verticalScrollBar().setValue(value)

    def zoom_in(self):
        """
        Zoom in on the image and reference views
        """
        self.image_view.zoom_in()
        self.reference_view.zoom_in()

    def zoom_out(self):
        """
        Zoom out on the image and reference views
        """
        self.image_view.zoom_out()
        self.reference_view.zoom_out()

    def backup_file(self) -> List[str]:
        """
        Backs up the current file to a backup folder when triggered by the timer.

        :return: A list of backup files
        :rtype: List[str]
        """

        backup_folder_path = os.path.normpath(self.backup_dir)
        # Create the backup folder if it doesn't exist
        os.makedirs(backup_folder_path, exist_ok=True)

        if self.backup_files is None:
            self.backup_files = []

        # Get the current time as a string
        current_time_str = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")

        # Construct the backup file name
        backup_file_name = f"auto_backup_{current_time_str}.bak"

        # Get a list of existing backup files
        backup_files = sorted(
            [f for f in os.listdir(backup_folder_path)])

        # If the number of backup files exceeds the maximum, delete the oldest one
        if len(backup_files) >= self.max_backups:
            os.remove(os.path.join(backup_folder_path, backup_files[0]))
            backup_files.pop(0)

        # Copy the original file to the backup folder with the new name
        self.save_json(os.path.join(backup_folder_path + backup_file_name))

        # Add the new backup file name to the list
        self.backup_files.append(backup_file_name)

        return backup_files

    # def wheelEvent(self, event: QWheelEvent):
    #     """
    #     Override the wheelEvent function to allow for scrolling with the mouse wheel to change the windowing parameters.
    #     - Ctrl/Cmd + Scroll: Change window width
    #     - Shift + Scroll: Change window center
    #
    #     :param event: The wheelEvent function to override
    #     :type event: QWheelEvent
    #     """
    #     if event.modifiers() == Qt.KeyboardModifier.ControlModifier:  # check if Ctrl key is pressed
    #         delta = event.angleDelta().y()  # get the scroll direction
    #         if delta > 0:
    #             # increase window width
    #             self.window_width_slider.setValue(self.window_width_slider.value() + 10)
    #         elif delta < 0:
    #             # decrease window width
    #             self.window_width_slider.setValue(self.window_width_slider.value() - 10)
    #     elif event.modifiers() == Qt.KeyboardModifier.ShiftModifier:  # check if Shft key is pressed
    #         delta = event.angleDelta().y()  # get the scroll direction
    #         if delta > 0:
    #             # increase window width
    #             self.window_center_slider.setValue(self.window_center_slider.value() + 5)
    #         elif delta < 0:
    #             # decrease window width
    #             self.window_center_slider.setValue(self.window_center_slider.value() - 5)
    #     else:
    #         super().wheelEvent(event)

    def open_config_yml(self) -> Dict:
        """
        Opens the config .yml file and returns the data, including the list of findings/checkboxes,
        the maximum number of backups, the backup directory and the log directory.

        :return: The config data
        :rtype: Dict
        """
        last_config_file = os.path.normpath(
            self.settings.value("last_config_file", os.path.join(resource_dir, "config.yml"))
        )
        return open_yml_file(last_config_file)

    def on_text_changed(self):
        """
        Updates the notes dictionary when the text in the notes textbox is changed.
        """
        textbox = self.sender()
        text_entered = textbox.toPlainText().replace("\n", " ").replace(",", ";")
        self.notes[self.file_list[self.current_index]] = text_entered

    def invert_colours(self):
        """
        Inverts the colors of the image.
        """
        for i, image in enumerate([self.image, self.reference_image]):
            if image is not None:
                # Invert the image
                inverted_image = image.copy()
                if image.ndim == 2:
                    inverted_image = 255 - image
                else:
                    inverted_image[..., :3] = 255 - image[..., :3]

                # Update the QPixmap
                qimage = array2qimage(inverted_image)
                pixmap = QPixmap.fromImage(qimage)
                if i == 0:
                    # print(image)
                    self.pixmap_item.setPixmap(pixmap)
                    self.image = inverted_image
                else:
                    self.reference_pixmap_item.setPixmap(pixmap)
                    self.reference_image = inverted_image

    def rotate_image_right(self):
        """
        Rotates the image 90 degrees to the right.
        """
        # Rotate the image by 90 degrees and update the display
        rotated_image = np.rot90(self.image, k=-1)
        rotated_reference_image = np.rot90(self.reference_image, k=-1)
        self.rotation[self.file_list[self.current_index]] = (self.rotation[self.file_list[self.current_index]]-90) % 360
        self.image = rotated_image
        self.reference_image = rotated_reference_image
        self.load_image()
        self.update_image()
        self.image_view.fitInView(self.image_scene.items()[-1].boundingRect(), Qt.AspectRatioMode.KeepAspectRatio)
        self.image_view.scale(self.image_view.zoom, self.image_view.zoom)
        self.reference_view.fitInView(self.reference_scene.items()[-1].boundingRect(),
                                      Qt.AspectRatioMode.KeepAspectRatio)
        self.reference_view.scale(self.reference_view.zoom, self.reference_view.zoom)

    def rotate_image_left(self):
        """
        Rotates the image 90 degrees to the left.
        """
        # Rotate the image by 90 degrees and update the display
        rotated_image = np.rot90(self.image, k=1)
        rotated_reference_image = np.rot90(self.reference_image, k=1)
        self.rotation[self.file_list[self.current_index]] = (self.rotation[self.file_list[self.current_index]]+90) % 360
        self.image = rotated_image
        self.reference_image = rotated_reference_image
        self.load_image()
        self.update_image()
        self.image_view.fitInView(self.image_scene.items()[-1].boundingRect(), Qt.AspectRatioMode.KeepAspectRatio)
        self.image_view.scale(self.image_view.zoom, self.image_view.zoom)
        self.reference_view.fitInView(self.reference_scene.items()[-1].boundingRect(),
                                      Qt.AspectRatioMode.KeepAspectRatio)
        self.reference_view.scale(self.reference_view.zoom, self.reference_view.zoom)

    def apply_stored_rotation(self):
        """
        Applies the stored rotation to the image from previous self.settings.
        """
        rotation_angle = self.rotation.get(self.file_list[self.current_index], 0)
        self.image = np.rot90(self.image, k=rotation_angle // 90)
        self.reference_image = np.rot90(self.reference_image, k=rotation_angle // 90)

    def resizeEvent(self, event: QResizeEvent):
        """
        Emits a signal to update the image size and zoom when the window is resized.

        :param event: The resize event containing the old and new sizes of the widget
        :type event: QResizeEvent
        """
        super().resizeEvent(event)
        self.resized.emit()

    def load_file(self):
        """
        Loads the image file and applies the look-up tables.
        """
        img_path = os.path.join(self.dir_path, self.file_list[self.current_index])
        img_extension = os.path.splitext(img_path)[1]
        # print(img_path)
        # print(img_extension)
        # print(self.reference_dir_path)

        ## Uncomment this block if adding delimiter to reference name
        if self.reference_delimiter and self.reference_delimiter != "":
            reference_name = self.file_list[self.current_index].rsplit(self.reference_delimiter, 1)[0]
        else:
            reference_name = os.path.splitext(self.file_list[self.current_index])[0]

        reference_name = os.path.basename(reference_name)

        if not reference_name.endswith(img_extension) and os.path.isfile(
                os.path.join(self.reference_dir_path, reference_name + img_extension)
        ):
            reference_name = reference_name + img_extension

        # print(reference_name)
        # print(os.path.isfile(
        #         os.path.join(self.reference_dir_path, reference_name + img_extension)
        # ))

        ## Comment out this line if adding delimiter to reference name
        # reference_name = os.path.basename(self.file_list[self.current_index])

        reference_path = os.path.join(self.reference_dir_path, reference_name)

        # print(f"Image Path: {img_path}")
        # print(f"Reference Path: {reference_path}")
        # print(f"Reference Name: {reference_name}")

        try:
            self.image = self.read_file(img_path, img_extension)
            self.reference_image = self.read_file(reference_path, img_extension)

        except Exception as e:
            # QMessageBox.critical(self, "Error", f"Failed to load file:\n{str(e)}",
            #                      QMessageBox.StandardButton.Ok,
            #                      defaultButton=QMessageBox.StandardButton.Ok)

            img_load_error_msg_box = QMessageBox(self)
            img_load_error_msg_box.setIcon(QMessageBox.Icon.Critical)
            img_load_error_msg_box.setWindowTitle("Error")
            img_load_error_msg_box.setText(f"Failed to load file:\n{str(e)}")
            ok_button = img_load_error_msg_box.addButton('Try Next Image', QMessageBox.ButtonRole.AcceptRole)
            quit_button = img_load_error_msg_box.addButton('Quit', QMessageBox.ButtonRole.RejectRole)

            img_load_error_msg_box.exec()

            if img_load_error_msg_box.clickedButton() == quit_button:
                self.quit_app()
                self.should_quit = "failed_to_load"
                return

            self.viewed_values[self.file_list[self.current_index]] = "FAILED"
            # self.next_image(prev_failed=True)
            logger.exception(f"Failed to load file: {img_path} - Message: {str(e)}")

    def check_no_of_images_wout_ref(self):
        """
        Checks the number of images without a reference image.
        """
        images_wout_ref = []
        for i, file in enumerate(self.file_list):
            img_extension = os.path.splitext(file)[1]
            if self.reference_delimiter and self.reference_delimiter != "":
                reference_name = self.file_list[self.current_index].rsplit(self.reference_delimiter, 1)[0]
            else:
                reference_name = os.path.splitext(os.path.basename(self.file_list[self.current_index]))[0]
            reference_name = os.path.basename(reference_name)
            if not reference_name.endswith(img_extension) and os.path.isfile(
                    os.path.join(self.reference_dir_path, reference_name + img_extension)
            ):
                reference_name = reference_name + img_extension
            if not os.path.isfile(os.path.join(self.reference_dir_path, reference_name)):
                images_wout_ref.append(file)
            # if i == 0:
            #     print(f"File: {file}")
            #     print(f"Reference delimiter: {self.reference_delimiter}")
            #     print(f"Reference name: {reference_name}")
            #     print(f"Reference path: {os.path.join(self.reference_dir_path, reference_name)}")
            #     print(f"Reference exists: {os.path.isfile(os.path.join(self.reference_dir_path, reference_name))}")
        return images_wout_ref

    def show_imgs_wout_ref_warning(self, imgs_wout):
        """
        Shows a warning message if there are images without a reference image.

        :param imgs_wout: The list of images without a reference image
        """

        # no_imgs_wout = len(imgs_wout)
        # total_no_imgs = len(self.file_list)

        unique_imgs = []
        for file in self.file_list:
            filename = os.path.basename(file)
            if filename not in unique_imgs:
                unique_imgs.append(filename)

        unique_img_files_wout_ref = []
        for file in imgs_wout:
            filename = os.path.basename(file)
            if filename not in unique_img_files_wout_ref:
                unique_img_files_wout_ref.append(filename)

        total_expected_ref_imgs = len(unique_imgs)
        total_unique_ref_imgs_missing = len(unique_img_files_wout_ref)

        # Display warning message
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Icon.Critical)
        msg_box.setWindowTitle("Error - Images without a Reference")
        msg_box.setText(f"{total_unique_ref_imgs_missing}/{total_expected_ref_imgs} reference images "
                        f"are missing.")
        ok_button = msg_box.addButton('Ok', QMessageBox.ButtonRole.AcceptRole)
        quit_button = msg_box.addButton('Quit', QMessageBox.ButtonRole.RejectRole)

        msg_box.exec()

        if msg_box.clickedButton() == quit_button:
            self.should_quit = "no_ref"

    @staticmethod
    def read_file(file_path: str, file_extension: str):
        """
        Reads the image file and applies the look-up tables.

        :param file_path: The path to the image file
        :type file_path: str
        :param file_extension: The extension of the image file
        :type file_extension: str
        """
        if file_extension == ".dcm":
            # Read the DICOM file
            ds = pydicom.dcmread(file_path)
            image = ds.pixel_array
            image = apply_modality_lut(image, ds)
            image = apply_voi_lut(image.astype(int), ds, 0)
            if ds.PhotometricInterpretation == "MONOCHROME1":
                image = invert_grayscale(image)
            # Convert the pixel array to an 8-bit integer array
            #############################
            # TODO: Check if we want this
            image = bytescale(image)
            #############################
        else:
            # Read the image file
            image = iio.imread(file_path)
            #############################
            # TODO: Check if we want this
            image = bytescale(image)
            #############################
        return image

    def load_image(self):
        """
        Loads the image into the image view.
        """
        # Load the main image
        qimage = array2qimage(self.image)
        self.pixmap = QPixmap.fromImage(qimage)
        self.pixmap_item.setPixmap(self.pixmap)

        # Load the reference image
        reference_qimage = array2qimage(self.reference_image)
        self.reference_pixmap = QPixmap.fromImage(reference_qimage)
        self.reference_pixmap_item.setPixmap(self.reference_pixmap)

    def update_image(self):
        """
        Updates the image in the image view with new windowing settings.
        """
        window_center = self.window_center_slider.value()
        window_width = self.window_width_slider.value()

        for i, image in enumerate([self.image, self.reference_image]):
            img = np.copy(image)
            img = img.astype(np.float16)
            img = (img - window_center + 0.5 * window_width) / window_width
            img[img < 0] = 0
            img[img > 1] = 1
            img = (img * 255).astype(np.uint8)
            qimage = array2qimage(img)
            if i == 0:
                self.pixmap = QPixmap.fromImage(qimage)
                self.pixmap_item.setPixmap(self.pixmap)
            else:
                self.reference_pixmap = QPixmap.fromImage(qimage)
                self.reference_pixmap_item.setPixmap(self.reference_pixmap)

    def create_checkboxes(self):
        """
        Creates the checkboxes for the findings.
        """
        filename = self.file_list[self.current_index]
        for cbox in self.findings:
            self.checkboxes[cbox] = QCheckBox(cbox, self)
            self.checkboxes[cbox].setObjectName(cbox)
            self.checkboxes[cbox].setTristate(self.tristate_checkboxes)
            semitrans_color = QColor(self.colors[cbox])
            semitrans_color.setAlpha(64)
            self.checkboxes[cbox].setStyleSheet(f"QCheckBox::indicator:checked {{ "
                                                f"background-color: {self.colors[cbox].name()}; "
                                                f"image: url(nocheck);"
                                                f"border: 1px solid #999;"
                                                f"width: 18px;"
                                                f"height: 18px;"
                                                f"}}"
                                                f"QCheckBox::indicator:indeterminate {{ "
                                                f"background-color: {semitrans_color.name(QColor.NameFormat.HexArgb)}; "
                                                f"image: url(nocheck);"
                                                f"border: 1px solid {self.colors[cbox].name()};"
                                                f"width: 18px;"
                                                f"height: 18px;"
                                                f"}} ")
            self.checkboxes[cbox].setCheckState(convert_to_checkstate(self.checkbox_values.get(filename, 0).get(cbox, 0)))
            self.connection_manager.connect(self.checkboxes[cbox].stateChanged, self.on_checkbox_changed)

    def create_radiobuttons(self, page, name, options_list):
        """
        Creates the radio buttons for the given options.

        :param name: The name of the radio button group
        :type name: str
        :param options_list: The list of options
        :type options_list: list
        """
        group_box = QGroupBox(name)
        default_gb_color = group_box.palette().color(group_box.backgroundRole())
        self.default_groupbox_color = (f"rgba({default_gb_color.red()}, "
                                           f"{default_gb_color.green()}, "
                                           f"{default_gb_color.blue()}, "
                                           f"{0})")
        self.highlighted_groupbox_color = (f"rgba({default_gb_color.red()}, "
                                           f"{default_gb_color.green()}, "
                                           f"{default_gb_color.blue()}, "
                                           f"{int(default_gb_color.alpha() * self.highlighted_opacity)})")
        group_box.setStyleSheet("QGroupBox { font-size: 14px; }")
        options = [str(option) for option in options_list]
        max_label_length = max([len(label) for label in options])
        layout = QGridLayout()
        num_columns = ceil(4 / max_label_length)  # Adjust the number of columns based on the label length

        # Create a new button group
        button_group = QButtonGroup()
        # Create the radio buttons
        for i, option in enumerate(options):
            radiobutton = QRadioButton(option)
            radiobutton.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            row = i // num_columns
            col = i % num_columns
            layout.addWidget(radiobutton, row, col)
            button_group.addButton(radiobutton, i)

        group_box.setLayout(layout)
        group_box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        self.radiobuttons_boxes[page][name] = group_box
        self.radiobuttons[page][name] = button_group
        self.set_checked_radiobuttons(page)
        self.connection_manager.connect(self.radiobuttons[page][name].idToggled,
                                        partial(self.on_radiobutton_changed, name))
        self.connection_manager.connect(self.radiobuttons[page][name].idClicked,
                                        partial(self.highlight_next_radiogroup, name))

    def on_radiobutton_changed(self, name, id, checked):
        """
        Called when a radio button is changed.

        :param name: Name of the radio button group
        :type name: str
        :param id: ID of the radio button
        :type id: int
        :param checked: Whether the radio button is checked
        :type checked: bool
        """
        if checked:
            self.radiobutton_values[self.file_list[self.current_index]][name] = id

        if all(v is not None for v in self.radiobutton_values[self.file_list[self.current_index]].values()):
            self.viewed_values[self.file_list[self.current_index]] = True
            self.viewed_icon.setPixmap(
                QPixmap(self.icons['viewed'].pixmap(self.file_tool_bar.iconSize() * 2) if self.is_image_viewed()
                        else self.icons['not_viewed'].pixmap(self.file_tool_bar.iconSize() * 2))
            )

    def highlight_next_radiogroup(self, name):
        """
        Highlights the next radio group.

        :param name: Name of the radio button group
        :type name: str
        """
        radiobuttons_boxes_keylist = list(self.radiobuttons_boxes[self.stack.currentIndex()+1].keys())
        current_index = radiobuttons_boxes_keylist.index(name)
        if current_index + 1 < len(radiobuttons_boxes_keylist):
            self.highlighted_radiogroup = radiobuttons_boxes_keylist[current_index + 1]
        else:
            self.highlighted_radiogroup = radiobuttons_boxes_keylist[0]
        self.highlight_radiogroup()

    def highlight_radiogroup(self):
        """
        Highlights the next radio group.
        """
        for name, group_box in self.radiobuttons_boxes[self.stack.currentIndex()+1].items():
            if name == self.highlighted_radiogroup:
                group_box.setStyleSheet(
                    f"QGroupBox {{ font-size: 14px; "
                    f"background-color: {self.highlighted_groupbox_color}; }}"
                )
            else:
                group_box.setStyleSheet(
                    f"QGroupBox {{ font-size: 14px; "
                    f"background-color: {self.default_groupbox_color}; }}"
                )

    def uncheck_all_radiobuttons(self):
        """
        Unchecks all the radio buttons.
        """
        for i in [1, 2]:
            if i in self.radiobuttons:
                for button_group in self.radiobuttons[i].values():
                    button_group.setExclusive(False)
                    for button in button_group.buttons():
                        button.setChecked(False)
                    button_group.setExclusive(True)

    def uncheck_all_radiobuttons_in_group(self, button_group):
        """
        Unchecks all the radio buttons.
        """
        button_group.setExclusive(False)
        for button in button_group.buttons():
            button.setChecked(False)
        button_group.setExclusive(True)

    def update_all_radiobutton_values(self):
        """
        Updates the values of all the radio buttons.
        """
        for i in [1, 2]:
            if i in self.radiobuttons:
                for name, button_group in self.radiobuttons[i].items():
                    self.radiobutton_values[self.file_list[self.current_index]][name] = button_group.checkedId()

    def set_checked_radiobuttons(self, page):
        """
        Sets the checked radio buttons.
        """
        for name in self.radiobuttons[page].keys():
            if self.radiobutton_values.get(self.file_list[self.current_index]).get(name) is not None:
                self.radiobuttons[page][name].button(
                    self.radiobutton_values.get(self.file_list[self.current_index]).get(name)
                ).setChecked(True)
            else:
                self.uncheck_all_radiobuttons_in_group(self.radiobuttons[page][name])
                # self.uncheck_all_radiobuttons()

    def open_page2_if_required_and_page1_complete(self):
        """
        Opens page 2 if required and page 1 is complete.
        """
        if 1 in self.radiobuttons:
            for name in self.radiobuttons[1].keys():
                if self.radiobutton_values.get(self.file_list[self.current_index]).get(name) is None:
                    self.show_page1()
                    self.highlighted_radiogroup = list(self.radiobuttons[1].keys())[0]
                    self.highlight_radiogroup()
                    return
        if 2 in self.radiobuttons:
            for name in self.radiobuttons[2].keys():
                if self.radiobutton_values.get(self.file_list[self.current_index]).get(name) is None:
                    self.show_page2()
                    self.highlighted_radiogroup = list(self.radiobuttons[2].keys())[0]
                    self.highlight_radiogroup()
        return

    def set_labelling_toolbar(self):
        """
        Sets the checkbox toolbar.
        """
        # Ensure always vertical orientation with handle at the top
        self.connection_manager.connect(
            self.labelling_toolbar.orientationChanged, self.correct_labelling_toolbar_orientation
        )
        # Ensure it can only be added to the left or right side
        self.labelling_toolbar.setAllowedAreas(Qt.ToolBarArea.LeftToolBarArea | Qt.ToolBarArea.RightToolBarArea)

        splitter = QSplitter(Qt.Orientation.Vertical)
        self.labelling_toolbar.addWidget(splitter)

        main_content_widget = QWidget()
        main_content_layout = QVBoxLayout(main_content_widget)

        spacer1 = QWidget()
        spacer1.setMinimumHeight(10)
        spacer1.setMaximumHeight(30)
        spacer1.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        main_content_layout.addWidget(spacer1)

        self.viewed_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.viewed_label.setObjectName("viewed_label")
        self.viewed_label.setText(("" if self.is_image_viewed() else "NOT ") + "PREVIOUSLY RATED")
        main_content_layout.addWidget(self.viewed_label)
        self.viewed_icon.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.viewed_icon.setPixmap(
            QPixmap(self.icons['viewed'].pixmap(self.file_tool_bar.iconSize() * 2) if self.is_image_viewed()
                    else self.icons['not_viewed'].pixmap(self.file_tool_bar.iconSize() * 2))
        )
        main_content_layout.addWidget(self.viewed_icon)

        spacer2 = QWidget()
        spacer2.setMinimumHeight(10)
        spacer2.setMaximumHeight(30)
        spacer2.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        main_content_layout.addWidget(spacer2)

        radiobutton_heading = QLabel(self)
        radiobutton_heading.setAlignment(Qt.AlignmentFlag.AlignLeft)
        radiobutton_heading.setText(f"For {self.task}, please rate the image quality in "
                                    f"comparison to the reference:".upper())
        radiobutton_heading.setWordWrap(True)
        radiobutton_heading.setStyleSheet("QLabel { margin-right: 10px; }")
        radiobutton_heading.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.page1_layout.addWidget(radiobutton_heading)

        h_text_layout1 = QHBoxLayout()
        instructions1 = QLabel(self)
        instructions1.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        instructions1.setText("1 = VERY POOR  /  4 = VERY GOOD")
        instructions1.setStyleSheet("QLabel { font-size: 12px; font-weight: normal }")
        # self.page1_layout.addWidget(instructions1)
        h_text_layout1.addWidget(instructions1)
        page_label1 = QLabel(self)
        page_label1.setAlignment(Qt.AlignmentFlag.AlignRight)
        page_label1.setText("1/2")
        page_label1.setStyleSheet("QLabel { font-size: 12px; font-weight: normal }")
        h_text_layout1.addWidget(page_label1)
        self.page1_layout.addLayout(h_text_layout1)

        if self.radiobutton_groups1 is not None:
            radiobutton_widget1 = QWidget()
            radiobutton_widget1.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            radiobutton_layout1 = QVBoxLayout()
            for radio_group_name, radio_group_box in self.radiobuttons_boxes[1].items():
                radiobutton_layout1.addWidget(radio_group_box)

            radiobutton_layout1.addStretch(1)

            radiobutton_widget1.setLayout(radiobutton_layout1)
            # Create a scroll area for the radio buttons
            scroll1 = QScrollArea()
            scroll1.setWidgetResizable(True)
            scroll1.setWidget(radiobutton_widget1)
            scroll1.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            scroll1.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            # Add the scroll area to the page layout
            self.page1_layout.addWidget(scroll1)

        # spacer4 = QWidget()
        # spacer4.setMinimumHeight(0)
        # spacer4.setMaximumHeight(10)
        # spacer4.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        # layout.addWidget(spacer4)

        if bool(self.radiobutton_groups2):
            button = QPushButton('Continue to 2/2', clicked=self.show_page2)
            button.setStyleSheet("font-size: 14px;")
            self.page1_layout.addWidget(button)

        self.page1.setLayout(self.page1_layout)
        self.page1.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.stack.addWidget(self.page1)

        if bool(self.radiobutton_groups2):
            radiobutton_heading2 = QLabel(self)
            radiobutton_heading2.setAlignment(Qt.AlignmentFlag.AlignLeft)
            radiobutton_heading2.setText(
                f"Please rate the image quality in comparison to the reference:".upper())
            radiobutton_heading2.setWordWrap(True)
            radiobutton_heading2.setStyleSheet("QLabel { margin-right: 10px; }")
            radiobutton_heading2.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            self.page2_layout.addWidget(radiobutton_heading2)

            h_text_layout2 = QHBoxLayout()
            instructions2 = QLabel(self)
            instructions2.setAlignment(Qt.AlignmentFlag.AlignLeft)
            instructions2.setText("1 = VERY POOR  /  4 = VERY GOOD")
            instructions2.setStyleSheet("QLabel { font-size: 12px; font-weight: normal }")
            # self.page2_layout.addWidget(instructions2)
            h_text_layout2.addWidget(instructions2)
            page_label2 = QLabel(self)
            page_label2.setAlignment(Qt.AlignmentFlag.AlignRight)
            page_label2.setText("2/2")
            page_label2.setStyleSheet("QLabel { font-size: 12px; font-weight: normal }")
            h_text_layout2.addWidget(page_label2)
            self.page2_layout.addLayout(h_text_layout2)

            radiobutton_widget2 = QWidget()
            radiobutton_widget2.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            radiobutton_layout2 = QVBoxLayout()
            for radio_group_name, radio_group_box in self.radiobuttons_boxes[2].items():
                radiobutton_layout2.addWidget(radio_group_box)

            radiobutton_layout2.addStretch(1)

            radiobutton_widget2.setLayout(radiobutton_layout2)
            # Create a scroll area for the radio buttons
            scroll2 = QScrollArea()
            scroll2.setWidgetResizable(True)
            scroll2.setWidget(radiobutton_widget2)
            scroll2.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            scroll2.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            # # Add the scroll area to the page layout
            self.page2_layout.addWidget(scroll2)

            # instructions2 = QLabel(self)
            # instructions2.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            # instructions2.setText("1 = VERY POOR  /  4 = VERY GOOD")
            # instructions2.setStyleSheet("QLabel { font-size: 12px; font-weight: normal }")
            # self.page2_layout.addWidget(instructions2)

            page2_button_layout = QHBoxLayout()

            # button = QPushButton('Back to 1/2', clicked=self.show_page1)
            button = QPushButton('Back', clicked=self.show_page1)
            button.setStyleSheet("font-size: 14px;")
            page2_button_layout.addWidget(button)

            # self.nextUnratedButton = QToolButton()
            # self.nextUnratedButton.setDefaultAction(self.nextUnratedAction)
            # self.nextUnratedButton.setFixedWidth(action_width)

            # self.next_unviewed_button = QToolButton()
            self.next_unviewed_button = QPushButton('Next Unrated')
            # self.next_unviewed_button.setStyleSheet("font-size: 14px;")
            page2_button_layout.addWidget(self.next_unviewed_button)

            # self.page2_layout.addWidget(button)
            self.page2_layout.addLayout(page2_button_layout)

            self.page2.setLayout(self.page2_layout)
            self.page2.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

            self.stack.addWidget(self.page2)
        else:
            self.next_unviewed_button = QPushButton('Next Unrated', clicked=self.next_unrated_image)
            self.next_unviewed_button.setStyleSheet("font-size: 14px;")
            self.page1_layout.addWidget(self.next_unviewed_button)

        main_content_layout.addWidget(self.stack)

        # spacer3 = QWidget()
        # spacer3.setMinimumHeight(0)
        # spacer3.setMaximumHeight(10)
        # spacer3.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        # layout.addWidget(spacer3)

        # Add the Notes textbox
        self.textbox_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.textbox_label.setObjectName("Notes")
        self.textbox_label.setText("NOTES:")
        # notes_layout.addWidget(self.textbox_label)

        self.textbox.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.textbox.setMinimumHeight(50)
        # self.textbox.setMaximumHeight(150)
        self.textbox.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)

        textbox_widget = QWidget()
        textbox_layout = QVBoxLayout(textbox_widget)
        textbox_layout.addWidget(self.textbox_label)
        textbox_layout.addWidget(self.textbox)
        splitter.addWidget(textbox_widget)

        splitter.addWidget(main_content_widget)
        splitter.addWidget(textbox_widget)

        # self.labelling_toolbar.addWidget(layout_widget)
        self.labelling_toolbar.setStyleSheet("QToolBar QLabel { font-weight: bold; font-size: 14px; }")
        # scroll_action = QWidgetAction(self)
        # scroll_action.setDefaultWidget(scroll)
        # self.labelling_toolbar.addAction(scroll_action)
        self.addToolBar(Qt.ToolBarArea.RightToolBarArea, self.labelling_toolbar)

        self.connection_manager.connect(self.resized, self.sort_toolbar_on_resized)
        self.resize_timer = QTimer()
        self.resize_timer.setSingleShot(True)
        self.connection_manager.connect(self.resize_timer.timeout, self.delayed_visibility_update)

    def sort_toolbar_on_resized(self):
        """Sort the toolbar on resize events."""
        toolbar_height = self.labelling_toolbar.sizeHint().height()
        should_show = toolbar_height * 0.9 <= self.height()

        if self.viewed_icon.isVisible() != should_show:
            # Restart the timer on every resize event
            self.resize_timer.start(200)  # Adjust the delay as needed

    def delayed_visibility_update(self):
        """Update the visibility of the viewed icon after a delay."""
        toolbar_height = self.labelling_toolbar.sizeHint().height()
        should_show = toolbar_height * 0.9 <= self.height()

        if self.viewed_icon.isVisible() != should_show:
            self.viewed_icon.setVisible(should_show)

    def correct_labelling_toolbar_orientation(self):
        """Correct the orientation of the labelling toolbar."""
        self.labelling_toolbar.setOrientation(Qt.Orientation.Vertical)

    def show_page1(self):
        """
        Shows the first page of the stacked widget.
        """
        self.stack.setCurrentIndex(0)
        self.highlighted_radiogroup = list(self.radiobuttons_boxes[self.stack.currentIndex()+1].keys())[0]
        self.highlight_radiogroup()

    def show_page2(self):
        """
        Shows the second page of the stacked widget.
        """
        self.stack.setCurrentIndex(1)
        self.highlighted_radiogroup = list(self.radiobuttons_boxes[self.stack.currentIndex()+1].keys())[0]
        self.highlight_radiogroup()

    def go_to_next_page_or_image(self):
        """
        Goes to the next page or image.
        """
        if self.stack.currentIndex() == 0 and bool(self.radiobutton_groups2):
            self.show_page2()
        else:
            self.change_image("next_unrated")

    def restore_from_saved_state(self):
        """
        Restores the state of the application from the saved state.
        """
        # Check for saved settings and restore last viewed file
        if self.settings.contains('last_file') and self.settings.contains('last_index'):
            last_file = self.settings.value('last_file')
            last_index = self.settings.value('last_index')
            self.current_index = self.file_list.index(last_file) if last_file in self.file_list else (
                last_index) if last_index < len(self.file_list) else 0

        # Create a new file list that puts unviewed files after the current file.
        unviewed_files = [f for f in self.file_list if not self.viewed_values[f]]
        # viewed_files = [f for f in self.file_list if self.viewed_values[f]]
        if len(unviewed_files) == 0:
            QMessageBox.information(self, "All Images Rated", "You have rated all the images.")
        # else:
        #     self.file_list = unviewed_files + viewed_files

    def reset_window_sliders(self):
        """
        Resets the window sliders to the default values.
        """
        self.window_center_slider.setValue(127)
        self.window_width_slider.setValue(255)

    def auto_window_sliders(self):
        """
        Resets the window sliders to the default values.
        """
        # Calculate the bounds for the central 90% of the intensities
        lower_bound = np.percentile(self.image, 5)
        upper_bound = np.percentile(self.image, 95)

        # Filter out the intensities outside of these bounds
        central_image = self.image[(self.image >= lower_bound) & (self.image <= upper_bound)]

        # Calculate median of the filtered image, which will be our window level
        window_level = np.median(central_image)

        # Calculate window width to cover a certain percentile of the pixel intensities
        percentile = 99
        lower = np.percentile(central_image, (100 - percentile) / 2)
        upper = np.percentile(central_image, 100 - ((100 - percentile) / 2))
        window_width = upper - lower

        self.window_center_slider.setValue(int(window_level))
        self.window_width_slider.setValue(int(window_width))

    def change_image(self, direction: str, go_to_index: Optional[int] = None,
                     # prev_failed: bool = False
                     ):
        """
        Changes the current image in the file list based on the given direction.

        :param direction: Either "previous", "next_unrated" or "next" image
        :type direction: str
        :param go_to_index: Only applicable if direction is "go_to"
        :type go_to_index: Optional[int]
        """
        if direction not in ("previous", "next", "go_to", "next_unrated"):
            raise ValueError("Invalid direction value. Expected 'previous' or 'next'.")

        # for cbox in self.findings:
        #     # Set the checkbox value based on the stored value
        #     checkbox_value = self.checkbox_values.get(self.file_list[self.current_index], False)[cbox]
        #     # print(cbox, checkbox_value)

        # if direction == "previous":
        #     self.viewed_values[self.file_list[self.current_index]] = True
        if self.viewed_values[self.file_list[self.current_index]] != "FAILED":
            if all(v is not None for v in self.radiobutton_values[self.file_list[self.current_index]].values()):
                self.viewed_values[self.file_list[self.current_index]] = True
            else:
                self.viewed_values[self.file_list[self.current_index]] = False

        # Save current file and index
        self.save_settings()

        if direction == "previous":
            self.current_index -= 1
            if self.current_index < 0:
                self.current_index = len(self.file_list) - 1
        elif direction == "go_to":
            self.current_index = go_to_index
        elif direction == "next":
            if self.current_index == len(self.file_list) - 1:
                # All images have been viewed
                QMessageBox.information(self, "All Images Viewed", "You have viewed all the images.")
                self.current_index = 0
            else:
                self.current_index += 1
        else:
            # Find the index of the next unviewed file
            unrated = [f for f in self.file_list[self.current_index + 1:] if not self.viewed_values[f]]
            next_unrated = unrated[0] if len(unrated) > 0 else None
            if next_unrated is None:
                unrated = [f for f in self.file_list[0:self.current_index] if not self.viewed_values[f]]
                next_unrated = unrated[0] if len(unrated) > 0 else None
            if next_unrated is None:
                # All images have been viewed
                QMessageBox.information(self, "All Images Rated", "You have rated all the images.")
            else:
                self.current_index = self.file_list.index(next_unrated)

            # next_unviewed_index = (self.current_index + 1) % len(self.file_list)
            # while next_unviewed_index != self.current_index and self.viewed_values[self.file_list[next_unviewed_index]]:
            #     next_unviewed_index = (next_unviewed_index + 1) % len(self.file_list)
            #
            # if next_unviewed_index == self.current_index:
            #     # All images have been viewed
            #     QMessageBox.information(self, "All Images Rated", "You have rated all the images.")
            #     self.current_index += 1
            #     if self.current_index >= len(self.file_list):
            #         self.current_index = 0
            # else:
            #     self.current_index = next_unviewed_index

        self.load_file()
        self.apply_stored_rotation()
        self.load_image()
        self.update_image()

        self.window_center_slider.setValue(127)
        self.window_width_slider.setValue(255)

        self.setWindowTitle(f"Speedy IQA - File: {self.file_list[self.current_index]}")
        self.image_view.zoom = 1
        self.reference_view.zoom = 1

        self.image_view.fitInView(self.image_scene.items()[-1].boundingRect(), Qt.AspectRatioMode.KeepAspectRatio)
        self.reference_view.fitInView(self.reference_scene.items()[-1].boundingRect(), Qt.AspectRatioMode.KeepAspectRatio)

        self.show_page1()
        self.set_checkbox_value()
        self.set_checked_radiobuttons(1)
        self.set_checked_radiobuttons(2)

        self.viewed_label.setText(("" if self.is_image_viewed() else "NOT ") + "PREVIOUSLY RATED")
        self.viewed_icon.setPixmap(
            QPixmap(self.icons['viewed'].pixmap(self.file_tool_bar.iconSize() * 2) if self.is_image_viewed()
                    else self.icons['not_viewed'].pixmap(self.file_tool_bar.iconSize() * 2))
        )

        self.open_page2_if_required_and_page1_complete()
        self.highlighted_radiogroup = list(self.radiobuttons_boxes[self.stack.currentIndex()+1].keys())[0]
        self.highlight_radiogroup()

        self.update_progress_text()
        percent_viewed = 100*len([value for value in self.viewed_values.values() if value])/len(self.file_list)
        self.update_progress_bar(percent_viewed)

        self.textbox.setPlainText(self.notes[self.file_list[self.current_index]])

    def previous_image(self):
        """
        Loads the previous image in the file list.
        """
        self.change_image("previous")

    def next_image(self):
        """
        Loads the next image in the file list.
        """
        self.change_image("next")

    def next_unrated_image(self):
        """
        Loads the next unrated image in the file list.
        """
        self.change_image("next_unrated")

    def is_image_viewed(self) -> bool:
        """
        Checks if the current image has been viewed previously.
        """
        filename = self.file_list[self.current_index]
        return self.viewed_values.get(filename, False)

    def set_checkbox_value(self):
        """
        Sets the checkbox value for the current file.
        """
        # Get the checkbox widget for the current file
        filename = self.file_list[self.current_index]
        for cbox in self.findings:
            # Set the checkbox value based on the stored value
            checkbox_value = self.checkbox_values.get(filename, False)[cbox]
            # print(cbox, checkbox_value)
            self.checkboxes[cbox].setCheckState(convert_to_checkstate(checkbox_value))

    # def keyPressEvent(self, event: QKeyEvent):
    #     """
    #     Handles key presses as shortcuts.
    #
    #     :param event: The key press event
    #     :type event: QKeyEvent
    #     """
    #     # Set up shortcuts
    #     # if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
    #     if event.key() == Qt.Key.Key_B:
    #         self.previous_image()
    #     elif event.key() == Qt.Key.Key_N:
    #         self.next_image()
    #     elif event.key() == Qt.Key.Key_Space:
    #         self.next_image()
    #     elif event.key() == Qt.Key.Key_Minus or event.key() == Qt.Key.Key_Underscore:
    #         self.zoom_out()
    #     elif event.key() == Qt.Key.Key_Plus or event.key() == Qt.Key.Key_Equal:
    #         self.zoom_in()
    #     elif event.key() == Qt.Key.Key_I:
    #         self.invert_colours()
    #     elif event.key() == Qt.Key.Key_R:
    #         self.rotate_image_right()
    #     elif event.key() == Qt.Key.Key_L:
    #         self.rotate_image_left()
    #     elif event.key() == Qt.Key.Key_S:
    #         self.save_to_json()
    #     elif event.modifiers() == Qt.KeyboardModifier.ControlModifier:
    #         if event.key() == Qt.Key.Key_Q:
    #             self.quit_app()
    #     else:
    #         super().keyPressEvent(event)

    def keyPressEvent(self, event: QKeyEvent):
        key = event.key()

        if Qt.Key.Key_1 <= key <= Qt.Key.Key_4:
            if key == Qt.Key.Key_1:
                self.radiobuttons[self.stack.currentIndex()+1][self.highlighted_radiogroup].button(0).setChecked(True)
                self.highlight_next_radiogroup(self.highlighted_radiogroup)
            elif key == Qt.Key.Key_2:
                self.radiobuttons[self.stack.currentIndex()+1][self.highlighted_radiogroup].button(1).setChecked(True)
                self.highlight_next_radiogroup(self.highlighted_radiogroup)
            elif key == Qt.Key.Key_3:
                self.radiobuttons[self.stack.currentIndex()+1][self.highlighted_radiogroup].button(2).setChecked(True)
                self.highlight_next_radiogroup(self.highlighted_radiogroup)
            elif key == Qt.Key.Key_4:
                self.radiobuttons[self.stack.currentIndex()+1][self.highlighted_radiogroup].button(3).setChecked(True)
                self.highlight_next_radiogroup(self.highlighted_radiogroup)

        elif key == Qt.Key.Key_Enter or key == Qt.Key.Key_Return:
            self.go_to_next_page_or_image()

    def save_settings(self):
        """
        Saves the current settings to the QSettings.
        """
        # Save current file and index
        self.settings.setValue('last_file', self.file_list[self.current_index])
        self.settings.setValue('last_index', self.current_index)
        self.settings.setValue("max_backups", self.max_backups)
        self.settings.setValue("backup_dir", self.backup_dir)
        self.settings.setValue("backup_interval", self.backup_interval)

    def save_to_json(self):
        """
        Saves the current outputs to a JSON file, by directing to the save or save as method as appropriate.
        """
        if not self.loaded:
            saved = self.save_as()
            if not saved:
                return False
            else:
                return True
        else:
            self.save_json(self.json_path)
            return True

    def save_as(self):
        """
        Save as dialog.
        """
        file_dialog = QFileDialog(self, 'Save to JSON', self.settings.value("default_directory", resource_dir))
        mime_type_filters = ["application/json", "application/octet-stream"]
        file_dialog.setMimeTypeFilters(mime_type_filters)
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        file_dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
        file_dialog.setDefaultSuffix("json")
        file_dialog.selectFile('untitled.json')

        if file_dialog.exec() == QFileDialog.DialogCode.Accepted:
            save_path = file_dialog.selectedFiles()[0]
            self.save_json(save_path)
            self.settings.setValue("default_directory", file_dialog.directory().path())
            self.save_settings()
            return True
        else:
            return False

    def create_output_dictionary(self):
        data = {
            'image_directory': self.dir_path,
            'reference_image_directory': self.reference_dir_path,
            'reference_delimiter': self.reference_delimiter,
            'files': []
        }
        for filename in self.file_list:
            viewed = self.viewed_values.get(filename, False)
            rotation = self.rotation.get(filename, 0)
            notes = self.notes.get(filename, "")

            cbox_out = {}
            for cbox in list(self.checkboxes.keys()):
                # Get the checkbox values for the file
                if viewed != "FAILED":
                    cbox_out[cbox] = self.checkbox_values[filename].get(cbox, False)
                else:
                    cbox_out[cbox] = "FAIL"

            radiobuttons_out = {}
            for name, value in self.radiobutton_values[filename].items():
                radiobuttons_out[name] = value

            data['files'].append({
                'filename': filename,
                'rated': viewed,
                'rotation': rotation,
                'notes': notes,
                'checkboxes': cbox_out,
                'radiobuttons': radiobuttons_out,
            })
        return data

    def save_json(self, selected_file: str):
        """
        Saves the current outputs to a JSON file.

        :param selected_file: Path to the file to save to
        :type selected_file: str
        """
        data = self.create_output_dictionary()
        with open(selected_file, 'w') as file:
            json.dump(data, file, indent=2)

    def load_from_json(self) -> bool:
        """
        Loads the previous saved outputs from a JSON file.

        :return: Whether the load was successful
        :rtype: bool
        """

        if self.settings.value("new_json", False):
            return False
        else:
            self.settings.setValue("default_directory", os.path.dirname(self.json_path))
            with open(self.json_path, 'r') as file:
                data = json.load(file)

            self.file_list = [entry['filename'] for entry in data['files']]
            self.dir_path = data['image_directory']
            self.reference_dir_path = data['reference_image_directory']
            self.reference_delimiter = data['reference_delimiter']

            for entry in data['files']:
                filename = entry['filename']
                self.viewed_values[filename] = entry['rated']
                self.rotation[filename] = entry['rotation']
                self.notes[filename] = entry['notes']

                if 'checkboxes' in entry:
                    for cbox, value in entry['checkboxes'].items():
                        if filename in self.checkbox_values:
                            self.checkbox_values[filename][cbox] = value
                        else:
                            self.checkbox_values[filename] = {cbox: value}

                if 'radiobuttons' in entry:
                    for name, value in entry['radiobuttons'].items():
                        if filename in self.radiobutton_values:
                            self.radiobutton_values[filename][name] = value
                        else:
                            self.radiobutton_values[filename] = {name: value}
            return True

    def export_to_csv(self):
        """
        Export to csv dialog.
        """
        file_dialog = QFileDialog(self, 'Save to CSV File', self.settings.value("default_directory", resource_dir),
                                  'CSV Files (*.csv);;All Files (*)')
        file_dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
        file_dialog.setDefaultSuffix("csv")
        file_dialog.selectFile('untitled.csv')
        mime_type_filters = ["text/csv", "application/octet-stream"]
        file_dialog.setMimeTypeFilters(mime_type_filters)
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFile)

        if file_dialog.exec() == QFileDialog.DialogCode.Accepted:
            save_path = file_dialog.selectedFiles()[0]
            self.save_csv(save_path)
            self.settings.setValue("default_directory", file_dialog.directory().path())
            self.save_settings()
            return True
        else:
            return False

    def save_csv(self, selected_file: str):
        """
        Saves the current outputs to a CSV file.

        :param selected_file: Path to the file to save to
        :type selected_file: str
        """
        data = self.create_output_dictionary()
        df = pd.DataFrame(data['files'])
        df = df.drop("checkboxes", axis=1)

        df, rb_cols = expand_dict_column(df, 'radiobuttons')

        for col in rb_cols:
            df = make_column_categorical(df, col)

        df.to_csv(selected_file, index=False)

    def on_checkbox_changed(self, state: int):
        """
        Updates the checkbox values when a checkbox is changed, updates the cursor mode, and sets the current finding
        in the image view based on the checkbox state.

        :param state: The state of the checkbox (Qt.CheckState.Unchecked or Qt.CheckState.Checked)
        :type state: int
        """
        filename = self.file_list[self.current_index]
        cbox = self.sender().text()
        self.checkbox_values[filename][cbox] = state
        # self.settings.setValue(filename, state)

    def assign_colors_to_findings(self):
        """
        Assigns a color to each finding/checkbox using the matplotlib rainbow color map.
        """
        num_colors = len(self.findings)
        cmap = plt.get_cmap("gist_rainbow")
        colors = [QColor(*(255 * np.array(cmap(i)[:3])).astype(int)) for i in np.linspace(0, 1, num_colors)]

        for idx, finding in enumerate(self.findings):
            color = colors[idx % len(colors)]
            self.colors[finding] = color

    def closeEvent(self, event: QCloseEvent):
        """
        Handles the close event.

        :param event: The close event
        :type event: QCloseEvent
        """
        # Ask the user if they want to save before closing

        if self.should_quit == "no_ref":
            event.accept()
            return

        close_msg_box = QMessageBox()

        icon_label = QLabel()
        icon_label.setPixmap(self.icons['question'].pixmap(64, 64))
        close_msg_box.setIconPixmap(icon_label.pixmap())

        self.settings.setValue('window_size', self.size())

        close_msg_box.setText("Save Changes?")
        close_msg_box.setInformativeText("Do you want to save changes before closing?")
        close_msg_box.setStandardButtons(QMessageBox.StandardButton.Yes |
                                         QMessageBox.StandardButton.No |
                                         QMessageBox.StandardButton.Cancel)
        close_msg_box.setDefaultButton(QMessageBox.StandardButton.Yes)

        clicked_button = close_msg_box.exec()
        if clicked_button == close_msg_box.StandardButton.Yes:
            saved = self.save_to_json()
            if not saved:
                event.ignore()
                return
        elif clicked_button == QMessageBox.StandardButton.Cancel:
            event.ignore()
            return

        event.accept()

    def init_menus(self):
        """
        Initializes the menus.
        """
        image_actions = [
            # self.invert_action,
            self.rotate_left_action, self.rotate_right_action, self.zoom_in_action, self.zoom_out_action,
            # self.reset_window_action, self.auto_window_action
        ]

        nav_actions = [self.prevAction, self.nextAction, self.nextUnratedAction, self.goToAction]

        # create the help menu
        help_menu = QMenu("Help", self)
        help_action = QAction("Help", self)
        help_menu.addAction(help_action)
        help_menu.addAction(self.logoAction)

        # create the file menu
        file_menu = QMenu("&File", self)
        menu_save_as_action = QAction(self.icons['save_as'], "&Save As...", self)
        menu_save_as_action.setShortcuts([
            QKeySequence(Qt.KeyboardModifier.ControlModifier | Qt.Key.Key_S),
            QKeySequence.StandardKey.Save
        ])
        file_menu.addAction(self.saveAction)
        help_menu.addAction(self.saveAction)
        file_menu.addAction(menu_save_as_action)
        help_menu.addAction(menu_save_as_action)
        file_menu.addSeparator()
        file_menu.addAction(self.exportAction)
        help_menu.addAction(self.exportAction)
        file_menu.addSeparator()
        file_menu.addAction(self.exitAction)
        help_menu.addAction(self.exitAction)

        # Create the image menu
        image_menu = QMenu("&Image", self)
        for action in image_actions:
            image_menu.addAction(action)
            help_menu.addAction(action)

        # Create the navigation menu
        navigation_menu = QMenu("&Navigation", self)
        for action in nav_actions:
            if action == self.goToAction:
                navigation_menu.addSeparator()
            navigation_menu.addAction(action)
            help_menu.addAction(action)

        # Style menu
        style_menu = QMenu("&Theme", self)

        self.themes = [
            'dark_blue.xml',
            'dark_amber.xml',
            'dark_cyan.xml',
            'dark_lightgreen.xml',
            'dark_medical.xml',
            'dark_pink.xml',
            'dark_purple.xml',
            'dark_red.xml',
            'dark_teal.xml',
            'dark_yellow.xml',
            'light_blue.xml',
            'light_amber.xml',
            'light_cyan.xml',
            'light_lightgreen.xml',
            'light_orange.xml',
            'light_pink.xml',
            'light_purple.xml',
            'light_red.xml',
            'light_teal.xml',
            'light_yellow.xml',
        ]

        self.reset_theme_action = QAction("Default Theme", self)
        self.reset_theme_action.setShortcut(QKeySequence(Qt.KeyboardModifier.ControlModifier | Qt.Key.Key_T))

        self.connection_manager.connect(self.reset_theme_action.triggered,
                                        partial(self.change_theme, "dark_blue.xml"))
        style_menu.addAction(self.reset_theme_action)
        help_menu.addAction(self.reset_theme_action)
        style_menu.addSeparator()

        self.theme_actions = {}
        added_separator = False
        for theme in self.themes:
            if "light_" in theme and not added_separator:
                style_menu.addSeparator()
                added_separator = True
            self.theme_actions[theme] = QAction(theme.replace("_", " ").replace(".xml", "").title(), self)
            self.connection_manager.connect(self.theme_actions[theme].triggered,
                                            partial(self.change_theme, theme))
            style_menu.addAction(self.theme_actions[theme])

        # add the menus to the menu bar
        menu_bar = QMenuBar(self)
        menu_bar.addMenu(file_menu)
        menu_bar.addMenu(image_menu)
        menu_bar.addMenu(navigation_menu)
        menu_bar.addMenu(style_menu)
        menu_bar.addMenu(help_menu)
        self.setMenuBar(menu_bar)

        self.connection_manager.connect(menu_save_as_action.triggered, self.save_as)

    def change_theme(self, theme):
        """
        Changes the theme of the application.

        :param theme: The theme to change to
        :type theme: str
        """

        apply_stylesheet(self.app, theme=theme)
        self.settings.setValue("theme", theme)

        self.image_view.change_label_color(theme)
        self.reference_view.change_label_color(theme)
        self.set_scroll_bar_colors()
        self.set_icons()
        self.set_action_icons()
        try:
            self.line_color = get_theme(theme)['secondaryLightColor']
        except KeyError:
            self.line_color = get_theme(theme)['secondaryColor']
        self.nav_spacer.setStyleSheet(f"border-bottom: 1px solid {self.line_color};")
        self.nav_spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_icons(self):
        """
        Sets the icons for the application and their colors.
        """
        try:
            icon_color = get_theme(self.settings.value("theme", 'dark_blue.xml'))['primaryLightColor']
        except KeyError:
            icon_color = get_theme(self.settings.value("theme", 'dark_blue.xml'))['primaryColor']

        try:
            nav_color = get_theme(self.settings.value("theme", 'dark_blue.xml'))['secondaryColor']
        except KeyError:
            nav_color = get_theme(self.settings.value("theme", 'dark_blue.xml'))['secondaryDarkColor']

        self.icons = {
            'save': qta.icon("mdi.content-save-all", color=icon_color),
            'save_as': qta.icon("mdi.content-save-edit", color=icon_color),
            'next': qta.icon("mdi.arrow-right-circle", color=nav_color),
            'prev': qta.icon("mdi.arrow-left-circle", color=nav_color),
            'goto': qta.icon("mdi.file-find", color=icon_color),
            'ww': qta.icon("mdi.contrast-box", color=icon_color),
            'wc': qta.icon("mdi.brightness-5", color=icon_color),
            'inv': qta.icon("mdi.invert-colors", color=icon_color),
            'rot_right': qta.icon("mdi.rotate-right", color=icon_color),
            'rot_left': qta.icon("mdi.rotate-left", color=icon_color),
            'zoom_in': qta.icon("mdi.magnify-plus", color=icon_color),
            'zoom_out': qta.icon("mdi.magnify-minus", color=icon_color),
            'exit': qta.icon("mdi.exit-to-app", color=icon_color),
            'reset_win': qta.icon("mdi.credit-card-refresh", color=icon_color),
            'auto_win': qta.icon("mdi.image-auto-adjust", color=icon_color),
            'viewed': qta.icon("mdi.checkbox-marked-circle", color="green", scale=2),
            'not_viewed': qta.icon("mdi.close-circle", color="red", scale=2),
            'question': qta.icon("mdi.help-circle", color="white", scale=2),
            'export': qta.icon("mdi.file-export", color=icon_color),
            'next_unrated': qta.icon("mdi.skip-next-circle", color=icon_color),
        }

    def set_action_icons(self):
        """
        Sets the icons for the actions in the application.
        """
        self.exitAction.setIcon(self.icons['exit'])
        self.goToAction.setIcon(self.icons['goto'])
        self.saveAction.setIcon(self.icons['save'])
        self.exitAction.setIcon(self.icons['exit'])
        self.nextAction.setIcon(self.icons['next'])
        self.nextUnratedAction.setIcon(self.icons['next_unrated'])
        self.prevAction.setIcon(self.icons['prev'])
        # self.reset_window_action.setIcon(self.icons['reset_win'])
        # self.auto_window_action.setIcon(self.icons['auto_win'])
        self.rotate_left_action.setIcon(self.icons['rot_left'])
        self.rotate_right_action.setIcon(self.icons['rot_right'])
        self.zoom_in_action.setIcon(self.icons['zoom_in'])
        self.zoom_out_action.setIcon(self.icons['zoom_out'])
        self.exportAction.setIcon(self.icons['export'])
        # self.invert_action.setIcon(self.icons['inv'])
        # self.window_width_action.setIcon(self.icons['ww'])
        # self.window_center_action.setIcon(self.icons['wc'])

    def set_scroll_bar_colors(self):
        """
        Sets the colors of the scroll bars in the image views.
        """
        # Set scrollbar style (too dark with qt material dark theme...)
        self.image_view.setStyleSheet(f"""
            QScrollBar::handle:vertical {{
                background: {get_theme(self.settings.value("theme", 'dark_blue.xml'))['primaryColor']};
                }}
            QScrollBar::handle:horizontal {{
                background: {get_theme(self.settings.value("theme", 'dark_blue.xml'))['primaryColor']};
                }}
        """)
        self.reference_view.setStyleSheet(f"""
                    QScrollBar::handle:vertical {{
                        background: {get_theme(self.settings.value("theme", 'dark_blue.xml'))['primaryColor']};
                        }}
                    QScrollBar::handle:horizontal {{
                        background: {get_theme(self.settings.value("theme", 'dark_blue.xml'))['primaryColor']};
                        }}
                """)

    def set_progress_bar_colors(self):
        """
        Sets the color of the progress bar.
        """
        progress_color = QColor(get_theme(self.settings.value("theme", 'dark_blue.xml'))['primaryColor'])
        progress_color.setAlpha(100)
        self.progress_bar.setStyleSheet(
            f"""QProgressBar::chunk {{background: {progress_color.name(QColor.NameFormat.HexArgb)};}}""")

    def show_about(self):
        """
        Shows the About box from the menu.
        """
        self.about_box.exec()

    def quit_app(self):
        """
        Quits the application, disconnecting all signals.
        """
        if hasattr(self, 'timer'):
            self.timer.stop()
        if hasattr(self, 'connection_manager'):
            self.connection_manager.disconnect_all()
        if hasattr(self, 'about_box'):
            self.about_box.connection_manager.disconnect_all()
        if hasattr(self, 'image_view'):
            self.image_view.connection_manager.disconnect_all()
        if hasattr(self, 'reference_view'):
            self.reference_view.connection_manager.disconnect_all()

        self.close()
        QApplication.quit()



