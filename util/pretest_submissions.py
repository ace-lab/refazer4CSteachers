import argparse
import sqlite3
import logging

from evaluate import TEST_CONDITIONS, evaluate_function, stringify_input, stringify_output


logging.basicConfig(level=logging.DEBUG, format="%(message)s")


def run_tests(database_cursor):

    cursor.execute("SELECT id, question_number, code FROM submissions")
    submissions = [
        {'id': row[0], 'question_number': row[1], 'code': row[2]}
        for row in cursor.fetchall()
    ]

    # For each submitted function, look up the corresponding test conditions.
    # Then save the results for every test case to the database.
    for submission_index, submission in enumerate(submissions):

        print("Testing submission:", submission_index)

        test_condition = TEST_CONDITIONS[submission['question_number']]
        results = evaluate_function(
            code_text=submission['code'],
            function_name=test_condition['function_name'],
            input_value_tuples=test_condition.get('input_value_tuples'),
            expected_outputs=test_condition.get('expected_outputs'),
            assertions=test_condition.get('assertions'),
            test_code=test_condition.get('test_code'),
            pre_code=test_condition.get('pre_code'),
        )

        for index, test_case in enumerate(results['test_cases']):

            # If this is an input-output example or if test code was run,
            # process the test case (changing it a bit)
            # and getting a human-readable string version of the output
            if test_case['test_type'] in ['input-output', 'test_code']:
                readable_output = stringify_output(test_case)
            else:
                readable_output = None

            if test_case['test_type'] == 'input-output':
                input_values = stringify_input(test_case.get('input_values'))
            else:
                input_values = test_case.get('test_code')

            # Save the test results to the database
            readable_output if test_case['test_type'] in ['input-output', 'test_code'] else None,
            cursor.execute('\n'.join([
                "INSERT INTO testresults(",
                "    submission_id, test_case_index, test_type, success,",
                "    input_values, expected, observed, assertion)",
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
            ]), (
                submission['id'],
                index,
                test_case['test_type'],
                test_case['success'],
                input_values,
                test_case.get('expected'),
                readable_output,
                test_case.get('assertion'),
            ))


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
