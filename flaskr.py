# all the imports
import os
import sqlite3
from flask import Flask, request, session, g, redirect, url_for, abort, \
     render_template, flash
import json
import highlight
import math

class Cluster:
    def __init__(self, fix, number, groups, items):
        self.fix = fix
        self.number = number
        self.groups = groups
        self.items = items
        # self.diffs = diffs
        # self.diffs = [diff[0] in diff for diffs]
        # self.inputoutputIDs = [diff[1] in diff for diffs]
        # self.results = results

app = Flask(__name__)
app.config.from_object(__name__)
ordered_clusters = []
group_id_to_test = {}
questions = {
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
        #print(entry['cluster_id'],entry['text'])
        #print(ordered_clusters[question_number][entry['cluster_id']].number)
        covered_bugs+=ordered_clusters[question_number][entry['cluster_id']].number
    total_bugs = 0
    for cluster in ordered_clusters[question_number]:
        #print(cluster.number)#, cluster.cluster_id)
        total_bugs+=cluster.number
        #try: print(cluster.text)
        #except: print('no text')
    #print(covered_bugs,total_bugs)
    return math.ceil(covered_bugs*100/total_bugs)

def get_fix(question_number, cluster_id):
    return ordered_clusters[question_number][cluster_id].fix

def get_test(failed):
    #print('failed',failed)
    expected_value = ''
    output_value = ''
    previous_line = ''
    testcases = []
    for line in failed:
        #print(line)
        if previous_line == '# Error: expected':
            #print('this is an expected value')
            expected_value = line[1:].strip()
        if previous_line == '# but got':
            #print('this is the output value')
            output_value = line[1:].strip()
            #print(output_value)
        if line.startswith('>>>'):
            #print('test case:', line)
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

def prepare_question(question_number):

    ordered_clusters = []
    with open('data/'+questions[question_number]) as data_file:
    	data = json.load(data_file)

    dict = {}
    all_items = {}
    clustered_items = {}
    clustered_groups = {}
    group_id_to_test_for_a_question = {}

    group_id = -1
    checked_tests = []

    for i in data:
        if (i['IsFixed'] == True):
            fix = i['UsedFix']
            fix = fix.replace('\\', '')
            dict[fix] = dict.get(fix, 0) + 1

            item = i
            file_before = i['before']
            file_after = i['SynthesizedAfter']
            filename = 'filename-' + str(i['Id'])
            diff_lines = highlight.diff_file(filename, file_before, file_after, 'full')

            test = get_test(i['failed'])
            item['diff_lines'] = diff_lines
            item['tests'] = test

            if (test in checked_tests):
                group_id = checked_tests.index(test)
            else:
                checked_tests.append(test)
                group_id = len(checked_tests)


            item['group_id'] = group_id
            group_id_to_test_for_a_question[group_id] = test

            id = i['Id']
            all_items[id] = item

            if (fix in clustered_items.keys()):
                clustered_items[fix].append(item)
            else:
                clustered_items[fix] = [item]
                clustered_groups[fix] = []
            #print('i',i)

            # print('')
            # print('number of items so far',len(all_items.keys()))
            # print('num of items in this fix so far',dict[fix])
            # print('clustered_groups[fix]',clustered_groups[fix])
            # print('num of group_ids',len(clustered_groups[fix]))
            clustered_groups[fix].append(group_id)
            # print('clustered_groups[fix] after',clustered_groups[fix])
            # print('num of group_ids after',len(clustered_groups[fix]))

    for key in dict.keys():
        #print('key',key)
        arr = (key, dict.get(key))
        fix = arr[0]
        #print('yah',group_id_to_test_for_a_question[group_id][0])
        #print('list of group ids',clustered_groups[fix])
        groups = set(clustered_groups[fix])
        group_list = []
        total = 0
        for group_id in groups:
            #print(group_id, clustered_groups[fix], clustered_groups[fix].count(group_id))
            #print(group_id_to_test_for_a_question[group_id])
            number_of_items_with_this_fix_and_group_id = clustered_groups[fix].count(group_id)
            total += number_of_items_with_this_fix_and_group_id
            group_id_to_test_for_a_question[group_id][0]['count'] = number_of_items_with_this_fix_and_group_id
            print('group_id',group_id,': ',group_id_to_test_for_a_question[group_id][0])

            group_list.append({
                'group_id':group_id,
                'count':number_of_items_with_this_fix_and_group_id,
                'input':group_id_to_test_for_a_question[group_id][0]['input'],
                'expected':group_id_to_test_for_a_question[group_id][0]['expected'],
                'output':group_id_to_test_for_a_question[group_id][0]['output'],
            })

        #group = list(clustered_groups[fix]) #sorted(clustered_groups[fix],key=lambda group_id: group_id_to_test_for_a_question[group_id][0].output)
        #group_with_count = [ (group, len(group)) for group in group )]
        #print('group',group)
        #print('fix',fix,'groups',list(groups))
        ordered_groups = sorted(group_list, key=lambda group: -group['count'])
        print('ordered_groups',[grp['count'] for grp in ordered_groups])

        print('total',total,'number',arr[1])
        print('question_number',question_number)
        print('')

        items = clustered_items[fix]
        cluster = Cluster(fix=fix, number=arr[1], groups=ordered_groups, items=items)
        ordered_clusters.append(cluster)
        #ordered_clusters.append((fix, item[1], fix.count("Insert"), fix.count("Update"), fix.count("Delete"), filesSample.values()))


    #print('clust_id,clust.keys()')
    ordered_clusters = sorted(ordered_clusters, key=lambda cluster: -cluster.number)
    #for clust_id,clust in enumerate(ordered_clusters):
    #    print(clust_id,clust)

    #print('_for_a_question',group_id_to_test_for_a_question)
    return (ordered_clusters, group_id_to_test_for_a_question)

def init_app():
    global ordered_clusters
    ordered_clusters = {}
    global group_id_to_test
    group_id_to_test = {}

    for question_number in questions.keys():
        ordered_clusters[question_number],group_id_to_test[question_number] = prepare_question(question_number)
        #print("question number ", question_number, group_id_to_test[question_number])

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

def get_hints(question_number):
    #todo: add question number to schema and db.execute call
    db = get_db()
    cur = db.execute('select title, cluster_id, text from entries order by id desc')
    hints = cur.fetchall()
    return hints

@app.route('/<int:question_number>')
def show_question(question_number):
    return redirect(url_for('show_detail', question_number=question_number, cluster_id=0, group_id=0))

@app.route('/')
def show_entries():
    return redirect(url_for('show_detail', question_number=1, cluster_id=0, group_id=0))

@app.route('/<int:question_number>/<int:cluster_id>/<int:group_id>')
def show_detail(question_number, cluster_id, group_id):

    entries = get_hints(question_number)
    coverage_percentage = get_coverage(question_number, entries)

    #print('last time printing group_id_to_test', group_id_to_test)
    return render_template('layout.html', question_name = questions[question_number], question_number = question_number, clusters = ordered_clusters[question_number], entries = entries, cluster_id=cluster_id, group_id=group_id, coverage_percentage=coverage_percentage, group_id_to_test=group_id_to_test)

@app.route('/delete', methods=['POST'])
def delete_hint():
    db = get_db()
    db.execute('delete from entries where cluster_id=' + request.form['cluster_id'] + ' and question_number=' + request.form['question_number'])
    db.commit()
    return redirect(url_for('show_detail', question_number=request.form['question_number'], cluster_id=request.form['cluster_id']))

@app.route('/add', methods=['POST'])
def add_hint():
    db = get_db()
    db.execute('insert into entries (title, cluster_id, question_number, text) values (?, ?, ?, ?)',
                 ['title', request.form['cluster_id'], request.form['question_number'], request.form['text']])
    db.commit()
    return redirect(url_for('show_detail', question_number=request.form['question_number'], cluster_id=request.form['cluster_id']))

if __name__ == '__main__':
    # initdb_command()
    init_app()
    port = int(os.environ.get('PORT', 5000))
    app.config.update(
        DEBUG=True,
        TEMPLATES_AUTO_RELOAD=True
    )
    app.run(host='0.0.0.0', port=port)
