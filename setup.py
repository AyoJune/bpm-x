"""
Setup configuration for BPM-X
Install with: pip install -e .
"""

from setuptools import setup, find_packages

with open('requirements.txt') as f:
    requirements = f.read().splitlines()

setup(
    name='bpm-x',
    version='0.1.0',
    description='Professional music library organizer with BPM/Key detection for DAW integration',
    author='Producer',
    packages=find_packages(),
    install_requires=requirements,
    entry_points={
        'console_scripts': [
            'bpm-x=interface.cli:run_cli',
        ],
    },
    python_requires='>=3.8',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: End Users/Desktop',
        'Topic :: Multimedia :: Sound/Audio',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
    ],
)
