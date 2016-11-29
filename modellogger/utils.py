from django.contrib.contenttypes.models import ContentType


class UnsetValue(object):
    def __repr__(self):
        return '<- UNSET ->'


UNSET = UnsetValue()

_CONTENT_TYPES_DICT = None


def xstr(s):
    return '' if s is None else str(s)


def content_type_dict():
    global _CONTENT_TYPES_DICT
    if not _CONTENT_TYPES_DICT:
        content_types = ContentType.objects.all()
        _CONTENT_TYPES_DICT = {ct.id: ct.model_class() for ct in content_types}
    return _CONTENT_TYPES_DICT


def dict_diff(old, new):
    """Return the difference between the two dicts"""
    return {key: (value, new[key]) for key, value in old.items() if value != new[key]}
