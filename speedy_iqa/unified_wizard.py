"""
unified_wizard.py

This is an updated version of the ConfigurationWizard class from speedy_iqa/config_wizard.py. It allows users to
customize the configuration of the Speedy IQA application without the need to restart the application.
"""

from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtWidgets import *
import yaml
import os
from qt_material import apply_stylesheet, get_theme
import sys

from speedy_iqa.utils import open_yml_file, setup_logging, ConnectionManager

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
    raise (FileNotFoundError(f"Resource directory not found from {os.path.dirname(os.path.abspath('__main__'))}"))

resource_dir = os.path.normpath(os.path.abspath(resource_dir))


class AdvancedSettingsDialog(QDialog):
    def __init__(self, unified_page_instance, parent=None):
        super().__init__(parent)
        self.unified_page_instance = unified_page_instance
        self.wiz = unified_page_instance.wiz
        self.settings = unified_page_instance.settings
        self.connection_manager = unified_page_instance.connection_manager
        self.log_dir = os.path.normpath(self.wiz.log_dir)
        self.backup_dir = os.path.normpath(self.wiz.backup_dir)
        self.backup_interval = self.wiz.backup_interval
        self.max_backups = self.wiz.max_backups
        self.setWindowTitle("Advanced Settings")

        try:
            self.entry_colour = get_theme(self.settings.value('theme', 'dark_blue.xml'))['secondaryTextColor']
        except KeyError:
            self.entry_colour = get_theme(self.settings.value('theme', 'dark_blue.xml'))['secondaryLightColor']
        try:
            self.disabled_colour = get_theme(self.settings.value('theme', 'dark_blue.xml'))['secondaryLightColor']
        except KeyError:
            self.disabled_colour = get_theme(self.settings.value('theme', 'dark_blue.xml'))['primaryLightColor']
        try:
            self.border_color = get_theme(self.settings.value("theme", 'dark_blue.xml'))['secondaryLightColor']
        except KeyError:
            self.border_color = get_theme(self.settings.value("theme", 'dark_blue.xml'))['secondaryColor']

        self.setStyleSheet(f"""
            QLineEdit {{
                color: {self.entry_colour};
            }}
            QSpinBox {{
                color: {self.entry_colour};
            }}
            QComboBox {{
                color: {self.entry_colour};
            }}
        """)

        self.layout = QVBoxLayout()

        config_frame = QFrame()
        config_frame.setObjectName("ConfigFrame")
        config_frame.setStyleSheet(f"#ConfigFrame {{ border: 2px solid {self.border_color}; border-radius: 5px; }}")
        self.config_layout = QVBoxLayout()
        self.config_file_title = QLabel("Configuration File Settings:")
        self.config_file_title.setStyleSheet("font-weight: bold;")
        self.config_layout.addWidget(self.config_file_title)

        # Create QComboBox for the list of available .yml files
        self.config_files_combobox = QComboBox()
        for file in os.listdir(resource_dir):
            if file.endswith('.yml'):
                self.config_files_combobox.addItem(file)

        existing_combo_layout = QHBoxLayout()
        existing_combo_title = QLabel("Existing Configuration Files:")
        existing_combo_title.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        existing_combo_layout.addWidget(existing_combo_title)
        existing_combo_layout.addWidget(self.config_files_combobox)
        self.config_layout.addLayout(existing_combo_layout)

        # Create QLineEdit for the filename
        new_filename_layout = QHBoxLayout()
        self.filename_edit = QLineEdit()
        self.filename_edit.setPlaceholderText("config.yml")
        self.connection_manager.connect(self.filename_edit.textChanged,
                                        self.update_config_combobox_state)
        new_filename_layout.addWidget(QLabel("New Filename (Optional):"))
        new_filename_layout.addWidget(self.filename_edit)
        self.config_layout.addLayout(new_filename_layout)

        # Display the save path
        save_path_layout = QHBoxLayout()
        save_path_label = QLabel("Save directory:")
        save_path_layout.addWidget(save_path_label)
        save_dir_label = QLabel(resource_dir)
        save_path_label.setStyleSheet("font-style: italic;")
        save_dir_label.setStyleSheet("font-style: italic;")
        save_path_layout.addWidget(save_dir_label)
        save_path_layout.addStretch()
        self.config_layout.addLayout(save_path_layout)

        config_frame.setLayout(self.config_layout)
        self.layout.addStretch()
        self.layout.addWidget(config_frame)
        self.layout.addStretch()

        log_frame = QFrame()
        log_frame.setObjectName("LogFrame")
        log_frame.setStyleSheet(f"#LogFrame {{ border: 2px solid {self.border_color}; border-radius: 5px; }}")
        self.log_layout = QVBoxLayout()

        # Create a widget for the log directory
        self.log_dir_title = QLabel("Log Settings:")
        self.log_dir_title.setStyleSheet("font-weight: bold;")
        self.log_layout.addWidget(self.log_dir_title)

        self.log_dir_layout = QHBoxLayout()
        log_dir_label = QLabel("Log directory:")
        self.log_dir_edit = QLineEdit()
        self.log_dir_edit.setText(self.settings.value("log_dir", os.path.normpath(os.path.expanduser(self.log_dir))))
        self.log_dir_layout.addWidget(log_dir_label)
        self.log_dir_layout.addWidget(self.log_dir_edit)
        self.log_layout.addLayout(self.log_dir_layout)

        log_frame.setLayout(self.log_layout)
        self.layout.addWidget(log_frame)
        self.layout.addStretch()

        backup_frame = QFrame()
        backup_frame.setObjectName("BackupFrame")
        backup_frame.setStyleSheet(f"#BackupFrame {{ border: 2px solid {self.border_color}; border-radius: 5px; }}")
        self.backup_layout = QVBoxLayout()

        # Create a widget for the log directory
        self.backup_title = QLabel("Backup Settings:")
        self.backup_title.setStyleSheet("font-weight: bold;")
        self.backup_layout.addWidget(self.backup_title)

        backup_dir_layout = QHBoxLayout()
        backup_dir_label = QLabel("Backup directory:")
        self.backup_dir_edit = QLineEdit()
        self.backup_dir_edit.setText(self.settings.value("backup_dir", os.path.normpath(
            os.path.expanduser(self.backup_dir)
        )))
        backup_dir_layout.addWidget(backup_dir_label)
        backup_dir_layout.addWidget(self.backup_dir_edit)
        self.backup_layout.addLayout(backup_dir_layout)

        # Create a widget for the maximum number of backups
        no_backups_layout = QHBoxLayout()
        self.backup_spinbox = QSpinBox()
        self.backup_spinbox.setRange(1, 100)
        self.backup_spinbox.setValue(self.max_backups)

        no_backups_layout.addWidget(QLabel("Maximum number of backups:"))
        no_backups_layout.addWidget(self.backup_spinbox)
        no_backups_layout.addStretch()
        self.backup_layout.addLayout(no_backups_layout)

        backup_int_layout = QHBoxLayout()
        self.backup_int_spinbox = QSpinBox()
        self.backup_int_spinbox.setRange(1, 30)
        self.backup_int_spinbox.setValue(self.backup_interval)

        backup_int_layout.addWidget(QLabel("Backup interval (mins):"))
        backup_int_layout.addWidget(self.backup_int_spinbox)
        backup_int_layout.addStretch()
        self.backup_layout.addLayout(backup_int_layout)

        backup_frame.setLayout(self.backup_layout)
        self.layout.addWidget(backup_frame)
        self.layout.addStretch()

        # Add a "Back" button
        back_button = QPushButton("Back")
        self.connection_manager.connect(back_button.clicked, self.close)
        self.layout.addWidget(back_button)

        self.setLayout(self.layout)
        self.setMinimumSize(400, 520)

        QTimer.singleShot(0, self.update_config_combobox_state)

    def update_config_combobox_state(self):
        """
        Updates the QComboBox on the save page with the list of existing .yml files.
        """
        if self.filename_edit.text():
            self.config_files_combobox.setEnabled(False)
        else:
            self.config_files_combobox.setEnabled(True)
        self.update_combobox_stylesheet()

    def update_combobox_stylesheet(self):
        """
        Updates the stylesheet of the QComboBox on the save page to indicate whether it is
        enabled or disabled.
        """
        if self.config_files_combobox.isEnabled():
            self.config_files_combobox.setStyleSheet(f"QComboBox {{ color: {self.entry_colour}; }}")
        else:
            self.config_files_combobox.setStyleSheet(f"QComboBox {{ color: {self.disabled_colour}; }}")

    def close(self):
        # self.settings.setValue("log_dir", self.log_dir_edit.text())
        # self.settings.setValue("backup_dir", self.backup_dir_edit.text())
        # self.settings.setValue("max_backups", self.backup_spinbox.value())
        # self.settings.setValue("backup_interval", self.backup_int_spinbox.value())

        if self.filename_edit.text():
            self.wiz.config_filename = self.filename_edit.text()
        else:
            self.wiz.config_filename = self.config_files_combobox.currentText()
        self.wiz.log_dir = os.path.normpath(self.log_dir_edit.text())
        self.wiz.backup_dir = os.path.normpath(self.backup_dir_edit.text())
        self.wiz.backup_interval = self.backup_int_spinbox.value()
        self.wiz.max_backups = self.backup_spinbox.value()
        super().close()


class UnifiedOptionsPage(QWizardPage):
    def __init__(self, wiz, parent=None):
        """
        Initializes the page.

        :param parent: The parent widget.
        :type parent: QWidget
        """
        super().__init__(parent)

        self.connection_manager = wiz.connection_manager

        self.wiz = wiz
        self.task = wiz.task
        self.radio_buttons = wiz.radio_buttons
        self.settings = wiz.settings

        self.setTitle(f"Set Up")
        self.setSubTitle(f"\nCustomise the task and subcategories for labelling.")

        self.layout = QVBoxLayout(self)

        self.task_layout = QHBoxLayout()
        task_label = QLabel("Task images are being assessed for:")
        task_label.setStyleSheet("font-weight: bold;")
        self.task_edit = QLineEdit()
        self.task_edit.setText(self.task)
        self.task_layout.addWidget(task_label)
        self.task_layout.addWidget(self.task_edit)
        self.layout.addLayout(self.task_layout)
        examples_label = QLabel(
            "Examples include: 'General use', 'Diagnosis', 'Tumour Classification', 'Facial Recognition', "
            "Object Detection, etc."
        )
        examples_label.setWordWrap(True)
        examples_label.setStyleSheet("font-style: italic;")
        self.layout.addWidget(examples_label)

        spacer = QSpacerItem(0, 40, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.layout.addItem(spacer)

        radio_label = QLabel("Quality Subcategories:")
        radio_label.setStyleSheet("font-weight: bold;")
        self.layout.addWidget(radio_label)

        self.scrollArea = QScrollArea(self)
        self.scrollWidget = QWidget()
        self.scrollLayout = QVBoxLayout()
        self.scrollWidget.setLayout(self.scrollLayout)
        self.scrollArea.setWidget(self.scrollWidget)
        self.scrollArea.setWidgetResizable(True)
        self.layout.addWidget(self.scrollArea)

        self.radio_widget = QWidget(self)
        self.radio_layout = QVBoxLayout(self.radio_widget)
        self.radio_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scrollArea.setWidget(self.radio_widget)

        self.radio_layouts = {}
        self.radio_box_layouts = {}
        for i in range(wiz.nradio_pages):
            # Remove to allow for page 1 to be edited
            if i != 0:
                self.radio_layouts[i] = QVBoxLayout()
                frame = QFrame()
                frame.setObjectName("RadioPageFrame")
                try:
                    border_color = get_theme(self.settings.value("theme", 'dark_blue.xml'))['secondaryLightColor']
                except KeyError:
                    border_color = get_theme(self.settings.value("theme", 'dark_blue.xml'))['secondaryColor']
                frame.setStyleSheet(f"#RadioPageFrame {{ border: 2px solid {border_color}; border-radius: 5px; }}")

                page_title_layout = QVBoxLayout()
                page_title = QLabel(f"Page {i + 1}")
                page_title.setStyleSheet("font-weight: bold;")
                page_title.setAlignment(Qt.AlignmentFlag.AlignLeft)

                if i == 0:
                    page_info = QLabel("Enter the subcategories to appear on the first page of buttons. "
                                       "You may wish these categories to be assessed independently of "
                                       "others, e.g. 'Overall Quality'.")
                else:
                    page_info = QLabel(f"Enter the quality subcategories which will appear on page {i + 1}, "
                                       f"e.g. 'Contrast', 'Noise', 'Artefacts'.")

                page_info.setStyleSheet("font-style: italic;")
                page_info.setWordWrap(True)
                page_info.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
                # Uncomment if you want the page title to be above the page info
                # page_title_layout.addWidget(page_title)
                page_info.setAlignment(Qt.AlignmentFlag.AlignTop)
                page_title_layout.addWidget(page_info)

                self.add_radio_button = QPushButton("+")
                self.add_radio_button.setProperty('class', 'success')
                self.connection_manager.connect(self.add_radio_button.clicked, lambda: self.add_radio_group(k=i))

                row_header_layout = QHBoxLayout()
                row_header_layout.addLayout(page_title_layout)
                row_header_layout.addWidget(self.add_radio_button, alignment=Qt.AlignmentFlag.AlignTop)
                self.radio_layouts[i].addLayout(row_header_layout)

                self.radio_box_layouts[i] = QVBoxLayout()
                for group in self.radio_buttons[i]:
                    self.add_radio_group(group['title'], i)

                self.radio_layouts[i].addLayout(self.radio_box_layouts[i])
                frame.setLayout(self.radio_layouts[i])

                self.radio_layout.addWidget(frame)

    def initializePage(self):

        self.wizard().setButtonLayout([
            QWizard.WizardButton.HelpButton,
            QWizard.WizardButton.Stretch,
            QWizard.WizardButton.FinishButton,
            QWizard.WizardButton.CancelButton
        ])

        self.wizard().button(QWizard.WizardButton.BackButton).hide()

        advanced_button = QPushButton("Advanced Settings")
        self.connection_manager.connect(advanced_button.clicked, self.open_advanced_settings)

        self.wizard().setButton(QWizard.WizardButton.HelpButton, advanced_button)

    def open_advanced_settings(self):
        advanced_settings_dialog = AdvancedSettingsDialog(self)
        advanced_settings_dialog.exec()

    def add_radio_group(self, label_text="", k=0):
        """
        Adds a label to the list of labels.
        """
        line_edit = QLineEdit(label_text)
        remove_button = QPushButton("-")
        remove_button.setProperty('class', 'danger')
        # remove_button.setFixedSize(100, 40)

        self.connection_manager.connect(
            remove_button.clicked, lambda: self.remove_radio_group(line_edit, remove_button)
        )

        # Create a horizontal layout for the line edit and the remove button
        hbox = QHBoxLayout()
        hbox.addWidget(line_edit)
        hbox.addWidget(remove_button)
        self.radio_box_layouts[k].addLayout(hbox)

    @staticmethod
    def remove_radio_group(line_edit, button):
        """
        Removes a label from the list of labels.
        """
        # Get the layout that contains the line edit and the button
        hbox = line_edit.parent().layout()

        # Remove the line edit and the button from the layout
        hbox.removeWidget(line_edit)
        hbox.removeWidget(button)

        # Delete the line edit and the button
        line_edit.deleteLater()
        button.deleteLater()


class ConfigurationWizard(QWizard):
    """
    A QWizard implementation for customizing the configuration of the Speedy IQA application.
    Allows users to customize checkbox labels, maximum number of backup files, and directories
    for backup and log files. Can be run from the initial dialog box, from the command line,
    or from Python.

    Methods:
        - create_label_page: Creates the first page of the wizard, allowing users to customize
                                the labels of the checkboxes.
        - create_backup_page: Creates the second page of the wizard, allowing users to customize
                                the maximum number of backup files and the directories for backup
                                and log files.
        - add_label: Adds a new label to the label page for a new checkbox/finding.
        - create_save_page: Creates the third page of the wizard, allowing users to save the
                                configuration to a .yml file.
        - update_combobox_stylesheet: Updates the stylesheet of the QComboBoxes in the label page
                                        to make the options more visible.
        - update_combobox_state: Updates the QComboBox on the save page with the list of existing .yml files.
        - accept: Saves the configuration to a .yml file and closes the wizard.
    """

    def __init__(self, config_file: str):
        """
        Initializes the wizard.

        :param config_file: The configuration file name.
        :type config_file: str
        """
        super().__init__()
        self.settings = QSettings('SpeedyIQA', 'ImageViewer')
        self.connection_manager = ConnectionManager()
        self.nradio_pages = 2
        self.radio_pages = {}
        self.radio_buttons = {}

        self.setStyleSheet(f"""
            QLineEdit {{
                color: {get_theme(self.settings.value('theme', 'dark_blue.xml'))['secondaryTextColor']};
            }}
            QSpinBox {{
                color: {get_theme(self.settings.value('theme', 'dark_blue.xml'))['secondaryTextColor']};
            }}
            QComboBox {{
                color: {get_theme(self.settings.value('theme', 'dark_blue.xml'))['secondaryTextColor']};
            }}
        """)

        # Set the wizard style to have the title and icon at the top
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)

        self.config_filename = os.path.basename(config_file)
        self.config_data = None

        # Enable IndependentPages option
        self.setOption(QWizard.WizardOption.IndependentPages, True)

        # Set the logo pixmap
        icon_path = os.path.normpath(os.path.join(resource_dir, 'assets/logo.png'))
        pixmap = QPixmap(icon_path)
        self.setPixmap(QWizard.WizardPixmap.LogoPixmap, pixmap.scaled(150, 150, Qt.AspectRatioMode.KeepAspectRatio))

        # Load the config file
        self.config_data = open_yml_file(os.path.normpath(os.path.join(resource_dir, self.config_filename)))

        for i in range(self.nradio_pages):
            self.radio_buttons[i] = self.config_data.get(f'radiobuttons_page{i + 1}', [])
        if self.nradio_pages >= 2:
            if not self.radio_buttons[0]:
                self.radio_buttons[0] = [{'title': "Overall Quality", 'labels': [1, 2, 3, 4]}, ]
            if not self.radio_buttons[1]:
                self.radio_buttons[1] = [
                    {'title': "Contrast", 'labels': [1, 2, 3, 4]},
                    {'title': "Noise", 'labels': [1, 2, 3, 4]},
                    {'title': "Artefacts", 'labels': [1, 2, 3, 4]},
                ]
        self.max_backups = self.config_data.get('max_backups', 10)
        self.backup_interval = self.config_data.get('backup_interval', 5)
        self.backup_dir = os.path.normpath(
            self.config_data.get('backup_dir', os.path.normpath(os.path.expanduser('~/speedy_iqa/backups')))
        )
        self.log_dir = os.path.normpath(
            self.config_data.get('log_dir', os.path.normpath(os.path.expanduser('~/speedy_iqa/logs')))
        )
        self.task = self.settings.value("task", self.config_data.get('task', 'General use'))

        self.main_page = self.create_unified_page()
        self.addPage(self.main_page)

        # Set the window title and modality
        self.setWindowTitle("Speedy IQA Settings")
        self.setWindowModality(Qt.WindowModality.ApplicationModal)

        # Set the size of the wizard
        self.resize(640, 800)
        self.setMinimumSize(600, 540)

        self.connection_manager.connect(self.finished, self.save_config)

    def create_unified_page(self):
        page = UnifiedOptionsPage(self)
        page.setCommitPage(True)
        return page

    def save_config(self):
        """
        Saves the configuration file and closes the wizard.
        """
        # filename = self.config_filename
        #
        # # Add .yml extension if not provided by the user
        # if not filename.endswith('.yml'):
        #     filename += '.yml'

        self.task = self.main_page.task_edit.text()
        self.config_data['task'] = self.task

        for i in range(self.nradio_pages):
            titles = []
            # Remove the below if statement (but keep the content!!) if you want the first page to be editable
            if i != 0:
                for k in range(self.main_page.radio_box_layouts[i].count()):
                    hbox = self.main_page.radio_box_layouts[i].itemAt(k).layout()  # Get the QHBoxLayout
                    if hbox is not None:
                        if hbox.count() > 0:
                            line_edit = hbox.itemAt(0).widget()  # Get the QLineEdit from the QHBoxLayout
                            if line_edit.text():
                                titles.append(line_edit.text())
            else:
                titles.append("Overall Quality")
            self.config_data[f'radiobuttons_page{i + 1}'] = [
                {'title': title, 'labels': [1, 2, 3, 4]} for title in titles
            ]

        self.config_data['log_dir'] = os.path.normpath(os.path.abspath(self.log_dir))
        self.config_data['backup_dir'] = os.path.normpath(os.path.abspath(self.backup_dir))
        self.config_data['max_backups'] = self.max_backups
        self.config_data['backup_interval'] = self.backup_interval

        if not self.config_filename.endswith('.yml'):
            self.config_filename += '.yml'

        self.settings.setValue('task', self.task)
        self.settings.setValue("last_config_file", os.path.normpath(
            os.path.join(os.path.normpath(os.path.abspath(resource_dir)), self.config_filename))
                               )
        self.settings.setValue("log_dir", os.path.normpath(os.path.abspath(self.log_dir)))
        self.settings.setValue("backup_dir", os.path.normpath(os.path.abspath(self.backup_dir)))
        self.settings.setValue("max_backups", self.max_backups)
        self.settings.setValue("backup_interval", self.backup_interval)

        # Save the config file
        with open(os.path.join(os.path.abspath(resource_dir), self.config_filename), 'w') as f:
            yaml.dump(self.config_data, f)

        # Makes a log of the new configuration
        logger, console_msg = setup_logging(os.path.normpath(self.config_data['log_dir']))
        logger.info(f"Configuration saved to {os.path.join(resource_dir, self.config_filename)}")
        # super().close()


if __name__ == '__main__':
    # Create the application and apply the qt material stylesheet
    app = QApplication([])
    apply_stylesheet(app, theme='dark_blue.xml')

    # Set the directory of the main.py file as the default directory for the config files
    default_dir = resource_dir

    # Load the last config file used
    settings = QSettings('SpeedyIQA', 'ImageViewer')
    config_file = settings.value('last_config_file', os.path.normpath(os.path.join(resource_dir, 'config.yml')))

    # Create the configuration wizard
    wizard = ConfigurationWizard(config_file)

    # Run the wizard
    wizard.show()

    app.exec()
