# coding: utf-8

from setuptools import setup
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='dokkupy',
    version='0.1',
    description='Python API and script for dokku',
    long_description=long_description,
    url='https://github.com/fenrrir/dokkupy',
    author=u'Rodrigo Pinheiro Marques de Araújo',
    author_email='fenrrir@gmail.com',
    license='MIT',

    classifiers=[
        'Development Status :: 1 - Planning',
        'Intended Audience :: Developers',
        'Environment :: Console',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
    ],
    keywords='python dokku',
    packages=['dokkupy'],
    scripts=['dokkupycli'],
    install_requires=['GitPython==3.1.3'],
)
