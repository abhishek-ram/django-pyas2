# -*- coding: utf-8 -*-
import os

from django.contrib import admin
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.utils.html import format_html

from pyas2.models import Mdn
from pyas2.models import Message
from pyas2.models import Organization
from pyas2.models import Partner
from pyas2.models import PrivateKey
from pyas2.models import PublicCertificate
from pyas2.forms import PartnerForm
from pyas2.forms import PublicCertificateForm
from pyas2.forms import PrivateKeyForm


@admin.register(PrivateKey)
class PrivateKeyAdmin(admin.ModelAdmin):
    """Admin class for the PrivateKey model."""

    form = PrivateKeyForm
    list_display = ("name", "valid_from", "valid_to", "serial_number", "download_key")

    @staticmethod
    def download_key(obj):
        """Return the url to download the private key."""
        download_url = reverse_lazy("download-file", args=["private_key", obj.id])
        return format_html(
            '<a href="{}" class="button">Click to Download</a>', download_url
        )

    download_key.allow_tags = True
    download_key.short_description = "Key File"


@admin.register(PublicCertificate)
class PublicCertificateAdmin(admin.ModelAdmin):
    """Admin class for the PublicCertificate model."""

    form = PublicCertificateForm
    list_display = ("name", "valid_from", "valid_to", "serial_number", "download_cert")

    @staticmethod
    def download_cert(obj):
        """Return the url to download the public cert."""
        download_url = reverse_lazy("download-file", args=["public_cert", obj.id])
        return format_html(
            '<a href="{}" class="button">Click to Download</a>', download_url
        )

    download_cert.allow_tags = True
    download_cert.short_description = "Certificate File"


@admin.register(Partner)
class PartnerAdmin(admin.ModelAdmin):
    """Admin class for the Partner model."""

    form = PartnerForm
    list_display = [
        "name",
        "as2_name",
        "target_url",
        "encryption",
        "encryption_cert",
        "signature",
        "signature_cert",
        "mdn",
        "mdn_mode",
        "canonicalize_as_binary",
    ]
    list_filter = ("name", "as2_name")
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "name",
                    "as2_name",
                    "email_address",
                    "target_url",
                    "subject",
                    "content_type",
                    "confirmation_message",
                )
            },
        ),
        (
            "Http Authentication",
            {
                "classes": ("collapse", "wide"),
                "fields": (
                    "http_auth",
                    "http_auth_user",
                    "http_auth_pass",
                    "https_verify_ssl",
                ),
            },
        ),
        (
            "Security Settings",
            {
                "classes": ("collapse", "wide"),
                "fields": (
                    "compress",
                    "encryption",
                    "encryption_cert",
                    "signature",
                    "signature_cert",
                ),
            },
        ),
        (
            "MDN Settings",
            {
                "classes": ("collapse", "wide"),
                "fields": ("mdn", "mdn_mode", "mdn_sign"),
            },
        ),
        (
            "Advanced Settings",
            {
                "classes": ("collapse", "wide"),
                "fields": (
                    "canonicalize_as_binary",
                    "keep_filename",
                    "cmd_send",
                    "cmd_receive",
                ),
            },
        ),
    )
    actions = ["send_message"]

    def send_message(self, request, queryset):  # pylint: disable=W0613,R0201
        """Send the message to the first partner chosen by the user."""
        partner = queryset.first()
        return HttpResponseRedirect(
            reverse_lazy("as2-send") + "?partner_id=%s" % partner.as2_name
        )

    send_message.short_description = "Send a message to the selected partner"


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    """Admin class for the Organization model."""

    list_display = ["name", "as2_name"]
    list_filter = ("name", "as2_name")


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    """Admin class for the Message model."""

    search_fields = ("message_id", "payload")

    list_filter = ("direction", "status", "organization__as2_name", "partner__as2_name")

    list_display = [
        "message_id",
        "timestamp",
        "status",
        "direction",
        "organization",
        "partner",
        "compressed",
        "encrypted",
        "signed",
        "download_file",
        "mdn_url",
    ]

    @staticmethod
    def mdn_url(obj):
        """Return the URL to the related MDN if present for the message."""
        # pylint: disable=W0212

        if hasattr(obj, "mdn"):
            view_url = reverse_lazy(
                f"admin:{Mdn._meta.app_label}_{Mdn._meta.model_name}_change",
                args=[obj.mdn.id],
            )
            return format_html('<a href="{}" class="">{}</a>', view_url, obj.mdn.mdn_id)
        return None

    mdn_url.allow_tags = True
    mdn_url.short_description = "MDN"

    @staticmethod
    def download_file(obj):
        """Return the URL to download the message payload."""
        if obj.payload:
            view_url = reverse_lazy("download-file", args=["message_payload", obj.id])
            return format_html(
                '<a href="{}">{}</a>', view_url, os.path.basename(obj.payload.name)
            )
        return None

    download_file.allow_tags = True
    download_file.short_description = "Payload"

    def has_add_permission(self, request):
        return False


@admin.register(Mdn)
class MdnAdmin(admin.ModelAdmin):
    """Admin class for the Mdn model."""

    search_fields = (
        "mdn_id",
        "message__message_id",
    )
    list_display = ("mdn_id", "message", "timestamp", "status")
    list_filter = ("status",)

    def has_add_permission(self, request):
        return False
