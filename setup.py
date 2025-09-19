"""
Setup script for preserve package.
"""

import os
from setuptools import setup, find_packages

# Get the long description from the README file
with open(os.path.join(os.path.dirname(__file__), 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name="preserve",
    version="0.3.0",
    description="A tool for preserving files with path normalization and verification",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Your Name",
    author_email="your.email@example.com",
    url="https://github.com/username/preserve",
    packages=find_packages(),
    install_requires=[
        # Base requirements
        "pathlib",
        "colorama>=0.4.0",  # For colored terminal output
    ],
    extras_require={
        "dazzlelink": ["dazzlelink>=0.5.0"],
        "windows": ["pywin32"],
        "dev": [
            "pytest",
            "pytest-cov",
            "black",
            "flake8",
        ],
        "all": ["dazzlelink>=0.5.0", "pywin32;platform_system=='Windows'"]
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
        "Topic :: System :: Archiving :: Backup",
        "Topic :: Utilities",
    ],
    python_requires=">=3.6",
    entry_points={
        "console_scripts": [
            "preserve=preserve.preserve:main",
        ],
    },
)
