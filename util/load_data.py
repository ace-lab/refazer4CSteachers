import ast
from inspect import getblock
import argparse
import os
import json
import sqlite3


class FunctionFinder(ast.NodeVisitor):
    '''
    AST visitor that looks for a function definition with a specified
    name and non-empty body.
    '''

    def __init__(self, function_name, *args, **kwargs):
        
        super(self.__class__, self).__init__(*args, **kwargs)
        self.function_name = function_name

        # The last function found will be stored in this variable
        self.function = None

    def visit_FunctionDef(self, node):
        
        if node.name != self.function_name:
            return

        # Look for evidence that this function contains more than
        # no-ops (e.g., pass or comment strings).
        function_changed = False
        for child in node.body:
            if isinstance(child, ast.Pass):
                continue
            elif isinstance(child, ast.Expr) and isinstance(child.value, ast.Str):
                continue
            function_changed = True
            break

        if function_changed:
            self.function = node


def extract_first_change(logs, function_name):
    '''
    Input: JSON logs for one student.
    '''

    # Order the logs by server upload date
    sorted_logs = sorted(logs, key=lambda e: e['server_time'])

    # Look for the first event where the function was changed
    for log_event in sorted_logs:

        code = log_event['messages']['file_contents']['hw02.py']
        parse_tree = ast.parse(code)

        # If the function finder has a non-null function property after
        # visiting the code, then a function with non-noop contents has been found.
        visitor = FunctionFinder(function_name)
        visitor.visit(parse_tree)
        if visitor.function is not None:

            # Split code by line, but add newlines back into each line
            code_lines = code.split('\n')
            for line_index in range(len(code_lines)):
                code_lines[line_index] += '\n'

            start_lineno = visitor.function.lineno
            start_line_index = start_lineno - 1

            # XXX this code uses an undocumented function from the 'inspect' library,
            # 'getblock' to find the lines of code that correspond to the function.
            # In the worst case, we could look at the code of getblock and replicate
            # it here if getblock stops being accessible through the inspect module.
            function_code_lines = getblock(code_lines[start_line_index:])
            function_code = ''.join(function_code_lines).rstrip('\n')
            return function_code

    return None


def save_submission(question_number, student_id, code, cursor):
    cursor.execute('\n'.join([
        "INSERT INTO submissions(question_number, submission_id, code)",
        "VALUES(?, ?, ?)",
    ]), (question_number, student_id, code))


def load_submissions(submissions_dir, function_names, database_cursor):

    # Open the log file for each student
    for student_index, student_id in enumerate(os.listdir(submissions_dir)):

        data_filename = os.path.join(submissions_dir, student_id, 'backups.json')
        with open(data_filename) as student_data_file:
            student_data = json.load(student_data_file)

            # For each function requestsed, consider it a new "question".
            # Find the first change that the student made for this question.
            # If there was at least one, save it to the atabase.
            for question_index, function_name in enumerate(function_names):
                first_change_code = extract_first_change(student_data, function_name)
                if first_change_code is not None:
                    save_submission(question_index, student_index, first_change_code, cursor)


if __name__ == '__main__':
    argument_parser = argparse.ArgumentParser(
        description="Load student's first changes to a function into the database"
    )
    argument_parser.add_argument(
        'submissions_dir',
        help="Directory of student submissions"
    )
    argument_parser.add_argument(
        'database_file',
        help="Name of SQLite database file to dump data to."
    )
    argument_parser.add_argument(
        'function_names',
        nargs='+',
        help="Names of functions for which a student's first changes will be extracted."
    )
    args = argument_parser.parse_args()

    # Initialize the database
    db = sqlite3.connect(args.database_file)
    db.row_factory = sqlite3.Row
    cursor = db.cursor()

    # Run the code to load in student submission
    load_submissions(args.submissions_dir, args.function_names, cursor)
    db.commit()
