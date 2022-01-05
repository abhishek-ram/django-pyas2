from django.urls import path
from django.contrib.auth.decorators import login_required
from django.urls import include, path

from pyas2 import views


urlpatterns = [
    # path('pyas2/', include('pyas2.urls')),
    path("as2receive/", views.ReceiveAs2Message.as_view(), name="as2-receive"),
    # Add the url again without slash for backwards compatibility
    path("as2receive", views.ReceiveAs2Message.as_view(), name="as2-receive"),
    path("as2send/", login_required(views.SendAs2Message.as_view()), name="as2-send"),
    path(
        "download/<str:obj_type>/<str:obj_id>/",
        login_required(views.DownloadFile.as_view()),
        name="download-file",
    ),
]
