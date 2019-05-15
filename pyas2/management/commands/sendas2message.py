import logging
import os
import sys
from django.core.management.base import BaseCommand
from django.core.management.base import CommandError
from pyas2lib import Message as AS2Message

from pyas2.models import Message
from pyas2.models import Organization
from pyas2.models import Partner

logger = logging.getLogger('pyas2')


class Command(BaseCommand):
    help = 'Send an as2 message to your trading partner'
    args = '<organization_as2name partner_as2name path_to_payload>'

    def add_arguments(self, parser):
        parser.add_argument('org_as2name', type=str)
        parser.add_argument('partner_as2name', type=str)
        parser.add_argument('path_to_payload', type=str)

        parser.add_argument(
            '--delete',
            action='store_true',
            dest='delete',
            default=False,
            help='Delete source file after processing'
        )

    def handle(self, *args, **options):

        # Check if organization and partner exists
        try:
            org = Organization.objects.get(
                as2_name=options['org_as2name'])
        except Organization.DoesNotExist:
            raise CommandError(
                'Organization "%s" does not exist' % options['org_as2name'])
        try:
            partner = Partner.objects.get(as2_name=options['partner_as2name'])
        except Partner.DoesNotExist:
            raise CommandError(
                'Partner "%s" does not exist' % options['partner_as2name'])

        # Check if file exists and we have the right permissions
        if not os.path.isfile(options['path_to_payload']):
            raise CommandError('Payload at location "%s" does not '
                               'exist.' % options['path_to_payload'])

        if options['delete'] and not os.access(options['path_to_payload'], os.W_OK):
            raise CommandError('Insufficient file permission for '
                               'payload %s.' % options['path_to_payload'])

        # Build and send the AS2 message
        with open(options['path_to_payload'], 'rb') as in_file:
            payload = in_file.read()
            as2message = AS2Message(
                sender=org.as2org, receiver=partner.as2partner)
            as2message.build(
                payload,
                filename=os.path.basename(options['path_to_payload']),
                subject=partner.subject,
                content_type=partner.content_type
            )
        message, _ = Message.objects.create_from_as2message(
            as2message=as2message,
            payload=payload,
            direction='OUT',
            status='P'
        )
        message.send_message(as2message.headers, as2message.content)

        # Delete original file if option is set
        if options['delete']:
            os.remove(options['path_to_payload'])
