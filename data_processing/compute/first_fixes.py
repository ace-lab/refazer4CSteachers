import logging
from peewee import fn

from models import FixEvent, FirstFix


logger = logging.getLogger('data')


def compute_first_fixes(event_compute_index=None):

    last_compute_index = FirstFix.select(fn.Max(FirstFix.compute_index)).scalar() or 0
    compute_index = last_compute_index + 1

    if event_compute_index is None:
        event_compute_index = FixEvent.select(fn.Max(FixEvent.compute_index)).scalar()

    # Fetch a list of all session IDs
    fix_events_by_session = (
        FixEvent.select(fn.Distinct(FixEvent.session))
        .where(FixEvent.compute_index == event_compute_index)
    )
    session_ids = [event.session_id for event in fix_events_by_session]

    for session_id in session_ids:

        # Filter the fix events to just those for this session,
        # ordered by the times at which they were fixed
        session_events = (
            FixEvent.select()
            .where(
                FixEvent.session_id == session_id,
                FixEvent.compute_index == event_compute_index,
            )
            .order_by(FixEvent.timestamp, 'asc')
        )

        automatically_fixed_submissions = []
        manually_fixed_submissions = []

        for event in session_events:

            event_type = event.event_type
            submission_id = event.submission_id
            authoring_event = event_type.startswith('authored')
            propagation_event = event_type.startswith('applied')
            if propagation_event:
                print("Manual:", submission_id in manually_fixed_submissions, "Automatic:", submission_id in automatically_fixed_submissions)

            # Only mark this as a "first fix" if we haven't seen a fix for it before,
            # or if a fix was "propagated" to it but not yet checked by hand
            if ((authoring_event and submission_id not in manually_fixed_submissions) or
                (propagation_event and 
                    (submission_id not in manually_fixed_submissions) and
                    (submission_id not in automatically_fixed_submissions))):

                FirstFix.create(
                    compute_index=compute_index,
                    username=event.username,
                    session=event.session,
                    question_number=event.question_number,
                    submission_id=event.submission_id,
                    event_type=event.event_type,
                    timestamp=event.timestamp,
                    fix_suggested=event.fix_suggested,
                    fix_used=event.fix_used,
                    fix_changed=event.fix_changed,
                    transformation_id=event.transformation_id,
                    fixed_submission_id=event.fixed_submission_id,
                )

            # Save a note that we have fixed this submission
            if authoring_event and submission_id not in manually_fixed_submissions:
                manually_fixed_submissions.append(event.submission_id)
            elif propagation_event and submission_id not in automatically_fixed_submissions:
                automatically_fixed_submissions.append(event.submission_id)


def main(event_compute_index, *args, **kwargs):
    compute_first_fixes(event_compute_index)


def configure_parser(parser):
    parser.description = "Compute a list of events related to fixing student submissions"
    parser.add_argument(
        '--event-compute-index',
        type=int,
        help=(
            "Which compute index of fix events to scan for first fixes. " +
            "If not specified, defaults to the most recent computation of fix events."
        )
    )
