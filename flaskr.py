# all the imports
import os
import sqlite3
from flask import Flask, request, session, g, redirect, url_for, abort, \
     render_template, flash, jsonify
import json
import highlight
import requests
import math
import sys
import inspect
import time
from multiprocessing import Manager, Process
from jinja2 import Environment, FileSystemLoader
from io import StringIO


class Rule_and_test:
    def __init__(self, test, rule):
        self.test = test
        self.rule = rule

    def __hash__(self):
        return hash((self.test[0]['input'], self.test[0]['output'], self.rule))

    def __eq__(self, other):
        return (self.test, self.rule) == (other.test, other.rule)

class Rule_based_cluster:
    def __init__(self, rule, size, fixes):
        self.rule = rule
        self.size = size
        self.fixes = fixes

class Test_based_cluster:
    def __init__(self, test, size, fixes):
        self.test = test
        self.size = size
        self.fixes = fixes

class Rule_and_test_based_cluster:
    def __init__(self, rule, test, size, fixes):
        self.rule = rule
        self.test = test
        self.size = size
        self.fixes = fixes

class Question:
    def __init__(self, question_id, rule_based_cluster, test_based_cluster, rule_and_test_based_cluster,
                 question_instructions, submissions):
        self.question_id = question_id
        self.rule_based_cluster = rule_based_cluster
        self.test_based_cluster = test_based_cluster
        self.rule_and_test_based_cluster = rule_and_test_based_cluster
        self.question_instructions = question_instructions
        self.submissions = submissions


app = Flask(__name__)
app.config.from_object(__name__)
ordered_clusters = []
PROCESS_TIMEOUT = .5

question_files = {
    1:'accumulate-mistakes.json',
    # 2:'G-mistakes.json',
    # 3:'Product-mistakes.json',
    # 4:'repeated-mistakes.json'
    }

question_instructions = {
    1:'''<code>accumulate(combiner, base, n, term)</code> takes the following arguments:
    <ul>
    <li>
        <code>term</code and <code>n</code: the same arguments as in <code>summation</code> and <code>product</code>
    </li>
    <li>
        <code>combiner</code>: a two-argument function that specifies how the current term combined with the previously accumulated terms.
    </li>
    <li>
        <code>base</code>: value that specifies what value to use to start the accumulation.
    </li>
    </ul>
    For example, <code>accumulate(add, 11, 3, square)</code> is <code>11 + square(1) + square(2) + square(3)</code>.''',
    2:'''A mathematical function G on positive integers is defined by two cases:

<code>G(n) = n</code> if <code>n <= 3</code>
<code>G(n) = G(n - 1) + 2 * G(n - 2) + 3 * G(n - 3)</code> if <code>n > 3</code>

Write a recursive function <code>g</code> that computes <code>G(n)</code>.''',
    3:'TODO: RETRIEVE DIRECTIONS FOR Product-mistakes.json',
    4:'TODO: RETRIEVE DIRECTIONS FOR repeated-mistakes.json'
}

app.config.update(dict(
    DATABASE=os.path.join(app.root_path, 'flaskr.db'),
    SECRET_KEY='development key',
    USERNAME='admin',
    PASSWORD='default'
))

app.config.from_envvar('FLASKR_SETTINGS', silent=True)

# def get_coverage(question_number,entries):

#     covered_bugs = 0
#     for entry in entries:
#         covered_bugs+=questions[question_number].rule_based_cluster['cluster_id'].number
#     total_bugs = 1
#     return math.ceil(covered_bugs*100/total_bugs)

def get_fix(question_number, cluster_id):
    return ordered_clusters[question_number][cluster_id].fix

def get_test(failed):
    expected_value = ''
    output_value = ''
    previous_line = ''
    testcases = []
    for line in failed:
        if previous_line == '# Error: expected':
            expected_value = line[1:].strip()
        if previous_line == '# but got':
            output_value = line[1:].strip()
        if line.startswith('>>>'):
            line_no_comment = line[4:].split('#')[0] #removes comments
            if not line_no_comment.startswith('check(') and not line_no_comment.startswith('from construct_check import check'):
                testcases.append(line_no_comment)
        previous_line = line
    if len(testcases)>0:
        failed_test = testcases[-1]
    else:
        #print('wtf no testcases?')
        failed_test = ''

    results = [{
        'input': failed_test,
        'output': output_value,
        'expected': expected_value
    }]
    return results

def create_grader_question(question_number):
    global question_instructions

    #TODO: read in all data, not just what was fixed, produce clusters, empty synthesized fixes and turn isFixed's to false, initialize isFixed to false
    ordered_clusters = []

    with open('data/'+question_files[question_number]) as data_file:
        submission_pairs = json.load(data_file)

    clustered_fixes_by_rule = {}
    clustered_fixes_by_test = {}
    clustered_fixes_by_rule_and_test = {}
    group_id_to_test_for_a_question = {}
    fixes = []

    group_id = -1
    checked_tests = []

    rule_and_test_based_cluster = []

    no_sequence_diff = []
    def_seq_diff = []
    num_fixed = []

    for submission_pair in submission_pairs:
        submission_pair['IsFixed'] = False #initialized to false
        #submission_pair['SynthesizedAfter'] =  ''
        num_fixed.append(submission_pair)
        rule = submission_pair['UsedFix']
        # rule = rule.replace('\\', '')

        fix = submission_pair
        code_before = submission_pair['before']
        code_after = '' #submission_pair['SynthesizedAfter'] #old correctino is erased
        code_student_after = submission_pair['after']
        filename = 'filename-' + str(submission_pair['Id'])

        # fix['diff_lines'] = highlight.diff_file(filename, code_before, code_after, 'full')
        # fix['diff_student_lines'] = highlight.diff_file(filename, code_before, code_student_after, 'full')
        # fix['diff_but_not_a_diff'] = highlight.diff_file(filename, code_before, code_before, 'full')

        test = get_test(submission_pair['failed'])
        
        fix['tests'] = test
        fix['before'] = code_before
        fix['input_output_before'] = {} #submission_pair['augmented_tidy_before_testcase_to_output']
        fix['synthesized_after'] = submission_pair['SynthesizedAfter']
        try:
            fix['dynamic_diff'] = submission_pair['sequence_comparison_diff']
        except:
            no_sequence_diff.append(submission_pair)

        id = submission_pair['Id']

        if (rule in clustered_fixes_by_rule.keys()):
            clustered_fixes_by_rule[rule].append(fix)
        else:
            clustered_fixes_by_rule[rule] = [fix]

        if (test in checked_tests):
            group_id = checked_tests.index(test)
            clustered_fixes_by_test[checked_tests.index(test)].append(fix)
        else:
            checked_tests.append(test)
            group_id = len(checked_tests)
            clustered_fixes_by_test[checked_tests.index(test)] = [fix]

        key = Rule_and_test(test=test,rule=rule)
        if key in clustered_fixes_by_rule_and_test.keys():
            clustered_fixes_by_rule_and_test[key].append(fix)
        else:
            clustered_fixes_by_rule_and_test[key] = [fix]

        fix['group_id'] = group_id
        group_id_to_test_for_a_question[group_id] = test
        fixes.append(fix)

    for key,value in clustered_fixes_by_rule.items():
        cluster = Rule_based_cluster(rule=key, fixes = value, size=len(value))
        ordered_clusters.append(cluster)

    test_based_clusters = []
    for key,value in clustered_fixes_by_test.items():
        cluster = Test_based_cluster(test=checked_tests[key], fixes = value, size=len(value))
        test_based_clusters.append(cluster)

    for key,value in clustered_fixes_by_rule_and_test.items():
        cluster = Rule_and_test_based_cluster(test=key.test, rule=key.rule, fixes = value, size = len(value))
        rule_and_test_based_cluster.append(cluster)

    ordered_clusters.sort(key = lambda x : len(x.fixes), reverse= True)
    test_based_clusters.sort(key = lambda x : len(x.fixes), reverse= True)
    rule_and_test_based_cluster.sort(key = lambda  x : len(x.fixes), reverse=True)
    question = Question(question_id=question_number, rule_based_cluster = ordered_clusters,
                        test_based_cluster = test_based_clusters, rule_and_test_based_cluster=rule_and_test_based_cluster,
                        question_instructions = question_instructions[question_number], submissions= fixes)

    return question

    #return create_question(question_number)

def create_question(question_number):

    global question_instructions
    ordered_clusters = []

    with open('data/'+question_files[question_number]) as data_file:
        submission_pairs = json.load(data_file)

    clustered_fixes_by_rule = {}
    clustered_fixes_by_test = {}
    clustered_fixes_by_rule_and_test = {}
    group_id_to_test_for_a_question = {}
    fixes = []

    group_id = -1
    checked_tests = []

    rule_and_test_based_cluster = []

    no_sequence_diff = []
    def_seq_diff = []
    num_fixed = []

    for submission_pair in submission_pairs:
        if (submission_pair['IsFixed'] == True):
            num_fixed.append(submission_pair)
            rule = submission_pair['UsedFix']
            rule = rule.replace('\\', '')

            fix = submission_pair
            code_before = submission_pair['before']
            code_after = submission_pair['SynthesizedAfter']
            code_student_after = submission_pair['after']
            filename = 'filename-' + str(submission_pair['Id'])

            fix['diff_lines'] = highlight.diff_file(filename, code_before, code_after, 'full')
            fix['diff_student_lines'] = highlight.diff_file(filename, code_before, code_student_after, 'full')
            fix['diff_but_not_a_diff'] = highlight.diff_file(filename, code_before, code_before, 'full')

            test = get_test(submission_pair['failed'])
            
            fix['tests'] = test
            fix['before'] = code_before
            fix['input_output_before'] = submission_pair['augmented_tidy_before_testcase_to_output']
            fix['synthesized_after'] = code_after
            fix['is_fixed'] = True;
            try:
                fix['dynamic_diff'] = submission_pair['sequence_comparison_diff']
            except:
                no_sequence_diff.append(submission_pair)

            id = submission_pair['Id']

            if (rule in clustered_fixes_by_rule.keys()):
                clustered_fixes_by_rule[rule].append(fix)
            else:
                clustered_fixes_by_rule[rule] = [fix]

            if (test in checked_tests):
                group_id = checked_tests.index(test)
                clustered_fixes_by_test[checked_tests.index(test)].append(fix)
            else:
                checked_tests.append(test)
                group_id = len(checked_tests)
                clustered_fixes_by_test[checked_tests.index(test)] = [fix]

            key = Rule_and_test(test=test,rule=rule)
            if key in clustered_fixes_by_rule_and_test.keys():
                clustered_fixes_by_rule_and_test[key].append(fix)
            else:
                clustered_fixes_by_rule_and_test[key] = [fix]

            fix['group_id'] = group_id
            group_id_to_test_for_a_question[group_id] = test
            fixes.append(fix)

    for key,value in clustered_fixes_by_rule.items():
        cluster = Rule_based_cluster(rule=key, fixes = value, size=len(value))
        ordered_clusters.append(cluster)

    test_based_clusters = []
    for key,value in clustered_fixes_by_test.items():
        cluster = Test_based_cluster(test=checked_tests[key], fixes = value, size=len(value))
        test_based_clusters.append(cluster)

    for key,value in clustered_fixes_by_rule_and_test.items():
        cluster = Rule_and_test_based_cluster(test=key.test, rule=key.rule, fixes = value, size = len(value))
        rule_and_test_based_cluster.append(cluster)

    ordered_clusters.sort(key = lambda x : len(x.fixes), reverse= True)
    test_based_clusters.sort(key = lambda x : len(x.fixes), reverse= True)
    rule_and_test_based_cluster.sort(key = lambda  x : len(x.fixes), reverse=True)
    question = Question(question_id=question_number, rule_based_cluster = ordered_clusters,
                        test_based_cluster = test_based_clusters, rule_and_test_based_cluster=rule_and_test_based_cluster,
                        question_instructions = question_instructions[question_number], submissions= fixes)

    return question

def init_app():
    global questions, grader_questions
    questions = {}
    grader_questions = {}
    for question_number in question_files.keys():
        questions[question_number] = create_question(question_number)
        grader_questions[question_number] = create_grader_question(question_number)
    print(questions)
    print(grader_questions)
    print(question_instructions)

def connect_db():
    """Connects to the specific database."""
    rv = sqlite3.connect(app.config['DATABASE'])
    rv.row_factory = sqlite3.Row
    return rv

def init_db():
    with app.app_context():
        db = get_db()
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()

@app.cli.command('initdb')
def initdb_command():
    """Initializes the database."""
    init_db()
    print('Initialized the database.')

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

# def get_fixes(question_number):
#     #todo: add question number to schema and db.execute call
#     db = get_db()
#     cur = db.execute('SELECT title, cluster_id, text, question_number, tab_id FROM entries ORDER BY id DESC')
#     fixes = cur.fetchall()
#     return fixes

def get_hint(question_number, cluster_id, tab_id):
    #todo: add question number to schema and db.execute call
    db = get_db()
    cur = db.execute('SELECT title, cluster_id, text, question_number, tab_id FROM entries WHERE question_number=? AND cluster_id=? AND tab_id=? ORDER BY id DESC', [question_number, cluster_id, tab_id])
    hint = cur.fetchone()
    return hint

def get_previous_hints(question_number):
    db = get_db()
    cur = db.execute('SELECT title, cluster_id, text, question_number, tab_id FROM entries WHERE question_number=? ORDER BY id DESC', [question_number])
    previous_hints = cur.fetchall()
    return previous_hints


def get_finished_cluster_ids(question_number, tab_id):
    #todo: add question number to schema and db.execute call
    db = get_db()
    cur = db.execute('SELECT cluster_id FROM entries WHERE question_number=? AND tab_id=?', [question_number, tab_id])
    results = cur.fetchall()
    cluster_ids = list(map(lambda item: item['cluster_id'], results))
    return cluster_ids

@app.route('/<int:question_number>')
def show_question(question_number):
    return redirect(url_for('show_detail', question_number=question_number, tab_id=0, cluster_id=0, group_id=0))

@app.route('/')
def show_fixes():
    return redirect(url_for('show_detail', question_number=1, tab_id=0, cluster_id=0, group_id=0))

def get_grade(question_number, submission_id):

    db = get_db()
    cursor = db.cursor()

    # Fetch grade if one has already been given
    cursor.execute('\n'.join([
        "SELECT id, grade FROM grades WHERE",
        "question_number = ? AND",
        "submission_id = ?"
    ]), (question_number, submission_id))
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

def get_graded_submissions(question_number):

    db = get_db()
    cursor = db.cursor()

    cursor.execute('\n'.join([
        "SELECT DISTINCT(submission_id) FROM grades",
        "WHERE question_number = ?",
    ]), (question_number,))
    graded_submissions = [r[0] for r in cursor.fetchall()]
    return graded_submissions

@app.route('/<int:question_number>/<int:tab_id>/<int:cluster_id>')
def show_detail(question_number, tab_id, cluster_id, filter=None):
    #coverage_percentage = get_coverage(question_number, fixes)
    #print('question_instructions',question_instructions)
    #print (questions[question_number].rule_based_cluster[0][0].fixes)
    #TODO refactor this method to extract sub functions. It's big!! 
    if (tab_id < 3):
        if (tab_id == 0):
            clusters = questions[question_number].rule_based_cluster
        elif (tab_id == 1):
            clusters = questions[question_number].test_based_cluster
        elif (tab_id == 2):
            clusters = questions[question_number].rule_and_test_based_cluster
        hint = get_hint(question_number, cluster_id, tab_id)
        previous_hints = get_previous_hints(question_number)
        finished_cluster_ids = get_finished_cluster_ids(question_number, tab_id)

        finished_count = 0
        total_count = 0
        for i in range(len(clusters)):
            if (i in finished_cluster_ids):
                finished_count += clusters[i].size
            total_count += clusters[i].size
        if not filter:
            current_filter = request.args.get('filter')        
        return render_template('index.html',
            question_name = question_files[question_number],
            question_number = question_number,
            clusters = clusters,
            cluster_id = cluster_id,
            tab_id = tab_id,
            hint = hint,
            previous_hints = previous_hints,
            total_count = total_count,
            finished_count = finished_count,
            finished_cluster_ids = finished_cluster_ids,
            current_filter = current_filter,
            question_instructions = questions[question_number].question_instructions
        )
    elif (tab_id==3):
        item1 = {}
        code_before = """def accumulate(combiner, base, n, term):
      if n==1:
          return combiner(base, term(n))
      else:
          return combiner(accumulate(combiner, base, n-1, term), term(n))"""
        code_after = """def accumulate(combiner, base, n, term):
      if n<=1:
          return combiner(base, term(n))
      else:
          return combiner(accumulate(combiner, base, n-1, term), term(n))"""
        filename = 'file1'
        item1['diff_lines'] = highlight.diff_file(filename, code_before, code_after, 'full')

        item2 = {}
        code_before = """def accumulate(combiner, base, n, term):
          if n==1:
              return combiner(base, term(n))
          else:
              return combiner(accumulate(combiner, base, n-1, term), term(n))"""
        code_after = """def accumulate(combiner, base, n, term):
          if n<=1:
              return combiner(base, term(n))
          else:
              return combiner(accumulate(combiner, base, n-1, term), term(n))"""
        filename = 'file2'
        item2['diff_lines'] = highlight.diff_file(filename, code_before, code_after, 'full')

        item3 = {}
        code_before = """def accumulate(combiner, base, n, term):
          if n==1:
              return combiner(base, term(n))
          else:
              return combiner(accumulate(combiner, base, n-1, term), term(n))"""
        code_after = """def accumulate(combiner, base, n, term):
          if n<=1:
              return combiner(base, term(n))
          else:
              return combiner(accumulate(combiner, base, n-1, term), term(n))"""
        filename = 'file3'
        item3['diff_lines'] = highlight.diff_file(filename, code_before, code_after, 'full')
        return render_template('task.html', item1 = item1, item2 = item2, item3 = item3, question_number = question_number)
    elif (tab_id==4):

        clusters = grader_questions[question_number].test_based_cluster
        hint = get_hint(question_number, cluster_id, tab_id)
        previous_hints = get_previous_hints(question_number)
        finished_cluster_ids = get_finished_cluster_ids(question_number, tab_id)

        fixes = []
        for cluster in clusters:
            fixes.extend(cluster.fixes)

        submission = fixes[cluster_id]
        test_results = run_code_evaluations(submission['before'])

        db = get_db()
        cursor = db.cursor()

        # This is what one can do to save a synthesized fix to a submission
        '''
        for fix_index, fix in enumerate(fixes, start=0):
            if fix['synthesized_after'] is not None and len(fix['synthesized_after']) > 0:
                cursor.execute('\n'.join([
                    "INSERT OR IGNORE INTO fixes (question_number, submission_id,",
                    "   fixed_submission_id, before, after)",
                    "VALUES (?, ?, ?, ?, ?)",
                ]), (question_number, fix_index, 10, fix['before'], fix['synthesized_after']))
        db.commit()
        '''

        # Get any grades and notes that have been saved for this submission
        (grade, notes) = get_grade(question_number, cluster_id)

        # Look for existing, applicable fixes, and grades
        cursor.execute('\n'.join([
            "SELECT fixed_submission_id, before, after FROM fixes WHERE",
            "question_number = ? AND",
            "submission_id = ?",
        ]), (question_number, cluster_id))
        row = cursor.fetchone()
        fix_exists = (row is not None)
        if fix_exists:
            (fixed_submission_id, before, after) = row
            fix_diff = get_diff_html(before, after)
            fixed_code = after
            (fix_grade, fix_notes) = get_grade(question_number, fixed_submission_id)
        else:
            fix_diff = None
            fixed_code = None
            fixed_submission_id = None
            fix_grade = None
            fix_notes = None
        fix_grade_exists = (fix_grade is not None)

        # Get a list of all notes that can be applied when grading
        cursor.execute("SELECT \"text\" FROM notes")
        note_options = [r[0] for r in cursor.fetchall()]

        # Fetch a list of which submission shave already been graded
        graded_submissions = get_graded_submissions(question_number)
        grade_status = {}
        for graded_submission_id in graded_submissions:
            grade_status[graded_submission_id] = 'graded'

        # Get the list of submissions for which some synthesized fix exists
        cursor.execute('\n'.join([
            "SELECT DISTINCT(submission_id) FROM fixes",
            "WHERE question_number = ?",
        ]), (question_number,))
        fixed_submissions = [r[0] for r in cursor.fetchall()]
        ungraded_fixed_submissions = []
        for id_ in fixed_submissions:
            if id_ not in graded_submissions:
                ungraded_fixed_submissions.append(id_)
        for ungraded_fixed_submission_id in ungraded_fixed_submissions:
            grade_status[ungraded_fixed_submission_id] = "fixed"

        finished_count = 0
        total_count = 0
        for i in range(len(clusters)):
            if (i in finished_cluster_ids):
                finished_count += clusters[i].size
            total_count += clusters[i].size
        if not filter:
            current_filter = request.args.get('filter')

        return render_template('grade.html',
            question_name = question_files[question_number],
            question_number = question_number,
            clusters = clusters,
            cluster_id = cluster_id,
            tab_id = tab_id,
            hint = hint,
            previous_hints = previous_hints,
            total_count = total_count,
            finished_count = finished_count,
            finished_cluster_ids = finished_cluster_ids,
            current_filter = current_filter,
            question_instructions = grader_questions[question_number].question_instructions,
            submissions = fixes,
            submission = submission,
            test_results = test_results,
            grade = grade,
            notes = notes,
            grade_status = grade_status,
            submission_ids = range(len(fixes)),
            fixed_submissions = ungraded_fixed_submissions,
            fix_exists = fix_exists,
            fix_submission_id = fixed_submission_id,
            fix_diff = fix_diff,
            # XXX We provide the fixed code as a dictionary with a single key
            # so that we can use Jinja2's built-in escaping of JSON when we
            # store it in a hidden input's value.  This is a hacky way to
            # make sure we can store the fixed code in the HTML.
            fixed_code = {'code': fixed_code},
            fix_grade_exists = fix_grade_exists,
            fix_grade = fix_grade,
            fix_notes = fix_notes,
            note_options = note_options,
        )

        # data = requests.post('http://localhost:53530/api/refazer', 
        #     json={"submissions":list(questions[question_number].submissions), "Examples" : 
        #     [{"before" : questions[question_number].submissions[1]['before'],"after" : 
        #     questions[question_number].submissions[1]['SynthesizedAfter']}]})
        # if data.ok:
        #     print("Number of submissions returned")
        #     print(len(data.json()))
        #     return render_template('grade.html', ok = True, fixes  = len(data.json()), error = "",question_number = question_number)
        # else:
        #     print("problem found")
        #     print(data.content)
        #     return render_template('grade.html', ok = False, error = data.content,question_number = question_number)

# @app.route('/delete', methods=['POST'])
# def delete_hint():
#     db = get_db()
#     db.execute('delete from entries where cluster_id=' + request.form['cluster_id'] + ' and question_number=' + request.form['question_number'])
#     db.commit()
#     return redirect(url_for('show_detail', question_number=request.form['question_number'], tab_id=0 cluster_id=request.form['cluster_id']))


def run_code_evaluations(code_text):

    results = evaluate_function(
        code_text=code_text,
        function_name='accumulate',
        input_value_tuples=[
            (lambda x, y: x + y, 11, 5, lambda x: x),
            (lambda x, y: x + y, 0, 5, lambda x: x),
            (lambda x, y: x * y, 2, 3, lambda x: x * x),
            (lambda x, y: x + y, 11, 0, lambda x: x),
            (lambda x, y: x + y, 11, 3, lambda x: x * x),
        ],
        expected_outputs=[
            26,
            15,
            72,
            11,
            25,
        ],
    )

    # Stringify the results.  This means:
    # 1. Adding a lambda's source as a string
    # 2. Adding the names of exceptions instead of their classes
    # 3. Setting the value of the displayable result
    for result in results['test_cases']:
        input_values = list(result['input_values'])
        for index, input_value in enumerate(input_values, start=0):
            # We use a heuristic if there are lambdas:
            # Just find the source code of the line where this set of examples
            # was defined, and add that source code line here.
            if callable(input_value):
                result['input_values'] = inspect.getsource(input_value).strip()
                break
        if not result['compile_success']:
            pass
        elif result['timeout']:
            pass
        elif not result['exec_success']:
            result['exec_exception']['type'] = result['exec_exception']['type'].__name__
        elif not result['runtime_success']:
            result['runtime_exception']['type'] = result['runtime_exception']['type'].__name__
        result['input_values'] = result['input_values'].strip(',()')

        if result['runtime_success']:
            result['human_readable_result'] = result['returned']
        elif not result['compile_success']:
            result['human_readable_result'] = 'N/A'
        elif result['timeout']:
            result['human_readable_result'] = 'Timeout'
        elif not result['exec_success']:
            result['human_readable_result'] = result['exec_exception']['type']
        elif not result['runtime_success']:
            result['human_readable_result'] = result['runtime_exception']['type']

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
def grade():

    grade = request.form['grade']
    notes = request.form.getlist('notes[]')
    question_number = request.form['question_number']
    submission_id = request.form['submission_id']

    db = get_db()
    cursor = db.cursor()

    # Insert the new grade and save its ID
    cursor.execute('\n'.join([
        "INSERT OR REPLACE INTO grades (id, question_number, submission_id, grade)",
        "VALUES (",
        # The select statement below lets us keep the old grade ID
        "    (SELECT id FROM grades WHERE"
        "        question_number = ? AND",
        "        submission_id = ?),"
        "     ?, ?, ?)"
    ]), (question_number, submission_id, question_number, submission_id, grade))
    cursor.execute('\n'.join([
        "SELECT id FROM grades WHERE",
        "question_number = ? AND",
        "submission_id = ?"
    ]), (question_number, submission_id))
    grade_id = cursor.fetchone()[0]

    # Create new note records for all that haven't been created yet
    note_ids = []
    for note in notes:
        cursor.execute("INSERT OR IGNORE INTO notes (\"text\") VALUES (?)", (note,))
        cursor.execute("SELECT id FROM notes WHERE \"text\" = ?", (note,))
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


# This function will take a long time to run (at least as long as it takes
# for Refazer to fulfill the request).  Don't expect to get a response in less
# than 30 seconds, and it may take minutes.
@app.route('/synthesize', methods=['POST'])
def synthesize():

    question_number = int(request.form['question_number'])
    submission_id = request.form['submission_id']
    code_before = request.form['code_before']
    code_after = request.form['code_after']

    clusters = grader_questions[question_number].test_based_cluster
    fixes = []
    for cluster in clusters:
        fixes.extend(cluster.fixes)

    code_to_fix = []
    for submission_index, f in enumerate(fixes, start=0):
        code_to_fix.append({
            'before': f['before'],
            'submission_id': submission_index,
            'IsFixed': False,
        })

    # XXX Filter to just a subset of the examples that Refazer has fixed without
    # failure.  Need to find out why Refazer is failing, and use all ~600 examples.
    # code_to_fix = code_to_fix[23:25]
    code_to_fix = code_to_fix[:300]
    # print(code_to_fix[264])
    # print(code_to_fix[219])
    # print(code_to_fix[95])
    # print(code_to_fix[24])
    del code_to_fix[264]
    del code_to_fix[219]
    del code_to_fix[95]
    del code_to_fix[24]

    LOCALHOST_URL = "http://172.16.83.130:8000"
    # REFAZER_URL = "http://refazer2.azurewebsites.net"

    data = {
        'submissions': code_to_fix,
        'Examples': [{
            'before': code_before,
            'after': code_after,
        }]
    }
    result = requests.post(LOCALHOST_URL + "/api/refazer", json=data)
    fixes = result.json()

    # Fetch a list of all submissions that have been graded so far
    graded_submissions = get_graded_submissions(question_number)

    # Save all fixes to the database, with a link between the this submission
    # and the submission for which the fix was produced.
    grading_suggestions = []
    db = get_db()
    cursor = db.cursor()
    for fix in fixes:
        if fix['fixes_worked']:
            if fix['submission_id'] not in graded_submissions:
                grading_suggestions.append(fix['submission_id'])
            cursor.execute('\n'.join([
                "INSERT OR REPLACE INTO fixes (id, question_number, submission_id,",
                "   fixed_submission_id, before, after)",
                "VALUES (",
                "    (SELECT id FROM fixes WHERE"
                "        question_number = ? AND",
                "        submission_id = ? AND",
                "        fixed_submission_id = ?),",
                "    ?, ?, ?, ?, ?)",
            ]), (question_number, fix['submission_id'], submission_id,
                 question_number, fix['submission_id'], submission_id,
                 fix['before'], fix['fixed_code']))
    db.commit()

    return jsonify({
        'submissions': grading_suggestions,
    })


@app.route('/evaluate', methods=['POST'])
def evaluate():

    print('before_id',request.form['before_id'])
    before_id = request.form['before_id']
    question_number = int(request.form['question_number'])

    code_text = request.form['code']
    results = run_code_evaluations(code_text)

    '''
    #if results['overall_success']:
    # make call to Gustavo's server
    print(questions.keys())
    before_code = [sol['before'] for sol in grader_questions[question_number].submissions if int(sol['Id'])==int(before_id)][0]
    #fake_after_code = [sol['SynthesizedAfter'] for sol in grader_questions[question_number].submissions if int(sol['Id'])==int(before_id)][0]
    print('before_code',before_code)
    for sub in grader_questions[question_number].submissions:
        sub['diff_lines'] = []
        sub['diff_student_lines'] = []
        sub['diff_but_not_a_diff'] = []
        #sub['is_fixed'] = False
    print('sub',sub)
    data = requests.post('http://refazer2.azurewebsites.net/api/refazer', 
       json={
        "submissions": list(grader_questions[question_number].submissions)[0:10], 
        "Examples" : [{
            "before" : before_code,
            "after" : code_text
            }]
        })
    if data.ok:
       print("Number of submissions returned")
       submssions = data.json()
       len_fixed_submissions = len([sub for sub in submssions['submissions'] if sub['isFixed']])
       print(len_fixed_submissions)
    else:
        print(data.content)
    '''

    return jsonify(results)


def evaluate_function(code_text, function_name, input_value_tuples, expected_outputs):

    results = {
        'overall_success': False,
        'test_cases': []
    }

    # Compute the result of each individual test
    for test_index in range(len(input_value_tuples)):
        results['test_cases'].append(evaluate_function_once(
            code_text=code_text,
            function_name=function_name,
            input_values=input_value_tuples[test_index],
            expected_output=expected_outputs[test_index],
        ))
    
    # Compute the overall success across all tests
    results['overall_success'] = all(r['success'] for r in results['test_cases'])

    return results

def evaluate_function_once(code_text, function_name, input_values, expected_output):

    cant_run_code = False
    result = {
        'input_values': input_values,
        'expected': expected_output,
        'success': False,  # we assume the test case failed until it completely succeeds
        'exec_success': False,
        'timeout': True,
        'runtime_success': False,
    }

    # Save the original stdout so we can resume them after this function runs
    original_stdout = sys.stdout

    # Compile the code to runnable form
    try:
        code = compile(code_text, '<string>', 'exec')
        result['compile_success'] = True
    except SyntaxError as s:
        result['compile_success'] = False
        result['syntax_error'] = {
            'lineno': s.lineno,
            'offset': s.offset,
            'msg': s.msg,
            'text': s.text,
        }
        cant_run_code = True

    # Set up fresh scopes for the code to run within
    local_scope = {}
    global_scope = {}

    if cant_run_code is False:

        # Run the code to capture the function definition
        try:
            exec(code, global_scope, local_scope)
            result['exec_success'] = True
        except Exception as e:
            result['exec_exception'] = {
                'type': type(e),
                'args': e.args,
            }
            cant_run_code = True

    if cant_run_code is False:

        def run_function(function, function_name, input_values, result):

            # It's critical to do a few things here:
            # 1. Transfer the input values into the sandbox scope
            # 2. Transfer the function name into the sandbox global scope so it can be called
            #    recursively (otherwise, it can't be found for recursive calls)
            # 3. Store the output in a sandbox variable and retrieve it later.
            local_scope['input_values'] = input_values
            global_scope[function_name] = local_scope[function_name]

            # Create a new version of stdout to capture what gets printed
            capturable_stdout = StringIO()
            sys.stdout = capturable_stdout

            try:
                exec('output = ' + function_name + '(*input_values)', global_scope, local_scope)
                output = local_scope['output']
                result['returned'] = output
                result['stdout'] = capturable_stdout.getvalue()
                result['runtime_success'] = True
            except Exception as e:
                result['runtime_exception'] = {
                    'type': type(e),
                    'args': e.args,
                }

        # Create a new process to run the test function, so we can terminate it if it loops
        result_shared_data = Manager().dict()
        process = Process(
            target=run_function,
            args=(
                local_scope[function_name],
                function_name,
                input_values,
                result_shared_data,
            )
        )

        # Run the function, and terminate it if it runs too long
        process.start()
        start = time.time()
        while time.time() < start + PROCESS_TIMEOUT:
            if process.is_alive():
                time.sleep(.1)
            else:
                result['timeout'] = False
                break

        process.terminate()

        # Merge the results from the function that was run with the  main results
        result.update(result_shared_data)
        result['success'] = (result['returned'] == expected_output) if 'returned' in result else False

        # Return stdout to original
        sys.stdout = original_stdout
    
    return result

@app.route('/submit', methods=['POST'])
def submit_code():
    print(request.form)
    return jsonify(success=True)

@app.route('/add', methods=['POST'])
def add_hint():
    print('adding hint',request.form['question_number'], request.form['cluster_id'], request.form['tab_id'], request.form['text'])
    db = get_db()
    db.execute('INSERT INTO entries (title, question_number, cluster_id, tab_id, text) VALUES (?, ?, ?, ?, ?)',
                 ['title', request.form['question_number'], request.form['cluster_id'], request.form['tab_id'], request.form['text']])
    db.commit()

    #does this need to be updated? TODO
    return redirect(url_for('show_detail', question_number=request.form['question_number'], tab_id=request.form['tab_id'], cluster_id=request.form['cluster_id'], filter=request.form['filter']))

@app.route('/update', methods=['POST'])
def update_hint():
    db = get_db()
    db.execute('UPDATE entries SET text=? WHERE cluster_id=? AND question_number=? AND tab_id=?', [request.form['text'], request.form['cluster_id'], request.form['question_number'], request.form['tab_id']])
    db.commit()
    return redirect(url_for('show_detail', question_number=request.form['question_number'], tab_id=request.form['tab_id'], cluster_id=request.form['cluster_id'], filter=request.form['filter']))


if __name__ == '__main__':
    initdb_command()
    init_app()
    port = int(os.environ.get('PORT', 5000))
    app.config.update(
        DEBUG=True,
        TEMPLATES_AUTO_RELOAD=True
    )
    app.run(host='0.0.0.0', port=port)
