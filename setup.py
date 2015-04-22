import os
from setuptools import setup

# Utility function to read the README file.
# Used for the long_description.  It's nice, because now 1) we have a top level
# README file and 2) it's easier to type in the README file than to put a raw
# string in below ...
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

from modellogger import __version__

setup(
    name="django-modellogger",
    version=__version__,
    author="CircleUp",
    author_email="webaccounts@circleup.com",
    description=("Change tracking for Django models."),
    keywords="django",
    url="http://packages.python.org/django-modellogger",
    packages=['modellogger', 'modellogger.migrations'],
    long_description=read('README'),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Topic :: Database",
    ],
)
