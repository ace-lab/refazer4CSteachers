import logging
from playhouse.migrate import migrate
from peewee import BooleanField


logger = logging.getLogger('data')


def forward(migrator):
    migrate(
        migrator.add_column('fixevent', 'fix_suggested', BooleanField(null=True)),
        migrator.add_column('fixevent', 'fix_used', BooleanField(null=True)),
        migrator.add_column('fixevent', 'fix_changed', BooleanField(null=True)),
    )
