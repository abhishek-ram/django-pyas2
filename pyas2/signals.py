from django.dispatch import Signal

post_receive = Signal(providing_args=["message", "full_filename"])
post_send = Signal(providing_args=["message"])
