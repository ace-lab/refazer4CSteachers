import argparse
import random
import copy
import sqlite3


def get_test_case_groups_by_first_failure(cursor, submissions, question_number):
    '''
    This method groups submissions by
    their return value on the first test case they fail.
    '''
    test_case_groups = {}
    for submission in submissions:

        cursor.execute('\n'.join([
            "SELECT test_case_index, success, observed, test_type",
            "FROM testresults JOIN submissions ON submissions.id = testresults.submission_id",
            "WHERE",
            "    submissions.submission_id = ? AND",
            "    question_number = ?"
        ]), (submission['id'], question_number,))

        submission_failed = False
        failure_key = (None, None)

        # Search for the first test case that fails.
        # Make a key for its group based on which test case failed and what it returned.
        for (test_case_index, success, observed, test_type) in cursor.fetchall():
            if not success:
                if test_type == 'assertion':
                    outcome_key = success
                elif test_type == 'input-output':
                    outcome_key = observed
                failure_key = (test_case_index, outcome_key)
                break

        if failure_key not in test_case_groups:
            test_case_groups[failure_key] = []
        test_case_groups[failure_key].append(submission['id'])

    return test_case_groups


def sample_submissions(groups, sample_size, users, n_top_groups=None):
    '''
    For each participant (# of `users`), sample `sample_size` items from
    across groups of items.  `groups` is a tuple of tuples.  Items will be
    sampled from each group in round-robin fashion.

    Assumes that all submission indexes above are unique.
    This probably won't have the desired effect if the same submission
    appears in multiple groups (it might be sampled twice.
    '''

    # Shuffle each of the groups, non-destructively
    local_groups = copy.deepcopy(groups)
    shuffled_groups = []
    for g in local_groups:
        group_list = list(g)
        random.shuffle(group_list)
        shuffled_groups.append(group_list)

    # Sort groups from largest to smallest
    groups_sorted = sorted(shuffled_groups, key=lambda g: len(g), reverse=True)

    # Truncate to just the biggest groups
    if n_top_groups is not None:
        groups_sorted = groups_sorted[:n_top_groups]

    samples = []
    within_group_indexes = [0 for _ in range(len(groups_sorted))]

    for user_index in range(users):
        
        user_sample = []
        group_index = 0
        group_blacklist = [list() for _ in range(len(groups_sorted))]

        while len(user_sample) < sample_size:
            within_group_index = within_group_indexes[group_index]
            if within_group_index not in group_blacklist[group_index]:
                user_sample.append(groups_sorted[group_index][within_group_index])
                within_group_indexes[group_index] =\
                    (within_group_index + 1) %\
                    len(groups_sorted[group_index])
                group_blacklist[group_index].append(within_group_index)
            group_index = (group_index + 1) % len(groups_sorted)

        samples.append(user_sample)

    return samples


def main(database_filename, question_indexes, sample_size, n_top_groups):

    db = sqlite3.connect(database_filename)
    db.row_factory = sqlite3.Row
    cursor = db.cursor()

    # Fetch the IDs of all users
    cursor.execute("SELECT id FROM users WHERE username LIKE \"user%\"")
    user_ids = [row[0] for row in cursor.fetchall()]
    user_count = len(user_ids)

    index_groups = []
    for question_index in question_indexes:
        
        # Fetch a list of submission IDs for this question
        cursor.execute("SELECT submission_id FROM submissions WHERE question_number = ?", (question_index,))
        submissions = [{'id': row[0]} for row in cursor.fetchall()]

        # Sort the submissions by which test case they fail first and how
        test_case_groups = get_test_case_groups_by_first_failure(cursor, submissions, question_index)

        # Ignore the group of submissions that passed all the tests
        del(test_case_groups[(None, None)])

        # Divide the submissions into samples for each user
        for group in test_case_groups.values():
            index_groups.append(tuple(group))
        samples = sample_submissions(
            groups=index_groups,
            users=user_count,
            sample_size=sample_size,
            n_top_groups=n_top_groups
        )

        # Save the submission samples to the database
        for user_index, sample in enumerate(samples):
            for submission_id in sample:
                cursor.execute('\n'.join([
                    "INSERT INTO submission_samples(user_id, question_number, submission_id)",
                    "VALUES(?, ?, ?)"
                ]), (user_ids[user_index], question_index, submission_id))

    db.commit()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=(
        "Sample submissions into groups for each participant. " +
        "A sample will be collected for each user in the database with a username of the " +
        "pattern 'userN'."
    ))
    parser.add_argument(
        'database_file',
        help="Name of SQLite database file to dump data to."
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=20,
        help="Number of submissions to assign to each participant (default: %(default)s)"
    )
    parser.add_argument(
        "question_indexes",
        type=int,
        nargs='+',
        help="Which questions for which submissions should be sampled"
    )
    parser.add_argument(
        "--top-groups",
        type=int,
        help="How many of the largest groups to inspect when sampling (default: all)",
    )
    args = parser.parse_args()
    main(
        args.database_file,
        args.question_indexes,
        args.sample_size,
        args.top_groups
    )
