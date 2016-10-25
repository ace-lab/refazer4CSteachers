import logging
import functools
from datetime import datetime
import json
import codecs
import time
import os.path


logger = logging.getLogger('data')


'''
The decorators named 'dump_*' take a "harvest" function that yields records,
and then pipes these records to a file in the data/ directory with the basename
specified by the 'dest_basename' argument.

For example,

@dump_json('json-data')
def my_func(*args, **kwargs):
    ...

Will run my_func as a generator.  With each invokation of the generator, it will
collect a JSON record or a list of records, and then dump those to a file
with the basename "json-data".
'''


def dump_json(dest_basename):
    ''' Iterate over a generator function and dump its JSON records to file. '''
    return functools.partial(
        _wrap_harvest_func_with_dump_func,
        dump_func=run_and_dump_json,
        dest_basename=dest_basename,
        file_extension='.json',
    )


def dump_text(dest_basename):
    ''' Iterate over a generator function to dump the text lines it yields to a file. '''
    return functools.partial(
        _wrap_harvest_func_with_dump_func,
        dump_func=run_and_dump_text,
        dest_basename=dest_basename,
        file_extension='.txt',
    )


def dump_csv(dest_basename, column_names, delimiter=','):
    ''' Iterate over a generator function to dump the text lines it yields to a file. '''
    return functools.partial(
        _wrap_harvest_func_with_dump_func,
        dump_func=functools.partial(
            run_and_dump_csv,
            column_names=column_names,
            delimiter=delimiter,
        ),
        dest_basename=dest_basename,
        file_extension='.csv',
    )


def make_dump_filename(dest_basename, file_extension):
    '''
    Create the name of a file for the results of a data "dump".
    One side-effect of this function is the creation of a 'dump' directory where
    this file can be saved.
    '''
    full_filename = dest_basename + '-' + time.strftime("%Y-%m-%d_%H:%M:%S") + file_extension
    if not os.path.exists('data'):
        os.makedirs('data')
    dump_path = os.path.join('data', full_filename)
    return dump_path


def _wrap_harvest_func_with_dump_func(harvest_func, dump_func, dest_basename, file_extension):

    @functools.wraps(harvest_func)
    def harvest_and_dump(*args, **kwargs):
        dump_path = make_dump_filename(dest_basename, file_extension)
        with codecs.open(dump_path, 'w', encoding='utf-8') as dump_file:
            dump_func(harvest_func, dump_file, *args, **kwargs)

    return harvest_and_dump


def run_and_dump_text(harvest_func, dump_file, *args, **kwargs):

    for line_list in harvest_func(*args, **kwargs):
        for line in line_list:
            dump_file.write(line + '\n')


def run_and_dump_csv(harvest_func, dump_file, column_names, delimiter, *args, **kwargs):

    def make_csv_line(record):
        # Convert all elements of the record into good CSV:
        # encapsulate all strings within double quotes, and
        # convert all other data types to writable strings.
        for index, item in enumerate(record):
            if type(item) == bytes or type(item) == str:
                escaped_string = item.replace('\r\n', "<newline>")
                escaped_string = escaped_string.replace('\n', "<newline>")
                record[index] = '"' + escaped_string + '"'
            elif isinstance(item, datetime):
                record[index] = item.isoformat()
            else:
                record[index] = str(item)
        return delimiter.join(record) + '\n'

    dump_file.write(make_csv_line(column_names))

    for line_list in harvest_func(*args, **kwargs):
        for line in line_list:
            dump_file.write(make_csv_line(line))


def run_and_dump_json(harvest_func, dump_file, *args, **kwargs):

    dump_file.write('[\n')
    first_record = True

    for value_list in harvest_func(*args, **kwargs):
        for record in value_list:

            if not first_record:
                dump_file.write(',\n')

            # Convert non-JSON data to JSON
            cleaned_record = {}
            for field, value in record.items():
                if isinstance(value, datetime):
                    cleaned_record[field] = value.isoformat()
                else:
                    cleaned_record[field] = value

            dump_file.write(json.dumps(cleaned_record))
            first_record = False

    dump_file.write('\n]')
