# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('contenttypes', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ChangeLog',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('timestamp', models.DateTimeField(auto_now=True)),
                ('object_id', models.PositiveIntegerField()),
                ('column_name', models.CharField(max_length=150)),
                ('old_value', models.TextField(null=True, blank=True)),
                ('new_value', models.TextField(null=True, blank=True)),
                ('content_type', models.ForeignKey(to='contenttypes.ContentType', on_delete=django.db.models.deletion.PROTECT)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, default=None, to=settings.AUTH_USER_MODEL, null=True)),
            ],
            options={
                'db_table': 'log_model_change',
            },
            bases=(models.Model,),
        ),
    ]
