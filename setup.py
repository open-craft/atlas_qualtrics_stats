"""Setup for qualtrics_stats XBlock."""

import os
from setuptools import setup


def package_data(pkg, root_list):
    """Generic function to find package_data for `pkg` under `root`."""
    data = []
    for root in root_list:
        for dirname, _, files in os.walk(os.path.join(pkg, root)):
            for fname in files:
                data.append(os.path.relpath(os.path.join(dirname, fname), pkg))

    return {pkg: data}


setup(
    name='qualtrics-stats-xblock',
    version='0.1',
    description='XBlock - Qualtrics statistics',
    packages=[
        'qualtrics_stats',
    ],
    install_requires=[
        'XBlock',
    ],
    entry_points={
        'xblock.v1': [
            'qualtrics_stats = qualtrics_stats:QualtricsXBlock',
        ]
    },
    package_data=package_data("qualtrics_stats", ["public", "templates"]),
)
