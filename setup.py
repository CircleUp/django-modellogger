from setuptools import setup

from modellogger import __version__

setup(
    name="django-modellogger",
    version=__version__,
    author="CircleUp",
    author_email="modellogger@accounts.brycedrennan.com",
    description=("Change tracking for Django models."),
    keywords="django",
    url="http://packages.python.org/django-modellogger",
    packages=['modellogger', 'modellogger.migrations'],
    long_description="""Tracks changes to django models.""",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Topic :: Database",
    ],
)
