"""Setup script for PyTunnel."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="pytunnel",
    version="0.3.0",
    author="PyTunnel",
    description="A ngrok-like tunneling application in Python with enterprise features",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=[
        "aiohttp>=3.9.1",
        "websockets>=12.0",
        "uvicorn>=0.25.0",
        "python-dotenv>=1.0.0",
        "colorama>=0.4.6",
        "cryptography>=41.0.7",
        "rich>=13.7.0",
        "click>=8.1.7",
        "psutil>=5.9.6",
        "questionary>=2.0.1",
        "geoip2>=4.7.0",
    ],
    entry_points={
        "console_scripts": [
            "pytunnel-server=pytunnel.server.cli:main",
            "pytunnel-client=pytunnel.client.cli:main",
            "pytunnel-status=pytunnel.cli_status:main",
        ],
    },
)
