Admin Commands
==============
``django-pyas2`` provides a set of Django ``manage.py`` admin commands that perform various functions. We have
already seen the usage of some of these commands in the previous sections. Let us now go through the list
of available commands:

sendas2message
--------------
The ``sendas2message`` command triggers a file transfer, it takes the mandatory arguments organization id, partner id and
the full path to the file to be transferred. The command can be used by other applications to integrate with ``django-pyas2``.

sendas2bulk
-----------
The ``sendas2bulk`` command looks in the outbox folder for each partner setup on the as2 server. It then triggers a transfer for each file found in the outbox.

manageas2server
---------------
The ``manageas2server`` command performs various management operation on the AS2 server. The following options are available which can either be used together or alone:

* ``--async-mdns``: This operation performs two functions; it sends asynchronous MDNs for messages received from your partners and also checks if we have received asynchronous MDNs for sent messages so that the message status can be updated appropriately.
* ``--retry``: This operation checks for any messages that have been set for retries and then re-triggers the transfer for these messages.
* ``--clean``: This operation deletes all messages objects and related files older that the ``MAX_ARCH_DAYS`` setting.

