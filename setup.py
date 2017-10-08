

from setuptools import setup, find_packages
from os.path import join, dirname

setup(
    name='gcm',
    version='1.2',
    packages=find_packages(),
    entry_points={
        'console_scripts':
            ['gcm = gcm.gnome_connection_manager:main']
    },
    long_description=open(join(dirname(__file__), 'README.txt')).read(),
    include_package_data=True,
    setup_requires=[
        'polib',
    ],
    install_requires=[
        'pyaes==1.6.1',
        'pygtk==2.24.0',

    ]
)
