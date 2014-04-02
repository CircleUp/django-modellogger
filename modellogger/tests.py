from django.test import TestCase
from django.db import models
from models import TrackableModel, ChangeLog


class TrackedModel(TrackableModel):
    TRACK_CHANGES = True
    ordinal = models.PositiveIntegerField(null=True, default=None)


class UserProfile(TrackableModel):
    TRACK_CHANGES = True
    first_name = models.CharField(max_length=40, default='')
    username = models.CharField(max_length=40, default='')
    identity_verification_user = models.ForeignKey('UserProfile', null=True, related_name="+")
  

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

    def test_changes_log(self):
        """Test that changes made to models are saved into the model change log"""
        person = UserProfile(first_name="Bob", username='')
        person.save()
        logs = ChangeLog.objects.all()
        self.assertEqual(1, len(logs))
        self.assertIsNone(logs[0].user_id)
        self.assertEqual(logs[0].column_name, 'first_name')
        self.assertEqual(logs[0].old_value, u'')
        self.assertEqual(logs[0].new_value, 'Bob')

        person.first_name = "Luke"
        person.save()
        logs = ChangeLog.objects.all()
        self.assertEqual(2, len(logs))
        self.assertIsNone(logs[1].user_id)
        self.assertEqual(logs[1].column_name, 'first_name')
        self.assertEqual(logs[1].old_value, 'Bob')
        self.assertEqual(logs[1].new_value, 'Luke')

        administrator = UserProfile(first_name='Anakin', username="anny")
        administrator.save()
        person.first_name = 'Leia'
        person.identity_verification_user = administrator
        person.save()

        logs = ChangeLog.objects.all()
        self.assertEqual(6, len(logs))

