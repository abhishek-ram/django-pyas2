import glob
import os
from django.core.management import call_command
from django.core.management.base import BaseCommand

from pyas2 import settings
from pyas2.models import Organization
from pyas2.models import Partner


class Command(BaseCommand):
    help = 'Command for sending all pending messages in the outbox folders'

    def handle(self, *args, **options):
        for partner in Partner.objects.all():
            self.stdout.write('Process files in the outbox directory for '
                              'partner "%s".' % partner.as2_name)
            for org in Organization.objects.all():
                outbox_folder = os.path.join(
                    settings.DATA_DIR, 'messages', partner.as2_name,
                    'outbox', org.as2_name)
                if not os.path.isdir(outbox_folder):
                    os.makedirs(outbox_folder)
                for pend_file in glob.glob(outbox_folder + '/*'):
                    self.stdout.write(
                        'Sending file "%s" from organization "%s" to partner '
                        '"%s".' % (pend_file, org.as2_name, partner.as2_name))
                    call_command(
                        'sendas2message', org.as2_name, partner.as2_name,
                        os.path.join(outbox_folder, pend_file), delete=True)
