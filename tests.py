import unittest
from django.test import TestCase
from django.db import models
from models import TrackableModel, ChangeLog

class TrackedModel(TrackableModel):
    TRACK_CHANGES = True
    ordinal = models.PositiveIntegerField(null=True, default=None)

class TestModellogger(TestCase):

    def test_nominal(self):
        tm = TrackedModel()
        tm.ordinal = 1
        print 'id: ' + str(tm.id)
        tm.save()
        print 'id: ' + str(tm.id)
        tm.ordinal = 2
        tm.save()

        print len(ChangeLog.objects.all())

        self.assertEqual(1, 1)

