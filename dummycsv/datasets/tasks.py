import csv

from celery import shared_task
from celery.utils.log import get_task_logger
from django.conf import settings

from itertools import chain, islice

from . import models

CHUNK_SIZE = 1000
logger = get_task_logger(__name__)


@shared_task(autoretry_for=(Exception,), max_retries=5)
def generate_file(dataset_id: str) -> None:
    """ Generate CSV file by the given dataset identifier """

    try:
        dataset = models.DataSet.objects.select_related('schema').get(id=dataset_id)

    except models.DataSet.DoesNotExist:
        logger.warning(f'Dataset not found: {dataset_id}')
        return

    file_path = settings.MEDIA_ROOT / f'{dataset_id}.csv'
    iterator = iter(dataset.schema.generate(count=dataset.rows))

    with open(file_path, 'w') as file:
        writer = csv.writer(
            file,
            delimiter=dataset.schema.separator,
            quotechar=dataset.schema.string_character,
            quoting=csv.QUOTE_ALL
        )

        # write by chunks without memory abuse

        for first in iterator:
            chunk = list(chain([first], islice(iterator, CHUNK_SIZE - 1)))
            writer.writerows(chunk)

    dataset.processed = True
    dataset.save(update_fields=['processed'])
