from django.db import models
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from django.db.models.signals import post_save, post_delete
from middleware import get_request


def reset_model_state(sender, instance, **kwargs):
    """Reset a dirty model to clean"""
    instance.reset_state()
    pass


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
    instance.reset_state()


class ChangeLog(models.Model):
    """Used to record field-level changes to models"""
    timestamp = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(User, null=True, default=None)
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    content_object = generic.GenericForeignKey()
    column_name = models.CharField(max_length=150)
    old_value = models.TextField(null=True, blank=True)
    new_value = models.TextField(null=True, blank=True)

    class Meta(object):
        """Object metaclass"""
        db_table = u'log_model_change'

    def __str__(self):
        return str(self.timestamp) + ' ' + self.column_name + ' changed to ' + self.new_value

class TrackableModel(models.Model):
    EXCLUDED_TRACKING_FIELDS = ['created_on', 'updated_on', 'id']
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)

    def __init__(self, *args, **kwargs):
        super(TrackableModel, self).__init__(*args, **kwargs)

        if hasattr(self.__class__, 'TRACK_CHANGES') and self.__class__.TRACK_CHANGES:
            post_save.connect(save_model_changes, sender=self.__class__, dispatch_uid='DirtyRecord-%s' % self.__class__.__name__)
        else:
            post_save.connect(reset_model_state, sender=self.__class__, dispatch_uid='DirtyRecord-%s' % self.__class__.__name__)
        self.reset_state()

    # we need these methods from Record
    def _excluded_tracking_fields(self):
        """Which fields do we not track"""
        return getattr(self.__class__, 'EXCLUDED_TRACKING_FIELDS', []) + TrackableModel.EXCLUDED_TRACKING_FIELDS

    def _empty_dict(self):
        """An empty dict version of the model - populated with defaults"""
        return dict([(f.attname, f.get_default()) for f in self._meta.fields if not f.attname in self._excluded_tracking_fields()])

    def _as_dict(self):
        """Converts the model to a dictionary in a way conducive to logging"""
        return dict([(f.attname, getattr(self, f.attname)) for f in self._meta.fields if not f.attname in self._excluded_tracking_fields()])

    def reset_state(self):
        """
        Set the model to a clean state

        This is called after the model is saved
        """
        if not self.pk:
            self._original_state = self._empty_dict()
        else:
            self._original_state = self._as_dict()

    @property
    def changes_pending(self):
        """Which fields are dirty and what changes are being made to them?"""
        new_state = self._as_dict()
        return dict([(key, (value, new_state[key])) for key, value in self._original_state.iteritems() if value != new_state[key]])

    class Meta(object):
        """Object metaclass"""
        abstract = True
