#! /usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals
import logging
import fcntl
import functools


logger = logging.getLogger('data')


def lock_method(lock_filename):
    ''' Use an OS lock such that a method can only be called once at a time. '''

    def decorator(func):

        @functools.wraps(func)
        def lock_and_run_method(*args, **kwargs):

            # Only run this program if it's not already running
            # Snippet based on
            # http://linux.byexamples.com/archives/494/how-can-i-avoid-running-a-python-script-multiple-times-implement-file-locking/
            fp = open(lock_filename, 'w')
            try:
                fcntl.lockf(fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except IOError:
                raise SystemExit(
                    "This program is already running.  Please stop the current process or " +
                    "remove " + lock_filename + " to run this script."
                )

            return func(*args, **kwargs)

        return lock_and_run_method

    return decorator
