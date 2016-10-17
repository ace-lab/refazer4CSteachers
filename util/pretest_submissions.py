import argparse
import sqlite3

from evaluate import TEST_CONDITIONS, evaluate_function, stringify_input, stringify_output


def run_tests(database_cursor):

    cursor.execute("SELECT id, question_number, code FROM submissions")
    submissions = [
        {'id': row[0], 'question_number': row[1], 'code': row[2]}
        for row in cursor.fetchall()
    ]

    # For each submitted function, look up the corresponding test conditions.
    # Then save the results for every test case to the database.
    for submission in submissions:

        test_condition = TEST_CONDITIONS[submission['question_number']]
        results = evaluate_function(
            code_text=submission['code'],
            input_value_tuples=test_condition['input_value_tuples'],
            function_name=test_condition['function_name'],
            expected_outputs=test_condition['expected_outputs'],
        )

        for index, test_case in enumerate(results['test_cases']):
            cursor.execute('\n'.join([
                "INSERT INTO testresults(",
                "    submission_id, test_case_index, input_values, success, expected, observed)",
                "VALUES (?, ?, ?, ?, ?, ?)"
            ]), (submission['id'], index, stringify_input(test_case['input_values']),
                 test_case['success'], test_case['expected'], stringify_output(test_case))
            )


if __name__ == '__main__':
    argument_parser = argparse.ArgumentParser(
        description="Run tests on all existing submissions and save results to database"
    )
    argument_parser.add_argument(
        'database_file',
        help="Name of SQLite database file to dump data to."
    )
    args = argument_parser.parse_args()

    # Initialize the database
    db = sqlite3.connect(args.database_file)
    db.row_factory = sqlite3.Row
    cursor = db.cursor()

    # Run the code to load in student submission
    run_tests(cursor)
    db.commit()
