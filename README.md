# Installation


$ pip install django-modellogger

Add to in settings.py

    INSTALLED_APPS = [ 
        'modellogger',
        ...
    ]

    MIDDLEWARE_CLASSES = (
        'modellogger.middleware.GlobalRequestMiddleware',
        )

$ python manage.py syncdb

# Usage

    class Customer(TrackableModel):
        TRACK_CHANGES = True
