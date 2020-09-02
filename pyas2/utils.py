# -*- coding: utf-8 -*-
import logging
import os
from string import Template

logger = logging.getLogger("pyas2")


class pyas2Utils:
    '''
    replace built-in function with
    - cust_run_post_send
    - cust_run_post_receive
    '''

    cust_run_post_send = None
    cust_run_post_receive = None

    @classmethod
    def get_msg_vars(cls, message):
        variables = {
            "filename": os.path.basename(message.payload.name),
            "sender": message.organization.as2_name,
            "receiver": message.partner.as2_name,
            "messageid": message.message_id,
        }
        variables.update(message.as2message.headers)
        return variables

    @classmethod
    def run_post_send(cls, message):
        """ Execute command after successful send, can be used to notify
        successful sends """
        command = message.partner.cmd_send
        if cls.cust_run_post_send or command:
            if cls.cust_run_post_send:
                cls.cust_run_post_send(**cls.get_msg_vars(message))
            else:
                logger.debug("Execute post successful send command %s" % command)
                # Create command template and replace variables in the command
                command = Template(command)
                # Execute the command
                os.system(command.safe_substitute(cls.get_msg_vars(message)))

    @classmethod
    def run_post_receive(cls, message, full_filename):
        """ Execute command after successful receive, can be used to call the
        edi program for further processing"""

        command = message.partner.cmd_receive
        if cls.cust_run_post_receive or command:
            logger.debug("Execute post successful receive command %s" % command)
            if cls.cust_run_post_receive:
                cls.cust_run_post_receive(**cls.get_msg_vars(message))
            else:
                # Create command template and replace variables in the command
                command = Template(command)
                # Execute the command
                os.system(command.safe_substitute(cls.get_msg_vars(message)))
