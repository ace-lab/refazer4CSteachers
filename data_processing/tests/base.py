#! /usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals
import logging
from abc import ABCMeta
import unittest
from peewee import SqliteDatabase
from playhouse.test_utils import test_database


logger = logging.getLogger('data')
test_db = SqliteDatabase(':memory:')


class TestCase(unittest.TestCase):
    '''
    A test case that runs database transactions in a temporary test database.
    This class is based on the test class from:
    http://stackoverflow.com/questions/15982801#answer-25894837
    '''

    __metaclass__ = ABCMeta

    def __init__(self, models, *args, **kwargs):
        super(TestCase, self).__init__(*args, **kwargs)
        self.models = models

    def run(self, result=None):
        with test_database(test_db, self.models):
            super(TestCase, self).run(result)
