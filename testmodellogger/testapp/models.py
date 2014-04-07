from django.db import models
from modellogger.models import TrackableModel


class TrackedModel(TrackableModel):
    TRACK_CHANGES = True
    ordinal = models.PositiveIntegerField(null=True, default=None)


class Person(TrackableModel):
    TRACK_CHANGES = True
    first_name = models.CharField(max_length=100, blank=True, default='')
    last_name = models.CharField(max_length=100, blank=True, default='')
    investor_executive = models.ForeignKey('self', null=True)
    donuts_consumed = models.PositiveIntegerField(null=True, default=None)
    preferred_ice_cream_flavor = models.CharField(max_length=100, default='Vanilla')


class UserProfile(Person):
    TRACK_CHANGES = True
    EXCLUDED_TRACKING_FIELDS = ['person_ptr_id', 'password']

    username = models.CharField(max_length=40, default='')
    identity_verification_user = models.ForeignKey('UserProfile', null=True, related_name="+")
    account_balance = models.FloatField(null=True, default=None)
    date_joined = models.DateTimeField(null=True, default=None)

