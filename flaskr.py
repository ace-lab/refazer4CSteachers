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
codes = {}

@app.route('/')
def show_entries():
    # db = get_db()
    # cur = db.execute('select title, text from entries order by id desc')
    # entries = cur.fetchall()

    global codes
    global orderedClusters

    codes = {}
    orderedClusters = []

    with open('response.json') as data_file:
    	data = json.load(data_file)

    dict = {}

    for i in data:
        fix = i['UsedFix']
        if(type(fix) == type(u'unicode')):
            fix = fix.replace('\\', '')
        dict[fix] = dict.get(fix, 0) + 1
        emp = codes.get(fix, [])
        emp.append( (i['before'], i['after']))
        codes[fix] = codes.get(fix, emp)


    beforeExample = data[0]['before']
    afterExample = data[0]['after']
    beforeExample2 = data[1]['before']
    afterExample2 = data[1]['after']

    beforeMap = {'example':beforeExample, 'example2':beforeExample2}
    afterMap = {'example':afterExample, 'example2':afterExample2}

    files = highlight.diff_files(beforeMap, afterMap, 'full')

    for x in dict.keys():
        item = (x, dict.get(x))
        if(type(item[0]) == type(u'unicode')):
            orderedClusters.append((item[0].replace("\\", ""), item[1]))
        else:
            orderedClusters.append(item)

    orderedClusters = sorted(orderedClusters, key=lambda cluster: -cluster[1])

    return render_template('layout.html', clusters = orderedClusters, files = [], rule = "")

@app.route('/<int:cluster_id>')
def show_detail(cluster_id):
    global codes
    global orderedClusters

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


    return render_template('layout.html', clusters = orderedClusters, files = files.values(), rule = fix)




if __name__ == '__main__':
    # initdb_command()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
