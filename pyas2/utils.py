# -*- coding: utf-8 -*-
import logging
import os
import time
from string import Template

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


def run_post_send(message):
    """ Execute command after successful send, can be used to notify
    successful sends """

    command = message.partner.cmd_send
    if command:
        logger.debug('Execute post successful send command %s' % command)
        # Create command template and replace variables in the command
        command = Template(command)
        variables = {
            'filename': os.path.basename(message.payload.name),
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
            'filename': os.path.basename(full_filename),
            'fullfilename': full_filename,
            'sender': message.organization.as2_name,
            'receiver': message.partner.as2_name,
            'messageid': message.message_id
        }
        variables.update(message.as2message.headers)

        # Execute the command
        os.system(command.safe_substitute(variables))
