from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r'schemas', views.DataSchemaViewSet)
router.register(r'sets', views.DataSetViewSet)

urlpatterns = [
    path('types/', views.ColumnTypesList.as_view()),
    *router.urls,
]
