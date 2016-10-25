import logging
import datetime

from models import FixEvent, Session


logger = logging.getLogger('data')


'''
This file contains functions that help us create models with mostly default properties, but
with the ability to configure any one specific field without having to define the others.
This is particularly helpful when we need to create test data, but don't want our test
logic to include many lines of model definitions.
'''


def create_session(**kwargs):
    arguments = {
        'user_id': 0,
        'question_number': 1,
        'session_id': 0,
    }
    arguments.update(kwargs)
    return Session.create(**arguments)


def create_fix_event(**kwargs):
    arguments = {
        'compute_index': 0,
        'username': "user1",
        'session_id': 0,
        'question_number': 1,
        'submission_id': 2,
        'event_type': "applied",
        'timestamp': datetime.datetime(2000, 1, 1, 12, 0, 1, 0),
        'fix_suggested': None,
        'fix_used': None,
        'fix_changed': None,
    }
    arguments.update(kwargs)
    return FixEvent.create(**arguments)
