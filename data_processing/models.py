import logging
import datetime
import json
import copy
import os.path
from peewee import Model, SqliteDatabase, Proxy, PostgresqlDatabase,\
    IntegerField, DateTimeField, TextField, BooleanField, FloatField, ForeignKeyField


logger = logging.getLogger('data')

POSTGRES_CONFIG_NAME = 'postgres-credentials.json'
DATABASE_PATH = os.path.join(os.pardir, 'flaskr.db')
db_proxy = Proxy()


class BatchInserter(object):
    '''
    A class for saving database records in batches.
    Save rows to the batch inserter, and it will save the rows to
    the database after it has been given a batch size of rows.
    Make sure to call the `flush` method when you're finished using it
    to save any rows that haven't yet been saved.

    Assumes all models have been initialized to connect to db_proxy.
    '''
    def __init__(self, ModelType, batch_size, fill_missing_fields=False):
        '''
        ModelType is the Peewee model to which you want to save the data.
        If the rows you save will have fields missing for some of the records,
        set `fill_missing_fields` to true so that all rows will be augmented
        with all fields to prevent Peewee from crashing.
        '''
        self.rows = []
        self.ModelType = ModelType
        self.batch_size = batch_size
        self.pad_data = fill_missing_fields

    def insert(self, row):
        '''
        Save a row to the database.
        Each row is a dictionary of key-value pairs, where each key is the name of a field
        and each value is the value of the row for that column.
        '''
        self.rows.append(row)
        if len(self.rows) >= self.batch_size:
            self.flush()

    def flush(self):
        if self.pad_data:
            self._pad_data(self.rows)
        with db_proxy.atomic():
            self.ModelType.insert_many(self.rows).execute()
        self.rows = []

    def _pad_data(self, rows):
        '''
        Before we can bulk insert rows using Peewee, they all need to have the same
        fields.  This method adds the missing fields to all rows to make
        sure they all describe the same fields.  It does this destructively
        to the rows provided as input.
        '''
        # Collect the union of all field names
        field_names = set()
        for row in rows:
            field_names = field_names.union(row.keys())

        # We'll enforce that default for all unspecified fields is NULL
        default_data = {field_name: None for field_name in field_names}

        # Pad each row with the missing fields
        for i, _ in enumerate(rows):
            updated_data = copy.copy(default_data)
            updated_data.update(rows[i])
            rows[i] = updated_data


class ProxyModel(Model):
    ''' A peewee model that is connected to the proxy defined in this module. '''

    class Meta:
        database = db_proxy


class Command(ProxyModel):
    '''
    A data-processing command run as part of this package.
    We save this so we can do forensics on what data and commands we used to produce
    computations and dumps of data.
    '''

    # Keep a record of when this command was performed
    date = DateTimeField(default=datetime.datetime.now)

    # The main part of this record is just a list of arguments we used to perform it
    arguments = TextField()


class User(ProxyModel):

    class Meta:
        db_table = 'users'

    username = TextField()


class Session(ProxyModel):

    class Meta:
        db_table = 'sessions'

    user = ForeignKeyField(User)
    question_number = IntegerField()
    session_id = IntegerField()


class Fix(ProxyModel):

    class Meta:
        db_table = 'fixes'

    session = ForeignKeyField(Session, to_field='session_id')
    question_number = IntegerField()
    submission_id = IntegerField()
    transformation_id = IntegerField()
    fixed_submission_id = IntegerField()
    before = TextField()
    after = TextField()
    timestamp = DateTimeField()


class Grade(ProxyModel):

    class Meta:
        db_table = 'grades'

    session = ForeignKeyField(Session, to_field='session_id')
    question_number = IntegerField()
    submission_id = IntegerField()
    fix_suggested = TextField()
    fix_used = TextField()
    fix_changed = TextField()
    grade_suggested = TextField()
    grade_used = TextField()
    grade_changed = TextField()
    timestamp = DateTimeField()


class FixEvent(ProxyModel):
    ''' A synthesis event related to either providing an example or receiving fixes. '''

    # Keep a record of when this record was computed
    compute_index = IntegerField(index=True)
    date = DateTimeField(default=datetime.datetime.now)

    username = TextField(index=True)
    session = ForeignKeyField(Session, to_field='session_id', index=True)
    question_number = IntegerField(index=True)
    submission_id = IntegerField(index=True)  # refers to submission_id field in submissions table
    event_type = TextField(index=True)
    fix_suggested = BooleanField(null=True)
    fix_used = BooleanField(null=True)
    fix_changed = BooleanField(null=True)
    timestamp = DateTimeField(index=True)
    transformation_id = IntegerField(null=True)
    fixed_submission_id = IntegerField(null=True)


class FirstFix(FixEvent):
    '''
    A fix event that was the first to fix the submission.
    Note that in the case that a fix was synthesized for a submission before manual
    feedback was given, the fix event will appear twice: once when it was synthesized,
    and once when it was given feedback by hand.
    In other cases, feedback by hand precludes a synthesized fix being reported.
    '''
    pass


def init_database(db_type, config_filename=None):

    if db_type == 'postgres':

        # If the user wants to use Postgres, they should define their credentials
        # in an external config file, which are used here to access the database.
        config_filename = config_filename if config_filename else POSTGRES_CONFIG_NAME
        with open(config_filename) as pg_config_file:
            pg_config = json.load(pg_config_file)

        config = {}
        config['user'] = pg_config['dbusername']
        if 'dbpassword' in pg_config:
            config['password'] = pg_config['dbpassword']
        if 'host' in pg_config:
            config['host'] = pg_config['host']
        if 'port' in pg_config:
            config['port'] = pg_config['port']

        db = PostgresqlDatabase(DATABASE_NAME, **config)

    # Sqlite is the default type of database.
    elif db_type == 'sqlite' or not db_type:
        db = SqliteDatabase(DATABASE_PATH)

    db_proxy.initialize(db)


def create_tables():
    db_proxy.create_tables([
        Command,
        FixEvent,
        FirstFix,
    ], safe=True)
