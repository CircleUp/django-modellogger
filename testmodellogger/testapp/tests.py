"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""
from django import forms
from django.test import TestCase
from modellogger.models import ChangeLog
from testapp.models import UserProfile, TrackedModel, Person


class TestModelLogger(TestCase):

    def test_track_changes_simple(self):
        p = Person()
        p.first_name = 'Bob'
        p.save()
        self.assertEqual(ChangeLog.objects.count(), 1)

        p.first_name = 'Sally'
        p.save()
        self.assertEqual(ChangeLog.objects.count(), 2)

        p.first_name = 'Bob'
        p.save()
        self.assertEqual(ChangeLog.objects.count(), 3)

    def test_track_changes_with_initial_id(self):
        p = Person(first_name='Bob', last_name='Smith', id=1)
        p.save()
        self.assertEqual(ChangeLog.objects.count(), 2)

        p.first_name = 'Sally'
        p.save()
        self.assertEqual(ChangeLog.objects.count(), 3)

    def test_track_changes_without_initial_id(self):
        p = Person(first_name='Bob', last_name='Smith')
        p.save()
        self.assertEqual(ChangeLog.objects.count(), 2)

        p.first_name = 'Sally'
        p.save()
        self.assertEqual(ChangeLog.objects.count(), 3)

    def test_track_changes_after_db_pull(self):
        p = Person(first_name='Bob', last_name='Smith', id=1)
        p.save()
        self.assertEqual(ChangeLog.objects.count(), 2)

        p1 = Person.objects.get(pk=1)
        p1.first_name = 'Sally'
        p1.save()
        self.assertEqual(ChangeLog.objects.count(), 3)

    def test_form_save(self):

        class PersonForm(forms.ModelForm):
            class Meta(object):
                model = Person
                fields = ('id', 'first_name', 'last_name')

        person = Person(first_name='John', last_name='Smith', id=2)
        person.save()

        self.assertEqual(ChangeLog.objects.count(), 2)

        post_data = {
            'first_name': 'Sally',
            'last_name': 'Jones'
        }

        form = PersonForm(post_data, instance=person)
        form.save()

        self.assertEqual(ChangeLog.objects.count(), 4)

    def test_nominal(self):
        tm = TrackedModel()
        tm.ordinal = 1
        tm.save()

        tm.ordinal = 2
        tm.save()

        self.assertEqual(ChangeLog.objects.count(), 2)

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

    def test_model_is_dirty_with_simple_field(self):
        """Test that a simple model detects changes properly"""
        # Unsaved models should always be "dirty"
        person = Person(first_name="Bob")
        self.assertTrue(person.is_dirty)

        # saving inital state doesn't matter since this model has never been saved to the database
        person.save_inital_state()
        self.assertTrue(person.is_dirty)

        person.save()
        self.assertFalse(person.is_dirty)

        # make a change, should be dirty
        person.first_name = "Bill"
        self.assertTrue(person.is_dirty)

        # change it back, should be clean
        person.first_name = "Bob"
        self.assertFalse(person.is_dirty)

    def test_is_dirty_with_inheritance(self):
        """Check that a subclassed model looks at it's parents fields as well"""
        person = UserProfile(first_name="Bob")
        self.assertTrue(person.is_dirty)

        # saving inital state doesn't matter since this model has never been saved to the database
        person.save_inital_state()
        self.assertTrue(person.is_dirty)
        person.save()

        # make a change
        person.first_name = "Bill"
        self.assertTrue(person.is_dirty)

        # change it back
        person.first_name = "Bob"
        self.assertFalse(person.is_dirty)

        person.username = 'bob@bob.com'
        self.assertTrue(person.is_dirty)

    def test_is_dirty_with_relationships(self):
        """Check that relationships are simplified into foreign key ids"""
        person = Person(first_name="Bob")
        person.investor_executive_id = 2

        self.assertTrue(person.is_dirty)
        assert ('investor_executive_id' in person.dirty_fields)
        self.assertEqual(2, person.changes_pending['investor_executive_id'][1])
        person.save()

        self.assertFalse(person.is_dirty)
