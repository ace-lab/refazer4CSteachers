# all the imports
import os
import sqlite3
from flask import Flask, request, session, g, redirect, url_for, abort, \
     render_template, flash
import json
import highlight

# create our little application :)
app = Flask(__name__)
app.config.from_object(__name__)
orderedClusters = []
current_question = []
questions = {1:'accumulate-mistakes.json', 2:'G-mistakes.json', 3:'Product-mistakes.json', 4:'repeated-mistakes.json'}

app.config.update(dict(
    DATABASE=os.path.join(app.root_path, 'flaskr.db'),
    SECRET_KEY='development key',
    USERNAME='admin',
    PASSWORD='default'
))

app.config.from_envvar('FLASKR_SETTINGS', silent=True)

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

def prepare(question_number):
    global codes
    global orderedClusters
    global current_question
    global questions

    codes = {}
    orderedClusters = []

    current_question = question_number

    with open(questions[question_number]) as data_file:
    	data = json.load(data_file)

    dict = {}

    for i in data:
        if(i['IsFixed'] == True):
            fix = i['UsedFix']
            if(type(fix) == type(u'unicode')):
                fix = fix.replace('\\', '')
            dict[fix] = dict.get(fix, 0) + 1
            emp = codes.get(fix, [])
            emp.append( (i['before'], i['SynthesizedAfter']))
            codes[fix] = codes.get(fix, emp)

    for x in dict.keys():
        item = (x, dict.get(x))
        if(type(item[0]) == type(u'unicode')):
            aux = item[0].replace("\\", "")
            codePair = codes[aux][0]

            beforeMap = {"example":codePair[0]}
            afterMap = {"example":codePair[1]}

            filesSample = highlight.diff_files(beforeMap, afterMap, 'full')
            for lines in filesSample.values():
                for line in lines:
                    line.contents = line.contents.replace("<", "&lt")
                    line.contents = line.contents.replace(">", "&gt");

            orderedClusters.append((aux, item[1], aux.count("Insert"), aux.count("Update"), aux.count("Delete"), filesSample.values()))

    orderedClusters = sorted(orderedClusters, key=lambda cluster: -cluster[1])


@app.route('/<int:question_number>')
def show_question(question_number):
    prepare(question_number)

    db = get_db()
    cur = db.execute('select title, cluster_id, text from entries order by id desc')
    entries = cur.fetchall()

    return render_template('layout.html', question_name = questions[question_number], question_number = question_number, clusters = orderedClusters, files = [], rule = "", entries = entries, cluster_id = -1)


@app.route('/')
def show_entries():
    prepare(1)

    db = get_db()
    cur = db.execute('select title, cluster_id, text from entries order by id desc')
    entries = cur.fetchall()

    return render_template('layout.html', question_name = questions[1], question_number = 1, clusters = orderedClusters, files = [], rule = "", entries = entries, cluster_id = -1)

@app.route('/<int:question_number>/<int:cluster_id>')
def show_detail(question_number, cluster_id):
    print(url_for('show_detail', question_number=1, cluster_id=0))
    global codes
    global orderedClusters

    db = get_db()
    cur = db.execute('select title, cluster_id, text from entries order by id desc')
    entries = cur.fetchall()

    if(question_number != current_question):
        prepare(question_number)


    beforeMap = {}
    afterMap = {}
    fix = orderedClusters[cluster_id][0]

    pairs_before_after = codes.get(fix, [])

    idx = 0
    for pair_before_after in pairs_before_after:
        beforeMap['example'+str(idx)] = pair_before_after[0]
        afterMap['example'+str(idx)] = pair_before_after[1]
        idx = idx+1
    files = highlight.diff_files(beforeMap, afterMap, 'full')

    for lines in files.values():
        for line in lines:
            line.contents = line.contents.replace("<", "&lt")
            line.contents = line.contents.replace(">", "&gt");


    return render_template('layout.html', question_name = questions[question_number], question_number = question_number, clusters = orderedClusters, files = files.values(), rule = fix, entries = entries, cluster_id=cluster_id)


@app.route('/delete', methods=['POST'])
def delete_tip():

    db = get_db()
    db.execute('delete from entries where cluster_id=' + request.form['cluster_id'] + ' and question_number=' + request.form['question_number'])
    db.commit()
    # print("Aqui")
    # print(request.form['cluster_id'])
    # flash('New entry was successfully posted')
    return redirect(url_for('show_detail', question_number=current_question, cluster_id=request.form['cluster_id']))

@app.route('/add', methods=['POST'])
def add_tip():

    db = get_db()
    db.execute('insert into entries (title, cluster_id, question_number, text) values (?, ?, ?, ?)',
                 ['title', request.form['cluster_id'], request.form['question_number'], request.form['text']])
    db.commit()
    print("Aqui")
    print(request.form['cluster_id'])
    flash('New entry was successfully posted')
    return redirect(url_for('show_detail', question_number=current_question, cluster_id=request.form['cluster_id']))

if __name__ == '__main__':
    # initdb_command()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
