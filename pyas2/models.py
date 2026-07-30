# -*- coding: utf-8 -*-
import logging
import os
import posixpath
import traceback
from email.parser import HeaderParser
from uuid import uuid4

import requests
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext as _

from pyas2lib import (
    Mdn as As2Mdn,
    Message as As2Message,
    Organization as As2Organization,
    Partner as As2Partner,
)
from pyas2lib.utils import extract_certificate_info

from pyas2 import settings
from pyas2.utils import run_post_send

logger = logging.getLogger("pyas2")


class PrivateKey(models.Model):
    """Model for storing an Organizations Private Key."""

    name = models.CharField(max_length=255)
    key = models.BinaryField()
    key_pass = models.CharField(max_length=100, verbose_name="Private Key Password")
    valid_from = models.DateTimeField(null=True, blank=True)
    valid_to = models.DateTimeField(null=True, blank=True)
    serial_number = models.CharField(max_length=64, null=True, blank=True)

    def save(self, *args, **kwargs):
        cert_info = extract_certificate_info(self.key)
        self.valid_from = cert_info["valid_from"]
        self.valid_to = cert_info["valid_to"]
        if not cert_info["serial"] is None:
            self.serial_number = cert_info["serial"].__str__()
        super().save(*args, **kwargs)

    def __str__(self):
        return str(self.name)


def order_certificates(certificates, at_time=None):
    """Order certificates by how likely they are to be the one currently in use.

    Certificates that are within their validity period at ``at_time`` come first,
    the most recently issued one leading. Certificates that are expired or not
    yet valid follow, the one expiring last leading, so that a partner is still
    reachable when none of its certificates are valid.
    """
    at_time = at_time or timezone.now()

    unique = []
    for certificate in certificates:
        if certificate is not None and certificate not in unique:
            unique.append(certificate)

    valid = [cert for cert in unique if cert.is_valid(at_time)]
    invalid = [cert for cert in unique if not cert.is_valid(at_time)]

    valid.sort(
        key=lambda cert: (cert.valid_from is not None, cert.valid_from), reverse=True
    )
    invalid.sort(
        key=lambda cert: (cert.valid_to is not None, cert.valid_to), reverse=True
    )

    return valid + invalid


def select_certificate(certificates, at_time=None):
    """Return the certificate to be used at ``at_time`` or None if there is none."""
    ordered = order_certificates(certificates, at_time=at_time)
    return ordered[0] if ordered else None


class PublicCertificate(models.Model):
    """Model for storing a Partners Public Certificate."""

    name = models.CharField(max_length=255)
    certificate = models.BinaryField()
    certificate_ca = models.BinaryField(
        verbose_name=_("Local CA Store"), null=True, blank=True
    )
    verify_cert = models.BooleanField(
        verbose_name=_("Verify Certificate"),
        default=True,
        help_text=_("Uncheck this option to disable certificate verification."),
    )
    valid_from = models.DateTimeField(null=True, blank=True)
    valid_to = models.DateTimeField(null=True, blank=True)
    serial_number = models.CharField(max_length=64, null=True, blank=True)

    def save(self, *args, **kwargs):
        cert_info = extract_certificate_info(self.certificate)
        self.valid_from = cert_info["valid_from"]
        self.valid_to = cert_info["valid_to"]
        if not cert_info["serial"] is None:
            self.serial_number = cert_info["serial"].__str__()
        super().save(*args, **kwargs)

    def is_valid(self, at_time=None):
        """Check if the certificate is within its validity period at ``at_time``."""
        at_time = at_time or timezone.now()
        if self.valid_from and at_time < self.valid_from:
            return False
        if self.valid_to and at_time > self.valid_to:
            return False
        return True

    def __str__(self):
        return str(self.name)


class Organization(models.Model):
    """Model for storing an AS2 Organization."""

    name = models.CharField(verbose_name=_("Organization Name"), max_length=100)
    as2_name = models.CharField(
        verbose_name=_("AS2 Identifier"), max_length=100, primary_key=True
    )
    email_address = models.EmailField(
        null=True,
        blank=True,
        help_text=_(
            "This email will be used for the Disposition-Notification-To "
            "header. If left blank, header defaults to: no-reply@pyas2.com"
        ),
    )
    encryption_key = models.ForeignKey(
        PrivateKey, null=True, blank=True, on_delete=models.SET_NULL
    )
    signature_key = models.ForeignKey(
        PrivateKey,
        related_name="org_s",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    confirmation_message = models.TextField(
        verbose_name=_("Confirmation Message"),
        null=True,
        blank=True,
        help_text=_(
            "Use this field to send a customized message in the "
            "MDN Confirmations for this Organization"
        ),
    )

    @property
    def as2org(self):
        """Returns an object of pyas2lib's Organization class"""
        params = {"as2_name": self.as2_name, "mdn_url": settings.MDN_URL}
        if self.signature_key:
            params["sign_key"] = bytes(self.signature_key.key)
            params["sign_key_pass"] = self.signature_key.key_pass

        if self.encryption_key:
            params["decrypt_key"] = bytes(self.encryption_key.key)
            params["decrypt_key_pass"] = self.encryption_key.key_pass

        if self.confirmation_message:
            params["mdn_confirm_text"] = self.confirmation_message

        return As2Organization(**params)

    def __str__(self):
        return str(self.name)


class Partner(models.Model):
    """Model for storing an AS2 Partner."""

    CONTENT_TYPE_CHOICES = (
        ("application/EDI-X12", "application/EDI-X12"),
        ("application/EDIFACT", "application/EDIFACT"),
        ("application/edi-consent", "application/edi-consent"),
        ("application/XML", "application/XML"),
        ("application/octet-stream", "binary"),
    )
    ENCRYPT_ALG_CHOICES = (
        ("tripledes_192_cbc", "3DES"),
        ("rc2_128_cbc", "RC2-128"),
        ("rc4_128_cbc", "RC4-128"),
        ("aes_128_cbc", "AES-128"),
        ("aes_192_cbc", "AES-192"),
        ("aes_256_cbc", "AES-256"),
    )
    SIGN_ALG_CHOICES = (
        ("sha1", "SHA-1"),
        ("sha224", "SHA-224"),
        ("sha256", "SHA-256"),
        ("sha384", "SHA-384"),
        ("sha512", "SHA-512"),
    )
    MDN_TYPE_CHOICES = (
        ("SYNC", "Synchronous"),
        ("ASYNC", "Asynchronous"),
    )

    name = models.CharField(verbose_name=_("Partner Name"), max_length=100)
    as2_name = models.CharField(
        verbose_name=_("AS2 Identifier"), max_length=100, primary_key=True
    )
    email_address = models.EmailField(null=True, blank=True)

    http_auth = models.BooleanField(
        verbose_name=_("Enable Authentication"), default=False
    )
    http_auth_user = models.CharField(max_length=100, null=True, blank=True)
    http_auth_pass = models.CharField(max_length=100, null=True, blank=True)
    https_verify_ssl = models.BooleanField(
        verbose_name=_("Verify SSL Certificate"),
        default=True,
        help_text=_(
            "Uncheck this option to disable SSL certificate verification to HTTPS."
        ),
    )

    target_url = models.URLField()
    subject = models.CharField(
        max_length=255, default=_("EDI Message sent using pyas2")
    )
    content_type = models.CharField(
        max_length=100, choices=CONTENT_TYPE_CHOICES, default="application/edi-consent"
    )

    compress = models.BooleanField(verbose_name=_("Compress Message"), default=False)
    encryption = models.CharField(
        max_length=20,
        verbose_name=_("Encrypt Message"),
        choices=ENCRYPT_ALG_CHOICES,
        null=True,
        blank=True,
    )
    encryption_cert = models.ForeignKey(
        PublicCertificate, null=True, blank=True, on_delete=models.SET_NULL
    )
    encryption_cert_rollover = models.ManyToManyField(
        PublicCertificate,
        related_name="partner_e_rollover",
        blank=True,
        verbose_name=_("Encryption Certificate Rollover List"),
        help_text=_(
            "Additional encryption certificates for this partner, the one that is "
            "currently valid is used for encrypting outbound messages."
        ),
    )
    signature = models.CharField(
        max_length=20,
        verbose_name=_("Sign Message"),
        choices=SIGN_ALG_CHOICES,
        null=True,
        blank=True,
    )
    signature_cert = models.ForeignKey(
        PublicCertificate,
        related_name="partner_s",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    signature_cert_rollover = models.ManyToManyField(
        PublicCertificate,
        related_name="partner_s_rollover",
        blank=True,
        verbose_name=_("Signature Certificate Rollover List"),
        help_text=_(
            "Additional signature certificates for this partner, inbound messages "
            "and MDNs are verified against each of them."
        ),
    )

    mdn = models.BooleanField(verbose_name=_("Request MDN"), default=False)
    mdn_mode = models.CharField(
        max_length=20, choices=MDN_TYPE_CHOICES, null=True, blank=True
    )
    mdn_sign = models.CharField(
        max_length=20,
        verbose_name=_("Request Signed MDN"),
        choices=SIGN_ALG_CHOICES,
        null=True,
        blank=True,
    )

    confirmation_message = models.TextField(
        verbose_name=_("Confirmation Message"),
        null=True,
        blank=True,
        help_text=_(
            "Use this field to send a customized message in the MDN "
            "Confirmations for this Partner"
        ),
    )

    keep_filename = models.BooleanField(
        verbose_name=_("Keep Original Filename"),
        default=False,
        help_text=_(
            "Use Original Filename to to store file on receipt, use this option "
            "only if you are sure partner sends unique names"
        ),
    )
    cmd_send = models.TextField(
        verbose_name=_("Command on Message Send"),
        null=True,
        blank=True,
        help_text=_(
            "Command executed after successful message send, replacements are "
            "$filename, $sender, $receiver, $messageid and any message header "
            "such as $Subject"
        ),
    )
    cmd_receive = models.TextField(
        verbose_name=_("Command on Message Receipt"),
        null=True,
        blank=True,
        help_text=_(
            "Command executed after successful message receipt, replacements "
            "are $filename, $fullfilename, $sender, $receiver, $messageid and "
            "any message header such as $Subject"
        ),
    )

    @property
    def encryption_cert_candidates(self):
        """Return the encryption certificates of this partner, preferred one first."""
        return order_certificates(
            [self.encryption_cert, *self.encryption_cert_rollover.all()]
        )

    @property
    def signature_cert_candidates(self):
        """Return the signature certificates of this partner, preferred one first."""
        return order_certificates(
            [self.signature_cert, *self.signature_cert_rollover.all()]
        )

    @property
    def active_encryption_cert(self):
        """Return the encryption certificate to be used for outbound messages."""
        return select_certificate(self.encryption_cert_candidates)

    @property
    def active_signature_cert(self):
        """Return the signature certificate to be used for verifying signatures."""
        return select_certificate(self.signature_cert_candidates)

    def build_as2partner(self, signature_cert=None, encryption_cert=None):
        """Returns an object of pyas2lib's Partner class.

        The certificates to be used can be given explicitly, by default the
        currently valid ones from the rollover lists are used.
        """
        params = {
            "as2_name": self.as2_name,
            "compress": self.compress,
            "sign": bool(self.signature),
            "digest_alg": self.signature,
            "encrypt": bool(self.encryption),
            "enc_alg": self.encryption,
            "mdn_mode": self.mdn_mode,
            "mdn_digest_alg": self.mdn_sign,
        }

        signature_cert = signature_cert or self.active_signature_cert
        encryption_cert = encryption_cert or self.active_encryption_cert

        if signature_cert:
            params["verify_cert"] = bytes(signature_cert.certificate)
            if signature_cert.certificate_ca:
                params["verify_cert_ca"] = bytes(signature_cert.certificate_ca)
            params["validate_certs"] = signature_cert.verify_cert

        if encryption_cert:
            params["encrypt_cert"] = bytes(encryption_cert.certificate)
            if encryption_cert.certificate_ca:
                params["encrypt_cert_ca"] = bytes(encryption_cert.certificate_ca)
            params["validate_certs"] = encryption_cert.verify_cert

        if self.confirmation_message:
            params["mdn_confirm_text"] = self.confirmation_message

        return As2Partner(**params)

    @property
    def as2partner(self):
        """Returns an object of pyas2lib's Partner class"""
        return self.build_as2partner()

    def __str__(self):
        return str(self.name)


def parse_as2mdn(raw_content, message):
    """Parse a received MDN and verify it against the partner's certificates.

    A partner that is rolling over its certificate could have signed the MDN with
    any certificate from its rollover list, so verification is attempted with each
    of them until one succeeds.

    :return: A three element tuple containing the pyas2lib Mdn object, the status
        and the detailed status of the MDN.
    """
    result = None
    for signature_cert in message.partner.signature_cert_candidates or [None]:
        as2mdn = As2Mdn()
        status, detailed_status = as2mdn.parse(
            raw_content,
            lambda x, y, cert=signature_cert: message.build_as2message(
                signature_cert=cert
            ),
        )
        # Only a failure to verify the MDN is worth a retry with another certificate
        if status != "failed/Failure" or detailed_status == "mdn-not-found":
            return as2mdn, status, detailed_status

        # Keep the first failure, it is the one for the certificate in use
        if result is None:
            result = (as2mdn, status, detailed_status)

    return result


class MessageManager(models.Manager):
    """Custom model manager for the AS2 Message model."""

    def create_from_as2message(
        self,
        as2message,
        payload,
        direction,
        status,
        filename=None,
        detailed_status=None,
    ):
        """Create the Message from the pyas2lib's Message object."""

        if direction == "IN":
            organization = as2message.receiver.as2_name if as2message.receiver else None
            partner = as2message.sender.as2_name if as2message.sender else None
        else:
            partner = as2message.receiver.as2_name if as2message.receiver else None
            organization = as2message.sender.as2_name if as2message.sender else None

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
                detailed_status=detailed_status,
            ),
        )

        # Save the headers and payload to store
        if not filename:
            filename = f"{uuid4()}.msg"
        message.headers.save(
            name=f"{filename}.header", content=ContentFile(as2message.headers_str)
        )
        message.payload.save(name=filename, content=ContentFile(payload))

        # Save the payload to the inbox folder
        full_filename = None
        if direction == "IN" and status == "S":
            if settings.DATA_DIR:
                dirname = os.path.join(
                    settings.DATA_DIR, "messages", organization, "inbox", partner
                )
            else:
                dirname = os.path.join("messages", organization, "inbox", partner)
            if not message.partner.keep_filename or not filename:
                filename = f"{message.message_id}.msg"
            full_filename = default_storage.generate_filename(
                posixpath.join(dirname, filename)
            )
            default_storage.save(name=full_filename, content=ContentFile(payload))

        return message, full_filename


def get_message_store(instance, filename):
    """Return the path for storing the message payload."""
    current_date = timezone.now().strftime("%Y%m%d")
    if instance.direction == "OUT":
        target_dir = os.path.join(
            "messages", "__store", "payload", "sent", current_date
        )
    else:
        target_dir = os.path.join(
            "messages", "__store", "payload", "received", current_date
        )
    return "{0}/{1}".format(target_dir, filename)


class Message(models.Model):
    """Model for storing an AS2 Message between an Organization and a Partner."""

    DIRECTION_CHOICES = (
        ("IN", _("Inbound")),
        ("OUT", _("Outbound")),
    )
    STATUS_CHOICES = (
        ("S", _("Success")),
        ("E", _("Error")),
        ("W", _("Warning")),
        ("P", _("Pending")),
        ("R", _("Retry")),
    )
    MODE_CHOICES = (
        ("SYNC", _("Synchronous")),
        ("ASYNC", _("Asynchronous")),
    )

    message_id = models.CharField(max_length=255)
    direction = models.CharField(max_length=5, choices=DIRECTION_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True)

    status = models.CharField(max_length=2, choices=STATUS_CHOICES)
    detailed_status = models.TextField(null=True)

    organization = models.ForeignKey(Organization, null=True, on_delete=models.SET_NULL)
    partner = models.ForeignKey(Partner, null=True, on_delete=models.SET_NULL)

    headers = models.FileField(upload_to=get_message_store, null=True, blank=True)
    payload = models.FileField(
        upload_to=get_message_store, null=True, blank=True, max_length=4096
    )

    compressed = models.BooleanField(default=False)
    encrypted = models.BooleanField(default=False)
    signed = models.BooleanField(default=False)

    mdn_mode = models.CharField(max_length=5, choices=MODE_CHOICES, null=True)
    mic = models.CharField(max_length=100, null=True)

    retries = models.IntegerField(null=True)

    objects = MessageManager()

    class Meta:
        """Define additional options for the Message model."""

        unique_together = ("message_id", "partner")

    def build_as2message(self, signature_cert=None):
        """Returns an object of pyas2lib's Message class.

        The partner signature certificate to be used can be given explicitly,
        by default the currently valid one is used.
        """
        as2partner = self.partner.build_as2partner(signature_cert=signature_cert)
        if self.direction == "IN":
            as2m = As2Message(sender=as2partner, receiver=self.organization.as2org)
        else:
            as2m = As2Message(sender=self.organization.as2org, receiver=as2partner)

        as2m.message_id = self.message_id
        as2m.mic = self.mic

        return as2m

    @property
    def as2message(self):
        """Returns an object of pyas2lib's Message class"""
        return self.build_as2message()

    @property
    def status_icon(self):
        """Return the icon for message status"""
        if self.status == "S":
            return "admin/img/icon-yes.svg"
        elif self.status == "E":
            return "admin/img/icon-no.svg"
        elif self.status in ["W", "P", "R"]:
            return "admin/img/icon-alert.svg"
        else:
            return "admin/img/icon-unknown.svg"

    def send_message(self, header, payload):
        """Send the message to the partner"""
        logger.info(
            f'Sending message {self.message_id} from organization "{self.organization}" '
            f'to partner "{self.partner}".'
        )

        # Set up the http auth if specified in the partner profile
        auth = None
        if self.partner.http_auth:
            auth = (self.partner.http_auth_user, self.partner.http_auth_pass)

        # Send the message to the partner
        try:
            response = requests.post(
                self.partner.target_url,
                auth=auth,
                headers=header,
                data=payload,
                verify=self.partner.https_verify_ssl,
            )
            response.raise_for_status()
        except requests.exceptions.RequestException:
            self.status = "R"
            self.detailed_status = (
                f"Failed to send message, error:\n{traceback.format_exc()}"
            )
            self.save()
            return

        # Process the MDN based on the partner profile settings
        if self.partner.mdn:
            if self.partner.mdn_mode == "ASYNC":
                self.status = "P"
            else:
                # Process the synchronous MDN received as response

                # Get the response headers, convert key to lower case
                # for normalization
                mdn_headers = dict(
                    (k.lower().replace("_", "-"), response.headers[k])
                    for k in response.headers
                )

                # create the mdn content with message-id and content-type
                # header and response content
                mdn_content = (
                    f'message-id: {mdn_headers.get("message-id", self.message_id)}\n'
                )
                mdn_content += f'content-type: {mdn_headers["content-type"]}\n\n'
                mdn_content = mdn_content.encode("utf-8") + response.content

                # Parse the as2 mdn received
                logger.debug(
                    f"Received MDN response for message {self.message_id} "
                    f"with content: {mdn_content}"
                )
                as2mdn, mdn_status, mdn_detailed_status = parse_as2mdn(
                    mdn_content, self
                )

                # Update the message status and return the response
                if mdn_status == "processed":
                    self.status = "S"
                    run_post_send(self)
                else:
                    self.status = "E"
                    self.detailed_status = (
                        f"Partner failed to process message: {mdn_detailed_status}"
                    )
                if mdn_detailed_status != "mdn-not-found":
                    Mdn.objects.create_from_as2mdn(
                        as2mdn=as2mdn, message=self, status="R"
                    )
        else:
            # No MDN requested mark message as success and run command
            self.status = "S"
            run_post_send(self)

        self.save()

    def __str__(self):
        return str(self.message_id)


class MdnManager(models.Manager):
    """Custom model manager for the AS2 MDN model."""

    def create_from_as2mdn(self, as2mdn, message, status, return_url=None):
        """Create the MDN from the pyas2lib's MDN object"""
        signed = bool(as2mdn.digest_alg)

        # Check for message-id in MDN.
        if as2mdn.message_id is None:
            message_id = as2mdn.orig_message_id
            logger.warning(
                f"Received MDN response without a message-id. Using original "
                f"message-id as ID instead: {message_id}"
            )
        else:
            message_id = as2mdn.message_id

        mdn, _ = self.update_or_create(
            message=message,
            defaults=dict(
                mdn_id=message_id,
                status=status,
                signed=signed,
                return_url=return_url,
            ),
        )
        filename = f"{uuid4()}.mdn"
        mdn.headers.save(
            name=f"{filename}.header", content=ContentFile(as2mdn.headers_str)
        )
        mdn.payload.save(filename, content=ContentFile(as2mdn.content))
        return mdn


def get_mdn_store(instance, filename):
    """Return the path for storing the MDN payload."""
    current_date = timezone.now().strftime("%Y%m%d")
    if instance.status == "S":
        target_dir = os.path.join("messages", "__store", "mdn", "sent", current_date)
    else:
        target_dir = os.path.join(
            "messages", "__store", "mdn", "received", current_date
        )

    return "{0}/{1}".format(target_dir, filename)


class Mdn(models.Model):
    """Model for storing a MDN for an AS2 Message."""

    STATUS_CHOICES = (
        ("S", _("Sent")),
        ("R", _("Received")),
        ("P", _("Pending")),
    )

    mdn_id = models.CharField(max_length=255)
    message = models.OneToOneField(Message, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=2, choices=STATUS_CHOICES)

    signed = models.BooleanField(default=False)
    return_url = models.URLField(null=True)

    headers = models.FileField(upload_to=get_mdn_store, null=True, blank=True)
    payload = models.FileField(
        upload_to=get_mdn_store, null=True, blank=True, max_length=4096
    )

    objects = MdnManager()

    def __str__(self):
        return str(self.mdn_id)

    def send_async_mdn(self):
        """Send the asynchronous MDN to the partner"""

        # convert the mdn headers to dictionary
        headers = HeaderParser().parsestr(self.headers.read().decode())

        # Send the mdn to the partner
        try:
            response = requests.post(
                self.return_url, headers=dict(headers.items()), data=self.payload.read()
            )
            response.raise_for_status()
        except requests.exceptions.RequestException:
            return

        # Update the status of the MDN
        self.status = "S"
        self.save()
