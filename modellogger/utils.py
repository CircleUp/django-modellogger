def zdict_diff(old, new):
    return dict([(key, (value, new[key])) for key, value in old.items() if value != new[key]])

def dict_diff(old, new):
    return {key: (value, new[key]) for key, value in old.items() if value != new[key]}