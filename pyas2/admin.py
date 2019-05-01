# -*- coding: utf-8 -*-
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
    form = PrivateKeyForm
    list_display = ('name', 'download_key',)

    def download_key(self, obj):
        download_url = reverse_lazy('download-file',
                                    args=['private_key', obj.id])
        return format_html('<a href="{}" class="button">Click to Download</a>',
                           download_url)

    download_key.allow_tags = True
    download_key.short_description = "Key File"


@admin.register(PublicCertificate)
class PublicCertificateAdmin(admin.ModelAdmin):
    form = PublicCertificateForm
    list_display = ('name', 'download_cert',)

    def download_cert(self, obj):
        download_url = reverse_lazy('download-file',
                                    args=['public_cert', obj.id])
        return format_html('<a href="{}" class="button">Click to Download</a>',
                           download_url)

    download_cert.allow_tags = True
    download_cert.short_description = "Certificate File"


@admin.register(Partner)
class PartnerAdmin(admin.ModelAdmin):
    form = PartnerForm
    list_display = ['name', 'as2_name', 'target_url', 'encryption',
                    'encryption_cert', 'signature', 'signature_cert',
                    'mdn', 'mdn_mode']
    list_filter = ('name', 'as2_name')
    fieldsets = (
        (None, {
            'fields': (
                'name', 'as2_name', 'email_address', 'target_url',
                'subject', 'content_type', 'confirmation_message')
        }),
        ('Http Authentication', {
            'classes': ('collapse', 'wide'),
            'fields': ('http_auth', 'http_auth_user', 'http_auth_pass')
        }),
        ('Security Settings', {
            'classes': ('collapse', 'wide'),
            'fields': ('compress', 'encryption', 'encryption_cert', 'signature',
                       'signature_cert')
        }),
        ('MDN Settings', {
            'classes': ('collapse', 'wide'),
            'fields': ('mdn', 'mdn_mode', 'mdn_sign')
        }),
        ('Advanced Settings', {
            'classes': ('collapse', 'wide'),
            'fields': ('keep_filename', 'cmd_send', 'cmd_receive')
        }),
    )
    actions = ['send_message']

    def send_message(self, request, queryset):
        partner = queryset.first()
        return HttpResponseRedirect(
            reverse_lazy('as2-send') + '?partner_id=%s' % partner.as2_name)

    send_message.short_description = "Send a message to the selected partner"


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ['name', 'as2_name']
    list_filter = ('name', 'as2_name')


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):

    def has_add_permission(self, request):
        return False

    search_fields = ('message_id',)

    list_filter = ('direction', 'status', 'organization__as2_name',
                   'partner__as2_name')

    list_display = ['message_id', 'timestamp', 'status', 'direction',
                    'organization', 'partner', 'compressed', 'encrypted',
                    'signed', 'mdn_url']

    def mdn_url(self, obj):
        if hasattr(obj, 'mdn'):
            view_url = reverse_lazy(
                'admin:%s_%s_change' % (Mdn._meta.app_label,
                                        Mdn._meta.model_name),
                args=[obj.mdn.id])
            return format_html('<a href="{}" class="button">View MDN</a>',
                               view_url)

    mdn_url.allow_tags = True
    mdn_url.short_description = "MDN"


@admin.register(Mdn)
class MdnAdmin(admin.ModelAdmin):

    def has_add_permission(self, request):
        return False

    search_fields = ('mdn_id', 'message_id',)
    list_display = ('mdn_id', 'message', 'timestamp', 'status')
    list_filter = ('status',)
