import os
from datetime import timedelta
from email.parser import BytesHeaderParser

import requests
from django.core.management.base import BaseCommand
from django.utils import timezone
from pyas2lib import Message as AS2Message

from pyas2 import settings
from pyas2.models import Message, Mdn


class Command(BaseCommand):
    """Command to manage the django pyas2 server."""

    help = (
        "Command to manage the as2 server, includes options to cleanup, "
        "handle async mdns and message retries"
    )

    def add_arguments(self, parser):

        parser.add_argument(
            "--clean",
            action="store_true",
            dest="clean",
            default=False,
            help="Cleans up all the old messages and archived files.",
        )

        parser.add_argument(
            "--retry",
            action="store_true",
            dest="retry",
            default=False,
            help="Retrying all failed outbound communications.",
        )

        parser.add_argument(
            "--async-mdns",
            action="store_true",
            dest="async_mdns",
            default=False,
            help="Handle sending and receiving of Asynchronous MDNs.",
        )

    def retry(self, retry_msg):
        """Retry sending the message to the partner."""
        # Increase the retry count
        if not retry_msg.retries:
            retry_msg.retries = 1
        else:
            retry_msg.retries += 1

        # if max retries has exceeded then mark message status as error
        if retry_msg.retries > settings.MAX_RETRIES:
            if retry_msg.status == "P":
                retry_msg.detailed_status = (
                    "Failed to receive asynchronous MDN within the threshold limit."
                )
            elif retry_msg.status == "R":
                retry_msg.detailed_status = "Retry count exceeded the limit."

            retry_msg.status = "E"
            retry_msg.save()
            return

        self.stdout.write("Retry send the message with ID %s" % retry_msg.message_id)

        # Build and resend the AS2 message
        as2message = AS2Message(
            sender=retry_msg.organization.as2org,
            receiver=retry_msg.partner.as2partner,
        )
        as2message.build(
            retry_msg.payload.read(),
            filename=os.path.basename(retry_msg.payload.name),
            subject=retry_msg.partner.subject,
            content_type=retry_msg.partner.content_type,
        )
        retry_msg.send_message(as2message.headers, as2message.content)

    def handle(self, *args, **options):

        if options["retry"]:
            self.stdout.write("Retrying all failed outbound messages")
            # Get the list of all messages with status retry
            failed_msgs = Message.objects.filter(status="R", direction="OUT")

            for failed_msg in failed_msgs:
                self.retry(failed_msg)

            self.stdout.write("Processed all failed outbound messages")

        if options["async_mdns"]:
            # First part of script sends asynchronous MDNs for inbound messages
            # received from partners fetch all the pending asynchronous
            # MDN objects
            self.stdout.write("Sending all pending asynchronous MDNs")
            in_pending_mdns = Mdn.objects.filter(status="P")

            for pending_mdn in in_pending_mdns:
                # Parse the MDN headers from text
                header_parser = BytesHeaderParser()
                mdn_headers = header_parser.parsebytes(pending_mdn.headers.read())
                try:
                    # Set http basic auth if enabled in the partner profile
                    auth = None
                    if (
                        pending_mdn.message.partner
                        and pending_mdn.message.partner.http_auth
                    ):
                        auth = (
                            pending_mdn.message.partner.http_auth_user,
                            pending_mdn.message.partner.http_auth_pass,
                        )

                    # Post the MDN message to the url provided on the
                    # original as2 message
                    requests.post(
                        pending_mdn.return_url,
                        auth=auth,
                        headers=dict(mdn_headers.items()),
                        data=pending_mdn.payload.read(),
                    )
                    pending_mdn.status = "S"
                except requests.exceptions.RequestException as e:
                    self.stdout.write(
                        'Failed to send MDN "%s", error: %s' % (pending_mdn.mdn_id, e)
                    )
                finally:
                    pending_mdn.save()

            # Second Part checks if MDNs have been received for outbound
            # messages to partners
            self.stdout.write(
                'Checking messages waiting for MDNs for more than "%s" '
                "minutes." % settings.ASYNC_MDN_WAIT
            )

            # Find all messages waiting MDNs for more than the set async m
            # dn wait time
            time_threshold = timezone.now() - timedelta(minutes=settings.ASYNC_MDN_WAIT)
            out_pending_msgs = Message.objects.filter(
                status="P", direction="OUT", timestamp__lt=time_threshold
            )

            # Retry sending the message if not MDN received.
            for pending_msg in out_pending_msgs:
                self.retry(pending_msg)

            self.stdout.write("Successfully processed all pending mdns.")

        if options["clean"]:
            self.stdout.write("Cleanup maintenance process started")
            max_archive_dt = timezone.now() - timedelta(settings.MAX_ARCH_DAYS)
            self.stdout.write(
                "Delete all messages older than %s" % settings.MAX_ARCH_DAYS
            )
            old_message = Message.objects.filter(timestamp__lt=max_archive_dt).order_by(
                "timestamp"
            )

            for message in old_message:
                message.payload.delete()
                message.headers.delete()

                try:
                    message.mdn.payload.delete()
                    message.mdn.headers.delete()
                    message.mdn.delete()
                except Mdn.DoesNotExist:
                    pass
                message.delete()
            self.stdout.write("Cleanup maintenance process completed")
