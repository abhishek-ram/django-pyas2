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

from pyas2.utils import pyas2Utils


@admin.register(PrivateKey)
class PrivateKeyAdmin(admin.ModelAdmin):
    form = PrivateKeyForm
    list_display = ("name", "valid_from", "valid_to", "serial_number", "download_key")

    def download_key(self, obj):
        download_url = reverse_lazy("download-file", args=["private_key", obj.id])
        return format_html(
            '<a href="{}" class="button">Click to Download</a>', download_url
        )

    download_key.allow_tags = True
    download_key.short_description = "Key File"


@admin.register(PublicCertificate)
class PublicCertificateAdmin(admin.ModelAdmin):
    form = PublicCertificateForm
    list_display = ("name", "valid_from", "valid_to", "serial_number", "download_cert")

    def download_cert(self, obj):
        download_url = reverse_lazy("download-file", args=["public_cert", obj.id])
        return format_html(
            '<a href="{}" class="button">Click to Download</a>', download_url
        )

    download_cert.allow_tags = True
    download_cert.short_description = "Certificate File"


@admin.register(Partner)
class PartnerAdmin(admin.ModelAdmin):
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
                "fields": ("keep_filename", "cmd_send", "cmd_receive"),
            },
        ),
    )
    actions = ["send_message"]

    def send_message(self, request, queryset):
        partner = queryset.first()
        return HttpResponseRedirect(
            reverse_lazy("as2-send") + "?partner_id=%s" % partner.as2_name
        )

    def get_readonly_fields(self, request, queryset):
        readOnlyFields = []
        if pyas2Utils.cust_run_post_send:
            readOnlyFields.append("cmd_send")
        if pyas2Utils.cust_run_post_receive:
            readOnlyFields.append("cmd_receive")

        if readOnlyFields:
            a = super().get_fieldsets(request, queryset)
            a[4][1]['description'] = "<b>Note: fields <i>%s</i> shown as readonly because customized function was linked</b>" % (", ".join(readOnlyFields))
        return readOnlyFields

    send_message.short_description = "Send a message to the selected partner"


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ["name", "as2_name"]
    list_filter = ("name", "as2_name")


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

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

    def mdn_url(self, obj):
        if hasattr(obj, "mdn"):
            view_url = reverse_lazy(
                f"admin:{Mdn._meta.app_label}_{Mdn._meta.model_name}_change",
                args=[obj.mdn.id],
            )
            return format_html('<a href="{}" class="">{}</a>', view_url, obj.mdn.mdn_id)

    mdn_url.allow_tags = True
    mdn_url.short_description = "MDN"

    def download_file(self, obj):
        if obj.payload:
            view_url = reverse_lazy("download-file", args=["message_payload", obj.id])
            return format_html(
                '<a href="{}">{}</a>', view_url, os.path.basename(obj.payload.name)
            )

    download_file.allow_tags = True
    download_file.short_description = "Payload"


@admin.register(Mdn)
class MdnAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    search_fields = (
        "mdn_id",
        "message_id",
    )
    list_display = ("mdn_id", "message", "timestamp", "status")
    list_filter = ("status",)
