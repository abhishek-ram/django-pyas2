# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.contrib import admin
from django.urls import reverse_lazy
from django.http import HttpResponseRedirect
from .models import Partner, Organization, PublicCertificate, \
    PrivateKey, Message, Mdn
from .forms import PrivateKeyForm, PartnerForm, PublicCertificateForm


@admin.register(PrivateKey)
class PrivateKeyAdmin(admin.ModelAdmin):
    form = PrivateKeyForm
    list_display = ('name', 'download_key',)

    def download_key(self, obj):
        return '<a href="%s" class="button">Click to Download</a>' % \
               reverse_lazy('download-file', args=['private_key', obj.id])

    download_key.allow_tags = True
    download_key.short_description = "Key File"


@admin.register(PublicCertificate)
class PublicCertificateAdmin(admin.ModelAdmin):
    form = PublicCertificateForm
    list_display = ('name', 'download_cert',)

    def download_cert(self, obj):
        return '<a href="%s" class="button">Click to Download</a>' % \
               reverse_lazy('download-file', args=['public_cert', obj.id])

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
            return '<a href="%s" class="button">View MDN</a>' % \
                   reverse_lazy('admin:%s_%s_change' % (Mdn._meta.app_label,
                                                        Mdn._meta.model_name),
                                args=[obj.mdn.id])

    mdn_url.allow_tags = True
    mdn_url.short_description = "MDN"


@admin.register(Mdn)
class MdnAdmin(admin.ModelAdmin):

    def has_add_permission(self, request):
        return False

    search_fields = ('mdn_id', 'message_id',)
    list_display = ('mdn_id', 'message', 'timestamp', 'status')
    list_filter = ('status',)
