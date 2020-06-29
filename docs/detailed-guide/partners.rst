Partners
========
Partners in ``django-pyas2`` mean all your trading partners with whom you will exchanges messages, i.e. they are the receivers
when you send messages and the senders when you receive messages. Partners can be managed from the Django Admin.
The admin lists the existing partners and also you gives the option to search them and create new ones. Each
partner is characterized by the following fields:

General Settings
----------------

=========================  ============================================  =========
Field Name                 Description                                   Mandatory
=========================  ============================================  =========
``Partner Name``           The descriptive name of the partner.          Yes
``As2 Identifier``         The as2 identifies for this partner as        Yes
                           communicated by the partner.
``Email Address``          The email address for the partner.            No
``Target Url``             The HTTP/S endpoint of the partner to         Yes
                           which files need to be posted.
``Subject``                The MIME subject header to be sent along      Yes
                           with the file.
``Content Type``           The content type of the message being         Yes
                           transmitted, can be XML, X12 or EDIFACT.
``Confirmation Message``   Use this field to customize the confirmation  No
                           message sent in MDNs to partners.
=========================  ============================================  =========

HTTP Authentication
-------------------
Use these settings if basic authentication has been enabled for the partners AS2 server.

==========================  ===========================================  =========
Field Name                  Description                                  Mandatory
==========================  ===========================================  =========
``Enable Authentication``   Check this option to enable basic AUTH.      No
``Http auth user``          User name to access the partners server.     No
``Http auth pass``          Password to access the partners server.      No
==========================  ===========================================  =========

Security Settings
-----------------

======================  ==========================================  =========
Field Name              Description                                 Mandatory
======================  ==========================================  =========
``Compress Message``    Check this option to enable AS2 message     No
                        compression.
``Encrypt Message``     Select the algorithm to be used for         No
                        encrypting messages, defaults to None.
``Encryption Key``      Select the ``Public Key`` used for          No
                        encrypting the outbound messages
                        to this partner.
``Sign Message``        Select the hash algorithm to be used for    No
                        signing messages, defaults to None.
                        incoming messages from trading partners.
``Signature key``       The ``Public Key`` used to verify inbound   No
                        signed messages and MDNs from this partner
======================  ==========================================  =========

MDN Settings
------------

======================  ==========================================  =========
Field Name              Description                                 Mandatory
======================  ==========================================  =========
``Request MDN``         Check this option to request MDN for        Yes
                        outbound messages to this partner.
``Mdn mode``            Select the MDN mode, defaults to            No
                        Synchronous
``Request Signed MDN``  Select the algorithm to be used in case     No
                        signed MDN is to be returned.
======================  ==========================================  =========

Advanced Settings
-----------------

==============================  =====================================================  =========
Field Name                      Description                                            Mandatory
==============================  =====================================================  =========
``Keep Original Filename``      Use Original File name to to store file on receipt,     No
                                use this option only if you are sure partner sends
                                unique names.
``Command on Message Send``     OS Command executed after successful message send,     No
                                replacements are ``$filename``, ``$sender``,
                                ``$receiver``, ``$messageid`` and any message header
                                such as ``$Subject``
``Command on Message Receipt``  OS Command executed after successful message receipt,  No
                                replacements are ``$filename``, ``$fullfilename``,
                                ``$sender``, ``$receiver``, ``$messageid`` and any
                                message header such as ``$Subject``.
==============================  =====================================================  =========

