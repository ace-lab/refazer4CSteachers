import json
import sqlite3
import os
import sys
import time
import re
import math
from concurrent.futures import ThreadPoolExecutor
from queue import Queue
import threading

from flask import Flask, request, session, g, redirect, url_for, abort, \
     render_template, flash, jsonify
from flask_login import LoginManager, login_required, UserMixin, login_user, current_user, logout_user
import requests
from jinja2 import Environment, FileSystemLoader

import highlight
from evaluate import TEST_CONDITIONS, stringify_input, stringify_output,\
    evaluate_function, evaluate_function_once
from util.load_data import prettify_code
from util.conditions import get_test_case_groups_by_first_failure, get_perfect_test_submissions,\
    get_imperfect_test_submissions


app = Flask(__name__)
app.config.from_object(__name__)
app.config.from_envvar('FLASKR_SETTINGS', silent=True)

# Configure the database endpoint
database_path = os.environ.get('FLASK_DATABASE_PATH', os.path.join(app.root_path, 'flaskr.db'))
app.config.update(dict(
    DATABASE=database_path,
    SECRET_KEY='development key',
    USERNAME='admin',
    PASSWORD='default'
))

REFAZER_ENDPOINT = "http://refazer2.azurewebsites.net/api/refazer"

''' The following section enables having users and logins. '''
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"
login_manager.logout_view = "logout"


class User(UserMixin):

    def __init__(self, user_id, username):
        self.user_id = user_id
        self.username = username

    def get_id(self):
        return self.username


def _start_user_session(question_number):

    # Load up the questions
    db = get_db()
    cursor = db.cursor()
    submissions = get_submissions(cursor, question_number)

    perfect_test_submissions = get_perfect_test_submissions(cursor, submissions, question_number)
    imperfect_submissions = filter(lambda s: s['id'] not in perfect_test_submissions, submissions)

    code_to_fix = []
    for submission in imperfect_submissions:
        code_to_fix.append({
            'Code': submission['code'],
            'QuestionId': question_number,
            'SubmissionId': submission['id'],
        })

    # Upload the new submissions that need to be fixed
    print("Launching new Refazer job")
    result = requests.post(REFAZER_ENDPOINT + "/Start", json={
        'Submissions': code_to_fix,
        'Question': question_number,
    })
    session_id = result.json()
    print("Job has been started and has ID", session_id)

    return session_id


@login_manager.user_loader
def load_user(username):

    db = get_db()
    cursor = db.cursor()

    cursor.execute('\n'.join([
        "SELECT id FROM users",
        "WHERE username = ?",
    ]), (username,))
    row = cursor.fetchone()

    if row is None:
        return None
    else:
        user_id = row[0]
        user = User(
            user_id=user_id,
            username=username,
        )
    return user


def _enqueue_synthesis_job(session_id, question_number):

    # If this user's session isn't currently being watched for new fixes, then
    # enqueue this session ID and start watching for updates!
    if session_id not in refresh_jobs:
        refresh_jobs.append(session_id)
        session_job_queue.put({
            'session_id': session_id,
            'question_id': question_number,
            'next_fix_id': 0,
        })


@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'GET':
        return render_template('login.html')
    elif request.method == 'POST':

        user = load_user(request.form['username'])
        if user is not None:

            login_user(user)
            question_number = int(request.form['question'])

            # Re-load all existing synthesis jobs for this user
            db = get_db()
            cursor = db.cursor()
            cursor.execute('\n'.join([
                "SELECT session_id, question_number FROM sessions",
                "WHERE user_id = ?",
            ]), (user.user_id,))
            for (past_session_id, past_question_number) in cursor.fetchall():
                _enqueue_synthesis_job(past_session_id, past_question_number)

            # See if any sessions have been created for this user for this question
            cursor.execute('\n'.join([
                "SELECT session_id FROM sessions WHERE",
                "user_id = ? AND",
                "question_number = ?",
            ]), (user.user_id, question_number))
            row = cursor.fetchone()

            # If no session has been created for this user yet, create one!
            # And then make sure to save this session for future reference.
            session_id = None
            if row is None:
                session_id = _start_user_session(question_number=question_number)
                cursor.execute('\n'.join([
                    "INSERT INTO sessions(user_id, question_number, session_id)",
                    "VALUES (?, ?, ?)",
                ]), (user.user_id, question_number, session_id))
                db.commit()

                # Start off a job to check for synthesis results
                _enqueue_synthesis_job(session_id, question_number)
            else:
                session_id = row[0]

            # Save in the session whether this user will be seeing fixes, the question number,
            # and the ID of the Refazer session
            interface = request.form['interface']
            session['fixes_enabled'] = True if interface == 'show_fixes' else False
            session['question_number'] = question_number
            session['refazer_session_id'] = session_id

            # Also, when this user sees submissions sorted for the first time, they will
            # be sorted by submission ID.
            session['sort_mode'] = 'submission_id'

            next_page = request.args.get('next')

            if next_page is not None:
                return redirect(next_page)
            else:
                submissions = get_submissions(cursor, question_number)
                imperfect_test_submissions = get_imperfect_test_submissions(cursor, submissions, question_number)
                return redirect('/' + str(question_number) + '/' + str(imperfect_test_submissions[0]))
        
        return render_template('login.html')


@app.route('/logout')
def logout():
    logout_user()
    return redirect('login')


@app.route('/set_sort_mode', methods=['POST'])
@login_required
def set_sort_mode():
    session['sort_mode'] = request.form['sort_mode']
    return jsonify({
        'success': True
    })


def fetch_new_fixes(cursor, session_id, question_id, next_fix_id):
    ''' Returns the ID of the last fix returned. '''

    # Request a set of new fixes from the server
    print("Getting fixes for session:", session_id)
    result = requests.get(REFAZER_ENDPOINT + "/GetFixes", params={
        'SessionId': session_id,
        'FixId': next_fix_id,
    })
    fixes = result.json()
    print("Fixes:", fixes)

    # Insert records of this fix into the database
    for fix in fixes:

        cursor.execute('\n'.join([
            "SELECT code FROM submissions WHERE",
            "question_number = ? AND",
            "submission_id = ?"
        ]), (question_id, fix['SubmissionId']))
        row = cursor.fetchone()
        submission_code = row[0]

        if fix['Transformation'] is not None and 'Examples' in fix['Transformation']:
            original_submissions_string = fix['Transformation']['Examples']
            transformation_id = fix['Transformation']['ID']
            one_original_submission_id =\
                int(re.search("'submission_id': (\d+),", original_submissions_string).group(1))

        # Refazer returns code with a different format than the one we upload.
        # To minimize diff size that's due purely to whitespace changes, prettify the
        # code that Refazer returns to conform to the same formatting.
        prettified_fixed_code = prettify_code(fix['FixedCode'])

        cursor.execute('\n'.join([
            "INSERT OR REPLACE INTO fixes (id, session_id, question_number, submission_id,",
            "   transformation_id, fixed_submission_id, before, after)",
            "VALUES (",
            "    (SELECT id FROM fixes WHERE"
            "        session_id = ? AND",
            "        question_number = ? AND",
            "        submission_id = ? AND",
            "        transformation_id = ?),",
            "    ?, ?, ?, ?, ?, ?, ?)",
        ]), (session_id, question_id, fix['SubmissionId'], transformation_id,
             session_id, question_id, fix['SubmissionId'], transformation_id,
             one_original_submission_id, submission_code, prettified_fixed_code))

    if len(fixes) > 0:
        next_fix_id = max([f['ID'] for f in fixes]) + 1

    return next_fix_id


def fetch_results(session_job_queue, database_name, interrupt_event):

    db = sqlite3.connect(database_name)
    db.row_factory = sqlite3.Row
    cursor = db.cursor()

    while True:

        # Check to see if an event has been set to break out of this thread
        if interrupt_event.is_set():
            return

        # Only try to fetch more results if there are sessions in the queue
        if session_job_queue.qsize() > 0:

            # Refresh fixes for all sessions in the queue
            for _ in range(session_job_queue.qsize()):

                # Unpack the job
                session_job = session_job_queue.get()
                session_id = session_job['session_id']
                next_fix_id = session_job['next_fix_id']
                question_id = session_job['question_id']

                # Call the server for new fixes
                new_next_fix_id = fetch_new_fixes(cursor, session_id, question_id, next_fix_id)

                # Update the job and enqueue it for the next iteration
                session_job['next_fix_id'] = new_next_fix_id
                session_job_queue.put(session_job)

                # Save the results to the database 
                db.commit()

        # Sleep for a predetermined amount of time after fetching
        # the new fixes for each session
        time.sleep(REFRESH_TIMEOUT)


def init_app():
    global questions, grader_questions
    questions = {}
    grader_questions = {}


def connect_db():
    """Connects to the specific database."""
    rv = sqlite3.connect(app.config['DATABASE'])
    rv.row_factory = sqlite3.Row
    return rv


def get_db():
    """Opens a new database connection if there is none yet for the
    current application context.
    """
    if not hasattr(g, 'sqlite_db'):
        g.sqlite_db = connect_db()
    return g.sqlite_db


@app.teardown_appcontext
def close_db(error):
    """Closes the database again at the end of the request."""
    if hasattr(g, 'sqlite_db'):
        g.sqlite_db.close()


def get_grade(session_id, question_number, submission_id):

    db = get_db()
    cursor = db.cursor()

    # Fetch grade if one has already been given
    cursor.execute('\n'.join([
        "SELECT id, grade FROM grades WHERE",
        "session_id = ? AND",
        "question_number = ? AND",
        "submission_id = ?"
    ]), (session_id, question_number, submission_id))
    row = cursor.fetchone()
    if row is not None:
        (grade_id, grade) = row
        # Fetch the notes if there was a grade
        notes = []
        cursor.execute('\n'.join([
            "SELECT \"text\" FROM",
            "notes JOIN gradenotes ON notes.id = note_id",
            "WHERE grade_id = ?"
        ]), (grade_id,))
        for row in cursor.fetchall():
            notes.append(row[0])
    else:
        grade = None
        notes = None

    return grade, notes


def get_graded_submissions(session_id, question_number):

    db = get_db()
    cursor = db.cursor()

    cursor.execute('\n'.join([
        "SELECT DISTINCT(submission_id) FROM grades WHERE",
        "session_id = ? AND",
        "question_number = ?",
    ]), (session_id, question_number,))
    graded_submissions = [r[0] for r in cursor.fetchall()]
    return graded_submissions


def get_grade_suggestions(session_id, question_number):

    db = get_db()
    cursor = db.cursor()

    graded_submissions = get_graded_submissions(session_id, question_number)

    cursor.execute('\n'.join([
        "SELECT DISTINCT(submission_id) FROM fixes WHERE",
        "session_id = ? AND",
        "question_number = ?",
    ]), (session_id, question_number))
    fixed_submissions = [r[0] for r in cursor.fetchall()]

    ungraded_fixed_submissions = []
    for id_ in fixed_submissions:
        if id_ not in graded_submissions:
            ungraded_fixed_submissions.append(id_)

    return ungraded_fixed_submissions


def get_fix_groups(submissions, session_id):

    db = get_db()
    cursor = db.cursor()

    fix_groups = {}

    for submission in submissions:
        
        # Get the ID of the first submission that, when it was fixed,
        # suggested a fix for this submission
        cursor.execute('\n'.join([
            "SELECT transformation_id, fixed_submission_id FROM fixes WHERE",
            "session_id = ? AND",
            "submission_id = ?",
        ]), (session_id, submission['id']))
        row = cursor.fetchone()

        # Group submissions by what submission can be used to fix them
        (transformation_id, fixed_submission_id) = row if row is not None else (None, None)
        if fixed_submission_id not in fix_groups:
            fix_groups[fixed_submission_id] = {}
        if transformation_id not in fix_groups[fixed_submission_id]:
            fix_groups[fixed_submission_id][transformation_id] = []
        fix_groups[fixed_submission_id][transformation_id].append(submission['id'])

    return fix_groups


@app.route('/<int:question_number>/<int:submission_id>')
@login_required
def show_grader_interface(question_number, submission_id):

    db = get_db()
    cursor = db.cursor()

    # Fetch all submissions from the database
    submissions = get_submissions(cursor, question_number)
    submission = next(filter(lambda s: s['id'] == submission_id, submissions))
    test_results = run_code_evaluations(submission['code'], question_number)

    # Get the ID of the Refazer session
    refazer_session_id = session['refazer_session_id']

    # Get any grades and notes that have been saved for this submission
    (grade, notes) = get_grade(
        refazer_session_id,
        question_number,
        submission_id
    )

    # Look for existing, applicable fixes, and grades
    cursor.execute('\n'.join([
        "SELECT fixed_submission_id, before, after FROM fixes WHERE",
        "session_id = ? AND",
        "question_number = ? AND",
        "submission_id = ?",
    ]), (refazer_session_id, question_number, submission_id))
    row = cursor.fetchone()
    fix_exists = (row is not None)
    if fix_exists:
        (fixed_submission_id, before, after) = row
        fix_diff = get_diff_html(before, after)
        fixed_code = after
        (fix_grade, fix_notes) = get_grade(
            refazer_session_id,
            question_number,
            fixed_submission_id
        )
    else:
        fix_diff = None
        fixed_code = None
        fixed_submission_id = None
        fix_grade = None
        fix_notes = None
    fix_grade_exists = (fix_notes is not None)

    # Get a list of all notes that can be applied when grading
    cursor.execute("SELECT DISTINCT(\"text\") FROM notes WHERE session_id = ?", (refazer_session_id,))
    note_options = [r[0] for r in cursor.fetchall()]

    # Fetch a list of which submission shave already been graded
    graded_submissions = get_graded_submissions(refazer_session_id, question_number)
    grade_status = {}
    for graded_submission_id in graded_submissions:
        grade_status[graded_submission_id] = 'graded'

    # Get the list of submissions for which some synthesized fix exists
    grade_suggestions = get_grade_suggestions(refazer_session_id, question_number)
    for ungraded_fixed_submission_id in grade_suggestions:
        grade_status[ungraded_fixed_submission_id] = "fixed"

    # Group submissions based on what test cases they pass
    test_case_groups = get_test_case_groups_by_first_failure(cursor, submissions, question_number)
    test_case_groups_sorted = sorted(
        test_case_groups.values(),
        key=lambda l: len(l),
        reverse=True,
    )

    # Get the list of submissions that have passed all tests
    perfect_test_submissions = get_perfect_test_submissions(cursor, submissions, question_number)

    # Group submissions based on shared fixes
    fix_groups = get_fix_groups(submissions, refazer_session_id)
    unfixable_submissions = fix_groups[None]
    del(fix_groups[None])
    # Sort fix groups by the number of fixes in the first level of the fix
    # hierarchy (clustered by the original submission ID that produced the fix)
    fix_groups = sorted(
        fix_groups.values(),
        key=lambda transformations: sum([len(l) for l in transformations.values()]),
        reverse=True,
    )
    fix_groups.append(unfixable_submissions)
    print(fix_groups)

    # Filter all submissions to just those that don't pass all test cases
    # XXX commented out because this isn't necessary with the current data source
    submission_ids = [s['id'] for s in submissions]
    '''
    fails_tests = lambda submission_id: submission_id not in perfect_test_submissions
    submission_ids = list(filter(fails_tests, [s['id'] for s in submissions]))
    submissions = list(filter(lambda s: s['id'] in submission_ids, submissions))
    for group_index in range(len(test_case_groups_sorted)):
        test_case_groups_sorted[group_index] = list(filter(fails_tests, test_case_groups_sorted[group_index]))
    for group_index in range(len(fix_groups)):
        fix_groups[group_index] = list(filter(fails_tests, fix_groups[group_index]))
    grade_suggestions = list(filter(fails_tests, grade_suggestions))
    '''

    return render_template('grade.html',
        question_number=question_number,
        submission=submission,
        test_results=test_results,
        grade=grade,
        notes=notes,
        grade_status=grade_status,
        submission_id=submission_id,
        submission_ids=submission_ids,
        fixed_submissions=grade_suggestions,
        fix_exists=fix_exists,
        fix_submission_id=fixed_submission_id,
        fix_diff=fix_diff,
        # XXX We provide the fixed code as a dictionary with a single key
        # so that we can use Jinja2's built-in escaping of JSON when we
        # store it in a hidden input's value.  This is a hacky way to
        # make sure we can store the fixed code in the HTML.
        fixed_code={'code': fixed_code},
        fix_grade_exists=fix_grade_exists,
        fix_grade=fix_grade,
        fix_notes=fix_notes,
        note_options=note_options,
        test_case_groups=test_case_groups_sorted,
        fix_groups=fix_groups,
        fixed_submission_ids=grade_suggestions,
        perfect_test_submission_ids=perfect_test_submissions,
        show_perfect_test_submissions=True,
        graded_submission_ids=graded_submissions,
        sort_mode=session['sort_mode'],
    )


def run_code_evaluations(code_text, question_number):

    test_condition = TEST_CONDITIONS[question_number]
    results = evaluate_function(
        code_text=code_text,
        function_name=test_condition['function_name'],
        input_value_tuples=test_condition.get('input_value_tuples'),
        expected_outputs=test_condition.get('expected_outputs'),
        assertions=test_condition.get('assertions'),
        test_code=test_condition.get('test_code'),
        pre_code=test_condition.get('pre_code'),
    )

    # Make test case results human readable and printable within HTML
    for test_case in results['test_cases']:
        test_case['input_values'] = stringify_input(test_case['input_values'])
        test_case['human_readable_result'] = stringify_output(test_case)
        if 'returned' in test_case:
            del(test_case['returned'])

    return results


def get_diff_html(code_before, code_after):
    env = Environment(loader=FileSystemLoader('templates'))
    template = env.get_template('diff.html')
    html = template.render(diff_lines=highlight.diff_file(
        '_', code_before, code_after, 'full'))
    return html


@app.route('/diff', methods=['POST'])
def diff():

    code_version_1 = request.form['code_version_1']
    code_version_2 = request.form['code_version_2']

    return jsonify({
        'diff_html': get_diff_html(code_version_1, code_version_2),
    })


@app.route('/grade', methods=['POST'])
@login_required
def grade():

    session_id = session['refazer_session_id']
    grade = request.form.get('grade')
    notes = request.form.getlist('notes[]')
    question_number = request.form['question_number']
    submission_id = request.form['submission_id']

    db = get_db()
    cursor = db.cursor()

    # Insert the new grade and save its ID
    cursor.execute('\n'.join([
        "INSERT OR REPLACE INTO grades (id, session_id, question_number, submission_id, grade)",
        "VALUES (",
        # The select statement below lets us keep the old grade ID
        "    (SELECT id FROM grades WHERE"
        "        session_id = ? AND",
        "        question_number = ? AND",
        "        submission_id = ?),"
        "     ?, ?, ?, ?)"
    ]), (session_id, question_number, submission_id,
         session_id, question_number, submission_id, grade))
    cursor.execute('\n'.join([
        "SELECT id FROM grades WHERE",
        "session_id = ? AND",
        "question_number = ? AND",
        "submission_id = ?"
    ]), (session_id, question_number, submission_id))
    grade_id = cursor.fetchone()[0]

    # Create new note records for all that haven't been created yet
    note_ids = []
    for note in notes:
        cursor.execute('\n'.join([
            "INSERT OR IGNORE INTO notes (session_id, \"text\")",
            "VALUES (?, ?)",
        ]), (session_id, note))
        cursor.execute('\n'.join([
            "SELECT id FROM notes WHERE",
            "session_id = ? AND",
            "\"text\" = ?",
        ]), (session_id, note))
        note_id = cursor.fetchone()[0]
        note_ids.append(note_id)

    # Flush the old notes for grades and create new ones
    cursor.execute('\n'.join([
        "DELETE FROM gradenotes WHERE",
        "grade_id = ?"
    ]), (grade_id,))
    for note_id in note_ids:
        cursor.execute('\n'.join([
            "INSERT INTO gradenotes (grade_id, note_id)",
            "VALUES (?, ?)"
        ]), (grade_id, note_id))

    db.commit()

    return jsonify({
        'success': True,
    })


@app.route('/get_grade_suggestions', methods=['GET'])
@login_required
def get_grade_suggestions_api_method():
    refazer_session_id = session['refazer_session_id']
    question_number = int(request.args.get('question_number'))
    return jsonify({
        'grade_suggestions': get_grade_suggestions(refazer_session_id, question_number)
    })


# This function will take a long time to run (at least as long as it takes
# for Refazer to fulfill the request).  Don't expect to get a response in less
# than 30 seconds, and it may take minutes.
def upload_example(url, json_data):
    payload = json_data
    for ranking in ['specific', 'general']:
        payload.update({
            'SynthesizedTransformations': 3,
            'Ranking': ranking,
        })
        print("Submitting fix suggestion to Refazer")
        result = requests.post(REFAZER_ENDPOINT + "/ApplyFixFromExample", json=payload)
        print("Refazer has accepted the job")


@app.route('/synthesize', methods=['POST'])
@login_required
def synthesize():

    session_id = session['refazer_session_id']
    question_number = int(request.form['question_number'])
    submission_id = request.form['submission_id']
    code_before = request.form['code_before']
    code_after = request.form['code_after']

    thread_pool.submit(
        upload_example, 
        REFAZER_ENDPOINT + "/ApplyFixFromExample", {
            'CodeBefore': code_before,
            'CodeAfter': code_after,
            'SessionId': session_id,
            'QuestionId': question_number,
            'SubmissionId': submission_id,
        })

    return jsonify({
        'success': True,
    })


@app.route('/evaluate', methods=['POST'])
def evaluate():

    before_id = request.form['before_id']
    question_number = int(request.form['question_number'])

    code_text = request.form['code']
    results = run_code_evaluations(code_text, question_number)

    # Save the code that the user has uploaded
    db = get_db()
    cursor = db.cursor()
    cursor.execute('\n'.join([
        "INSERT INTO codeedits(session_id, question_number, submission_id, code)",
        "VALUES (?, ?, ?, ?)",
    ]), (session['refazer_session_id'], question_number, before_id, code_text))
    db.commit()

    return jsonify(results)


@app.route('/submit', methods=['POST'])
def submit_code():
    return jsonify(success=True)


def get_submissions(cursor, question_number):

    cursor.execute('\n'.join([
        "SELECT submission_id, code FROM submissions WHERE",
        "question_number = ?",
    ]), (question_number,))
    submissions = [
        {'id': row[0], 'code': row[1]}
        for row in cursor.fetchall()
    ]

    return submissions


''' More initializations that can't be done until all the functions are defined. '''

# Every few seconds, we'll query Refazer to learn if it has discovered any
# new fixes for student submissions.  The list below lets us keep
# track of which jobs we're currently checking.
refresh_jobs = []
REFRESH_TIMEOUT = 3
thread_pool = ThreadPoolExecutor(max_workers=3)
session_job_queue = Queue()
shutdown_event = threading.Event()
thread_pool.submit(fetch_results, session_job_queue, app.config['DATABASE'], shutdown_event)


if __name__ == '__main__':

    init_app()
    port = int(os.environ.get('PORT', 5000))
    app.config.update(
        TEMPLATES_AUTO_RELOAD=True
    )

    app.run(
        host='0.0.0.0',
        port=port,
        debug=False,
    )
