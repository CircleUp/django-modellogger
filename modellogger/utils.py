def dict_diff(old, new):
    """Return the difference between the two dicts"""
    return {key: (value, new[key]) for key, value in old.items() if value != new[key]}