create table if not exists entries (
  id integer primary key,
  title text not null,
  cluster_id integer not null,
  question_number integer not null,
  tab_id integer not null,
  'text' text not null
);

create table if not exists users (
  id integer primary key,
  username text not null,
  session_id integer,  /* A null session ID means one has to be generated */
  unique(username)
);
insert or ignore into users (username) values
('admin1'), 
('admin2'), 
('admin3'), 
('admin4'), 
('user1'), 
('user2'), 
('user3'), 
('user4'), 
('user5'), 
('user6'), 
('user7'), 
('user8'), 
('user9'), 
('user10'); 

create table if not exists testresults (
  id integer primary key,
  submission_id integer not null,
  test_case_index integer not null,
  test_type text not null,
  success boolean not null,
  input_values text,
  expected text,
  observed text,
  assertion text,
  foreign key (submission_id) references submissions(id),
  unique(submission_id, test_case_index)
);

create table if not exists submissions (
  id integer primary key,
  question_number integer not null,
  submission_id integer not null,
  code text note null,
  unique(question_number, submission_id)
);

create table if not exists grades (
  id integer primary key,
  session_id integer note null,
  question_number integer not null,
  submission_id integer not null,
  grade float not null,
  unique(session_id, question_number, submission_id)
);

create table if not exists notes (
  id integer primary key,
  session_id integer not null,
  'text' text not null,
  unique(id, 'text')
);

create table if not exists gradenotes (
  id integer primary key,
  note_id integer not null,
  grade_id integer not null,
  foreign key (note_id) references notes(id),
  foreign key (grade_id) references grades(id),
  unique(note_id, grade_id)
);

create table if not exists codeedits (
  id integer primary key,
  question_number integer not null,
  submission_id integer not null,
  code text not null,
  unique(question_number, submission_id)
);

create table if not exists fixes (
  id integer primary key,
  session_id integer not null,
  question_number integer not null,
  submission_id integer not null,
  fixed_submission_id integer not null,  /* which submission was fixed to produce this fix */
  before text not null,
  after text not null,
  unique(session_id, question_number, submission_id, fixed_submission_id)
);
