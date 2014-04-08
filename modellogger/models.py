from django.db import models
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from django.db.models.fields import FieldDoesNotExist
from django.db.models.signals import post_save, pre_save
from middleware import get_request

CONTENT_TYPES_DICT = None

def xstr(s):
    return '' if s is None else str(s)

def content_type_dict():
    global CONTENT_TYPES_DICT
    if not CONTENT_TYPES_DICT:
        content_types = ContentType.objects.all()
        CONTENT_TYPES_DICT = dict([(ct.id, ct.model_class()) for ct in content_types])
    return CONTENT_TYPES_DICT


def mark_from_db(sender, instance, **kwargs):
    """Lets modellogger know if this object came from the database"""
    if instance._state.db:
        instance._from_db = True


def save_initial_model_state(sender, instance, **kwargs):
    """Reset a dirty model to clean"""
    instance.save_inital_state()


def save_model_changes(sender, instance, **kwargs):
    """Save a log of dirty model changes and reset the model to clean"""
    changes = instance.changes_pending
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
    instance.save_inital_state()


class ChangeLog(models.Model):
    """Used to record field-level changes to models"""
    timestamp = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(User, null=True, default=None, on_delete=models.PROTECT)
    content_type = models.ForeignKey(ContentType, on_delete=models.PROTECT)
    object_id = models.PositiveIntegerField()
    content_object = generic.GenericForeignKey()
    column_name = models.CharField(max_length=150)
    old_value = models.TextField(null=True, blank=True)
    new_value = models.TextField(null=True, blank=True)

    class Meta(object):
        """Object metaclass"""
        db_table = u'log_model_change'

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

        # what action is taken after each save?
        post_save_method = save_initial_model_state
        try:
            if self.__class__.TRACK_CHANGES:
                post_save_method = save_model_changes
        except AttributeError:
            pass

        post_save.connect(post_save_method, sender=self.__class__, dispatch_uid='DirtyRecord-%s' % self.__class__.__name__)

        pre_save.connect(mark_from_db, sender=self.__class__, dispatch_uid='MarkFromDb-%s' % self.__class__.__name__)

        # set the initial state
        self.save_inital_state()

    # we need these methods from Record
    def _excluded_tracking_fields(self):
        """Which fields do we not track"""
        return getattr(self.__class__, 'EXCLUDED_TRACKING_FIELDS', []) + TrackableModel.EXCLUDED_TRACKING_FIELDS

    def _empty_dict(self):
        """An empty dict version of the model"""
        return dict([(f.attname, None) for f in self._meta.fields if not f.attname in self._excluded_tracking_fields()])

    def _default_dict(self):
        """An empty dict version of the model - populated with defaults"""
        return dict([(f.attname, f.get_default()) for f in self._meta.fields if not f.attname in self._excluded_tracking_fields()])

    def _as_dict(self):
        """Converts the model to a dictionary in a way conducive to logging"""
        return dict([(f.attname, f.get_prep_value(getattr(self, f.attname))) for f in self._meta.fields if not f.attname in self._excluded_tracking_fields()])

    def reset_state(self):
        self.save_inital_state()

    def save_inital_state(self):
        """
        Set the model to a clean state

        This is called after the model is saved
        """
        self._original_state = self._as_dict()
        self._from_db = False
        if self._state.db:
            self._from_db = True

    @property
    def original_state(self):
        if self._from_db:
            return self._original_state
        return self._empty_dict()

    @property
    def dirty_fields(self):
        """Which fields are dirty?"""
        new_state = self._as_dict()
        return [key for key, value in self.original_state.iteritems() if value != new_state[key]]

    @property
    def is_dirty(self):
        """Has the model changed since it was last saved?"""
        return bool(self.dirty_fields)

    @property
    def changes_pending(self):
        """Which fields are dirty and what changes are being made to them?"""
        new_state = self._as_dict()
        return dict([(key, (value, new_state[key])) for key, value in self.original_state.iteritems() if value != new_state[key]])

    class Meta(object):
        """Object metaclass"""
        abstract = True
