appname: grader
groupname: grader
group_users:
- andrew
domain: grader.tutorons.com
localport: 8030
projectdir: /home/andrew/drive/{{ appname }}
repo: https://github.com/lucasmf/refazer4education
branch: grader-tab
privatebucket: refazer-grader
venv: "{{ projectdir }}/venv"
src: "{{ projectdir }}/src"
logdir: "{{ projectdir }}/logs"
code_data: "{{ projectdir }}/data"
flask_dir: "{{ src }}"
sqlite_database: "{{ code_data }}/{{ appname }}.db"
