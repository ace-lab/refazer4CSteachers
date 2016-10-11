drop table if exists entries;
create table entries (
  id integer primary key,
  title text not null,
  cluster_id integer not null,
  question_number integer not null,
  tab_id integer not null,
  'text' text not null
);

drop table if exists users;
create table users (
  id integer primary key,
  username text not null,
  session_id integer,  /* A null session ID means one has to be generated */
  unique(username)
);
insert into users (username) values
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

drop table if exists submissions;
create table submissions (
  id integer primary key,
  question_number integer not null,
  submission_id integer not null,
  code text note null,
  unique(question_number, submission_id)
);

drop table if exists grades;
create table grades (
  id integer primary key,
  session_id integer note null,
  question_number integer not null,
  submission_id integer not null,
  grade float not null,
  unique(session_id, question_number, submission_id)
);

drop table if exists notes;
create table notes (
  id integer primary key,
  session_id integer not null,
  'text' text not null,
  unique(id, 'text')
);

drop table if exists gradenotes;
create table gradenotes (
  id integer primary key,
  note_id integer not null,
  grade_id integer not null,
  foreign key (note_id) references notes(id),
  foreign key (grade_id) references grades(id),
  unique(note_id, grade_id)
);

drop table if exists codeedits;
create table codeedits (
  id integer primary key,
  question_number integer not null,
  submission_id integer not null,
  code text not null,
  unique(question_number, submission_id)
);

drop table if exists fixes;
create table fixes (
  id integer primary key,
  session_id integer not null,
  question_number integer not null,
  submission_id integer not null,
  fixed_submission_id integer not null,  /* which submission was fixed to produce this fix */
  before text not null,
  after text not null,
  unique(session_id, question_number, submission_id, fixed_submission_id)
);
