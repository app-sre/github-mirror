"""Functions to help waiting for a given state"""

import time


def wait_for(func, timeout, first=0.0, step=1.0, args=None, kwargs=None):
    """Wait until func() evaluates to True.

    If func() evaluates to True before timeout expires, return the
    value of func(). Otherwise return None.

    :param timeout: Timeout in seconds
    :param first: Time to sleep before first attempt
    :param step: Time to sleep between attempts in seconds
    :param args: Positional arguments to func
    :param kwargs: Keyword arguments to func
    """
    if args is None:
        args = []
    if kwargs is None:
        kwargs = {}
    start_time = time.monotonic()
    end_time = start_time + timeout
    time.sleep(first)
    while time.monotonic() < end_time:
        result = func(*args, **kwargs)
        if result:
            return result
        time.sleep(step)
    return None
