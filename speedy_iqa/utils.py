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

import logging.config
import yaml
import os
from typing import Dict, Union, Any, Optional, Tuple, List
from PyQt6.QtCore import *
import sys
import numpy as np
from PIL import Image

if hasattr(sys, '_MEIPASS'):
    # This is a py2app executable
    resource_dir = sys._MEIPASS
elif 'main.py' in os.listdir(os.path.dirname(os.path.abspath("__main__"))):
    # This is a regular Python script
    resource_dir = os.path.dirname(os.path.abspath("__main__"))
elif 'main.py' in os.path.join(os.path.dirname(os.path.abspath("__main__")), 'speedy_iqa'):
    resource_dir = os.path.join(os.path.dirname(os.path.abspath("__main__")), 'speedy_iqa')
elif 'main.py' in os.path.join(os.path.dirname(os.path.abspath("__main__")), 'speedy_iqa', 'speedy_iqa'):
    resource_dir = os.path.join(os.path.dirname(os.path.abspath("__main__")), 'speedy_iqa', 'speedy_iqa')
else:
    raise(FileNotFoundError(f"Resource directory not found from {os.path.dirname(os.path.abspath('__main__'))}"))


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
        'backup_dir': os.path.expanduser('~/speedy_iqa/backups'),
        'log_dir': os.path.expanduser('~/speedy_iqa/logs'),
        # 'tristate_checkboxes': True,
        'backup_interval': 5,
        'task': 'General use',
    }

    save_path = os.path.join(resource_dir, 'config.yml')

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

    if not os.path.isfile(config_path):
        # If the config file does not exist, look for the default config file
        print(f"Could not find config file at {config_path}")
        if os.path.isfile(os.path.join(resource_dir, 'config.yml')):
            print(f"Using default config file at "
                  f"{os.path.join(resource_dir, 'config.yml')}")
            config_path = os.path.join(resource_dir, 'config.yml')
            with open(config_path, 'r') as f:
                config_data = yaml.safe_load(f)
        else:
            # If the default config file does not exist, create a new one
            print(f"Could not find default config file at {os.path.join(resource_dir, 'config.yml')}")
            print(f"Creating a new default config file at "
                  f"{os.path.join(resource_dir, 'config.yml')}")
            config_data = create_default_config()
    else:
        # Open the config file and load the data
        with open(config_path, 'r') as f:
            config_data = yaml.safe_load(f)

    return config_data


def setup_logging(log_out_path: str, resource_directory: str = resource_dir) -> Tuple[logging.Logger, logging.Logger]:
    """
    Sets up the logging for the application. The log file will be saved in the log_out_path in the directory
    specified in the chosen config .yml file.

    :param log_out_path: str, the path to the directory where the log file will be saved.
    :param resource_directory: str, the path to the resource directory.
    :return: tuple (logger, console_msg), where logger is a configured logging.Logger instance, and console_msg is a
             reference to the same logger to be used for console messaging.
    """
    full_log_file_path = os.path.expanduser(os.path.join(log_out_path, "speedy_iqa.log"))
    os.makedirs(os.path.dirname(full_log_file_path), exist_ok=True)
    logging.config.fileConfig(os.path.join(resource_directory, 'log.conf'),
                              defaults={'log_file_path': full_log_file_path})
    logger = logging.getLogger(__name__)
    console_msg = logging.getLogger(__name__)
    return logger, console_msg


def bytescale(
        arr: np.ndarray,
        low: Optional[float] = None,
        high: Optional[float] = None,
        a: float = 0,
        b: float = 255
) -> np.ndarray:
    """
    Linearly rescale values in an array. By default, it scales the values to the byte range (0-255).

    :param arr: The array to rescale.
    :type arr: np.ndarray
    :param low: Lower boundary of the output interval. All values smaller than low are clipped to low.
    :type low: float
    :param high: Upper boundary of the output interval. All values larger than high are clipped to high.
    :type high: float
    :param a: Lower boundary of the input interval.
    :type a: float
    :param b: Upper boundary of the input interval.
    :type b: float
    :return: The rescaled array.
    :rtype: np.ndarray
    """

    arr = arr.astype(float)  # to ensure floating point division

    # Clip to specified high/low values, if any
    if low is not None:
        arr = np.maximum(arr, low)
    if high is not None:
        arr = np.minimum(arr, high)

    min_val, max_val = np.min(arr), np.max(arr)

    if np.isclose(min_val, max_val):  # avoid division by zero
        return np.full_like(arr, a, dtype=np.uint8)

    # Normalize between a and b
    return (((b - a) * (arr - min_val) / (max_val - min_val)) + a).astype(np.uint8)


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
