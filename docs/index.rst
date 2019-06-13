.. pyAS2 documentation master file, created by
   sphinx-quickstart on Wed May  1 12:24:04 2019.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

********************************************
django-pyas2: pythonic AS2 server
********************************************

Release v\ |release|. (:doc:`Changelog <changelog>`)

``django-pyas2`` is an AS2 server/client written in python and built on the `Django framework`_.
The application supports AS2 version 1.2 as defined in the `RFC 4130`_. Our goal is to
provide a native python library for implementing the AS2 protocol. It supports Python 3.6+.

The application includes a server for receiving files from partners,  a front-end web interface for
configuration and monitoring, a set of ``django-admin`` commands that serves as a client
for sending messages, asynchronous MDNs and a daemon process that monitors directories
and sends files to partners when they are placed in the partner's watched directory.

Features
========

* Technical

  - Asynchronous and Synchronous MDN
  - Partner and Organization management
  - Digital signatures
  - Message encryption
  - Secure transport (SSL)
  - Support for SSL client authentication
  - System task to auto clear old log entries
  - Data compression (AS2 1.1)
  - Multinational support: Uses Django's internationalization feature

* Integration

  - Easy integration to existing systems, using a partner based file system interface
  - Message post processing (scripting on receipt)

* Monitoring

  - Web interface for transaction monitoring
  - Email event notification

* The following encryption algorithms are supported:

  - Triple DES
  - RC2-128
  - RC4-128
  - AES-128
  - AES-192
  - AES-256

* The following hash algorithms are supported:

  - SHA-1
  - SHA-224
  - SHA-256
  - SHA-384
  - SHA-512

Dependencies
============
* Python 3.6+
* Django (1.9+)
* requests
* pyas2lib

Guide
=====
.. toctree::
   :maxdepth: 2

   installation
   quickstart
   detailed-guide/index
   changelog

.. _`RFC 4130`: https://www.ietf.org/rfc/rfc4130.txt
.. _`Django framework`: https://www.djangoproject.com/
