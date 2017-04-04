#!/usr/bin/env python

from distutils.core import setup
import setuptools


setup(name='web-bank-connect',
    version='0.1',
    description='Python Framework for online banking with Selenium',
    author='Alexis Yushin',
    author_email='alexis@ww.net',
    url='https://github.com/ayushin/web-bank-connect.git',
    install_requires = ['selenium>=3.3.1'],
    packages = ['wbc',
                'wbc.plugins',
                'wbc.plugins.cz',
                'wbc.plugins.nl',
                'wbc.plugins.tr'],
    entry_points = {
        'console_scripts': ['wbc=wbc.cli:main'],
    }
)
