"""Setup for atlas XBlock."""

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
    name='xblock-atlas',
    version='0.1',
    description='XBlock - Atlas statistics',
    packages=[
        'atlas',
    ],
    install_requires=[
        'XBlock',
        'requests',
        'pytz'
    ],
    entry_points={
        'xblock.v1': [
            'atlas = atlas:AtlasXBlock',
        ]
    },
    package_data=package_data("atlas", ["public", "templates"]),
)
