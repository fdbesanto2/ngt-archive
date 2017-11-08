from django.conf.urls import url
from django.contrib.auth.decorators import login_required

from ui.views import IndexView, doi, download

urlpatterns = [
    url(r'^$', login_required(IndexView.as_view()), name="home"),
    url(r'^dois/(?P<ngt_id>[a-zA-Z0-9]+)/$', doi, name='doi'),
    url(r'^download/(?P<ngt_id>[a-zA-Z0-9]+)', download, name='download'),
]
