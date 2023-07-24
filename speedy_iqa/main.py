"""
main.py

Main module for Speedy IQA, a dual image viewer for desktop which allows image labeling for an image compared to a
reference image.

This module initializes the application, sets the theme and icon styles, and displays the main window or
configuration wizard based on user input.

Functions:
    main(theme: str, material_theme: str, icon_theme: str) -> None: Initializes and runs the application.
    load_dicom_dialog() -> str: Prompts the user to select a directory containing DICOM files.

Usage:
    Run this module as a script to start the Speedy IQA application:
        - From the command line (if installed by pip):
            `speedy_iqa`
        - From python:
            `python -m main`
"""


import sys
import os
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtWidgets import *
from qt_material import apply_stylesheet

from speedy_iqa.main_app import MainApp
from speedy_iqa.wizard import ConfigurationWizard
from speedy_iqa.windows import LoadMessageBox, SetupWindow

if hasattr(sys, '_MEIPASS'):
    # This is a py2app executable
    resource_dir = sys._MEIPASS
elif 'main.py' in os.listdir(os.path.dirname(os.path.abspath("__main__"))):
    # This is a regular Python script
    resource_dir = os.path.dirname(os.path.abspath("__main__"))
else:
    resource_dir = os.path.join(os.path.dirname(os.path.abspath("__main__")), 'speedy_iqa')


def main(theme='qt_material', material_theme='dark_blue.xml', icon_theme='qtawesome'):
    """
    Main function. Creates the main window and runs the application.

    If the user selects to `Conf. Wizard` in the initial dialog box (load_msg_box), the ConfigurationWizard is shown
    instead, allowing the user to configure the application settings. The last selected config .yml file is saved and
    shown as the default in the QComboBox of the initial dialog box.

    The user must select a folder of DICOM files to run the application. If the selected folder does not contain any
    DICOM files, an error message box is shown, and the user is prompted to select a new folder.

    :param theme: str, the application theme. Default is 'qt_material', which uses the qt_material library. Other options
        include 'Fusion', 'Windows', 'WindowsVista', 'WindowsXP', 'Macintosh', 'Plastique', 'Cleanlooks', 'CDE', 'GTK+'
        and 'Motif' from the QStyleFactory class.
    :param material_theme: str, the qt_material theme if theme set to qt_material. Default is 'dark_blue.xml'.
    :param icon_theme: str, the icon theme. Default is 'qtawesome', which uses the qtawesome library. Other options
        include 'breeze', 'breeze-dark', 'hicolor', 'oxygen', 'oxygen-dark', 'tango', 'tango-dark', and 'faenza' from the
        QIcon class.
    """

    def cleanup():
        """
        Cleanup function. Closes and deletes all windows and widgets.
        """
        # Cleanup load intro window
        try:
            # This might raise an exception if setup_window was never created,
            # so we catch the exception and ignore it.
            load_msg_box.close()
            load_msg_box.deleteLater()
        except NameError:
            pass

        # Cleanup main window
        try:
            # This might raise an exception if setup_window was never created,
            # so we catch the exception and ignore it.
            window.close()
            window.deleteLater()
        except NameError:
            pass

        # Cleanup setup window
        try:
            # This might raise an exception if setup_window was never created,
            # so we catch the exception and ignore it.
            setup_window.close()
            setup_window.deleteLater()
        except NameError:
            pass

        # Cleanup wizard
        try:
            # This might raise an exception if wizard was never created,
            # so we catch the exception and ignore it.
            wizard.close()
            wizard.deleteLater()
        except NameError:
            pass
        return

    # Create the application
    app = QApplication(sys.argv)

    # Set the application theme
    if theme == 'qt_material':
        apply_stylesheet(app, theme=material_theme)
    else:
        app.setStyle(QStyleFactory.create(theme))

    font = app.font()
    font.setPointSize(18)
    app.setFont(font)

    # Set the application icon theme
    QIcon.setThemeName(icon_theme)

    # Create the initial dialog box
    load_msg_box = LoadMessageBox()
    result = load_msg_box.exec()
    config_file = load_msg_box.config_combo.currentText()
    print("main", config_file)
    load_msg_box.save_last_config(config_file)

    settings = QSettings('SpeedyIQA', 'ImageViewer')

    # User selects to `Ok` -> load the load dialog box
    if result == load_msg_box.DialogCode.Accepted:
        # If the user selects to `Ok`, load the dialog to select the dicom directory
        setup_window = SetupWindow(settings)
        result = setup_window.exec()

        if result == setup_window.DialogCode.Accepted:
            # Create the main window and pass the dicom directory
            window = MainApp(settings)
            window.show()
        else:
            cleanup()
            sys.exit()

    # User selects to `Cancel` -> exit the application
    elif result == load_msg_box.DialogCode.Rejected:
        cleanup()
        sys.exit()

    # User selects to `Conf. Wizard` -> show the ConfigurationWizard
    else:
        if hasattr(sys, '_MEIPASS'):
            # This is a py2app executable
            resource_dir = sys._MEIPASS
        elif 'main.py' in os.listdir(os.path.dirname(os.path.abspath("__main__"))):
            # This is a regular Python script
            resource_dir = os.path.dirname(os.path.abspath("__main__"))
        else:
            resource_dir = os.path.join(os.path.dirname(os.path.abspath("__main__")), 'speedy_iqa')
        wizard = ConfigurationWizard(os.path.join(resource_dir, config_file))
        wizard.show()

    exit_code = app.exec()
    cleanup()
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
