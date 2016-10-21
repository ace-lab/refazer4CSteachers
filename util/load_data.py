import ast
from inspect import getblock
import argparse
import os
import json
import sqlite3
import re
import autopep8
import pyminifier.minification
import pyminifier.token_utils

from util.old_code import create_grader_question


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


def prettify_code(code):
    '''
    Note: after removing docstrings, this may leave some methods empty, which will then fail to
    compile.  However, when this is called only on function source code with non-empty bodies, there
    won't be any problems.
    '''

    # Remove docstrings from the code
    # Based on the pyminifier source code (for example, see
    # https://github.com/liftoff/pyminifier/blob/master/pyminifier/__init__.py ).
    tokens = pyminifier.token_utils.listified_tokenizer(code)
    pyminifier.minification.remove_docstrings(tokens)
    code_without_docstrings = pyminifier.token_utils.untokenize(tokens)

    # Sometimes, code includes a "*** YOUR CODE HERE ***" string literal from
    # the original template for the code.  We remove that literal here.
    code_without_docstrings = re.sub(
        "^\s*(\"|')\*\*\* YOUR CODE HERE \*\*\*(\"|')[\t ]*$\n",
        "",
        code_without_docstrings,
        flags=re.MULTILINE,
    )

    # Adjust spacing to Pep8 standards
    code_with_spaces_fixed = autopep8.fix_code(code_without_docstrings)

    return code_with_spaces_fixed


def extract_first_change(logs, function_name, prettify=False):
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

            # If the caller requests, the code can be "prettified" before it's loaded
            # into the database, removing docstrings and whitespace anomalies.
            if prettify:
                function_code = prettify_code(function_code)

            return function_code

    return None


def save_submission(question_number, student_id, code, cursor):
    cursor.execute('\n'.join([
        "INSERT INTO submissions(question_number, submission_id, code)",
        "VALUES(?, ?, ?)",
    ]), (question_number, student_id, code))


def load_submissions(submissions_dir, function_names, prettify_code, database_cursor):

    # Open the log file for each student
    for student_index, student_id in enumerate(os.listdir(submissions_dir)):

        data_filename = os.path.join(submissions_dir, student_id, 'backups.json')
        with open(data_filename) as student_data_file:
            student_data = json.load(student_data_file)

            # For each function requestsed, consider it a new "question".
            # Find the first change that the student made for this question.
            # If there was at least one, save it to the atabase.
            for question_index, function_name in enumerate(function_names):
                first_change_code = extract_first_change(student_data, function_name, prettify_code)
                if first_change_code is not None:
                    save_submission(question_index, student_index, first_change_code, cursor)


def load_submissions_from_json_file(json_filename, question_number, prettify, database_cursor):

    grader_questions = create_grader_question(json_filename, question_number)
    clusters = grader_questions.test_based_cluster

    submission_index = 0
    for cluster in clusters:
        for submission in cluster.fixes:

            # If the caller requests, the code can be "prettified" before it's loaded
            # into the database, removing docstrings and whitespace anomalies.
            code = submission['before']
            if prettify:
                code = prettify_code(code)

            cursor.execute('\n'.join([
                "INSERT OR IGNORE INTO submissions (question_number, submission_id, code)",
                "VALUES (?, ?, ?)",
            ]), (question_number, submission_index, code))
            submission_index += 1

    db.commit()


if __name__ == '__main__':

    argument_parser = argparse.ArgumentParser(
        description="Load student's submissions into the database"
    )
    subparsers = argument_parser.add_subparsers(
        help="Submodules for loading data from different sources",
        dest='command'
    )

    # Subcommand: read in the data from a directory of data from CS61A
    dir_parser = subparsers.add_parser("61a_dir", description="read from CS61A data directory")
    dir_parser.add_argument(
        'submissions_dir',
        help="Directory of student submissions"
    )
    dir_parser.add_argument(
        'function_names',
        nargs='+',
        help="Names of functions for which a student's first changes will be extracted."
    )

    # Subcommand: read in the data from a preprocessed JSON file
    file_parser = subparsers.add_parser("file", description="JSON file of student submissions")
    file_parser.add_argument(
        'submissions_json',
        help="JSON file containing all student submissions for a problem"
    )
    file_parser.add_argument(
        'question_index',
        help="The index of the question for all submissions, which will be stored with each submission."
    )

    # Add common arguments to all parsers
    for subparser in [dir_parser, file_parser]:
        subparser.add_argument(
            'database_file',
            help="Name of SQLite database file to dump data to."
        )
        subparser.add_argument(
            '--prettify-code',
            action='store_true',
            default=True,
            help="Whether to prettify students' code before saving it (on by default)."
        )
    
    args = argument_parser.parse_args()

    # Initialize the database
    db = sqlite3.connect(args.database_file)
    db.row_factory = sqlite3.Row
    cursor = db.cursor()

    # Run the code to load in student submissions
    if args.command == '61a_dir':
        load_submissions(args.submissions_dir, args.function_names, args.prettify_code, cursor)
    elif args.command == 'file':
        load_submissions_from_json_file(args.submissions_json, args.question_index, args.prettify_code, cursor)

    db.commit()
