import logging

from dump.dump import dump_csv
from models import FixEvent, Session


logger = logging.getLogger('data')


@dump_csv(__name__, [
    "Id", "Compute Index", "User", "Session ID", "Question Number", "Submission ID",
    "Event Type", "Fix Suggested", "Fix Used", "Fix Changed", "Timestamp", 
    "Transformation ID", "Fixed Submission ID"])
def main(*args, **kwargs):

    for event in FixEvent.select():
        
        # Some of the links to sessions in our database are broken and
        # these sessions no longer exist.  Just use a null session ID for these records
        try:
            session_id = event.session.session_id
        except Session.DoesNotExist:
            session_id = None

        yield [[
            event.id,
            event.compute_index,
            event.username,
            session_id,
            event.question_number,
            event.submission_id,
            event.event_type,
            event.fix_suggested,
            event.fix_used,
            event.fix_changed,
            event.timestamp,
            event.transformation_id,
            event.fixed_submission_id,
        ]]

    raise StopIteration


def configure_parser(parser):
    parser.description = "Dump records of all fix events."
