from setuptools import setup, find_packages

APP = ['speedy_iqa/main.py']
OPTIONS = {**{'iconfile': 'speedy_iqa/assets/logo.icns', 'includes': ['_cffi_backend'],
              'resources': ['speedy_iqa/assets', 'speedy_iqa/config.yml', 'speedy_iqa/log.conf'],
              'dylib_excludes': ['libgfortran.3.dylib'], 'frameworks': ['/usr/local/opt/libffi/lib/libffi.8.dylib'],
              'dist_dir': 'dist/86x64',
              }, **dict(plist=dict(NSRequiresAquaSystemAppearance=False,
                                   CFBundleIconFile="speedy_iqa/assets/logo.icns"))}

setup(
    app=APP,
    author='Ian Selby',
    author_email='ias49@cam.ac.uk',
    description='Tool to label images against a reference image for image quality assessment',
    name='Speedy IQA',
    url='https://github.com/selbs/speedy_iqa',
    use_scm_version=True,
    setup_requires=["setuptools_scm>=7.0.4", "py2app>=0.28"],
    packages=find_packages(),
    include_package_data=True,
    options={'py2app': OPTIONS},
    entry_points={
        'console_scripts': [
            'speedy_iqa=speedy_iqa.main:main',
            'speedy_config=speedy_iqa.wizard:main'
        ]
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=[
        "pip>=23.0.1",
        "pydicom>=2.3.1",
        "pylibjpeg==1.4.0",
        "numpy>=1.21.0",
        "setuptools>=42.0.0",
        "PyQt6>=6.2",
        "python-gdcm>=3.0.21",
        "PyYAML>=6.0",
        "qimage2ndarray>=1.10.0",
        "qt-material>=2.14",
        "QtAwesome>=1.2.3",
        "matplotlib>=3.4.3",
        "imageio>=2.31.0",
        "pillow>=10.0.0",
        "pandas"
    ],
)
