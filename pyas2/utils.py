# -*- coding: utf-8 -*-
import logging
import os
import shlex
import subprocess
from string import Template

logger = logging.getLogger("pyas2")


def _run_command(template_str, variables):
    """Tokenize the admin's command template and execute it without a shell.

    The template is parsed once via shlex.split, then each token is run through
    Template.safe_substitute. This means substituted values land inside a single
    argv entry and cannot be parsed as shell syntax — protecting against injection
    from partner-supplied AS2 values (message ID, headers, filename).
    """
    tokens = shlex.split(template_str)
    args = [Template(tok).safe_substitute(variables) for tok in tokens]
    if not args:
        return
    subprocess.run(args, shell=False, check=False)


def run_post_send(message):
    """Execute command after successful send, can be used to notify
    successful sends"""

    command = message.partner.cmd_send
    if command:
        logger.debug(f"Execute post successful send command {command}")
        variables = {
            "filename": os.path.basename(message.payload.name),
            "sender": message.organization.as2_name,
            "receiver": message.partner.as2_name,
            "messageid": message.message_id,
        }
        variables.update(message.as2message.headers)
        _run_command(command, variables)


def run_post_receive(message, full_filename):
    """Execute command after successful receive, can be used to call the
    edi program for further processing"""

    command = message.partner.cmd_receive
    if command:
        logger.debug(f"Execute post successful receive command {command}")
        variables = {
            "filename": os.path.basename(full_filename),
            "fullfilename": full_filename,
            "sender": message.partner.as2_name,
            "receiver": message.organization.as2_name,
            "messageid": message.message_id,
        }
        variables.update(message.as2message.headers)
        _run_command(command, variables)
