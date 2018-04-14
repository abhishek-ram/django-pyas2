# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.shortcuts import HttpResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.utils.translation import ugettext as _
from django.views.decorators.csrf import csrf_exempt
from pyas2lib import Message as AS2Message, MDN as AS2MDN
from pyas2lib.exceptions import *
from .models import Message, MDN, Partner, Organization
from .utils import run_post_receive, run_post_send
import logging

logger = logging.getLogger('pyas2')


@method_decorator(csrf_exempt, name='dispatch')
class AS2Receive(View):
    """
       Class receives AS2 requests from partners.
       Checks whether its an AS2 message or an MDN and acts accordingly.
    """

    @staticmethod
    def find_message(message_id, partner_id):
        """ Find the org using the message  and return its pyas2 version"""
        message = Message.objects.filter(
            message_id=message_id, partner_id=partner_id).first()
        if message:
            return message.as2message

    @staticmethod
    def find_organization(org_id):
        """ Find the org using the As2 Id and return its pyas2 version"""
        org = Organization.objects.filter(as2_name=org_id).first()
        if org:
            return org.as2org

    @staticmethod
    def find_partner(partner_id):
        """ Find the partner using the As2 Id and return its pyas2 version"""
        partner = Partner.objects.filter(as2_name=partner_id).first()
        if partner:
            return partner.as2partner

    @csrf_exempt
    def post(self, request, *args, **kwargs):

        # extract the  headers from the http request
        as2headers = ''
        for key in request.META:
            if key.startswith('HTTP') or key.startswith('CONTENT'):
                as2headers += '%s: %s\n' % (
                    key.replace("HTTP_", "").replace("_", "-").lower(),
                    request.META[key]
                )

        # build the body along with the headers
        request_body = as2headers.encode() + b'\r\n' + request.body
        logger.debug(
            b'Received an HTTP POST from {} with payload :\n{}'.format(
                request.META['REMOTE_ADDR'],  request_body)
        )

        # First try to see if this is an MDN
        try:
            logger.debug('Check to see if payload is an Asynchronous MDN.')
            as2mdn = AS2MDN()

            # Parse the mdn and get the message status
            as2message, status, detailed_status = as2mdn.parse(
                request_body, self.find_message)
            message = Message.objects.get(message_id=as2message.message_id)
            logger.info(
                'Asynchronous MDN received for AS2 message {} to organization '
                '{} from partner {}'.format(as2mdn.message_id,
                                            message.organization.as2_name,
                                            message.partner.as2_name))

            # Update the message status and return the response
            if status == 'processed':
                message.status = 'S'
                run_post_send(message)
            else:
                message.status = 'E'
                message.detailed_status = \
                    'Partner failed to process MDN: %s' % detailed_status
            MDN.objects.create_from_as2mdn(
                as2mdn=as2mdn, message=message, status='R')
            return HttpResponse(_('AS2 ASYNC MDN has been received'))

        except MDNNotFound:
            logger.debug('Payload is not an MDN parse it as an AS2 Message')
            as2message = AS2Message()
            status, exception, as2mdn = as2message.parse(
                request_body, self.find_organization, self.find_partner)

            logger.info(
                'Received an AS2 message with id {} for organization {} from '
                'partner {}'.format(as2message.message_id,
                                    as2message.receiver.as2_id,
                                    as2message.sender.as2_id))

            # Create the Message and MDN objects
            message = Message.objects.create_from_as2message(
                as2message=as2message,
                direction='IN',
                status='S' if status == 'processed' else 'E')

            # return the mdn in case of sync else return text message
            if as2mdn.mdn_mode == 'SYNC':
                message.mdn = MDN.objects.create_from_as2mdn(
                    as2mdn=as2mdn, message=message, status='S')
                response = HttpResponse(as2mdn.content)
                for key, value in as2mdn.headers.items():
                    response[key] = value
                return response
            else:
                MDN.objects.create_from_as2mdn(
                    as2mdn=as2mdn, message=message, status='P',
                    return_url=as2mdn.mdn_url)
                return HttpResponse(_('AS2 message has been received'))

    def get(self, request, *args, **kwargs):
        """"""
        return HttpResponse(
            _('To submit an AS2 message, you must POST the message to this URL')
        )

    def options(self, request, *args, **kwargs):
        response = HttpResponse()
        response['allow'] = ','.join(['POST', 'GET'])
        return response
