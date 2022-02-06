import os
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.core.files.storage import default_storage

from pyas2 import settings
from pyas2.models import Organization
from pyas2.models import Partner


class Command(BaseCommand):
    """Command to send all pending messages."""

    help = "Command for sending all pending messages in the outbox folders"

    def handle(self, *args, **options):
        for partner in Partner.objects.all():
            self.stdout.write(
                "Process files in the outbox directory for "
                'partner "%s".' % partner.as2_name
            )
            for org in Organization.objects.all():
                if settings.DATA_DIR:
                    outbox_folder = os.path.join(
                        settings.DATA_DIR,
                        "messages",
                        partner.as2_name,
                        "outbox",
                        org.as2_name,
                    )
                else:
                    outbox_folder = os.path.join(
                        "messages", partner.as2_name, "outbox", org.as2_name
                    )

                # Check of the directory exists and if not create it
                try:
                    _, pending_files = default_storage.listdir(outbox_folder)
                except FileNotFoundError:
                    pending_files = []
                    os.makedirs(default_storage.path(outbox_folder))

                # For each file found call send message to send it to the server
                pending_files = filter(lambda x: x != ".", pending_files)
                for pending_file in pending_files:
                    pending_file = os.path.join(outbox_folder, pending_file)
                    self.stdout.write(
                        'Sending file "%s" from organization "%s" to partner '
                        '"%s".' % (pending_file, org.as2_name, partner.as2_name)
                    )
                    call_command(
                        "sendas2message",
                        org.as2_name,
                        partner.as2_name,
                        pending_file,
                        delete=True,
                    )
