# -*- coding: utf-8 -*-
import os
from setuptools import setup

root = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(root, 'README.rst')) as f:
    README = f.read()

install_requires = [
    'pyas2lib==1.4.0',
    'django>=2.2.18',
    'requests'
]

tests_require = [
    "pytest==5.4.3",
    "pytest-cov==2.11.1",
    "pytest-django==3.9.0",
    "pytest-mock==3.5.1"
    "pylama==7.7.1"
    "pylint==2.7.3"
    "pytest-black==0.3.12"
    "black==21.5b0",
    "django-environ==0.4.5",
]


setup(
    name='django-pyas2',
    version='1.2.1',
    description='AS2 file transfer Server built on Python and Django.',
    license="GNU GPL v3.0",
    long_description=README,
    author='Abhishek Ram',
    author_email='abhishek8816@gmail.com',
    url='http://github.com/abhishek-ram/django-pyas2',
    packages=['pyas2'],
    zip_safe=False,
    include_package_data=True,
    classifiers=[
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        "Topic :: Security :: Cryptography",
        "Topic :: Communications",
    ],
    setup_requires=["pytest-runner"],
    install_requires=install_requires,
    tests_require=tests_require,
    extras_require={
        "tests": tests_require,
    },
)
