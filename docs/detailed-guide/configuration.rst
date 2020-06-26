Configuration
=============

The global settings for ``pyAS2`` are kept in a single configuration dictionary named ``PYAS2`` in
your `project's settings.py <https://docs.djangoproject.com/en/stable/ref/settings/>`_ module. Below is a sample configuration:

.. code-block:: python

    PYAS2 = {
        'DATA_DIR' : '/path_to_datadir/data',
        'MAX_RETRIES': 5,
        'MDN_URL' : 'https://192.168.1.115:8888/pyas2/as2receive',
        'ASYNC_MDN_WAIT' : 30,
        'MAX_ARCH_DAYS' : 30,
    }

The available settings along with their usage is described below:

+------------------------+----------------------------+------------------------------------------------+
| Settings Name          | Default Value              | Usage                                          |
+========================+============================+================================================+
| DATA_DIR               | MEDIA_ROOT or BASE_DIR     | Full path to the base directory for storing    |
|                        |                            | messages                                       |
+------------------------+----------------------------+------------------------------------------------+
| MAX_RETRIES            | 10                         | Maximum number of retries for failed outgoing  |
|                        |                            | messages                                       |
+------------------------+----------------------------+------------------------------------------------+
| MDN_URL                | ``None``                   | Return URL for receiving asynchronous MDNs from|
|                        |                            | partners.                                      |
+------------------------+----------------------------+------------------------------------------------+
| ASYNC_MDN_WAIT         | 30                         | Number of minutes to wait for asynchronous MDNs|
|                        |                            | after which message will be marked as failed.  |
+------------------------+----------------------------+------------------------------------------------+
| MAX_ARCH_DAYS          | 30                         | Number of days files and messages are kept in  |
|                        |                            | storage.                                       |
+------------------------+----------------------------+------------------------------------------------+


The Data Directory
------------------

The ``Data Directory`` is a file system directory that stores sent and received files.
The location of this directory is set to either the ``MEDIA_ROOT`` or the project base folder by default.
We can also change this directory by updating the ``DATA_DIR`` setting.
The structure of the directory is below:

.. code-block:: console

    {DATA DIRECTORY}
    └── messages
        ├── __store
        │   ├── mdn
        │   │   ├── received
        │   │   └── sent
        │   │       ├── 20150908
        │   │       │   ├── 20150908115337.7244.44635@Abhisheks-MacBook-Air.local.mdn
        │   │       │   └── 20150908121942.7244.71894@Abhisheks-MacBook-Air.local.mdn
        │   │       └── 20150913
        │   │           ├── 20150913071324.20065.47671@Abhisheks-MacBook-Air.local.mdn
        │   │           └── 20150913083125.20403.32480@Abhisheks-MacBook-Air.local.mdn
        │   └── payload
        │       ├── received
        │       │   ├── 20150908
        │       │   │   ├── 20150908115458.7255.98107@Abhisheks-MacBook-Air.local
        │       │   │   └── 20150908121933.7343.83150@Abhisheks-MacBook-Air.local
        │       │   └── 20150913
        │       │       ├── 20150913071323.20074.48016@Abhisheks-MacBook-Air.local
        │       │       └── 20150913083125.20475.14667@Abhisheks-MacBook-Air.local
        │       └── sent
        ├── p1as2
        │   └── outbox
        │       └── p2as2
        └── p2as2
            └── inbox
                └── p1as2
                    ├── 20150908115458.7255.98107@Abhisheks-MacBook-Air.local.msg
                    └── 20150913083125.20475.14667@Abhisheks-MacBook-Air.local.msg

inbox
-----
The inbox directory stores files received from your partners. The path of this directory is ``{DATA DIRECTORY}/messages/{ORG AS2 ID}/inbox/{PARTNER AS2 ID}``.
We need to take this location into account when integrating ``django-pyas2`` with other applications.

outbox
------
The outbox directory works in conjunction with the ``sendas2bulk`` process. The bulk process looks in all of the outbox
directories and will trigger a transfer for each file found. The path of this  directory is ``{DATA DIRECTORY}/messages/{PARTNER AS2 ID}/outbox/{ORG AS2 ID}``.

__store
------
The __store directory contains the payloads and MDNs. The payload and MDN files are stored in the sent and received sub-directories respectively, and are further seperated by additional sub-directories for each day, named as YYYYMMDD.

