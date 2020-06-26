Send & Receive MDNs
===================
Message Disposition Notifications or MDNs are return receipts used to notify the sender of a message of any of
the several conditions that may occur after successful delivery. In the context of the AS2 protocol, the MDN is used
to notify if the message was successfully processed by the receiver's system or not and in case of failures the
reason for the failure is sent with the MDN.

MDNs can be transmitted either in a synchronous manner or in an asynchronous manner. The synchronous transmission uses
the same HTTP session as that of the AS2 message and the MDN is returned as an HTTP response message. The asynchronous
transmission uses a new HTTP session to send the MDN to the original AS2 message sender.

Send MDNs
---------
The choice of whether to send an MDN and its transfer mode is with the sender of the AS2 message. The sender lets us know what
to do through an AS2 header field. In case the partner requests a synchronous MDN no action is needed as ``django-pyas2``
takes care of this internally, however in the case of an asynchronous MDN the admin command ``manageas2server --async-mdns`` needs to be
run to send the MDN to the trading partner.

The command ``{PYTHONPATH}/python {DJANGOPROJECTPATH}/manage.py manageas2server --async-mdns`` should be scheduled every 10 minutes so
that ``django-pyas2`` sends any pending asynchronous MDN requests received from your trading partners.

Receive MDNs
------------
The choice of whether or not to receive MDN and its transfer mode is with us. The `MDN Settings <partners.html#mdn-settings>`__
for the partner should be used to specify your preference. In case of synchronous mode ``django-pyas2`` processes the received MDN
without any action from you.

In the case of asynchronous mode we do need to take care of a couple of details to enable the receipt of the MDNs.
The :doc:`global setting<configuration>` ``MDNURL`` should be set to the URL ``http://{hostname}:{port}/pyas2/as2receive``
so that the trading partner knows where to send the MDN. The other setting of note here is the ``ASYNCMDNWAIT``
that decides how long ``django-pyas2`` waits for an MDN before setting the message as failed so that it can be retried. The admin
command ``manageas2server --async-mdns`` makes this check for all pending messages so it must be scheduled to run regularly.
