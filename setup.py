# -*- coding: utf-8 -*-
import os
from setuptools import setup, find_packages

version = __import__('pyas2').__version__
is_py2 = __import__('pyas2').is_py2

root = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(root, 'README.md')) as f:
    README = f.read()

install_requires = [
    'pyas2lib==1.0.3',
    'django>=1.10.0,<2.0' if is_py2 else 'django>=1.10.0',
    'requests'
]

tests_require = [
    'pytest',
    'pytest-cov',
    'pytest-django',
    'coverage',
    'mock'
]


setup(
    name='django-pyas2',
    version=version,
    description='A Django app for transferring files using AS2 protocol',
    license="GNU GPL v3.0",
    long_description=README,
    author='Abhishek Ram',
    author_email='abhishek8816@gmail.com',
    url='http://github.com/abhishek-ram/django-pyas2',
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    classifiers=[
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        "Topic :: Security :: Cryptography",
        "Topic :: Communications",
    ],
    install_requires=install_requires,
    tests_require=tests_require,
)
