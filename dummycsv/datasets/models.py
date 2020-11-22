from django.db import models
from django.contrib.auth import get_user_model

from uuid import uuid4
from random import choice, randint
from datetime import datetime, date, timedelta

from . import gen_data

DATE_START = datetime.fromtimestamp(0)
DATE_END = datetime.now()
DATE_DELTA = int((DATE_END - DATE_START).total_seconds())

TYPE_SIDS = (
    ('name', 'Full name'),
    ('job', 'Job'),
    ('text', 'Text'),
    ('integer', 'Integer'),
    ('date', 'Date'),
)

NAME_SID = TYPE_SIDS[0][0]
JOB_SID = TYPE_SIDS[1][0]
TEXT_SID = TYPE_SIDS[2][0]
INTEGER_SID = TYPE_SIDS[3][0]
DATE_SID = TYPE_SIDS[4][0]


class ColumnType(models.Model):
    """
    CSV column type base model

    sid: type related unique string identifier
    """

    sid = None
    _sid = models.CharField(max_length=20, unique=True, choices=TYPE_SIDS)

    class Meta:
        db_table = 'column_types'

    def __str__(self):
        return f'{self.__class__.__name__}: {self._sid}'

    def get_proxy(self):
        """
        Returns proxy model based on the loaded sid

        :raises: RuntimeError
        """

        for subclass in self.__class__.__subclasses__():
            if subclass.sid == self._sid:
                return subclass

        raise RuntimeError(f'Proxy with sid={self._sid} not found')

    @staticmethod
    def generate_value(params: dict):
        """ Generate dummy value for CSV column """

        raise NotImplementedError('Value generation should be overridden in subclasses')


class FullName(ColumnType):
    """ Person full name: first name and last name """

    sid = NAME_SID

    class Meta:
        proxy = True

    @staticmethod
    def generate_value(params: dict) -> str:
        return f'{choice(gen_data.first_names)} {choice(gen_data.last_names)}'


class Job(ColumnType):
    """ Person job position """

    sid = JOB_SID

    class Meta:
        proxy = True

    @staticmethod
    def generate_value(params: dict) -> str:
        return choice(gen_data.jobs)


class Text(ColumnType):
    sid = TEXT_SID

    class Meta:
        proxy = True

    @staticmethod
    def generate_value(params: dict) -> str:
        """
        Generate dummy value for CSV column, requires non empty 'params' dictionary

        :raises: AssertionError
        """

        assert params is not None and len(params)
        start, end = params['start'], params['end']
        return ''.join(choice(gen_data.sentences) for _ in range(randint(start, end)))


class Integer(ColumnType):
    sid = INTEGER_SID

    class Meta:
        proxy = True

    @staticmethod
    def generate_value(params: dict) -> int:
        """
        Generate dummy value for CSV column, requires non empty 'params' dictionary

        :raises: AssertionError
        """

        assert params is not None and len(params)
        return randint(params['start'], params['end'])


class Date(ColumnType):
    sid = DATE_SID

    class Meta:
        proxy = True

    @staticmethod
    def generate_value(params: dict) -> date:
        return (DATE_START + timedelta(seconds=randint(0, DATE_DELTA))).date()


class Column(models.Model):
    """ CSV column with specific type """

    name = models.CharField(max_length=50)
    order = models.PositiveIntegerField(db_index=True)
    params = models.JSONField(blank=True, null=True, help_text='Column additional params for data generation')
    type = models.ForeignKey(ColumnType, on_delete=models.CASCADE)
    schema = models.ForeignKey('DataSchema', on_delete=models.CASCADE, related_name='columns')

    class Meta:
        db_table = 'columns'

    def __str__(self):
        return f'{self.__class__.__name__}: {self.name}, params: {self.params}'


class DataSchema(models.Model):
    """ CSV schema model that aggregates columns """

    title = models.CharField(max_length=250)
    modified = models.DateTimeField(auto_now=True, db_index=True)
    separator = models.CharField(default=',', max_length=3, help_text='Line separator')
    string_character = models.CharField(default='"', max_length=1, help_text='A single character used for quoting')
    user = models.ForeignKey(get_user_model(), on_delete=models.PROTECT)

    class Meta:
        db_table = 'schemas'

    def __str__(self):
        return f'{self.__class__.__name__}: {self.title}, {self.id}'

    def generate(self, count: int):
        """ Generate a sequence of values by given count """

        columns = self.columns.select_related('type').order_by('order')
        proxies = [(column.type.get_proxy(), column.params) for column in columns]

        # yield header

        yield [column.name for column in columns]

        for _ in range(count):
            yield [proxy.generate_value(params) for proxy, params in proxies]


def get_id() -> str:
    return uuid4().hex


class DataSet(models.Model):
    """ CSV dataset model, UUID4 identifier represents filename on media storage """

    id = models.CharField(primary_key=True, default=get_id, max_length=32)
    rows = models.PositiveIntegerField()
    processed = models.BooleanField(default=False, help_text='Dataset processing status')
    created = models.DateTimeField(auto_now_add=True, db_index=True)
    schema = models.ForeignKey(DataSchema, on_delete=models.CASCADE)

    class Meta:
        db_table = 'datasets'

    def __str__(self):
        return f'{self.__class__.__name__}: {self.id}'
