from django.conf.urls import url

from figment import views
from figment import settings

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^get/$', views.get_component),
    url(r'^search/$', views.search_component),
    url(r'^provides/$', views.find_feature),

    url(r'^static/(?P<path>.*)$', 'django.views.static.serve',
        {'document_root': settings.STATIC_DOC_ROOT}),
]
