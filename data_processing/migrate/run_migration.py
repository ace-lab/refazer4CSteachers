#! /usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals
import logging
import os
import inspect
import re
import importlib
from playhouse.migrate import PostgresqlMigrator, SqliteMigrator

from models import db_proxy


logger = logging.getLogger('data')
path_to_migrations = '.'.join(__name__.split('.')[:-1])


def main(migration_name, db, *args, **kwargs):

    # Create a migrator for the type of database that is being used
    if db == 'sqlite':
        migrator = SqliteMigrator(db_proxy)
    elif db == 'postgres':
        migrator = PostgresqlMigrator(db_proxy)
    else:
        logger.error("Could not find appropriate migrator for the database.")
        return

    # Import migration module and run forward migration
    module_name = path_to_migrations + '.' + migration_name
    migration = importlib.import_module(module_name)
    migration.forward(migrator)


def configure_parser(parser):

    parser.description = "Run a migration script. These can only be run forward, not in reverse."

    # Inspect the local directory for which migration modules the user can run.
    local_files = os.listdir(
        os.path.dirname(
            inspect.getfile(
                inspect.currentframe()
            )))
    migration_files = [f for f in local_files if re.match('^\d{4}.*\.py$', f)]
    migration_names = [m.rstrip('.py') for m in migration_files]

    parser.add_argument(
        'migration_name',
        choices=migration_names,
        help="The name of the migration script you want to run."
    )
