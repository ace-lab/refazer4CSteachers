# all the imports
import os
import sqlite3
from flask import Flask, request, session, g, redirect, url_for, abort, \
     render_template, flash
import json
import highlight
import math

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
    def __init__(self, question_id, rule_based_cluster, test_based_cluster, rule_and_test_based_cluster):
        self.question_id = question_id,
        self.rule_based_cluster = rule_based_cluster,
        self.test_based_cluster = test_based_cluster
        self.rule_and_test_based_cluster = rule_and_test_based_cluster


app = Flask(__name__)
app.config.from_object(__name__)
ordered_clusters = []
group_id_to_test = {}

question_files = {
    1:'accumulate-mistakes.json',
    2:'G-mistakes.json',
    3:'Product-mistakes.json',
    4:'repeated-mistakes.json'
    }

app.config.update(dict(
    DATABASE=os.path.join(app.root_path, 'flaskr.db'),
    SECRET_KEY='development key',
    USERNAME='admin',
    PASSWORD='default'
))

app.config.from_envvar('FLASKR_SETTINGS', silent=True)

def get_coverage(question_number,entries):

    covered_bugs = 0
    for entry in entries:
        covered_bugs+=questions[question_number].rule_based_cluster['cluster_id'].number
    total_bugs = 1
    return math.ceil(covered_bugs*100/total_bugs)

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


def create_question(question_number):
    ordered_clusters = []

    with open('data/'+question_files[question_number]) as data_file:
    	submission_pairs = json.load(data_file)

    clustered_fixes_by_rule = {}
    clustered_fixes_by_test = {}
    clustered_fixes_by_rule_and_test = {}
    group_id_to_test_for_a_question = {}

    group_id = -1
    checked_tests = []

    rule_and_test_based_cluster = []

    for submission_pair in submission_pairs:
        if (submission_pair['IsFixed'] == True):
            rule = submission_pair['UsedFix']
            rule = rule.replace('\\', '')

            fix = submission_pair
            code_before = submission_pair['before']
            code_after = submission_pair['SynthesizedAfter']
            filename = 'filename-' + str(submission_pair['Id'])
            diff_lines = highlight.diff_file(filename, code_before, code_after, 'full')

            test = get_test(submission_pair['failed'])
            fix['diff_lines'] = diff_lines
            fix['tests'] = test

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
                        test_based_cluster = test_based_clusters, rule_and_test_based_cluster=rule_and_test_based_cluster)

    return question

def init_app():
    global group_id_to_test
    group_id_to_test = {}
    global questions
    questions = {}
    for question_number in question_files.keys():
        questions[question_number] = create_question(question_number)
    print(questions)

def connect_db():
    """Connects to the specific database."""
    rv = sqlite3.connect(app.config['DATABASE'])
    rv.row_factory = sqlite3.Row
    return rv

def init_db():
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

def get_fixes(question_number):
    #todo: add question number to schema and db.execute call
    db = get_db()
    cur = db.execute('select title, cluster_id, text from entries order by id desc')
    fixes = cur.fetchall()
    return fixes

@app.route('/<int:question_number>')
def show_question(question_number):
    return redirect(url_for('show_detail', question_number=question_number, view_id=0, cluster_id=0, group_id=0))

@app.route('/')
def show_fixes():
    return redirect(url_for('show_detail', question_number=1, view_id=0, cluster_id=0, group_id=0))

@app.route('/<int:question_number>/<int:view_id>/<int:cluster_id>')
def show_detail(question_number, view_id, cluster_id):

    fixes = get_fixes(question_number)
    coverage_percentage = get_coverage(question_number, fixes)

    print (questions[question_number].rule_based_cluster[0][0].fixes)
    if (view_id==0):
        return render_template('show_fixes_by_rules.html', question_name = question_files[question_number],
                               question_number = question_number, clusters = questions[question_number].rule_based_cluster[0],
                               fixes = fixes, cluster_id=cluster_id,
                               coverage_percentage=coverage_percentage)
    elif (view_id==1):

        return render_template('show_fixes_by_test.html', question_name = questions[question_number],
                               question_number = question_number, clusters = questions[question_number].test_based_cluster,
                               fixes = fixes, cluster_id=cluster_id,
                               coverage_percentage=coverage_percentage)
    elif (view_id==2):
        return render_template('show_fixes_by_testsxrules.html', question_name = questions[question_number],
                               question_number = question_number, clusters = questions[question_number].rule_and_test_based_cluster,
                               fixes = fixes, cluster_id=cluster_id,
                               coverage_percentage=coverage_percentage)
        

# @app.route('/delete', methods=['POST'])
# def delete_hint():
#     db = get_db()
#     db.execute('delete from entries where cluster_id=' + request.form['cluster_id'] + ' and question_number=' + request.form['question_number'])
#     db.commit()
#     return redirect(url_for('show_detail', question_number=request.form['question_number'], view_id=0 cluster_id=request.form['cluster_id']))

# @app.route('/add', methods=['POST'])
# def add_hint():
#     db = get_db()
#     db.execute('insert into entries (title, cluster_id, question_number, text) values (?, ?, ?, ?)',
#                  ['title', request.form['cluster_id'], request.form['question_number'], request.form['text']])
#     db.commit()
#     return redirect(url_for('show_detail', question_number=request.form['question_number'], cluster_id=request.form['cluster_id']))

if __name__ == '__main__':
    # initdb_command()
    init_app()
    port = int(os.environ.get('PORT', 5000))
    app.config.update(
        DEBUG=True,
        TEMPLATES_AUTO_RELOAD=True
    )
    app.run(host='0.0.0.0', port=port)
