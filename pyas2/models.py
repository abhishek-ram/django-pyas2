# -*- coding: utf-8 -*-
import os
import requests
import traceback
from django.core.files.base import ContentFile
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from django.utils.translation import ugettext as _
from email.parser import HeaderParser
from pyas2lib import Mdn as As2Mdn
from pyas2lib import Message as As2Message
from pyas2lib import Organization as As2Organization
from pyas2lib import Partner as As2Partner
from uuid import uuid4

from pyas2 import settings
from pyas2.utils import run_post_send
from pyas2.utils import store_file


class PrivateKey(models.Model):
    name = models.CharField(max_length=255)
    key = models.BinaryField()
    key_pass = models.CharField(
        max_length=100, verbose_name='Private Key Password')

    def __str__(self):
        return self.name


class PublicCertificate(models.Model):
    name = models.CharField(max_length=255)
    certificate = models.BinaryField()
    certificate_ca = models.BinaryField(
        verbose_name=_('Local CA Store'), null=True, blank=True)
    verify_cert = models.BooleanField(
        verbose_name=_('Verify Certificate'), default=True,
        help_text=_('Uncheck this option to disable certificate verification.'))

    def __str__(self):
        return self.name


class Organization(models.Model):
    name = models.CharField(
        verbose_name=_('Organization Name'), max_length=100)
    as2_name = models.CharField(
        verbose_name=_('AS2 Identifier'), max_length=100, primary_key=True)
    email_address = models.EmailField(null=True, blank=True)
    encryption_key = models.ForeignKey(
        PrivateKey, null=True, blank=True, on_delete=models.SET_NULL)
    signature_key = models.ForeignKey(
        PrivateKey, related_name='org_s', null=True, blank=True,
        on_delete=models.SET_NULL
    )
    confirmation_message = models.TextField(
        verbose_name=_('Confirmation Message'),
        null=True,
        blank=True,
        help_text=_('Use this field to send a customized message in the '
                    'MDN Confirmations for this Organization')
    )

    @property
    def as2org(self):
        """ Returns an object of pyas2lib's Organization class"""
        params = {
            'as2_name': self.as2_name,
            'mdn_url': settings.MDN_URL
        }
        if self.signature_key:
            params['sign_key'] = bytes(self.signature_key.key)
            params['sign_key_pass'] = self.signature_key.key_pass

        if self.encryption_key:
            params['decrypt_key'] = bytes(self.encryption_key.key)
            params['decrypt_key_pass'] = self.encryption_key.key_pass

        if self.confirmation_message:
            params['mdn_confirm_text'] = self.confirmation_message

        return As2Organization(**params)

    def __str__(self):
        return self.name


class Partner(models.Model):
    CONTENT_TYPE_CHOICES = (
        ('application/EDI-X12', 'application/EDI-X12'),
        ('application/EDIFACT', 'application/EDIFACT'),
        ('application/edi-consent', 'application/edi-consent'),
        ('application/XML', 'application/XML'),
    )
    ENCRYPT_ALG_CHOICES = (
        ('tripledes_192_cbc', '3DES'),
        ('rc2_128_cbc', 'RC2-128'),
        ('rc4_128_cbc', 'RC4-128'),
        ('aes_128_cbc', 'AES-128'),
        ('aes_192_cbc', 'AES-192'),
        ('aes_256_cbc', 'AES-256')
    )
    SIGN_ALG_CHOICES = (
        ('sha1', 'SHA-1'),
        ('sha224', 'SHA-224'),
        ('sha256', 'SHA-256'),
        ('sha384', 'SHA-384'),
        ('sha512', 'SHA-512')
    )
    MDN_TYPE_CHOICES = (
        ('SYNC', 'Synchronous'),
        ('ASYNC', 'Asynchronous'),
    )

    name = models.CharField(
        verbose_name=_('Partner Name'), max_length=100)
    as2_name = models.CharField(
        verbose_name=_('AS2 Identifier'), max_length=100, primary_key=True)
    email_address = models.EmailField(null=True, blank=True)

    http_auth = models.BooleanField(
        verbose_name=_('Enable Authentication'), default=False)
    http_auth_user = models.CharField(max_length=100, null=True, blank=True)
    http_auth_pass = models.CharField(max_length=100, null=True, blank=True)

    target_url = models.URLField()
    subject = models.CharField(
        max_length=255, default=_('EDI Message sent using pyas2'))
    content_type = models.CharField(
        max_length=100, choices=CONTENT_TYPE_CHOICES,
        default='application/edi-consent'
    )

    compress = models.BooleanField(
        verbose_name=_('Compress Message'), default=False)
    encryption = models.CharField(
        max_length=20, verbose_name=_('Encrypt Message'),
        choices=ENCRYPT_ALG_CHOICES, null=True, blank=True)
    encryption_cert = models.ForeignKey(
        PublicCertificate, null=True, blank=True, on_delete=models.SET_NULL)
    signature = models.CharField(
        max_length=20, verbose_name=_('Sign Message'),
        choices=SIGN_ALG_CHOICES, null=True, blank=True)
    signature_cert = models.ForeignKey(
        PublicCertificate, related_name='partner_s', null=True, blank=True,
        on_delete=models.SET_NULL
    )

    mdn = models.BooleanField(verbose_name=_('Request MDN'), default=False)
    mdn_mode = models.CharField(
        max_length=20, choices=MDN_TYPE_CHOICES, null=True, blank=True)
    mdn_sign = models.CharField(
        max_length=20, verbose_name=_('Request Signed MDN'),
        choices=SIGN_ALG_CHOICES, null=True, blank=True)

    confirmation_message = models.TextField(
        verbose_name=_('Confirmation Message'),
        null=True,
        blank=True,
        help_text=_(
            'Use this field to send a customized message in the MDN '
            'Confirmations for this Partner')
    )

    keep_filename = models.BooleanField(
        verbose_name=_('Keep Original Filename'),
        default=False,
        help_text=_(
            'Use Original Filename to to store file on receipt, use this option'
            ' only if you are sure partner sends unique names')
    )
    cmd_send = models.TextField(
        verbose_name=_('Command on Message Send'),
        null=True,
        blank=True,
        help_text=_(
            'Command executed after successful message send, replacements are '
            '$filename, $sender, $recevier, $messageid and any message header '
            'such as $Subject')
    )
    cmd_receive = models.TextField(
        verbose_name=_('Command on Message Receipt'),
        null=True,
        blank=True,
        help_text=_(
            'Command executed after successful message receipt, replacements '
            'are $filename, $fullfilename, $sender, $recevier, $messageid and '
            'any message header such as $Subject')
    )

    @property
    def as2partner(self):
        """ Returns an object of pyas2lib's Partner class"""
        params = {
            'as2_name': self.as2_name,
            'compress': self.compress,
            'sign': True if self.signature else False,
            'digest_alg': self.signature,
            'encrypt': True if self.encryption else False,
            'enc_alg': self.encryption,
            'mdn_mode': self.mdn_mode,
            'mdn_digest_alg': self.mdn_sign
        }

        if self.signature_cert:
            params['verify_cert'] = bytes(self.signature_cert.certificate)
            if self.signature_cert.certificate_ca:
                params['verify_cert_ca'] = bytes(
                    self.signature_cert.certificate_ca)
            params['validate_certs'] = self.signature_cert.verify_cert

        if self.encryption_cert:
            params['encrypt_cert'] = bytes(self.encryption_cert.certificate)
            if self.encryption_cert.certificate_ca:
                params['encrypt_cert_ca'] = bytes(
                    self.encryption_cert.certificate_ca)
            params['validate_certs'] = self.encryption_cert.verify_cert

        if self.confirmation_message:
            params['mdn_confirm_text'] = self.confirmation_message

        return As2Partner(**params)

    def __str__(self):
        return self.name


class MessageManager(models.Manager):

    def create_from_as2message(self, as2message, payload, direction, status,
                               detailed_status=None):
        """Create the Message from the pyas2lib's Message object"""

        if direction == 'IN':
            organization = as2message.receiver.as2_name \
                if as2message.receiver else None
            partner = as2message.sender.as2_name if as2message.sender else None
        else:
            partner = as2message.receiver.as2_name \
                if as2message.receiver else None
            organization = as2message.sender.as2_name \
                if as2message.sender else None

        message, _ = self.update_or_create(
            message_id=as2message.message_id,
            partner_id=partner,
            organization_id=organization,
            defaults=dict(
                direction=direction,
                status=status,
                compressed=as2message.compressed,
                encrypted=as2message.encrypted,
                signed=as2message.signed,
                detailed_status=detailed_status
            )
        )

        # Save the headers and payload to store
        message.headers.save(name='%s.header' % uuid4(),
                             content=ContentFile(as2message.headers_str))
        message.payload.save(name='%s.msg' % uuid4(),
                             content=ContentFile(payload))

        # Save the payload to the inbox folder
        full_fn = None
        if direction == 'IN' and status == 'S':
            folder = os.path.join(
                settings.DATA_DIR, 'messages', organization, 'inbox', partner)
            if message.partner.keep_filename and \
                    as2message.payload.get_filename():
                filename = as2message.payload.get_filename()
            else:
                filename = '%s.msg' % message.message_id
            full_fn = store_file(folder, filename, payload)

        return message, full_fn


def get_message_store(instance, filename):
    current_date = timezone.now().strftime('%Y%m%d')
    if instance.direction == 'OUT':
        target_dir = os.path.join(
            'messages', '__store', 'payload', 'sent', current_date)
    else:
        target_dir = os.path.join(
            'messages', '__store', 'payload', 'received', current_date)
    return '{0}/{1}'.format(target_dir, filename)


class Message(models.Model):
    DIRECTION_CHOICES = (
        ('IN', _('Inbound')),
        ('OUT', _('Outbound')),
    )
    STATUS_CHOICES = (
        ('S', _('Success')),
        ('E', _('Error')),
        ('W', _('Warning')),
        ('P', _('Pending')),
        ('R', _('Retry')),
    )
    MODE_CHOICES = (
        ('SYNC', _('Synchronous')),
        ('ASYNC', _('Asynchronous')),
    )

    message_id = models.CharField(max_length=255)
    direction = models.CharField(max_length=5, choices=DIRECTION_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True)

    status = models.CharField(max_length=2, choices=STATUS_CHOICES)
    detailed_status = models.TextField(null=True)

    organization = models.ForeignKey(
        Organization, null=True, on_delete=models.SET_NULL)
    partner = models.ForeignKey(
        Partner, null=True, on_delete=models.SET_NULL)

    headers = models.FileField(
        upload_to=get_message_store, null=True, blank=True)
    payload = models.FileField(
        upload_to=get_message_store, null=True, blank=True)

    compressed = models.BooleanField(default=False)
    encrypted = models.BooleanField(default=False)
    signed = models.BooleanField(default=False)

    mdn_mode = models.CharField(max_length=5, choices=MODE_CHOICES, null=True)
    mic = models.CharField(max_length=100, null=True)

    retries = models.IntegerField(null=True)

    objects = MessageManager()

    class Meta:
        unique_together = ('message_id', 'partner')

    @property
    def as2message(self):
        """ Returns an object of pyas2lib's Message class"""
        if self.direction == 'IN':
            as2m = As2Message(
                sender=self.partner.as2partner,
                receiver=self.organization.as2org)
        else:
            as2m = As2Message(
                sender=self.organization.as2org,
                receiver=self.partner.as2partner)

        as2m.message_id = self.message_id
        as2m.mic = self.mic

        return as2m

    @property
    def status_icon(self):
        """ Return the icon for message status """
        if self.status == 'S':
            return 'admin/img/icon-yes.svg'
        elif self.status == 'E':
            return 'admin/img/icon-no.svg'
        elif self.status in ['W', 'P']:
            return 'admin/img/icon-clock.sng'
        else:
            return 'admin/img/icon-unknown.sng'

    def send_message(self, header, payload):
        """ Send the message to the partner"""
        # Set up the http auth if specified in the partner profile
        auth = None
        if self.partner.http_auth:
            auth = (self.partner.http_auth_user, self.partner.http_auth_pass)

        # Send the message to the partner
        try:
            response = requests.post(
                self.partner.target_url, auth=auth, headers=header, data=payload)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            self.status = 'R'
            self.detailed_status = \
                'Failed to send message, error:\n%s' % traceback.format_exc()
            self.save()
            return

        # Process the MDN based on the partner profile settings
        if self.partner.mdn:
            if self.partner.mdn_mode == 'ASYNC':
                self.status = 'P'
            else:
                # Process the synchronous MDN received as response

                # Get the response headers, convert key to lower case
                # for normalization
                mdn_headers = dict(
                    (k.lower().replace('_', '-'), response.headers[k])
                    for k in response.headers
                )

                # create the mdn content with message-id and content-type
                # header and response content
                mdn_content = '%s: %s\n' % (
                    'message-id', mdn_headers.get('message-id', self.message_id))
                mdn_content += '%s: %s\n\n' % (
                    'content-type', mdn_headers['content-type'])
                mdn_content = mdn_content.encode('utf-8') + response.content

                # Parse the as2 mdn received
                as2mdn = As2Mdn()
                status, detailed_status = as2mdn.parse(
                    mdn_content, lambda x, y: self.as2message)

                # Update the message status and return the response
                if status == 'processed':
                    self.status = 'S'
                    run_post_send(self)
                else:
                    self.status = 'E'
                    self.detailed_status = \
                        'Partner failed to process message: %s' % detailed_status
                Mdn.objects.create_from_as2mdn(
                    as2mdn=as2mdn, message=self, status='R')
        else:
            # No MDN requested mark message as success and run command
            self.status = 'S'
            run_post_send(self)

        self.save()

    def __str__(self):
        return self.message_id


class MdnManager(models.Manager):

    def create_from_as2mdn(self, as2mdn, message, status, return_url=None):
        """Create the MDN from the pyas2lib's MDN object"""
        signed = True if as2mdn.digest_alg else False
        mdn, _ = self.update_or_create(
            message=message,
            defaults=dict(
                mdn_id=as2mdn.message_id,
                status=status,
                signed=signed,
                return_url=return_url
            )
        )
        mdn.headers.save(name='%s.header' % uuid4(),
                         content=ContentFile(as2mdn.headers_str))
        mdn.payload.save(name='%s.mdn' % uuid4(),
                         content=ContentFile(as2mdn.content))
        return mdn


def get_mdn_store(instance, filename):
    current_date = timezone.now().strftime('%Y%m%d')
    if instance.status == 'S':
        target_dir = os.path.join(
            'messages', '__store', 'mdn', 'sent', current_date)
    else:
        target_dir = os.path.join(
            'messages', '__store', 'mdn', 'received', current_date)

    return '{0}/{1}'.format(target_dir, filename)


class Mdn(models.Model):
    STATUS_CHOICES = (
        ('S', _('Sent')),
        ('R', _('Received')),
        ('P', _('Pending')),
    )

    mdn_id = models.CharField(max_length=255)
    message = models.OneToOneField(Message, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=2, choices=STATUS_CHOICES)

    signed = models.BooleanField(default=False)
    return_url = models.URLField(null=True)

    headers = models.FileField(
        upload_to=get_mdn_store, null=True, blank=True)
    payload = models.FileField(
        upload_to=get_mdn_store, null=True, blank=True)

    objects = MdnManager()

    def __str__(self):
        return self.mdn_id

    def send_async_mdn(self):
        """ Send the asynchronous MDN to the partner"""

        # convert the mdn headers to dictionary
        headers = HeaderParser().parsestr(
            self.headers.read().decode())

        # Send the mdn to the partner
        try:
            response = requests.post(
                self.return_url,
                headers=dict(headers.items()),
                data=self.payload.read())
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            return

        # Update the status of the MDN
        self.status = 'S'
        self.save()
