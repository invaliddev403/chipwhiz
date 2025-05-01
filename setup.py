# setup.py
from setuptools import setup, find_packages
setup(
    name="chipwhiz",
    version="0.1",
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'chipwhiz=chipwhiz.chipwhiz:Main',
        ],
    },
    author="Invalid.Dev.403",
    description="Modernized fork of chipinfo for USB flash controller analysis",
    license="MIT",
)
