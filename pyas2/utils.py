# -*- coding: utf-8 -*-
import logging
import os
from string import Template

logger = logging.getLogger("pyas2")

# The disposition modifiers set by pyas2lib when the certificate used for verifying
# the signature of a message is either invalid or not the one that signed it.
SIGNATURE_ERROR_MODIFIERS = ("authentication-failed", "invalid-certificate")


def is_signature_error(exception):
    """Check if the exception was caused by the signature verification certificate."""
    return getattr(exception, "disposition_modifier", None) in SIGNATURE_ERROR_MODIFIERS


def run_post_send(message):
    """Execute command after successful send, can be used to notify
    successful sends"""

    command = message.partner.cmd_send
    if command:
        logger.debug(f"Execute post successful send command {command}")
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
    """Execute command after successful receive, can be used to call the
    edi program for further processing"""

    command = message.partner.cmd_receive
    if command:
        logger.debug(f"Execute post successful receive command {command}")

        # Create command template and replace variables in the command
        command = Template(command)
        variables = {
            "filename": os.path.basename(full_filename),
            "fullfilename": full_filename,
            "sender": message.partner.as2_name,
            "receiver": message.organization.as2_name,
            "messageid": message.message_id,
        }
        variables.update(message.as2message.headers)

        # Execute the command
        os.system(command.safe_substitute(variables))
