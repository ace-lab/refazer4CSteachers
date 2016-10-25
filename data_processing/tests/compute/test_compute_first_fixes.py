import logging
import datetime

from compute.first_fixes import compute_first_fixes
from tests.base import TestCase
from tests.modelfactory import create_fix_event, create_session
from models import FixEvent, FirstFix, Session, User


logger = logging.getLogger('data')


class ComputeLocationRatingTest(TestCase):

    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(
            [FixEvent, FirstFix, User, Session],
            *args, **kwargs
        )

    def test_create_first_fix_for_novel_visits(self):

        # Create fix events for multiple submissions
        create_session()
        create_fix_event(
            submission_id=0,
        )
        create_fix_event(
            submission_id=1,
        )

        # We should be able to find a first fix for each of these submissions
        compute_first_fixes()
        first_fixes = FirstFix.select()
        self.assertEqual(first_fixes.count(), 2)
        submission_ids = [fix.submission_id for fix in first_fixes]
        self.assertIn(0, submission_ids)
        self.assertIn(1, submission_ids)

    def test_omit_second_fix_for_duplicate_visit(self):

        # Both of these fix events fix the same submission.  We should only record
        # the first one as a "first fix".
        create_session()
        create_fix_event(
            submission_id=1,
            event_type="authored",
            timestamp=datetime.datetime(2000, 1, 1, 12, 0, 1, 0),
        )
        create_fix_event(
            submission_id=1,
            event_type="authored",
            timestamp=datetime.datetime(2000, 1, 1, 12, 0, 30, 0),
        )

        # We should be able to find a first fix for each of these submissions
        compute_first_fixes()
        first_fixes = FirstFix.select()
        self.assertEqual(first_fixes.count(), 1)

    def test_omit_second_fix_for_duplicate_synthesis_fix(self):

        # This is the same as the last test case, except this time around, the submission
        # has been fixed by a synthesized fix instead of by hand.
        create_session()
        create_fix_event(
            submission_id=1,
            event_type="applied",
            timestamp=datetime.datetime(2000, 1, 1, 12, 0, 1, 0),
        )
        create_fix_event(
            submission_id=1,
            event_type="applied",
            timestamp=datetime.datetime(2000, 1, 1, 12, 0, 30, 0),
        )

        compute_first_fixes()
        first_fixes = FirstFix.select()
        self.assertEqual(first_fixes.count(), 1)

    def test_implicitly_order_first_fixes_by_timestamp(self):

        # Even though these fix events are out of order, we should be able to detect that
        # the second one is actually the first fix.
        create_session()
        create_fix_event(
            submission_id=1,
            timestamp=datetime.datetime(2000, 1, 1, 12, 0, 30, 0),
        )
        create_fix_event(
            submission_id=1,
            timestamp=datetime.datetime(2000, 1, 1, 12, 0, 1, 0),
        )

        compute_first_fixes()
        first_fix = FirstFix.select().first()
        self.assertEqual(first_fix.timestamp, datetime.datetime(2000, 1, 1, 12, 0, 1, 0))

    def test_omit_first_fix_for_synthesis_after_visit_to_submission(self):

        create_session()
        create_fix_event(
            event_type="authored",
            submission_id=0,
            timestamp=datetime.datetime(2000, 1, 1, 12, 0, 1, 0),
        )
        create_fix_event(
            event_type="applied",
            submission_id=0,
            timestamp=datetime.datetime(2000, 1, 1, 12, 0, 30, 0),
        )

        compute_first_fixes()
        first_fixes = FirstFix.select()
        self.assertEqual(first_fixes.count(), 1)
        self.assertEqual(first_fixes.first().event_type, "authored")

    def test_include_first_fix_for_visit_after_synthesis(self):

        create_session()
        create_fix_event(
            event_type="applied",
            submission_id=0,
            timestamp=datetime.datetime(2000, 1, 1, 12, 0, 1, 0),
        )
        create_fix_event(
            event_type="authored",
            submission_id=0,
            timestamp=datetime.datetime(2000, 1, 1, 12, 0, 30, 0),
        )

        compute_first_fixes()
        first_fixes = FirstFix.select()
        self.assertEqual(first_fixes.count(), 2)
        event_types = [fix.event_type for fix in first_fixes]
        self.assertIn("applied", event_types)
        self.assertIn("authored", event_types)

    def test_group_first_fixes_by_session(self):

        # Even though these two fix events fix the same submission ID, they should be
        # considered distinct as they belong to a different synthesis session.
        create_session(session_id=0)
        create_session(session_id=1)
        create_fix_event(
            session_id=0,
            submission_id=1,
            event_type="applied",
            timestamp=datetime.datetime(2000, 1, 1, 12, 0, 1, 0),
        )
        create_fix_event(
            session_id=1,
            submission_id=1,
            event_type="applied",
            timestamp=datetime.datetime(2000, 1, 1, 12, 0, 30, 0),
        )

        compute_first_fixes()
        first_fixes = FirstFix.select()
        self.assertEqual(first_fixes.count(), 2)

    def test_only_inspect_fixes_from_compute_index(self):

        # Even though these two fix events fix the same submission ID, they should be
        # considered distinct as they belong to a different synthesis session.
        create_session()
        create_fix_event(
            compute_index=0,
            submission_id=0,
        )
        create_fix_event(
            compute_index=0,
            submission_id=1,
        )
        create_fix_event(
            compute_index=1,
            submission_id=1,
        )

        compute_first_fixes(event_compute_index=1)
        first_fixes = FirstFix.select()
        self.assertEqual(first_fixes.count(), 1)

    def test_only_inspect_fixes_from_most_recent_compute_index_if_not_specified(self):

        # Even though these two fix events fix the same submission ID, they should be
        # considered distinct as they belong to a different synthesis session.
        create_session()
        create_fix_event(
            compute_index=0,
            submission_id=0,
        )
        create_fix_event(
            compute_index=0,
            submission_id=1,
        )
        create_fix_event(
            compute_index=1,
            submission_id=1,
        )

        compute_first_fixes()
        first_fixes = FirstFix.select()
        self.assertEqual(first_fixes.count(), 1)
