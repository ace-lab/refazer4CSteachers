import unittest
import datetime

from util.load_data import extract_first_change, prettify_code


def _make_log_message(function_name, timestamp, contents):
    return {
        'messages': {
            'analytics': {
                'question': [function_name]
            },
            'file_contents': {
                'hw02.py': contents,
            },
        },
        'server_time': timestamp,
    }


class TestPrettify(unittest.TestCase):

    def test_spacing_added_around_operators(self):
        prettified = prettify_code("a=2+1\n")
        self.assertEqual(prettified, "a = 2 + 1\n")

    def test_multiline_comments_removed(self):
        prettified = prettify_code('\n'.join([
            "def func():",
            "    ''' This docstring will be removed '''",
            "    pass",
            "",
        ]))
        self.assertEqual(prettified, '\n'.join([
            "def func():",
            "    pass",
            "",
        ]))

    def test_remove_YOUR_CODE_HERE_literal(self):
        prettified = prettify_code('\n'.join([
            "def func():",
            "    \"*** YOUR CODE HERE ***\"",
            "    '*** YOUR CODE HERE ***'",
            "    pass",
            ""
        ]))
        self.assertEqual(prettified, '\n'.join([
            "def func():",
            "    pass",
            ""
        ]))


class ExtractFirstChangeTest(unittest.TestCase):

    def test_ignore_repeated_submission_for_function_if_function_unchanged(self):
        logs = [
            _make_log_message(
                'func', 
                datetime.datetime(2016, 1, 1, 12, 0, 0, 0),
                '\n'.join([
                    "def func():",
                    "    ''' insert code here '''",
                ])
            ),
            _make_log_message(
                'func', 
                datetime.datetime(2016, 1, 1, 12, 0, 1, 0),
                '\n'.join([
                    "def func():",  # This is the same version of the method as before
                    "    ''' insert code here '''",
                ])
            ),
        ]
        code = extract_first_change(logs, function_name='func')
        self.assertIsNone(code)

    def test_extract_change_for_function(self):
        logs = [
            _make_log_message(
                'func', 
                datetime.datetime(2016, 1, 1, 12, 0, 0, 0),
                '\n'.join([
                    "def not_func():",
                    "    ''' insert code here '''",
                    "",
                    "def func():",
                    "    ''' insert code here '''",
                ])
            ),
            _make_log_message(
                'func', 
                datetime.datetime(2016, 1, 1, 12, 0, 1, 0),
                # Even though both "not_func" and "func" change here, we want to only
                # get the code from "func" changing.
                '\n'.join([
                    "def not_func():",
                    "    return 1",
                    "",
                    "def func():",
                    "    return 2",
                ])
            ),
        ]
        code = extract_first_change(logs, function_name='func')
        self.assertEqual(code, '\n'.join([
            "def func():",
            "    return 2",
        ]))

    def test_accept_first_submission_if_not_empty(self):
        logs = [
            _make_log_message(
                'func', 
                datetime.datetime(2016, 1, 1, 12, 0, 0, 0),
                '\n'.join([
                    "def func():",
                    "    return 1",
                ])
            ),
        ]
        code = extract_first_change(logs, function_name='func')
        self.assertEqual(code, '\n'.join([
            "def func():",
            "    return 1",
        ]))

    def test_accept_first_change_even_if_function_wasnt_the_named_change(self):
        logs = [
            _make_log_message(
                # Even though these edits were reported as affecting 'not_func',
                # we should still be able to capture the change that happened in 'func'
                # between these two revisions.
                'not_func', 
                datetime.datetime(2016, 1, 1, 12, 0, 0, 0),
                '\n'.join([
                    "def func():",
                    "    ''' insert code here '''",
                ])
            ),
            _make_log_message(
                'not_func', 
                datetime.datetime(2016, 1, 1, 12, 0, 1, 0),
                '\n'.join([
                    "def func():",
                    "    return 1",
                ])
            ),
        ]
        code = extract_first_change(logs, function_name='func')
        self.assertEqual(code, '\n'.join([
            "def func():",
            "    return 1",
        ]))

    def test_first_change_found_by_server_log_date_order(self):
        logs = [
            # Here, the log messages are reported from most recent to
            # oldest.  This test makes sure that we look from changes from
            # the oldest to the most recent submissions.
            _make_log_message(
                'not_func', 
                datetime.datetime(2016, 1, 1, 12, 0, 1, 0),
                '\n'.join([
                    "def func():",
                    "    return 1",
                ])
            ),
            _make_log_message(
                'not_func', 
                datetime.datetime(2016, 1, 1, 12, 0, 0, 0),
                '\n'.join([
                    "def func():",
                    "    ''' insert code here '''",
                ])
            ),
        ]
        code = extract_first_change(logs, function_name='func')
        self.assertEqual(code, '\n'.join([
            "def func():",
            "    return 1",
        ]))
