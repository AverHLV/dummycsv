from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from django.db.transaction import atomic

from . import models


class ColumnTypeSerializer(serializers.ModelSerializer):
    sid = serializers.CharField(source='_sid')

    class Meta:
        model = models.ColumnType
        fields = 'id', 'sid'


class ColumnSerializer(serializers.ModelSerializer):
    params_required_types = models.INTEGER_SID, models.TEXT_SID

    class Meta:
        model = models.Column
        fields = 'id', 'name', 'order', 'params', 'type'

    def __init__(self, *args, **kwargs):
        if 'schema' in kwargs:
            context = kwargs.get('context', {})
            context['schema'] = kwargs.pop('schema')
            kwargs['context'] = context

        super().__init__(*args, **kwargs)

    def validate(self, attrs: dict):
        """ Validate 'params' depending on column type """

        params = attrs.get('params', None)
        column_type = attrs['type']

        if params is None and column_type._sid in self.params_required_types:
            raise ValidationError({'params': 'This field is required for given column types'})

        elif column_type._sid not in self.params_required_types:
            attrs['params'] = None
            return attrs

        if not isinstance(params, dict):
            raise ValidationError({'params': 'Only dictionaries allowed'})

        validate_params = {}

        for key in ('start', 'end'):
            value = params.get(key, None)

            if value is None:
                raise ValidationError({'params': 'Invalid input'})

            try:
                value = float(value)

            except (TypeError, ValueError, OverflowError):
                raise ValidationError({'params': 'Invalid input'})

            validate_params[key] = value

        if validate_params['start'] >= validate_params['end']:
            raise ValidationError({'params': 'Invalid input'})

        attrs['params'] = validate_params
        return attrs

    def create(self, validated_data: dict):
        """ Set column schema from context if exists """

        if 'schema' in self.context:
            validated_data['schema'] = self.context['schema']

        return super().create(validated_data)


class DataSchemaNoColumnsSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.DataSchema
        fields = 'id', 'modified', 'title', 'separator', 'string_character'
        read_only_fields = 'id', 'modified'


class DataSchemaSerializer(serializers.ModelSerializer):
    columns = ColumnSerializer(many=True, required=True)

    class Meta:
        model = models.DataSchema
        fields = 'id', 'modified', 'title', 'separator', 'string_character', 'columns'
        read_only_fields = 'id', 'modified'

    @staticmethod
    def validate_columns(value: list):
        if not len(value):
            raise ValidationError('At least one column is required')

        return value

    def validate(self, attrs: dict) -> dict:
        """ Extend attributes with current user """

        attrs['user'] = self.context['request'].user
        return attrs

    @atomic
    def create(self, validated_data: dict):
        """ Create schema and columns in an atomic transaction """

        model = self.Meta.model
        columns = validated_data.pop('columns')
        instance = model.objects.create(**validated_data)

        column_model = self.fields['columns'].child.Meta.model
        columns = [column_model(schema=instance, **column_data) for column_data in columns]
        column_model.objects.bulk_create(columns)

        return instance


class DataSetSerializer(serializers.ModelSerializer):
    schema = serializers.PrimaryKeyRelatedField(queryset=models.DataSchema.objects.only('pk'))

    class Meta:
        model = models.DataSet
        fields = 'id', 'created', 'processed', 'rows', 'schema'
        read_only_fields = 'id', 'created', 'processed'
