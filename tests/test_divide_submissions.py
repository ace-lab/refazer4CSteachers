import unittest

from util.conditions import sample_submissions


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
