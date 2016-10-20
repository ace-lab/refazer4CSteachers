import unittest
import os.path
import sqlite3

from util.conditions import sample_submissions, get_submissions_working_set


class GetWorkingSetTest(unittest.TestCase):

    def setUp(self):

        # Create an in-memory database for tests
        self.db = sqlite3.connect(':memory:')
        self.db.row_factory = sqlite3.Row
        self.cursor = self.db.cursor()
        
        # Initialize the database
        # Note that at the time of writing this, the initializations script
        # added both users with 'admin' and 'user' usernames.
        schema_filename = os.path.join('db', 'init.sql')
        with open(schema_filename) as schema_file:
            schema_sql = schema_file.read()
            self.cursor.executescript(schema_sql)

        # Fetch ID for user1 from the database, so we can insert recrods for this user
        self.cursor.execute("SELECT id FROM users WHERE username=\"user1\"")
        self.user1_id = self.cursor.fetchone()[0]

        # Insert submission samples that will be pre-queried
        self.cursor.executemany('\n'.join([
            "INSERT INTO submission_samples(user_id, question_number, submission_id, sample_type)",
            "VALUES(?, ?, ?, ?)",
        ]), [
            (self.user1_id, 0, 1, "stratified"),
            (self.user1_id + 1, 0, 2, "stratified"),  # This one should be ignored: wrong user
            (self.user1_id, 1, 2, "stratified"),  # This one should be ignored: wrong question
            (self.user1_id, 0, 3, "stratified"),
            (self.user1_id, 0, 4, "stratified"),
            (self.user1_id, 0, 5, "fixes_split1"),
            (self.user1_id, 0, 6, "fixes_split1"),
            (self.user1_id, 0, 7, "fixes_split2"),
            (self.user1_id, 0, 8, "fixes_split2"),
        ])

        # For admins, we will fetch all submissions that don't pass all test cases
        # So, we need to insert a bunch of submissions and test results.
        self.cursor.executemany('\n'.join([
            "INSERT INTO submissions(id, question_number, submission_id, code)",
            "VALUES(?, ?, ?, \"code\")",
        ]), [
            (1, 0, 1),
            (2, 1, 2),  # questions without the specified question number should be ignored
            (3, 0, 3),
            (4, 0, 4),
        ])
        self.cursor.executemany('\n'.join([
            "INSERT INTO testresults(submission_id, test_case_index, test_type, success)",
            "VALUES(?, ?, \"input-output\", ?)",
        ]), [
            # Ignore this first one---it passes all of the test cases
            (1, 0, True),
            (1, 1, True),
            (1, 2, True),
            (1, 3, True),
            (1, 4, True),
            # Ignore this one---wrong question number
            (2, 0, False),
            (2, 1, False),
            (2, 2, False),
            (2, 3, False),
            (2, 4, False),
            # Both submissions 3 and 4 should be found.  They both fail
            # at least one test case.
            (3, 0, False),
            (3, 1, False),
            (3, 2, True),
            (3, 3, False),
            (3, 4, False),
            (4, 0, False),
            (4, 1, False),
            (4, 2, False),
            (4, 3, True),
            (4, 4, False),
        ])

    def test_get_all_untested_submissions_for_admin_in_any_interface(self):
        for interface in ['A', 'B', 'C']:
            working_set = get_submissions_working_set(
                self.cursor,
                username='admin1',
                question_number=0,
                interface='A'
            )
            self.assertEqual(working_set, [3, 4])

    def test_get_stratified_sample_for_user_in_interface_a(self):
        working_set = get_submissions_working_set(
            self.cursor,
            username='user1',
            question_number=0,
            interface='A',
        )
        self.assertEqual(working_set, [1, 3, 4])

    def test_get_fixes_sample_for_user_in_interface_b(self):
        working_set = get_submissions_working_set(
            self.cursor,
            username='user1',
            question_number=0,
            interface='B',
        )
        self.assertEqual(working_set, [5, 6])

    def test_get_another_fixes_sample_for_user_in_interface_c(self):
        working_set = get_submissions_working_set(
            self.cursor,
            username='user1',
            question_number=0,
            interface='C',
        )
        self.assertEqual(working_set, [7, 8])


class DivideSubmissionsTest(unittest.TestCase):

    def test_choose_submissions_round_robin(self):
        indexes = (
            (1, 2, 3, 4),
            (5, 6, 7),
            (8, 9),
        )
        samples = sample_submissions(
            indexes,
            sample_size=5,
            users=1,
        )
        user1_samples = samples[0]
        self.assertEqual(len(user1_samples), 5)
        self.assertIn(user1_samples[0], (1, 2, 3, 4))
        self.assertIn(user1_samples[1], (5, 6, 7))
        self.assertIn(user1_samples[2], (8, 9))
        self.assertIn(user1_samples[0], (1, 2, 3, 4))

    def test_function_does_not_destroy_order_of_input(self):
        indexes = (
            (1, 2, 3, 4),
            (5, 6, 7),
            (8, 9),
        )
        samples = sample_submissions(
            indexes,
            sample_size=5,
            users=1,
        )
        self.assertEqual(indexes, (
            (1, 2, 3, 4),
            (5, 6, 7),
            (8, 9),
        ))

    def test_ignore_smaller_groups(self):
        indexes = (
            (1, 2, 3, 4),
            (5, 6, 7),
            (8, 9),
        )
        samples = sample_submissions(
            indexes,
            sample_size=5,
            users=1,
            n_top_groups=2,  # this specifies how many of the largest groups we sample from
        )
        user1_samples = samples[0]
        self.assertIn(user1_samples[0], (1, 2, 3, 4))
        self.assertIn(user1_samples[1], (5, 6, 7))
        self.assertIn(user1_samples[0], (1, 2, 3, 4))

    def test_no_repetitions_even_from_small_bins(self):
        indexes = (
            (1, 2, 3, 4),
            (8,),
        )
        samples = sample_submissions(
            indexes,
            sample_size=5,
            users=1,
        )
        user1_samples = samples[0]
        self.assertIn(user1_samples[0], (1, 2, 3, 4))
        self.assertIn(user1_samples[1], (8,))
        self.assertIn(user1_samples[0], (1, 2, 3, 4))
        self.assertIn(user1_samples[0], (1, 2, 3, 4))  # don't return to group 1---no resampling!

    def test_consecutive_users_have_distinct_entries(self):
        indexes = (
            (1, 2, 3, 4),
            (5, 6, 7),
            (8, 9),
        )
        samples = sample_submissions(
            indexes,
            sample_size=4,
            users=2,
        )
        user1_samples = samples[0]
        user2_samples = samples[1]
        self.assertEqual(len(user1_samples), 4)
        self.assertEqual(len(user2_samples), 4)
        for user1_index in user1_samples:
            self.assertNotIn(user1_index, user2_samples)
        for user2_index in user2_samples:
            self.assertNotIn(user2_index, user1_samples)

    def test_sampling_bans_reset_with_new_users(self):
        indexes = (
            (1, 2, 3, 4),
            (5, 6, 7),
            (8, 9),
        )
        samples = sample_submissions(
            indexes,
            sample_size=6,
            users=2,
        )
        # While 8 and 9 will be blacklisted for user 1 after it is sampled for them,
        # user 2 should still be able to sample 8 and 9.  In other words, while the
        # round-robin pointer continues to rotate, the blacklist for any item
        # resets when we sample for each new user.
        user1_samples = samples[0]
        user2_samples = samples[1]
        self.assertIn(8, samples[0])
        self.assertIn(9, samples[0])
        self.assertIn(8, samples[1])
        self.assertIn(9, samples[1])
