"""Setup script for Readwise to Twos sync package."""

from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
readme_path = Path(__file__).parent / "README.md"
long_description = readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""

setup(
    name="readwise-twos-sync",
    version="1.0.0",
    author="Jordan Kuhns",
    author_email="jkuhns13@gmail.com",
    description="Sync Readwise highlights to Twos app",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/readwise-twos-sync",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.8",
    install_requires=[
        "requests>=2.25.0",
        "python-dotenv>=0.19.0",
    ],
    extras_require={
        "dev": [
            "pytest>=6.0",
            "pytest-cov>=2.0",
            "black>=21.0",
            "flake8>=3.8",
            "mypy>=0.800",
        ]
    },
    entry_points={
        "console_scripts": [
            "readwise-twos-sync=readwise_twos_sync.cli:main",
        ],
    },
    keywords="readwise twos sync highlights api",
    project_urls={
        "Bug Reports": "https://github.com/yourusername/readwise-twos-sync/issues",
        "Source": "https://github.com/yourusername/readwise-twos-sync",
    },
)