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

create table if not exists sessions (
  id integer primary key,
  user_id integer not null,
  question_number integer not null,
  session_id integer not null,
  foreign key (user_id) references users(id)
  unique(user_id, question_number)
);

create table if not exists queries (
  session_id integer not null,
  submission_id integer not null,
  fix_suggested boolean not null,
  feedback_suggested boolean not null,
  timestamp datetime default current_timestamp
);

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

create table if not exists submission_samples (
  id integer primary key,
  user_id integer not null,
  question_number integer not null,
  submission_id integer not null,  /* refers to submission_id field in submissions table */
  sample_type text not null,
  foreign key (user_id) references users(id)
);

create table if not exists grades (
  id integer primary key,
  session_id integer note null,
  question_number integer not null,
  submission_id integer not null,
  grade float,
  propagated boolean,
  dirty boolean,
  timestamp datetime default current_timestamp,
  unique(session_id, question_number, submission_id)
);

create table if not exists notes (
  id integer primary key,
  session_id integer not null,
  'text' text not null,
  timestamp datetime default current_timestamp,
  unique(id, 'text')
);

create table if not exists gradenotes (
  id integer primary key,
  note_id integer not null,
  grade_id integer not null,
  timestamp datetime default current_timestamp,
  foreign key (note_id) references notes(id),
  foreign key (grade_id) references grades(id),
  unique(note_id, grade_id)
);

create table if not exists codeedits (
  id integer primary key,
  session_id integer not null,
  question_number integer not null,
  submission_id integer not null,
  code text not null,
  timestamp datetime default current_timestamp
);

create table if not exists fixes (
  id integer primary key,
  session_id integer not null,
  question_number integer not null,
  /* Note that this refers to the submission_id column on the submissions table.
     This is in contrast to the submission_id column on the testresults tabe, that 
     is a foreign key to the `id` column on the submissions table.  Sorry. */
  submission_id integer not null,
  transformation_id integer not null,
  fixed_submission_id integer not null,  /* which submission was fixed to produce this fix */
  before text not null,
  after text not null,
  timestamp datetime default current_timestamp,
  unique(session_id, question_number, submission_id, transformation_id)
);
