Configuration
=======================
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
