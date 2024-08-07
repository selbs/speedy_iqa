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


def configure_qt_environment():
    """
    Configures the environment for PyQt6 to ensure it uses the Qt version from the virtual environment.

    :return: None
    """
    # Assuming this script is run within a virtual environment, locate the site-packages directory.
    venv_path = sys.prefix
    bin_path = os.path.join(venv_path, 'bin')
    qt_path = None
    if os.path.isdir(os.path.join(venv_path, 'lib', 'python' + sys.version[:3], 'site-packages', 'PyQt6', 'Qt6')):
        qt_path = os.path.join(venv_path, 'lib', 'python' + sys.version[:3], 'site-packages', 'PyQt6', 'Qt6')
    elif os.path.isdir(os.path.join(venv_path, 'lib', 'site-packages', 'PyQt6', 'Qt6')):
        qt_path = os.path.join(venv_path, 'lib', 'site-packages', 'PyQt6', 'Qt6')
    elif os.path.isdir(os.path.join(venv_path, 'lib', 'PyQt6', 'Qt')):
        qt_path = os.path.join(venv_path, 'lib', 'PyQt6', 'Qt')

    qt_plugin_path = os.path.join(qt_path, 'plugins') if qt_path is not None else None

    # Set the QT_PLUGIN_PATH environment variable to the PyQt6 plugins directory.
    os.environ['PATH'] = bin_path
    os.environ['QTDIR'] = qt_path
    os.environ['QT_PLUGIN_PATH'] = qt_plugin_path


configure_qt_environment()

from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtWidgets import *
from qt_material import apply_stylesheet

from speedy_iqa.main_app import MainApp
# from speedy_iqa.wizard import ConfigurationWizard
from speedy_iqa.unified_wizard import ConfigurationWizard
from speedy_iqa.windows import LoadMessageBox, SetupWindow

if hasattr(sys, '_MEIPASS'):
    # This is a py2app executable
    resource_dir = sys._MEIPASS
elif 'main.py' in os.listdir(os.path.dirname(os.path.realpath(__file__))):
    resource_dir = os.path.dirname(os.path.realpath(__file__))
elif 'main.py' in os.listdir(os.path.dirname(os.path.abspath("__main__"))):
    # This is a regular Python script
    resource_dir = os.path.dirname(os.path.abspath("__main__"))
elif 'main.py' in os.path.join(os.path.dirname(os.path.abspath("__main__")), 'speedy_iqa'):
    resource_dir = os.path.join(os.path.dirname(os.path.abspath("__main__")), 'speedy_iqa')
else:
    raise(FileNotFoundError(f"Resource directory not found from {os.path.dirname(os.path.abspath('__main__'))}"))

resource_dir = os.path.normpath(resource_dir)


def qt_message_handler(mode, context, message):
    if "no target window" in message:
        return  # Filter out the specific warning
    else:
        # Default behavior for other messages
        sys.stderr.write(f"{message}\n")


qInstallMessageHandler(qt_message_handler)


def main(theme='qt_material', material_theme=None, icon_theme='qtawesome'):
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
            load_msg_box.close()
            load_msg_box.deleteLater()
        except NameError:
            pass

        # Cleanup main window
        try:
            window.close()
            window.deleteLater()
        except NameError:
            pass

        # Cleanup setup window
        try:
            setup_window.close()
            setup_window.deleteLater()
        except NameError:
            pass

        # Cleanup wizard
        try:
            wizard.close()
            wizard.deleteLater()
        except NameError:
            pass
        return

    # Create the application
    app = QApplication(sys.argv)

    settings = QSettings('SpeedyIQA', 'ImageViewer')

    # Set the application theme
    if theme == 'qt_material':
        if material_theme is None:
            material_theme = settings.value('theme', 'dark_blue.xml')
        else:
            settings.setValue('theme', material_theme)
        apply_stylesheet(app, theme=material_theme, extra={})
    else:
        app.setStyle(QStyleFactory.create(theme))

    # Set the application icon theme
    QIcon.setThemeName(icon_theme)

    while True:

        # Create the initial dialog box
        load_msg_box = LoadMessageBox()
        result = load_msg_box.exec()
        config_filename = load_msg_box.config_combo.currentText()
        # print("main", config_file)
        load_msg_box.save_last_config(config_filename)

        # User selects to `Ok` -> load the load dialog box
        if result == load_msg_box.DialogCode.Accepted:
            # If the user selects to `Ok`, load the dialog to select the dicom directory
            setup_window = SetupWindow(settings)
            result = setup_window.exec()

            if result == setup_window.DialogCode.Accepted:
                # Create the main window and pass the dicom directory
                window = MainApp(app, settings)
                if not window.should_quit:
                    window.show()
                    break
                else:
                    cleanup()
                    sys.exit()
            else:
                continue
                # cleanup()
                # sys.exit()

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
            resource_dir = os.path.normpath(resource_dir)
            wizard = ConfigurationWizard(os.path.join(resource_dir, config_filename))
            result = wizard.exec()
            if result == 1:
                continue
                # setup_window = SetupWindow(settings)
                # result = setup_window.exec()
                #
                # if result == setup_window.DialogCode.Accepted:
                #     # Create the main window and pass the dicom directory
                #     window = MainApp(app, settings)
                #     if not window.should_quit:
                #         window.show()
                #     else:
                #         cleanup()
                #         sys.exit()
                # else:
                #     cleanup()
                #     sys.exit()
            else:
                cleanup()
                sys.exit()

    exit_code = app.exec()
    cleanup()
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
