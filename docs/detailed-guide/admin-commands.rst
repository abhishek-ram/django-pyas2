Admin Commands
==============
``django-pyas3`` provides a set of Django ``manage.py`` admin commands that perform various functions. We have
already seen the usage of some of these commands in the previous sections. Let us now go through the list
of available commands:

sendas2message
--------------
The ``sendas2message`` command triggers a file transfer, it takes the mandatory arguments organization id, partner id and
the full path to the file to be transferred. The command can be used by other applications to integrate with ``pyAS2``.

sendasyncmdn
------------
The ``sendasyncmdn`` command performs two functions; it sends asynchronous MDNs for messages received from your partners and
also checks if we have received asynchronous MDNs for sent messages so that the message status can be updated appropriately.
The command does not take any arguments and should be run on a repeating schedule.

retryfailedas2comms
-------------------
The ``retryfailedas2comms`` command checks for any messages that have been set for retries and then retriggers the transfer
for these messages. The command does not take any arguments and should be run on a repeating schedule.

cleanas2server
--------------
The ``cleanas2server`` command is a maintenance command and it deletes all DB objects, logs and files older that the ``MAXARCHDAYS``
setting. It is recommended to run this command once a day using cron or windows scheduler.
