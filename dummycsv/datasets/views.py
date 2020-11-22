import csv

from rest_framework import status, viewsets, mixins, generics
from rest_framework.exceptions import NotFound
from rest_framework.decorators import action
from rest_framework.views import Response

from django.conf import settings
from django.http import StreamingHttpResponse

from itertools import chain, islice

from . import models, serializers, tasks


class SimpleIO:
    """
    A simple I/O interface that supports just 'write' method

    :param encoding: encoding for converting to bytes
    """

    def __init__(self, encoding: str = 'utf8'):
        self.encoding = encoding

    def write(self, value: str, encode: bool = False) -> bytes:
        """
        Return value, instead of writing it to the buffer

        :param value: .csv row
        :param encode: whether to convert a value to bytes
        :return: encoded row
        """

        return value.encode(self.encoding) if encode else value

    def encode_chunk(self, value: list) -> bytes:
        """ Encode chunk of .csv rows """

        return ''.join(value).encode(self.encoding)


class ColumnTypesList(generics.ListAPIView):
    """ List of CSV column types """

    queryset = models.ColumnType.objects.order_by('id')
    serializer_class = serializers.ColumnTypeSerializer


class DataSchemaViewSet(viewsets.ModelViewSet):
    queryset = models.DataSchema.objects.prefetch_related('columns').order_by('-modified')
    serializer_class = serializers.DataSchemaSerializer

    serializer_action_classes = {
        'update': serializers.DataSchemaNoColumnsSerializer,
        'partial_update': serializers.DataSchemaNoColumnsSerializer,
        'add_column': serializers.ColumnSerializer,
        'update_column': serializers.ColumnSerializer,
    }

    def get_serializer_class(self):
        """ Look for serializer class in actions dictionary first """

        return self.serializer_action_classes.get(self.action) or super().get_serializer_class()

    def get_queryset(self):
        """ Filter schemas by current user """

        return self.queryset.filter(user_id=self.request.user.id)

    @action(methods=['POST'], detail=True, url_path=r'columns')
    def add_column(self, request, pk):
        """ Add schema column """

        schema = self.get_object()
        serializer = self.get_serializer(data=request.data, schema=schema)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data)

    @action(methods=['PUT'], detail=True, url_path=r'columns/(?P<column_id>\d+)')
    def update_column(self, request, pk, column_id):
        """ Update schema column """

        self.get_object()
        column = generics.get_object_or_404(models.Column.objects.all(), schema_id=pk, id=column_id)
        serializer = self.get_serializer(instance=column, data=request.data, partial=False)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data)

    @update_column.mapping.delete
    def delete_column(self, request, pk, column_id):
        """ Delete schema column """

        self.get_object()
        column = generics.get_object_or_404(models.Column.objects.all(), schema_id=pk, id=column_id)
        column.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)


class DataSetViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet
):
    queryset = models.DataSet.objects.order_by('-created')
    serializer_class = serializers.DataSetSerializer

    def create(self, request, *args, **kwargs):
        """ Create a dataset object and emit file generation """

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)

        # send generation task

        tasks.generate_file.delay(dataset_id=serializer.data['id'])
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def retrieve(self, request, *args, **kwargs):
        """ Retrieve dataset object and stream corresponded file by chunks """

        dataset = self.get_object()
        filename = f'{dataset.id}.csv'
        file_path = settings.MEDIA_ROOT / filename

        if not file_path.is_file():
            raise NotFound

        buffer = SimpleIO()
        reader = csv.reader(open(file_path), delimiter=dataset.schema.separator)
        writer = csv.writer(buffer, delimiter=dataset.schema.separator)
        response = StreamingHttpResponse(self.chunked_read(reader, writer, buffer), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    @staticmethod
    def chunked_read(reader, writer, buffer: SimpleIO):
        """ Generator for chunked reading from csv reader """

        iterator = iter(reader)

        for first in iterator:
            chunk = list(chain([first], islice(iterator, tasks.CHUNK_SIZE - 1)))
            yield buffer.encode_chunk([writer.writerow(row) for row in chunk])
