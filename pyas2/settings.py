# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.conf import settings
import os

APP_SETTINGS = getattr(settings, 'PYAS2', {})

# Get the root directory for saving messages
if APP_SETTINGS.get('DATA_DIR') \
        and os.path.isdir(APP_SETTINGS['DATA_DIR']):
    DATA_DIR = APP_SETTINGS['DATA_DIR']
else:
    DATA_DIR = settings.BASE_DIR

# Set the payload and mdn store directories
PAYLOAD_RECEIVED_STORE = os.path.join(
    DATA_DIR, 'messages', '__store', 'payload', 'received')
PAYLOAD_SENT_STORE = os.path.join(
    DATA_DIR, 'messages', '__store', 'payload', 'sent')
MDN_RECEIVED_STORE = os.path.join(
    DATA_DIR, 'messages', '__store', 'mdn', 'received')
MDN_SENT_STORE = os.path.join(
    DATA_DIR, 'messages', '__store', 'mdn', 'sent')

# Max number of times to retry failed sends
MAX_RETRIES = APP_SETTINGS.get('MAX_RETRIES', 5)

# URL for receiving asynchronous MDN from partners
MDN_URL = APP_SETTINGS.get('MDN_URL', 'http://localhost:8080/pyas2/as2receive')

# Max time to wait for asynchronous MDN in minutes
ASYNC_MDN_WAIT = APP_SETTINGS.get('ASYNC_MDN_WAIT', 30)

# Max number of days worth of messages to be saved in archive
MAX_ARCH_DAYS = APP_SETTINGS.get('MAX_ARCH_DAYS', 30)

