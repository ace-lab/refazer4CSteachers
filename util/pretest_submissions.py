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

        test_condition = TEST_CONDITIONS[submission['question_number']]
        logging.debug("Now testing submission %d", submission_index)
        results = evaluate_function(
            code_text=submission['code'],
            function_name=test_condition['function_name'],
            input_value_tuples=test_condition.get('input_value_tuples'),
            expected_outputs=test_condition.get('expected_outputs'),
            assertions=test_condition.get('assertions'),
        )

        for index, test_case in enumerate(results['test_cases']):

            # If this is an input-output example, process the test case (changing it a bit)
            # and getting a human-readable string version of the output
            if test_case['test_type'] == 'input-output':
                readable_output = stringify_output(test_case)

            # Save the test results to the database
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
                stringify_input(test_case.get('input_values')),
                test_case.get('expected'),
                readable_output if test_case['test_type'] == 'input-output' else None,
                test_case.get('assertion'),
            ))

        print("Finished with submission for question", submission['question_number'])


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
