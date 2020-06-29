# -*- coding: utf-8 -*-
import logging
import os
from string import Template
from django.core.mail import mail_managers
from django.utils.timezone import localtime

logger = logging.getLogger("pyas2")


def run_post_send(message):
    """ Execute command after successful send, can be used to notify
    successful sends """

    command = message.partner.cmd_send
    if command:
        logger.debug("Execute post successful send command %s" % command)
        # Create command template and replace variables in the command
        command = Template(command)
        variables = {
            "filename": os.path.basename(message.payload.name),
            "sender": message.organization.as2_name,
            "receiver": message.partner.as2_name,
            "messageid": message.message_id,
        }
        variables.update(message.as2message.headers)

        # Execute the command
        os.system(command.safe_substitute(variables))


def run_post_receive(message, full_filename):
    """ Execute command after successful receive, can be used to call the
    edi program for further processing"""

    command = message.partner.cmd_receive
    if command:
        logger.debug("Execute post successful receive command %s" % command)

        # Create command template and replace variables in the command
        command = Template(command)
        variables = {
            "filename": os.path.basename(full_filename),
            "fullfilename": full_filename,
            "sender": message.organization.as2_name,
            "receiver": message.partner.as2_name,
            "messageid": message.message_id,
        }
        variables.update(message.as2message.headers)

        # Execute the command
        os.system(command.safe_substitute(variables))


def notify_error(message):
    """ Notify via email about errors with transmission of messages """

    try:
        email_subject = 'pyAS2 Error'
        email_body = 'Error: Message transmission failed!' \
                      '\n\nMessage ID: %(id)s' \
                      '\nDate/Time: %(time)s' \
                      '\nOrganization: %(org)s' \
                      '\nPartner: %(prt)s' \
                      '\nDirection: %(dir)s' \
                      '\nDetailed Status: %(stat)s' \
                      % {'id': message.message_id,
                         'time': localtime(message.timestamp).strftime('%Y-%m-%d %H:%M:%S'),
                         'org': message.organization,
                         'prt': message.partner,
                         'dir': message.get_direction_display(),
                         'stat': message.detailed_status}
        mail_managers(
            email_subject,
            email_body,
            fail_silently=False,
        )
    except Exception as msg:
        logger.warning("Error sending email notification: %(msg)s", {'msg': msg})
