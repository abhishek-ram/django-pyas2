Organizations
=============
Organizations in ``django-pyas2`` mean the host of the AS2 server, i.e. it is the sender when sending messages and the
receiver when receiving the messages. Organizations can be managed from the Django Admin.
The admin lists the existing organizations and also you gives the option to create new ones. Each
organization is characterized by the following fields:

=========================  ============================================  =========
Field Name                 Description                                   Mandatory
=========================  ============================================  =========
``Organization Name``      The descriptive name of the organization.     Yes
``As2 Identifier``         The as2 identifies for this organization,     Yes
                           must be a unique value as it identifies
                           the as2 host.
``Email Address``          The email address for the organization.       No
``Encryption Key``         The ``Private Key`` used for decrypting       No
                           incoming messages from trading partners.
``Signature Key``          The ``Private Key`` used to sign outgoing     No
                           messages to trading partners
``Confirmation Message``   Use this field to customize the confirmation  No
                           message sent in MDNs to partners.
=========================  ============================================  =========
