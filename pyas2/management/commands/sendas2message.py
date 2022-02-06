import logging
import os

from django.core.management.base import BaseCommand
from django.core.management.base import CommandError
from django.core.files.storage import default_storage
from pyas2lib import Message as AS2Message

from pyas2.models import Message
from pyas2.models import Organization
from pyas2.models import Partner

logger = logging.getLogger("pyas2")


class Command(BaseCommand):
    """Command to send an AS2 message."""

    help = "Send an as2 message to your trading partner"
    args = "<organization_as2name partner_as2name path_to_payload>"

    def add_arguments(self, parser):
        parser.add_argument("org_as2name", type=str)
        parser.add_argument("partner_as2name", type=str)
        parser.add_argument("path_to_payload", type=str)

        parser.add_argument(
            "--delete",
            action="store_true",
            dest="delete",
            default=False,
            help="Delete source file after processing",
        )

    def handle(self, *args, **options):

        # Check if organization and partner exists
        try:
            org = Organization.objects.get(as2_name=options["org_as2name"])
        except Organization.DoesNotExist as e:
            raise CommandError(
                f'Organization "{options["org_as2name"]}" does not exist'
            ) from e
        try:
            partner = Partner.objects.get(as2_name=options["partner_as2name"])
        except Partner.DoesNotExist as e:
            raise CommandError(
                f'Partner "{options["partner_as2name"]}" does not exist'
            ) from e

        # Check if file exists
        if not default_storage.exists(options["path_to_payload"]):
            raise CommandError(
                f'Payload at location "{options["path_to_payload"]}" does not exist.'
            )

        # Build and send the AS2 message
        original_filename = os.path.basename(options["path_to_payload"])
        with default_storage.open(options["path_to_payload"], "rb") as in_file:
            payload = in_file.read()
            as2message = AS2Message(sender=org.as2org, receiver=partner.as2partner)
            as2message.build(
                payload,
                filename=original_filename,
                subject=partner.subject,
                content_type=partner.content_type,
                disposition_notification_to=org.email_address or "no-reply@pyas2.com",
            )
        message, _ = Message.objects.create_from_as2message(
            as2message=as2message,
            payload=payload,
            filename=original_filename,
            direction="OUT",
            status="P",
        )
        message.send_message(as2message.headers, as2message.content)

        # Delete original file if option is set
        if options["delete"]:
            default_storage.delete(options["path_to_payload"])
