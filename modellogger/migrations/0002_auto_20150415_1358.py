# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('modellogger', '0001_initial'),
    ]

    operations = [
        migrations.AlterIndexTogether(
            name='changelog',
            index_together=set([('content_type', 'object_id')]),
        ),
    ]
