import os
from django import forms
from django.utils.translation import ugettext as _
from pyas2lib import Organization as As2Organization
from pyas2lib import Partner as As2Partner
from pyas2lib.exceptions import AS2Exception

from pyas2.models import Organization
from pyas2.models import Partner
from pyas2.models import PrivateKey
from pyas2.models import PublicCertificate


class PartnerForm(forms.ModelForm):

    def clean(self):
        cleaned_data = super(PartnerForm, self).clean()

        # If http auth is set and credentials are missing raise error
        if cleaned_data.get('http_auth'):
            if not cleaned_data.get('http_auth_user'):
                raise forms.ValidationError(
                    _('HTTP username is mandatory when HTTP authentication '
                      'is enabled'))
            if not cleaned_data.get('http_auth_pass'):
                self._errors['http_auth_pass'] = self.error_class(
                    _('HTTP password is mandatory when HTTP authentication '
                      'is enabled'))

        # if encryption is set and no cert is mentioned set error
        if cleaned_data.get('encryption') and \
                not cleaned_data.get('encryption_cert'):
            raise forms.ValidationError(
                _('Encryption Key is mandatory when message encryption is set'))

        # if signature is set and no cert is mentioned set error
        if cleaned_data.get('signature') and \
                not cleaned_data.get('signature_cert'):
            raise forms.ValidationError(
                _('Signature Key is required when message signature is set'))

        # if mdn is set then the mode must also be set
        if cleaned_data.get('mdn') and not cleaned_data.get('mdn_mode'):
            raise forms.ValidationError(_('MDN Mode needs to be specified'))

        # if the mdn signature is set then the signature cert must be set
        if cleaned_data.get('mdn_sign') and \
                not cleaned_data.get('signature_cert'):
            raise forms.ValidationError(
                _('Signature Key is mandatory when signed mdn is requested'))

        return cleaned_data

    class Meta:
        model = Partner
        exclude = []


class PrivateKeyForm(forms.ModelForm):
    key_file = forms.FileField()

    def clean_key_file(self):
        key_file = self.cleaned_data['key_file']

        ext = os.path.splitext(key_file.name)[1]
        valid_extensions = ['.pem', '.p12', '.pfx']

        if not ext.lower() in valid_extensions:
            raise forms.ValidationError(_(
                'Unsupported key format, supported formats '
                'include %s.') % ', '.join(valid_extensions))
        return key_file

    def clean(self):
        cleaned_data = super(PrivateKeyForm, self).clean()
        key_file = cleaned_data.get('key_file')

        if key_file:
            cleaned_data['key_filename'] = key_file.name
            cleaned_data['key_file'] = key_file.read()

            try:

                As2Organization.load_key(cleaned_data['key_file'],
                                         cleaned_data['key_pass'])
            except AS2Exception as e:
                raise forms.ValidationError(e.args[0])

        return cleaned_data

    def save(self, commit=True):
        instance = super(PrivateKeyForm, self).save(commit=False)
        instance.name = self.cleaned_data['key_filename']
        instance.key = self.cleaned_data['key_file']
        if commit:
            instance.save()
        return instance

    class Meta:
        model = PrivateKey
        fields = ['key_file', 'key_pass']
        widgets = {
            'key_pass': forms.PasswordInput(),
        }


class PublicCertificateForm(forms.ModelForm):
    cert_file = forms.FileField(label='Certificate File')
    cert_ca_file = forms.FileField(label='Certificate CA File', required=False)

    def clean_cert_file(self):
        cert_file = self.cleaned_data['cert_file']

        ext = os.path.splitext(cert_file.name)[1]
        valid_extensions = ['.pem', '.der', '.cer']

        if not ext.lower() in valid_extensions:
            raise forms.ValidationError(_(
                'Unsupported certificate format, supported formats '
                'include %s.') % ', '.join(valid_extensions))

        return cert_file

    def clean_cert_ca_file(self):
        cert_ca_file = self.cleaned_data['cert_ca_file']

        if cert_ca_file:
            ext = os.path.splitext(cert_ca_file.name)[1]
            valid_extensions = ['.pem', '.der', '.cer', '.ca']

            if not ext.lower() in valid_extensions:
                raise forms.ValidationError(_(
                    'Unsupported certificate format, supported formats '
                    'include %s.') % ', '.join(valid_extensions))

        return cert_ca_file

    def clean(self):
        cleaned_data = super(PublicCertificateForm, self).clean()
        cert_file = cleaned_data.get('cert_file')
        cert_ca_file = cleaned_data.get('cert_ca_file', '')

        if cert_file and cert_ca_file != '':
            cleaned_data['cert_filename'] = cert_file.name
            cleaned_data['cert_file'] = cert_file.read()

            if cert_ca_file:
                cleaned_data['cert_ca_file'] = cert_ca_file.read()

            try:
                partner = As2Partner(
                    'partner',
                    verify_cert=cleaned_data['cert_file'],
                    verify_cert_ca=cleaned_data['cert_ca_file'],
                    validate_certs=cleaned_data['verify_cert']
                )
                partner.load_verify_cert()
            except AS2Exception as e:
                raise forms.ValidationError(e.args[0])

        return cleaned_data

    def save(self, commit=True):
        instance = super(PublicCertificateForm, self).save(commit=False)
        instance.name = self.cleaned_data['cert_filename']
        instance.certificate = self.cleaned_data['cert_file']

        if self.cleaned_data['cert_ca_file']:
            instance.certificate_ca = self.cleaned_data['cert_ca_file']

        if commit:
            instance.save()
        return instance

    class Meta:
        model = PublicCertificate
        fields = ['cert_file', 'cert_ca_file', 'verify_cert']


class SendAs2MessageForm(forms.Form):
    organization = forms.ModelChoiceField(
        queryset=Organization.objects.all(), empty_label=None)
    partner = forms.ModelChoiceField(queryset=Partner.objects.all())
    file = forms.FileField()

