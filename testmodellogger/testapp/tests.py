import pytest
from django import forms
from django.contrib.contenttypes.models import ContentType
from django.db import models

from modellogger.models import ChangeLog, TrackableModel
from testapp.models import UserProfile, TrackedModel, Person

pytestmark = pytest.mark.django_db


def test_class_setup_with_subclasses():
    """Test class configuration for subclasses"""

    class Vehicle(TrackableModel):
        TRACK_CHANGES = True
        weight = models.PositiveIntegerField(null=True, default=None)

    class Car(Vehicle):
        TRACK_CHANGES = True
        EXCLUDED_TRACKING_FIELDS = ['weight']
        engine_type = models.CharField(max_length=40, default='')

    with pytest.raises(AttributeError):
        Car._trackable_model_initialized

    Vehicle()
    assert Car._trackable_model_initialized == 'Vehicle'

    Car()
    assert Car._trackable_model_initialized == 'Car'
    assert Vehicle._trackable_model_initialized == 'Vehicle'


def test_track_changes_simple():
    p = Person()
    p.first_name = 'Bob'
    p.save()
    assert ChangeLog.objects.count() == 3

    p.first_name = 'Sally'
    p.save()
    assert ChangeLog.objects.count() == 4

    p.first_name = 'Bob'
    p.save()
    assert ChangeLog.objects.count() == 5


def test_track_changes_with_initial_id():
    p = Person(first_name='Bob', last_name='Smith', id=1)
    p.save()
    assert ChangeLog.objects.count() == 0

    p.first_name = 'Sally'
    p.save()
    assert ChangeLog.objects.count() == 1


def test_track_changes_without_initial_id():
    p = Person(first_name='Bob', last_name='Smith')
    p.save()
    assert ChangeLog.objects.count() == 3

    p.first_name = 'Sally'
    p.save()
    assert ChangeLog.objects.count() == 4


def test_change_log_returns_actual_python_objects():
    p = Person(donuts_consumed=5)
    p.save()

    log = ChangeLog.objects.filter(column_name='donuts_consumed')[0]
    assert '5' != log.new_value_as_python
    assert 5 == log.new_value_as_python


def test_handling_records_for_deleted_models():
    log = ChangeLog(content_type_id=999, object_id=15, column_name='soda_consumed', old_value='1', new_value='2')
    with pytest.raises(ContentType.DoesNotExist, message='does not exist'):
        log.new_value_as_python


def test_handling_records_for_deleted_columns():
    log = ChangeLog(content_type_id=1, object_id=15, column_name='soda_consumed', old_value='1', new_value='2')
    with pytest.raises(ContentType.DoesNotExist, message='column no longer exists'):
        log.new_value_as_python


def test_track_changes_for_floats_saved_to_integer_fields():
    """
    Some data discrepancy is caused by saving a float into an integer field. The model ends up
    with a whole number but the change record records the float.
    """

    p = Person(donuts_consumed=1.2)
    p.save()
    logs = ChangeLog.objects.filter(column_name='donuts_consumed')
    assert logs[0].new_value_as_python == 1


def test_track_changes_after_db_pull():
    p = Person(first_name='Bob', last_name='Smith')
    p.save()
    assert ChangeLog.objects.count() == 3

    p1 = Person.objects.get(pk=p.pk)
    p1.first_name = 'Sally'
    p1.save()
    assert ChangeLog.objects.count() == 4


def test_form_save():
    class PersonForm(forms.ModelForm):
        class Meta(object):
            model = Person
            fields = ('id', 'first_name', 'last_name')

    person = Person(first_name='John', last_name='Smith')
    person.save()

    assert ChangeLog.objects.count() == 3

    post_data = {
        'first_name': 'Sally',
        'last_name': 'Jones'
    }

    form = PersonForm(post_data, instance=person)
    form.save()

    assert ChangeLog.objects.count() == 5


def test_nominal():
    tm = TrackedModel()
    tm.ordinal = 1
    tm.save()

    tm.ordinal = 2
    tm.save()

    assert ChangeLog.objects.count() == 2


def test_changes_log():
    """Test that changes made to models are saved into the model change log"""
    person = UserProfile(first_name="Bob", username='')
    person.save()
    logs = ChangeLog.objects.filter(column_name="first_name")
    assert len(logs) == 1
    assert logs[0].user_id is None
    assert logs[0].column_name == 'first_name'
    assert logs[0].old_value is None
    assert logs[0].new_value == 'Bob'

    person.first_name = "Luke"
    person.save()
    logs = ChangeLog.objects.filter(column_name='first_name')
    assert len(logs) == 2
    assert logs[1].user_id is None
    assert logs[1].column_name == 'first_name'
    assert logs[1].old_value == 'Bob'
    assert logs[1].new_value == 'Luke'


def test_model_is_dirty_with_simple_field():
    """Test that a simple model detects changes properly"""
    # Unsaved models should always be "dirty"
    person = Person(first_name="Bob")
    assert person.is_dirty

    # saving inital state doesn't matter since this model has never been saved to the database
    person.save_initial_state()
    assert person.is_dirty

    person.save()
    assert not person.is_dirty

    # make a change, should be dirty
    person.first_name = "Bill"
    assert person.is_dirty

    # change it back, should be clean
    person.first_name = "Bob"
    assert not person.is_dirty


def test_is_dirty_with_inheritance():
    """Check that a subclassed model looks at it's parents fields as well"""
    person = UserProfile(first_name="Bob")
    assert person.is_dirty

    # saving inital state doesn't matter since this model has never been saved to the database
    person.save_initial_state()
    assert person.is_dirty
    person.save()

    # make a change
    person.first_name = "Bill"
    assert person.is_dirty

    # change it back
    person.first_name = "Bob"
    assert not person.is_dirty

    person.username = 'bob@bob.com'
    assert person.is_dirty


def test_is_dirty_with_relationships():
    """Check that relationships are simplified into foreign key ids"""
    person = Person(first_name="Bob")
    person.investor_executive_id = 2

    assert person.is_dirty
    assert 'investor_executive_id' in person.dirty_fields
    assert person.changes_pending['investor_executive_id'][1] == 2
    person.save()

    assert not person.is_dirty


def test_records_default_values_as_changes():
    person = Person()
    assert len(person.changes_pending) == 3

    person = Person(preferred_ice_cream_flavor='Strawberry')
    assert len(person.changes_pending) == 3


def test_is_dirty_from_db_get():
    Person(first_name="Bob").save()

    p = Person.objects.get(first_name="Bob")
    assert not p.is_dirty


def test_is_dirty_from_db_filter():
    Person(first_name="Bob").save()

    p = Person.objects.filter(first_name="Bob")[0]
    assert not p.is_dirty


def test_find_unlogged_changes():
    Person(first_name="Bob").save()

    Person.objects.all().update(first_name="Sam")

    p = Person.objects.get(first_name="Sam")
    unlogged_data = p.find_unlogged_changes()

    assert len(unlogged_data) == 1

    assert unlogged_data['first_name'] == ('Bob', 'Sam')
