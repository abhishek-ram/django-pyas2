import os

from django.conf import settings

APP_SETTINGS = getattr(settings, "PYAS2", {})

# Get the root directory for saving messages
DATA_DIR = None
if APP_SETTINGS.get("DATA_DIR") and os.path.isdir(APP_SETTINGS["DATA_DIR"]):
    DATA_DIR = APP_SETTINGS["DATA_DIR"]

# Max number of times to retry failed sends
MAX_RETRIES = APP_SETTINGS.get("MAX_RETRIES", 5)

# URL for receiving asynchronous MDN from partners
MDN_URL = APP_SETTINGS.get("MDN_URL", "http://localhost:8080/pyas2/as2receive")

# Max time to wait for asynchronous MDN in minutes
ASYNC_MDN_WAIT = APP_SETTINGS.get("ASYNC_MDN_WAIT", 30)

# Max number of days worth of messages to be saved in archive
MAX_ARCH_DAYS = APP_SETTINGS.get("MAX_ARCH_DAYS", 30)

# Send positive MDN when duplicate message is received
ERROR_ON_DUPLICATE = APP_SETTINGS.get("ERROR_ON_DUPLICATE", True)