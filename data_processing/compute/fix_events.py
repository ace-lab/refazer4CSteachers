import logging
from peewee import fn

from models import User, Fix, Grade, Session, FixEvent


logger = logging.getLogger('data')


def compute_fix_events():

    # Create a new index for this computation
    last_compute_index = FixEvent.select(fn.Max(FixEvent.compute_index)).scalar() or 0
    compute_index = last_compute_index + 1

    # Save fix events for the fixes that the user made manually
    for grade in Grade.select():

        # Determine how the grade was authored based on whether a grade was suggested,
        # applied, and changed when the participant gave feedback.
        grade_suggested = True if grade.grade_suggested == "true" else False
        grade_used = True if grade.grade_used == "true" else False
        grade_changed = True if grade.grade_changed == "true" else False
        event_type =\
            "authored - reused" if grade_used and not grade_changed else\
            "authored - reused and changed" if grade_used and grade_changed else\
            "authored - available and ignored" if grade_suggested and not grade_used else\
            "authored - from scratch"

        # Convert fix change status to Booleans
        fix_suggested = True if grade.fix_suggested == "true" else False
        fix_used = True if grade.fix_used == "true" else False
        fix_changed = True if grade.fix_changed == "true" else False

        FixEvent.create(
            compute_index=compute_index,
            username=grade.session.user.username,
            session=grade.session,
            question_number=grade.session.question_number,
            submission_id=grade.submission_id,
            event_type=event_type,
            timestamp=grade.timestamp,
            fix_suggested=fix_suggested,
            fix_used=fix_used,
            fix_changed=fix_changed,
        )

    # Save fix events for the fixes that were found by the Refazer server
    for fix in Fix.select():
        FixEvent.create(
            compute_index=compute_index,
            username=fix.session.user.username,
            session=fix.session,
            question_number=fix.session.question_number,
            submission_id=fix.session_id,
            event_type="applied",
            timestamp=fix.timestamp,
            transformation_id=fix.transformation_id,
            fixed_submission_id=fix.fixed_submission_id,
        )


def main(*args, **kwargs):
    compute_fix_events()


def configure_parser(parser):
    parser.description = "Compute a list of events related to fixing student submissions"
