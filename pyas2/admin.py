# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.contrib import admin
from .models import Partner, Organization, PublicCertificate, \
    PrivateKey, Message
from .forms import PrivateKeyForm, PartnerForm, PublicCertificateForm


@admin.register(PrivateKey)
class PrivateKeyAdmin(admin.ModelAdmin):
    form = PrivateKeyForm


@admin.register(PublicCertificate)
class PublicCertificateAdmin(admin.ModelAdmin):
    form = PublicCertificateForm


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


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ['name', 'as2_name']
    list_filter = ('name', 'as2_name')


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['message_id', 'timestamp', 'status', 'direction',
                    'organization', 'partner', 'compressed', 'encrypted',
                    'signed', 'mdn']
