# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.db import models
from django.core.files.base import ContentFile
from django.utils.translation import ugettext as _
from django.db.models.signals import post_save
from django.dispatch import receiver
from pyas2lib import Partner as AS2Partner, Organization as AS2Organization, \
    Message as AS2Message
from . import settings
from .utils import store_file
# import os


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
        PrivateKey, null=True, blank=True)
    signature_key = models.ForeignKey(
        PrivateKey, related_name='org_s', null=True, blank=True)
    confirmation_message = models.CharField(
        verbose_name=_('Confirmation Message'),
        max_length=300,
        null=True,
        blank=True,
        help_text=_('Use this field to send a customized message in the '
                    'MDN Confirmations for this Organization')
    )

    @property
    def as2org(self):
        """ Returns an object of pyas2lib's Organization class"""
        params = {
            'as2_id': self.as2_name,
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

        return AS2Organization(**params)

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
    )
    SIGN_ALG_CHOICES = (
        ('sha1', 'SHA-1'),
        ('sha256', 'SHA-256'),
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
        PublicCertificate, null=True, blank=True)
    signature = models.CharField(
        max_length=20, verbose_name=_('Sign Message'),
        choices=SIGN_ALG_CHOICES, null=True, blank=True)
    signature_cert = models.ForeignKey(
        PublicCertificate, related_name='partner_s', null=True, blank=True)

    mdn = models.BooleanField(verbose_name=_('Request MDN'), default=False)
    mdn_mode = models.CharField(
        max_length=20, choices=MDN_TYPE_CHOICES, null=True, blank=True)
    mdn_sign = models.CharField(
        max_length=20, verbose_name=_('Request Signed MDN'),
        choices=SIGN_ALG_CHOICES, null=True, blank=True)

    confirmation_message = models.CharField(
        verbose_name=_('Confirmation Message'),
        max_length=300,
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
            'as2_id': self.as2_name,
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

        return AS2Partner(**params)

    def __str__(self):
        return self.name


class MessageManager(models.Manager):

    def create_from_as2message(self, as2message, direction, status):
        """Create the Message from the pyas2lib's Message object"""

        message = self.create(
            message_id=as2message.message_id,
            direction=direction,
            status=status,
            organization_id=as2message.receiver.as2_id,
            partner_id=as2message.sender.as2_id,
            compressed=as2message.compressed,
            encrypted=as2message.encrypted,
            signed=as2message.signed,
        )

        message.headers.save(name='%s.header' % message.message_id,
                             content=ContentFile(as2message.headers_str))
        message.payload.save(name='%s.msg' % message.message_id,
                             content=ContentFile(as2message.content))
        return message


def get_message_store(instance, filename):
    target_dir = settings.PAYLOAD_SENT_STORE if instance.direction == 'OUT' \
        else settings.PAYLOAD_RECEIVED_STORE
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

    message_id = models.CharField(max_length=100)
    direction = models.CharField(max_length=5, choices=DIRECTION_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True)

    status = models.CharField(max_length=2, choices=STATUS_CHOICES)
    detailed_status = models.TextField(null=True)

    organization = models.ForeignKey(Organization, null=True)
    partner = models.ForeignKey(Partner, null=True)

    headers = models.FileField(
        upload_to=get_message_store, max_length=500, null=True, blank=True)
    payload = models.FileField(
        upload_to=get_message_store, max_length=500, null=True, blank=True)

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
            as2m = AS2Message(
                sender=self.partner.as2partner,
                receiver=self.organization.as2org)
        else:
            as2m = AS2Message(
                sender=self.organization.as2org,
                receiver=self.partner.as2partner)

        as2m.message_id = self.message_id
        as2m.mic = self.mic

        return as2m

    def __str__(self):
        return self.message_id


class MdnManager(models.Manager):

    def create_from_as2mdn(self, as2mdn, message, status, return_url=None):
        """Create the MDN from the pyas2lib's MDN object"""
        signed = True if as2mdn.digest_alg else False
        mdn = self.create(
            mdn_id=as2mdn.message_id, message=message, status=status,
            signed=signed,
            return_url=return_url)
        mdn.headers.save(name='%s.header' % mdn.mdn_id,
                         content=ContentFile(as2mdn.headers_str))
        mdn.payload.save(name='%s.mdn' % mdn.mdn_id,
                         content=ContentFile(as2mdn.payload))
        return mdn


def get_mdn_store(instance, filename):
    target_dir = settings.MDN_SENT_STORE if instance.status == 'S' \
        else settings.MDN_RECEIVED_STORE
    return '{0}/{1}'.format(target_dir, filename)


class MDN(models.Model):
    STATUS_CHOICES = (
        ('S', _('Sent')),
        ('R', _('Received')),
        ('P', _('Pending')),
    )

    mdn_id = models.CharField(max_length=100, primary_key=True)
    message = models.OneToOneField(Message, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=2, choices=STATUS_CHOICES)

    signed = models.BooleanField(default=False)
    return_url = models.URLField(null=True)

    headers = models.FileField(
        upload_to=get_mdn_store, max_length=500, null=True, blank=True)
    payload = models.FileField(
        upload_to=get_mdn_store, max_length=500, null=True, blank=True)

    objects = MdnManager()

    def __str__(self):
        return self.mdn_id


@receiver(post_save, sender=Organization)
def check_org_dirs(sender, instance, created, **kwargs):
    pass


@receiver(post_save, sender=Partner)
def check_partner_dirs(sender, instance, created, **kwargs):
    pass
