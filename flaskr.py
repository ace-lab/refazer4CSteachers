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
            orderedClusters.append((aux, item[1], aux.count("Insert"), aux.count("Update"), aux.count("Delete")))
        else:
            orderedClusters.append(item)

    orderedClusters = sorted(orderedClusters, key=lambda cluster: -cluster[1])


@app.route('/<int:question_number>')
def show_question(question_number):
    prepare(question_number)

    return render_template('layout.html', question_name = questions[question_number], question_number = question_number, clusters = orderedClusters, files = [], rule = "")


@app.route('/')
def show_entries():

    prepare(1)

    return render_template('layout.html', question_name = questions[1], question_number = 1, clusters = orderedClusters, files = [], rule = "")

@app.route('/<int:question_number>/<int:cluster_id>')
def show_detail(question_number, cluster_id):
    print("aqui")
    print(url_for('show_detail', question_number=1, cluster_id=1))
    global codes
    global orderedClusters

    if(question_number != current_question):
        prepare(question_number)


    # print(orderedClusters)

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


    return render_template('layout.html', question_name = questions[question_number], question_number = question_number, clusters = orderedClusters, files = files.values(), rule = fix)




if __name__ == '__main__':
    # initdb_command()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
