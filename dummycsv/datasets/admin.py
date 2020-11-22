from django.contrib import admin
from . import models

admin.register(models.ColumnType, models.Column, models.DataSchema, models.DataSet)(admin.ModelAdmin)
