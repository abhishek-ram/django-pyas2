from django.conf.urls import url
from . import views


urlpatterns = [
    url(r'^as2receive/', views.AS2Receive.as_view(), name="as2-receive")
]