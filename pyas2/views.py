import logging
import os

from django.contrib import messages
from django.shortcuts import Http404
from django.shortcuts import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.urls import reverse_lazy
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.generic import FormView
from pyas2lib import Message as As2Message
from pyas2lib import Mdn as As2Mdn
from pyas2lib.exceptions import DuplicateDocument

from pyas2.models import Mdn
from pyas2.models import Message
from pyas2.models import Organization
from pyas2.models import Partner
from pyas2.models import PrivateKey
from pyas2.models import PublicCertificate
from pyas2.utils import run_post_receive
from pyas2.utils import run_post_send
from pyas2.forms import SendAs2MessageForm

logger = logging.getLogger("pyas2")


@method_decorator(csrf_exempt, name="dispatch")
class ReceiveAs2Message(View):
    """
    Class receives AS2 requests from partners.
    Checks whether its an AS2 message or an MDN and acts accordingly.
    """

    @staticmethod
    def find_message(message_id, partner_id):
        """Find the message using the message_id  and return its pyas2 type"""
        message = Message.objects.filter(
            message_id=message_id, partner_id=partner_id.strip()
        ).first()
        if message:
            return message.as2message
        return None

    @staticmethod
    def check_message_exists(message_id, partner_id):
        """Check if the message already exists in the system"""
        return Message.objects.filter(
            message_id=message_id, partner_id=partner_id.strip()
        ).exists()

    @staticmethod
    def find_organization(org_id):
        """Find the org using the As2 Id and return its pyas2 type"""
        org = Organization.objects.filter(as2_name=org_id).first()
        if org:
            return org.as2org
        return None

    @staticmethod
    def find_partner(partner_id):
        """Find the partner using the As2 Id and return its pyas2 type"""
        partner = Partner.objects.filter(as2_name=partner_id).first()
        if partner:
            return partner.as2partner
        return None

    @xframe_options_exempt
    @csrf_exempt
    def post(self, request, *args, **kwargs):
        """Handle the post message received by the AS2 server."""
        # extract the  headers from the http request
        as2headers = ""
        for key in request.META:
            if key.startswith("HTTP") or key.startswith("CONTENT"):
                as2headers += (
                    f'{key.replace("HTTP_", "").replace("_", "-").lower()}: '
                    f"{request.META[key]}\n"
                )

        # build the body along with the headers
        request_body = as2headers.encode() + b"\r\n" + request.body
        logger.debug(
            f'Received an HTTP POST from {request.META["REMOTE_ADDR"]} '
            f"with payload :\n{request_body}"
        )

        # First try to see if this is an MDN
        logger.debug("Check to see if payload is an Asynchronous MDN.")
        as2mdn = As2Mdn()

        # Parse the mdn and get the message status
        status, detailed_status = as2mdn.parse(request_body, self.find_message)

        if not detailed_status == "mdn-not-found":
            message = Message.objects.get(
                message_id=as2mdn.orig_message_id, direction="OUT"
            )
            logger.info(
                f"Asynchronous MDN received for AS2 message {as2mdn.message_id} to organization "
                f"{message.organization.as2_name} from partner {message.partner.as2_name}"
            )

            # Update the message status and return the response
            if status == "processed":
                message.status = "S"
                run_post_send(message)
            else:
                message.status = "E"
                message.detailed_status = (
                    f"Partner failed to process message: {detailed_status}"
                )
            # Save the message and create the mdn
            message.save()
            Mdn.objects.create_from_as2mdn(as2mdn=as2mdn, message=message, status="R")

            return HttpResponse(_("AS2 ASYNC MDN has been received"))

        else:
            logger.debug("Payload is not an MDN parse it as an AS2 Message")
            as2message = As2Message()
            status, exception, as2mdn = as2message.parse(
                request_body,
                self.find_organization,
                self.find_partner,
                self.check_message_exists,
            )

            logger.info(
                f'Received an AS2 message with id {as2message.headers.get("message-id")} for '
                f'organization {as2message.headers.get("as2-to")} from '
                f'partner {as2message.headers.get("as2-from")}.'
            )

            # In case of duplicates update message id
            if isinstance(exception[0], DuplicateDocument):
                as2message.message_id += "_duplicate"

            # Create the Message and MDN objects
            message, full_fn = Message.objects.create_from_as2message(
                as2message=as2message,
                filename=as2message.payload.get_filename(),
                payload=as2message.content,
                direction="IN",
                status="S" if status == "processed" else "E",
                detailed_status=exception[1],
            )

            # run post receive command on success
            if status == "processed":
                run_post_receive(message, full_fn)

            # Return the mdn in case of sync else return text message
            if as2mdn and as2mdn.mdn_mode == "SYNC":
                message.mdn = Mdn.objects.create_from_as2mdn(
                    as2mdn=as2mdn, message=message, status="S"
                )
                response = HttpResponse(as2mdn.content)
                for key, value in as2mdn.headers.items():
                    response[key] = value
                return response

            elif as2mdn and as2mdn.mdn_mode == "ASYNC":
                Mdn.objects.create_from_as2mdn(
                    as2mdn=as2mdn,
                    message=message,
                    status="P",
                    return_url=as2mdn.mdn_url,
                )
            return HttpResponse(_("AS2 message has been received"))

    def get(self, request, *args, **kwargs):
        """Handle the GET call made to the AS2 server post endpoint."""
        return HttpResponse(
            _("To submit an AS2 message, you must POST the message to this URL")
        )

    def options(self, request, *args, **kwargs):
        """Handle the OPTIONS call made to the AS2 server post endpoint."""
        response = HttpResponse()
        response["allow"] = ",".join(["POST", "GET"])
        return response


class SendAs2Message(FormView):
    """View for sending AS2 messages to a partner."""

    # pylint: disable=W0212
    template_name = "pyas2/send_as2_message.html"
    form_class = SendAs2MessageForm
    success_url = reverse_lazy(
        f"admin:{Message._meta.app_label}_{Message._meta.model_name}_changelist"
    )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "opts": Partner._meta,
                "change": True,
                "is_popup": False,
                "save_as": False,
                "has_delete_permission": False,
                "has_add_permission": False,
                "has_change_permission": False,
            }
        )
        return context

    def form_valid(self, form):
        # Send the file to the partner
        payload = form.cleaned_data["file"].read()
        as2message = As2Message(
            sender=form.cleaned_data["organization"].as2org,
            receiver=form.cleaned_data["partner"].as2partner,
        )
        logger.debug(
            f'Building message from {form.cleaned_data["file"].name} to send to partner '
            f"{as2message.receiver.as2_name} from org {as2message.sender.as2_name}."
        )
        as2message.build(
            payload,
            filename=form.cleaned_data["file"].name,
            subject=form.cleaned_data["partner"].subject,
            content_type=form.cleaned_data["partner"].content_type,
            disposition_notification_to=form.cleaned_data["organization"].email_address
            or "no-reply@pyas2.com",
        )

        message, _ = Message.objects.create_from_as2message(
            as2message=as2message,
            payload=payload,
            filename=form.cleaned_data["file"].name,
            direction="OUT",
            status="P",
        )
        message.send_message(as2message.headers, as2message.content)
        if message.status in ["S", "P"]:
            messages.success(
                self.request, "Message has been successfully send to Partner."
            )
        else:
            messages.error(
                self.request,
                "Message transmission failed, check Messages tab for details.",
            )
        return super().form_valid(form)


class DownloadFile(View):
    """A generic view for downloading files such as payload, certificates..."""

    def get(self, request, obj_type, obj_id, *args, **kwargs):
        """Return the requested file bytes as a response."""
        filename = ""
        file_content = ""
        # Get the file content based
        if obj_type == "message_payload":
            obj = get_object_or_404(Message, pk=obj_id)
            filename = os.path.basename(obj.payload.name)
            file_content = obj.payload.read()

        elif obj_type == "mdn_payload":
            obj = get_object_or_404(Mdn, pk=obj_id)
            filename = os.path.basename(obj.payload.name)
            file_content = obj.payload.read()

        elif obj_type == "public_cert":
            obj = get_object_or_404(PublicCertificate, pk=obj_id)
            filename = obj.name
            file_content = obj.certificate

        elif obj_type == "private_key":
            obj = get_object_or_404(PrivateKey, pk=obj_id)
            filename = obj.name
            file_content = obj.key

        # Return the file contents as attachment
        if filename and file_content:
            response = HttpResponse(content_type="application/x-pem-file")
            disposition_type = "attachment"
            response["Content-Disposition"] = (
                disposition_type + "; filename=" + filename
            )
            response.write(bytes(file_content))
            return response
        else:
            raise Http404()
