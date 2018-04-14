# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from pyas2lib import MDN as AS2MDN
from string import Template
import requests
import logging
import os
import time

logger = logging.getLogger('pyas2')


def store_file(target_dir, filename, content, archive=False):
    """ Function to store content to a file in target dir"""

    # Add date sub directory to target folder when archiving
    if archive:
        target_dir = os.path.join(target_dir, time.strftime('%Y%m%d'))

    # Create the target folder if not exists
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)

    # if file already exists then change filename
    if os.path.isfile(os.path.join(target_dir, filename)):
        filename = os.path.splitext(filename)[0] + time.strftime('_%H%M%S') + \
                   os.path.splitext(filename)[1]

    # write file to folder and return the path
    full_filename = os.path.join(target_dir, filename)
    with open(full_filename, 'wb') as tf:
        tf.write(content)
    return full_filename


def send_message(message, payload):
    """ Sends the AS2 message to the partner. Takes the message and payload as
     arguments and posts the as2 message to the partner."""

    try:
        # Set up the http auth if specified in the partner profile
        auth = None
        if message.partner.http_auth:
            auth = (message.partner.http_auth_user,
                    message.partner.http_auth_pass)

        # Send the AS2 message to the partner
        try:
            response = requests.post(
                message.partner.target_url, auth=auth,
                headers=message.as2message.headers, data=payload)
            response.raise_for_status()

        except Exception, e:
            message.status = 'R'
            message.detailed_status = \
                'Failure during transmission of message to partner ' \
                'with error "%s".\n\nTo retry transmission run the ' \
                'management command "retryfailedas2comms".' % e
            return

        # Process the MDN based on the partner profile settings
        if message.partner.mdn:
            if message.partner.mdn_mode == 'ASYNC':
                message.status = 'P'
                return

            # In case of Synchronous MDN the response content will be the MDN.
            # So process it.  Get the response headers, convert key to lower
            # case for normalization
            mdn_headers = dict(
                (k.lower().replace('_', '-'), response.headers[k])
                for k in response.headers
            )

            # create the mdn content with message-id and content-type header
            # and response content
            mdn_content = b'%s: %s\n' % (
                'message-id', mdn_headers['message-id'])
            mdn_content += b'%s: %s\n\n' % (
                'content-type', mdn_headers['content-type'])
            mdn_content += response.content

            logger.debug('Synchronous MDN for message %s received:'
                         '\n%s' % (message.message_id, mdn_content))

            # Parse the mdn and extract the status
            mdn = AS2MDN()
            _, status, detailed_status = mdn.parse(
                mdn_content, lambda x, y: message.as2message)

            # Update the message status based on MDN data
            if status == 'processed':
                message.status = 'S'
            else:
                message.status = 'E'
                message.detailed_status = \
                    'Partner failed to process MDN: %s' % detailed_status
        else:
            message.status = 'S'
            logger.debug(
                'No MDN needed, File Transferred successfully to the partner')
    finally:
        if message.status == 'S':
            run_post_send(message)
        message.save()


def run_post_send(message):
    """ Execute command after successful send, can be used to notify
    successful sends """

    command = message.partner.cmd_send
    if command:
        logger.debug('Execute post successful send command %s' % command)
        # Create command template and replace variables in the command
        command = Template(command)
        variables = {
            'filename': message.payload.name,
            'sender': message.organization.as2_name,
            'receiver': message.partner.as2_name,
            'messageid': message.message_id
        }
        variables.update(message.as2message.headers)

        # Execute the command
        os.system(command.safe_substitute(variables))


def run_post_receive(message, full_filename):
    """ Execute command after successful receive, can be used to call the
    edi program for further processing"""

    command = message.partner.cmd_receive
    if command:
        logger.debug('Execute post successful receive command %s' % command)

        # Create command template and replace variables in the command
        command = Template(command)
        variables = {
            'filename': message.payload.name,
            'fullfilename': full_filename,
            'sender': message.organization.as2_name,
            'receiver': message.partner.as2_name,
            'messageid': message.message_id
        }
        variables.update(message.as2message.headers)

        # Execute the command
        os.system(command.safe_substitute(variables))
