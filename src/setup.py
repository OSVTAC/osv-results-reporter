"""
This file lets the project be installed locally using `pip install`.

This setup.py is not meant to support publishing the project to PyPI!
"""

from setuptools import setup, find_packages

setup(
    name='osv-results-reporter',
    # TODO: DRY up with orr.main.VERSION.
    version='0.0.1',
    description='template-based election results report generator',
    url='https://github.com/carl3/open-results-reporter',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
    ],
    packages=find_packages(),
    install_requires=[
        # TODO
    ],
    entry_points={
        'console_scripts': [
            'orr=orr.main:main',
        ],
    },
)
