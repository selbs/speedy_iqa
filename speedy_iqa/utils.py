"""
utils.py

Utility module for the speedy_iqa application.

This module provides utility functions and classes to support the speedy_iqa application, including:

1. Default configuration file creation and management.
2. YAML file loading.
3. Logging setup.
4. Connection management for signals and slots in a Qt application.

Classes:
    Connection
    ConnectionManager

Functions:
    create_default_config() -> dict
    open_yml_file(config_path: str) -> dict
    setup_logging(log_out_path: str) -> Tuple[logging.Logger, logging.Logger]
    bytescale(data: np.ndarray, cmin: int = None, cmax: int = None, high: int = 255, low: int = 0) -> np.ndarray
    convert_to_checkstate(value: Any) -> Qt.CheckState
"""

# import logging.config
import yaml
import os
from typing import Dict, Union, Any, Optional, Tuple, List, Collection
from PyQt6.QtCore import *
import numpy as np
from PIL import Image
import glob
import pandas as pd
import logging
from logging import FileHandler, StreamHandler
import sys


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

resource_dir = os.path.normpath(os.path.abspath(resource_dir))


class Connection:
    """
    A class to manage a single connection between a signal and a slot in a Qt application.
    """
    def __init__(self, signal: pyqtSignal, slot: callable):
        self.signal = signal
        self.slot = slot
        self.connection = self.signal.connect(self.slot)

    def disconnect(self):
        """
        Disconnects the signal from the slot.
        """
        self.signal.disconnect(self.slot)


class ConnectionManager:
    """
    A class to manage multiple connections between signals and slots in a Qt application.
    """
    def __init__(self):
        self.connections = {}

    def connect(self, signal: Any, slot: callable):
        """
        Connects a signal to a slot and stores the connection in a dictionary.

        :param signal: QtCore.pyqtSignal, the signal to connect.
        :param slot: callable, the slot (function or method) to connect to the signal.
        """
        connection = Connection(signal, slot)
        self.connections[id(connection)] = connection

    def disconnect_all(self):
        """
        Disconnects all connections and clears the dictionary.
        """
        for connection in self.connections.values():
            if isinstance(connection, Connection):
                connection.disconnect()
        self.connections = {}


def create_default_config() -> Dict:
    """
    Creates a default config file in the speedy_iqa directory.

    :return: dict, the default configuration data.
    """
    # Default config...
    default_config = {
        # 'checkboxes': ['QC1', 'QC2', 'QC3', 'QC4', 'QC5'],
        'radiobuttons_page1': [{'title': "Overall Quality", 'labels': [1, 2, 3, 4]}, ],
        'radiobuttons_page2': [
            {'title': "Contrast", 'labels': [1, 2, 3, 4]},
            {'title': "Noise", 'labels': [1, 2, 3, 4]},
            {'title': "Artefacts", 'labels': [1, 2, 3, 4]},
        ],
        'max_backups': 10,
        'backup_dir': os.path.normpath(os.path.expanduser('~/speedy_iqa/backups')),
        'log_dir': os.path.normpath(os.path.expanduser('~/speedy_iqa/logs')),
        # 'tristate_checkboxes': True,
        'backup_interval': 5,
        'task': 'General use',
    }

    save_path = os.path.normpath(os.path.join(resource_dir, 'config.yml'))

    # Save the default config to the speedy_iqa directory
    with open(save_path, 'w') as f:
        yaml.dump(default_config, f)

    return default_config


def open_yml_file(config_path: str) -> Dict:
    """
    Opens a config .yml file and returns the data. If the file does not exist, it will look
    for the default config file, otherwise, it will create a new default config file.

    :param config_path: str, the path to the config file.
    :return: dict, the loaded configuration data from the YAML file.
    """
    # print("*"*50)
    # print("Resource directory:", resource_dir)
    # print("*"*50)

    if not os.path.isfile(os.path.normpath(config_path)):
        # If the config file does not exist, look for the default config file
        print(f"Could not find config file at {os.path.normpath(config_path)}")
        if os.path.isfile(os.path.normpath(os.path.join(resource_dir, 'config.yml'))):
            print(f"Using default config file at "
                  f"{os.path.normpath(os.path.join(resource_dir, 'config.yml'))}")
            config_path = os.path.normpath(os.path.join(resource_dir, 'config.yml'))
            with open(config_path, 'r') as f:
                config_data = yaml.safe_load(f)
        else:
            # If the default config file does not exist, create a new one
            print(f"Could not find default config file at {os.path.normpath(os.path.join(resource_dir, 'config.yml'))}")
            print(f"Creating a new default config file at "
                  f"{os.path.normpath(os.path.join(resource_dir, 'config.yml'))}")
            config_data = create_default_config()
    else:
        # Open the config file and load the data
        with open(os.path.normpath(config_path), 'r') as f:
            config_data = yaml.safe_load(f)

    return config_data


def setup_logging(log_out_path: str) -> Tuple[logging.Logger, logging.Logger]:
    """
    Sets up the logging for the application. Creates two loggers: one for logging to a file and another for console
    output. Changed from using a .conf file due to issues with making it OS-agnostic.

    :param log_out_path: The path to the directory where the log file will be saved. :param resource_directory: The
        path to the resource directory, not directly used here but can be utilized for additional configurations.
    :param resource_directory: The path to the resource directory.
    :return: A tuple (file_logger, console_logger), where file_logger is configured to log to a file,
        and console_logger is configured for console output.
    """
    full_log_file_path = os.path.normpath(os.path.expanduser(os.path.join(log_out_path, "speedy_iqa.log")))
    os.makedirs(os.path.dirname(full_log_file_path), exist_ok=True)

    # Configure logger for file output
    file_logger = logging.getLogger('fileLogger')
    file_logger.setLevel(logging.DEBUG)
    file_logger.propagate = False
    fileHandler = FileHandler(full_log_file_path, mode='a')
    fileHandler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%d/%m/%Y %H:%M:%S')
    )
    file_logger.addHandler(fileHandler)

    # Configure logger for console output
    console_logger = logging.getLogger('consoleLogger')
    console_logger.setLevel(logging.DEBUG)
    console_logger.propagate = False
    consoleHandler = StreamHandler(sys.stdout)
    consoleHandler.setFormatter(
        logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%d/%m/%Y %H:%M:%S')
    )
    console_logger.addHandler(consoleHandler)

    return file_logger, console_logger


# def setup_logging(log_out_path: str, resource_directory: str = resource_dir) -> Tuple[logging.Logger, logging.Logger]:
#     """
#     Sets up the logging for the application. The log file will be saved in the log_out_path in the directory
#     specified in the chosen config .yml file.
#
#     :param log_out_path: str, the path to the directory where the log file will be saved.
#     :param resource_directory: str, the path to the resource directory.
#     :return: tuple (logger, console_msg), where logger is a configured logging.Logger instance, and console_msg is a
#              reference to the same logger to be used for console messaging.
#     """
#     full_log_file_path = os.path.normpath(os.path.expanduser(os.path.join(log_out_path, "speedy_iqa.log")))
#     os.makedirs(os.path.dirname(os.path.abspath(os.path.normpath(full_log_file_path))), exist_ok=True)
#     logging.config.fileConfig(os.path.join(os.path.normpath(resource_directory), 'log.conf'),
#                               defaults={'log_file_path': os.path.normpath(full_log_file_path)})
#     logger = logging.getLogger(__name__)
#     console_msg = logging.getLogger(__name__)
#     return logger, console_msg


def convert_to_checkstate(value: int) -> Qt.CheckState:
    """
    Converts an integer value to a Qt.CheckState value for tri-state checkboxes.

    :param value: int, the value to convert.
    :type: int
    :return: The converted value.
    :rtype: Qt.CheckState
    """
    if value == 0:
        return Qt.CheckState.Unchecked
    elif value == 1:
        return Qt.CheckState.PartiallyChecked
    elif value == 2:
        return Qt.CheckState.Checked
    else:
        # Handle invalid values or default case
        return Qt.CheckState.Unchecked


def create_icns(
        png_path: str,
        icns_path: str,
        sizes: Optional[Union[Tuple[int], List[int]]] = (16, 32, 64, 128, 256, 512, 1024)
):
    img = Image.open(png_path)
    icon_sizes = []

    for size in sizes:
        # Resize while maintaining aspect ratio (thumbnail method maintains aspect ratio)
        copy = img.copy()
        copy.thumbnail((size, size))

        # Create new image and paste the resized image into it, centering it
        new_image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        new_image.paste(copy, ((size - copy.width) // 2, (size - copy.height) // 2))

        icon_sizes.append(new_image)

    if icns_path.endswith('.icns'):
        icns_path = icns_path[:-5]

    # Save the images as .icns
    icon_sizes[0].save(f'{icns_path}.icns', format='ICNS', append_images=icon_sizes[1:])


def find_relative_image_path(
        base_path: str,
        extensions: Collection[str] = ('png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff', 'tif', 'dcm', 'dicom',)
) -> List[str]:
    """
    Recursively find all image files in a given directory and return their relative paths.

    :param base_path: The path to the directory to search.
    :param extensions: A list of file extensions to consider as image files. Default is ['png', 'jpg', 'jpeg', 'gif',
        'bmp', 'tiff', 'tif', 'dcm', 'dicom',].
    :return: A list of relative paths pointing to the image files.
    """
    all_images = []
    for extension in extensions:
        for image_path in glob.glob(f"{base_path}/**/*.{extension}", recursive=True):
            relative_path = os.path.relpath(image_path, start=base_path)
            all_images.append(relative_path)

    return all_images


def invert_grayscale(image):
    return np.max(image) + np.min(image) - image


def expand_dict_column(df, column_name):
    """
    Expand a column containing dictionaries into new columns.

    :param df: DataFrame containing the dictionary column.
    :param column_name: Name of the column to expand.
    :return: DataFrame with expanded columns.
    :rtype: pandas.DataFrame
    """
    # Use apply to create a new DataFrame with the expanded columns
    expanded_df = df[column_name].apply(pd.Series)

    # Concatenate the expanded DataFrame with the original DataFrame
    result_df = pd.concat([df, expanded_df], axis=1)

    # Drop the original dictionary column
    result_df.drop(column_name, axis=1, inplace=True)

    new_columns = expanded_df.columns

    for col in new_columns:
        result_df = result_df.rename(columns={col: col.lower().replace(" ", "_")})
    new_columns = [col.lower().replace(" ", "_") for col in new_columns]

    return result_df, new_columns


def make_column_categorical(df, column_name):
    """
    Convert a column with float values to categorical values '1', '2', '3', '4', and 'Blank'.

    :param df: DataFrame containing the column to convert.
    :param column_name: Name of the column to make categorical.
    :return: DataFrame with the specified column as categorical.
    :rtype: pandas.DataFrame
    """
    # Define the bin edges for categorization
    bin_edges = [0, 1, 2, 3, 4, np.inf]

    # Define labels for each category
    labels = ['1', '2', '3', '4', 'Blank']

    # Use pd.cut() to categorize the values
    df[column_name] = pd.cut(df[column_name], bins=bin_edges, labels=labels, right=False)

    return df

