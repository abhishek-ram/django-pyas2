from django.conf.urls import url

from pyas2 import views


urlpatterns = [
    url(r'^as2receive/', views.ReceiveAs2Message.as_view(), name="as2-receive"),
    # Add the url again without slash for backwards compatibility
    url(r'^as2receive', views.ReceiveAs2Message.as_view(), name="as2-receive"),
    url(r'^as2send/', views.SendAs2Message.as_view(), name="as2-send"),
    url(r'^download/(?P<obj_type>.+)/(?P<obj_id>.+)/',
        views.DownloadFile.as_view(), name='download-file'),
]