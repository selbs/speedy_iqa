Speedy IQA for Desktop <img src="speedy_iqa/assets/logo.png" alt="App Logo" width="200" style="float: right;">
=====================

Speedy IQA is an image viewer and labeller for image quality assessment (IQA). The program may be
used to quickly check the quality of the images against a reference image and to label them with the required ground 
truth for developing an IQA model.

The program may be run from the command line or as an executable, which can be downloaded or 
created from the source code.

Primarily developed for use on Mac OS X, but should work on Linux and Windows.

> **Warning:** Please note that this application is still in development and there may be unresolved bugs and issues. 
> Use at your own risk!

![Screenshot](speedy_iqa/assets/screenshot.png)

## Table of Contents
- [Installation](#installation)
- [Usage](#usage)
  - [Inputs and Outputs](#inputs-and-outputs)
    - [Checkboxes](#checkboxes)
    - [Bounding Boxes](#bounding-boxes)
    - [Radiobuttons](#radiobuttons)
  - [Progress](#progress)
  - [Keyboard Shortcuts](#keyboard-shortcuts)
- [Customisation](#customisation)
  - [Configuration Wizard](#configuration-wizard)
  - [YAML File](#yaml-file)
- [Backup Files](#backup-files)
- [Executable Application](#executable-application)

Installation
------------

Install the package using pip:

```bash
pip install git+https://github.com/selbs/speedy_iqa
```

It is recommended to install the package in a Python 3.10 virtual environment as this
version of python was used in development. However, other versions of Python 3 should still work.

You can also clone the package from GitHub and install it manually:

```bash
git clone https://github.com/selbs/speedy_iqa.git
cd speedy_iqa
pip install .
```

Usage
-----

Run the following command in the command line:

```bash
speedy_iqa
```

Alternatively, the app may be run from an executable (see below).

### Inputs and Outputs

#### Radiobuttons

Radiobutton outputs are stored as integers in the output json file.

### Progress

Your progress through the folder of images is shown in the progress bar at the bottom of the window.

### Keyboard Shortcuts

|                      Key                      |       Action       |
|:---------------------------------------------:|:------------------:|
|                 <kbd>B</kbd>                  |   Previous image   |
|                 <kbd>N</kbd>                  |     Next image     |
|          <kbd>+</kbd> / <kbd>=</kbd>          |      Zoom in       |
|          <kbd>-</kbd> / <kbd>_</kbd>          |      Zoom out      |
|                 <kbd>I</kbd>                  |   Invert colours   |
|                 <kbd>R</kbd>                  | Rotate image right |
|                 <kbd>L</kbd>                  | Rotate image left  |
|                 <kbd>S</kbd>                  |        Save        |
| <kbd>Cmd</kbd>/<kbd>Ctrl</kbd> + <kbd>Q</kbd> |        Quit        |
|            <kbd>Cmd</kbd> + Scroll            |      Contrast      |
|           <kbd>Shift</kbd> + Scroll           |     Brightness     |

Note: <kbd>Cmd</kbd> + Scroll and <kbd>Shift</kbd> + Scroll are only currently available on Mac OS X.

Backup Files
------------

Work is automatically backed up every 5 minutes, but this interval can be customised. By default, the backups are 
stored in the user's home directory (`~`) in the folder `~/speedy_iqa/backups` and up to the latest ten backups are 
stored. The number of backups, the backup interval and the backup directory can be customised in the configuration 
wizard or the `config.yml` file.


Executable Application
----------------------

The executable application may be downloaded from:
- Mac OS X:  https://github.com/selbs/speedy_iqa/releases/
  - *Universal binary for both 86x64 (Intel) and arm64 (Apple Silicon) Macs*. 
- Windows: [add link](https://www.example_link.com)

### Creating an Executable

An executable can be created using `py2app` for Mac OS X or `py2exe` for Windows. The customised `setup_py2app_****.py`
scripts have been included for `py2app` for both 86x64 (*Intel*) and arm64 (*Apple Silicon*) architectures on OS X. 
These may work out of the box but may need some tweaking for your local environment. For example, if the libffi library 
is in a different directory (see below) or if you are using a different version of Python (3.10) to that used in 
development (e.g. a `|` operator is used to join dictionaries for example, which is new in Python 3.9, so this would need
changing for Python 3.8).

To create an executable with `py2app` on 86x64, the following command can be used from inside the `speedy_qc` directory
on a 86x64 Mac, or using an 86x64 conda environment or using Rosetta 2 on a arm64 Mac:

```bash
python setup_86x64.py py2app
```

For arm64, the following command can be used, but note that if using conda, it must be an arm64 conda environment:

```bash
python setup_arm64.py py2app
```

The finished executable will be in the `dist` folder, which can be moved to the `Applications` folder as required.

If experiencing issues with `py2app` on Mac OS X, you can run the program the terminal to see more information:

```bash
'dist_86x64/Speedy IQA.app/Contents/MacOS/Speedy IQA'
```

or alternatively compile the program in alias mode:

```bash
python setup_86x64.py py2app -A
```
In both cases, replace '86x64' with 'arm64' for the arm64 executable as necessary.

`PyInstaller` may also work to create an executable but has not been tested.

#### Creating a Universal Binary

A universal binary can be created by combining the two executables created by `py2app`. This can be done using the
`lipo` command after both executables have been created (e.g. inside arm64 and 86x64 conda environments). 
To create a universal binary for the 86x64 and arm64 executables, use the following commands:

```bash
mkdir -p "dist/universal/Speedy IQA.app/"
cp -R "dist/arm64/Speedy IQA.app/" "dist/universal/Speedy IQA.app/"
rm -rf "dist/universal/Speedy IQA.app/Contents/MacOS/Speedy IQA"
rm -rf "dist/universal/Speedy IQA.app/Contents/MacOS/Python"
lipo -create -output "dist/universal/Speedy IQA.app/Contents/MacOS/Speedy IQA" "dist/arm64/Speedy IQA.app/Contents/MacOS/Speedy IQA" "dist/86x64/Speedy IQA.app/Contents/MacOS/Speedy IQA"
lipo -create -output "dist/universal/Speedy IQA.app/Contents/MacOS/Python" "dist/arm64/Speedy IQA.app/Contents/MacOS/Python" "dist/86x64/Speedy IQA.app/Contents/MacOS/Python"
```

#### libffi

The libffi library is required for the executable to run on MacOS. This can be installed using Homebrew:

```bash
brew install libffi
```

If using a arm64 Mac, the libffi library will be installed in the `/opt/homebrew/Cellar` directory, whilst the 86x64
version will be installed in the `/usr/local/opt` directory. The `setup_86x64.py` and `setup_arm64.py` scripts
have been configured to look for the library in the `/opt/homebrew` directory. If the library is installed in a
different directory, the `setup_86x64.py` and `setup_arm64.py` scripts will need to be modified accordingly.
