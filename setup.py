from setuptools import setup, find_packages

setup(
    author='Ian Selby',
    author_email='ias49@cam.ac.uk',
    description='Tool to label images against a reference image for image quality assessment',
    name='SpeedyIQA',
    url='https://github.com/selbs/speedy_iqa',
    use_scm_version=True,
    setup_requires=["setuptools_scm>=7.0.4"],
    packages=find_packages(),
    include_package_data=True,
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
        "importlib_metadata>=6.1.0",
        "numpy>=1.24.2",
        "py2app>=0.28.5",
        "pydicom>=2.3.1",
        "PyQt6>=6.4",
        "PyYAML>=6.0",
        "qimage2ndarray>=1.10.0",
        "qt_material>=2.14",
        "QtAwesome>=1.2.3",
        "pylibjpeg==1.4.0",
        "setuptools>=42.0.0",
        "python-gdcm>=3.0.21",
        "py2app>=0.28.5",
        "matplotlib>=3.4.3",
        "imageio>=2.31.0",
        "pandas"
    ],
)
