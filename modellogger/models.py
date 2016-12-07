from __future__ import absolute_import

from django.db import models
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import fields
from django.db import router, connections
from django.db.models.fields import FieldDoesNotExist
from django.db.models.signals import post_save
from django.dispatch import Signal
from modellogger.utils import dict_diff, UNSET, xstr, content_type_dict

from .middleware import get_request


def mark_from_db(sender, instance, **kwargs):
    """Lets modellogger know that this object came from the database"""
    instance._from_db = True


def save_initial_model_state(sender, instance, **kwargs):
    """Reset a dirty model to clean"""
    instance.save_initial_state()


def save_model_changes(sender, instance, **kwargs):
    """Save a log of dirty model changes and reset the model to clean"""
    changes = instance._changes_pending_no_check_db
    changelog_objects = []
    request = get_request()
    for column_name, (old_value, new_value) in changes.items():
        if column_name == 'id':
            continue
        changelog = ChangeLog(content_object=instance, column_name=column_name, old_value=old_value, new_value=new_value)
        if request and request.user and request.user.id:
            changelog.user_id = request.user.id
        changelog_objects.append(changelog)

    ChangeLog.objects.bulk_create(changelog_objects)
    instance.save_initial_state()
    if changes:
        model_changes_saved.send(sender=sender, instance=instance, changes=changes)


model_changes_saved = Signal(providing_args=["instance", "changes"])


class ChangeLog(models.Model):
    """Used to record field-level changes to models"""
    timestamp = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, default=None, on_delete=models.PROTECT)
    content_type = models.ForeignKey(ContentType, on_delete=models.PROTECT)
    object_id = models.PositiveIntegerField()
    content_object = fields.GenericForeignKey()
    column_name = models.CharField(max_length=150)
    old_value = models.TextField(null=True, blank=True)
    new_value = models.TextField(null=True, blank=True)

    class Meta(object):
        """Object metaclass"""
        db_table = u'log_model_change'
        index_together = [
            ["content_type", "object_id"]
        ]

    @property
    def new_value_as_python(self):
        return self._value_to_python(self.new_value)

    @property
    def old_value_as_python(self):
        return self._value_to_python(self.old_value)

    def _value_to_python(self, value):
        try:
            model_class = content_type_dict()[self.content_type_id]
        except KeyError:
            raise ContentType.DoesNotExist('Django ContentType %i does not exist' % self.content_type_id)

        try:
            field_class = model_class._meta.get_field_by_name(self.column_name)[0]
        except FieldDoesNotExist:
            raise ContentType.DoesNotExist('the %s column no longer exists in the %s model' % (self.column_name, str(model_class)))

        return field_class.to_python(value)

    def __str__(self):
        return xstr(self.timestamp) + ' ' + self.column_name + ' changed to ' + xstr(self.new_value)


class TrackableModel(models.Model):
    EXCLUDED_TRACKING_FIELDS = ['created_on', 'updated_on', 'id']
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)

    def __init__(self, *args, **kwargs):
        super(TrackableModel, self).__init__(*args, **kwargs)
        self.__class__.class_setup()
        self._from_db = self.pk is not None
        self.save_initial_state()

    @classmethod
    def class_setup(cls):
        """
        Setup the class according to the options specified in it's class definition.

        The correct way to do this would be with a metaclass but I couldn't figure
        out how to safely override the django metaclass. It broke the UserProfile object for some reason.
        """

        # use this flag where the value must equal the class name in order to account for inheritance
        # For example if Person has TrackChanges = True and Employee(Person) has TrackChanges = False.  If we naively
        # only check if the flag is set then when we're running class setup for Employee it will find that the flag was
        # already set when class_setup was called for Person.
        if not getattr(cls, '_trackable_model_initialized', '') == cls.__name__:
            cls._trackable_model_initialized = cls.__name__
            # cache results at the class level - there is certainly a more correct way to do this
            if '_excluded_tracking_fields' not in cls.__dict__:
                # Which fields do we not track
                cls._excluded_tracking_fields = getattr(cls, 'EXCLUDED_TRACKING_FIELDS', []) + TrackableModel.EXCLUDED_TRACKING_FIELDS
                cls._fields_minus_exclusions = [f for f in cls._meta.fields if f.attname not in cls._excluded_tracking_fields]

            # what action is taken after each save?
            post_save_method = save_initial_model_state
            try:
                if cls.TRACK_CHANGES:
                    post_save_method = save_model_changes
            except AttributeError:
                pass

            post_save.connect(post_save_method, sender=cls, dispatch_uid='DirtyRecord-%s' % cls.__name__)
            post_save.connect(mark_from_db, sender=cls, dispatch_uid='MarkFromDb-%s' % cls.__name__)

    def _empty_dict(self):
        """An empty dict version of the model"""
        return {f.attname: UNSET for f in self._fields_minus_exclusions}

    def _as_dict_no_prep(self):
        """The model's state as a dictionary (without passing through prep value)

        This is an optimization over using _as_dict for cases where the object is unlikely to be modified.
        For example if we're creating 1000 objects for display only.  Calling get_prep_value across 1000 objects x # of fields
        actually adds up to a lot of cpu time. Because we don't call get_prep_value here, we call it when the _original_state value is used in
        _original_state_no_check_db
        """
        return {f.attname: getattr(self, f.attname) for f in self._fields_minus_exclusions}

    def _as_dict(self):
        """Converts the model to a dictionary in a way conducive to logging"""
        return {f.attname: f.get_prep_value(getattr(self, f.attname)) for f in self._fields_minus_exclusions}

    def save_initial_state(self):
        """
        Set the model to a clean state

        This is called after the model is initialized or saved
        """
        self._original_state = self._as_dict_no_prep()

    @property
    def _original_state_no_check_db(self):
        """When called from the post_save signal we want the original state"""
        if not self._from_db:
            return self._empty_dict()
        return {f.attname: f.get_prep_value(self._original_state[f.attname]) for f in self._fields_minus_exclusions}

    @property
    def dirty_fields(self):
        """Which fields are dirty?"""
        return self._changes_pending_no_check_db.keys()

    @property
    def is_dirty(self):
        """Has the model changed since it was last saved?"""
        return bool(self.dirty_fields)

    @property
    def changes_pending(self):
        """Which fields are dirty and what changes are being made to them?"""
        return self._changes_pending_no_check_db

    @property
    def _changes_pending_no_check_db(self):
        """Which fields are dirty and what changes are being made to them?"""
        return dict_diff(self._original_state_no_check_db, self._as_dict())

    def find_unlogged_changes(self):
        """Compares the current object to the most recent values stored in the ChangeLog"""
        if self.pk is None:
            return {}

        content_type = ContentType.objects.get_for_model(self)
        sql = """
        SELECT lmc.column_name, lmc.`new_value`
        FROM (
            SELECT lmc.`column_name`, MAX(id) AS most_recent_id
            FROM log_model_change lmc
            WHERE lmc.`object_id` = {object_id} AND lmc.`content_type_id`={content_type_id}
            GROUP BY lmc.`column_name`
            ) a
        INNER JOIN log_model_change lmc ON lmc.id = a.most_recent_id
        """
        sql = sql.format(object_id=self.pk, content_type_id=content_type.pk)
        db_name = router.db_for_read(ChangeLog)
        with connections[db_name].cursor() as cursor:
            cursor.execute(sql)
            rows = cursor.fetchall()
        logged_data = {n: v for n, v in rows}
        changes = dict_diff(logged_data, self._as_dict())
        unlogged_changes = {}
        for col_name, (log_version, obj_version) in changes.items():
            if obj_version != UNSET:
                unlogged_changes[col_name] = (log_version, obj_version)

        return unlogged_changes

    class Meta(object):
        """Object metaclass"""
        abstract = True
