from django.conf import settings
from django.contrib import admin
from django.urls import path, include
from django.views.generic.base import RedirectView

from rest_framework.permissions import AllowAny

from drf_yasg import openapi
from drf_yasg.views import get_schema_view

urlpatterns = [
    path('api/', include('datasets.urls')),
    path('api/auth/', include('auth_api.urls')),
    path('admin/', admin.site.urls),
]

# add swagger ui view

if settings.DEBUG:
    schema_view = get_schema_view(
        openapi.Info(title='DummyCSV API', default_version='v0.1'),
        url=settings.REST_API_DOCS_URL,
        public=True,
        permission_classes=(AllowAny,),
    )

    urlpatterns += [
        path('api/docs/', schema_view.with_ui(), name='docs'),
        path('', RedirectView.as_view(url='/api/docs/')),
    ]
