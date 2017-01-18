appname: grader
groupname: ubuntu
group_users:
- ubuntu
domain: grader.tutorons.com
localport: 8030
projectdir: /usr/local/{{ appname }}
repo: https://github.com/andrewhead/refazer4grading
branch: master
privatebucket: refazer
venv: "{{ projectdir }}/venv"
src: "{{ projectdir }}/src"
logdir: "{{ projectdir }}/logs"
code_data: "{{ projectdir }}/data"
flask_dir: "{{ src }}"
sqlite_database: "{{ code_data }}/{{ appname }}.db"
