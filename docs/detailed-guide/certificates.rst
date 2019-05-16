Keys & Certificates
===================
The AS2 protocol strongly encourages the use of RSA certificates to sign and encrypt messages for enhanced security.
A signed and encrypted message received from your partner ensures message repudiation and integrity. The RSA
certificate consists of a public key and a private key which are together used for encrypting, decrypting, signing
and verifying messages.


Generating Certificates
-----------------------
When you set up a new AS2 server you will need to generate a Public/Private key pair. The private key will be
added to your server and the public key needs to be shared with your trading partners.

One of the ways of generating a certificate is by using the ``openssl`` command line utility, the following command
needs to be used:

.. code-block:: console

    $ openssl req -x509 -newkey rsa:2048  -sha256 -keyout private.pem -out public.pem -days 365
    Generating a 2048 bit RSA private key
    .....+++
    ................................................................................................+++
    writing new private key to 'private.pem'
    Enter PEM pass phrase:
    Verifying - Enter PEM pass phrase:
    -----
    You are about to be asked to enter information that will be incorporated
    into your certificate request.
    What you are about to enter is what is called a Distinguished Name or a DN.
    There are quite a few fields but you can leave some blank
    For some fields there will be a default value,
    If you enter '.', the field will be left blank.
    -----
    Country Name (2 letter code) [AU]:IN
    State or Province Name (full name) [Some-State]:Karnataka
    Locality Name (eg, city) []:Bangalore
    Organization Name (eg, company) [Internet Widgits Pty Ltd]:Name
    Organizational Unit Name (eg, section) []:AS2
    Common Name (e.g. server FQDN or YOUR name) []:as2id
    Email Address []:
    $ cat public.pem >> private.pem

The above commands will generate a PEM encoded private key called ``private.pem`` and a PEM encoded public key called ``public.pem``.

Private Keys
------------
``Private Keys`` are used for signing outbound messages to your partners and decrypting incoming messages
from your partners. We can manage them in ``django-pyas2`` from the Django Admin. The
admin lists all your private keys and lets you add new ones. Each ``Private Key`` is
characterized by the following fields:

==========================  ==========================================  =========
Field Name                  Description                                 Mandatory
==========================  ==========================================  =========
``Key File``                Select the **PEM** or **DER** encoded       Yes
                            [#f1]_ private key file [#f2]_.
``Private Key Password``    The pass phrase entered at the time of the  Yes
                            certificate generation.
==========================  ==========================================  =========

Public Certificates
-------------------
``Public Certificates`` are used for verifying signatures of inbound messages and encrypting outbound messages to your partners. The public key file will be shared by your partner. We can manage them in ``django-pyas2`` from the Django Admin. The admin screen lists all your public certificates and lets you add new ones. Each ``Public Certificate`` is characterized by the following fields:

==========================  ==========================================  =========
Field Name                                          Description                                 Mandatory
==========================  ==========================================  =========
``Certificate File``        Select the **PEM** or **DER** encoded       Yes
                            [#f1]_ public key file.
``Certificate CA Store``    In case the certificate has been signed by  No
                            an unknown CA then select the CA
                            certificate here.
``Verify Certificate``      Uncheck this option to disable certificate  No
                            verification at the time of signature
                            verification.
==========================  ==========================================  =========

.. rubric:: Footnotes

.. [#f1] ``django-pyas2`` supports only PEM/DER encoded certificates.
.. [#f2] The private key file must contain **both the private and public** parts of the RSA certificate.
