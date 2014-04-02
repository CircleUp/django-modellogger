from threading import currentThread

_requests = {}


class GlobalRequestMiddleware(object):
    """
    Allows access to the request variable from anywhere in the code.

    We use this to allow the model auditlog to save the user who makes a change.

    It's possible the thread aspect of this can be simplified. See the discussion here for
    more information: http://nedbatchelder.com/blog/201008/global_django_requests.html
    """
    def process_request(self, request):
        """Stick the request variable in global scope"""
        _requests[currentThread()] = request

    def process_response(self, request, response):
        """Clear the request from global scope as its finishing"""
        _requests.pop(currentThread(), None)
        return response


def get_request():
    """Returns the current request if it's available"""
    #pylint: disable=W0702
    try:
        return _requests[currentThread()]
    except:
        return None
