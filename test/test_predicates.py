from datetime import date, datetime, timedelta, timezone
from functools import partial
from itertools import product
from test import fixtures as f
from typing import Callable, List, Tuple, TypeVar
from unittest import TestCase
from unittest.mock import Mock, create_autospec, patch

from freezegun import freeze_time

from archie.asana.client import Client
from archie.asana.models import Story, Task
from archie.predicates import (
    AlwaysTrue,
    Assigned,
    DueWithin,
    HasComment,
    HasDescription,
    HasEnumValue,
    HasExternal,
    HasNoDueDate,
    HasUnsetEnum,
    IsComplete,
    IsIncomplete,
    IsInProject,
    IsInProjectAndSection,
    Overdue,
    Predicate,
    Unassigned,
    Untriaged,
    _And,
    _duration_suffix,
    _for_at_least,
    _Not,
    _Or,
)

PST = timezone(timedelta(hours=-8))
T = TypeVar("T")


class DateBasedTestCase(TestCase):
    def _test_multiple_dates(
        self,
        predicate: Predicate,
        task_factory: Callable[[T], Task],
        inputs_and_expectations: List[Tuple[T, bool]],
    ) -> None:
        client = create_autospec(Client)
        for value, expectation in inputs_and_expectations:
            with self.subTest(input=value, expectation=expectation):
                task = task_factory(value)
                self.assertEqual(expectation, predicate(task, client))


class TestDurationSuffix(TestCase):
    def test_duration(self) -> None:
        delta = timedelta(days=2)
        self.assertEqual(" for at least 2 days, 0:00:00", _duration_suffix(delta))
        delta = timedelta(hours=2)
        self.assertEqual(" for at least 2:00:00", _duration_suffix(delta))

    def test_no_duration(self) -> None:
        self.assertEqual("", _duration_suffix(None))

    def test_max_duration(self) -> None:
        self.assertEqual("", _duration_suffix(timedelta.max))


@freeze_time(datetime(2019, 1, 3, 12, 0, 0, tzinfo=timezone.utc))
class TestForAtLeast(TestCase):
    task = f.task(created_at=datetime(2019, 1, 1, 12, 0, 0, tzinfo=timezone.utc))

    @staticmethod
    def matcher(story: Story) -> bool:
        return True

    def test_story(self) -> None:
        matching_story = f.story(
            text="a", created_at=datetime(2019, 1, 2, 12, 0, 0, tzinfo=timezone.utc)
        )
        for td, expected in [(timedelta(hours=24), False), (timedelta(hours=23), True)]:
            with self.subTest(timedelta=td, expected=expected):
                result = _for_at_least(self.task, [matching_story], self.matcher, td)
                self.assertEqual(expected, result)

    def test_no_story(self) -> None:
        for td, expected in [(timedelta(hours=48), False), (timedelta(hours=47), True)]:
            with self.subTest(timedelta=td, expected=expected):
                result = _for_at_least(self.task, [], self.matcher, td)
                self.assertEqual(expected, result)


class TestPredicate(Predicate):
    def __call__(self, task: Task, client: Client) -> bool:
        return True


class TestAnd(TestCase):
    def test_logic(self) -> None:
        task = f.task()
        client = create_autospec(Client)
        for one, two in product((True, False), (True, False)):
            first, second = (
                create_autospec(Predicate, return_value=one),
                create_autospec(Predicate, return_value=two),
            )
            predicate = _And(first, second)
            with self.subTest(one=one, two=two):
                self.assertEqual(one and two, predicate(task, client))
                first.assert_called_once_with(task, client)
                if one:
                    second.assert_called_once_with(task, client)

    def test_operator(self) -> None:
        first, second = TestPredicate(), TestPredicate()
        combination = first & second
        self.assertIsInstance(combination, _And)
        self.assertIs(combination.first, first)  # type: ignore
        self.assertIs(combination.second, second)  # type: ignore


class TestOr(TestCase):
    def test_logic(self) -> None:
        task = f.task()
        client = create_autospec(Client)
        for one, two in product((True, False), (True, False)):
            first, second = (
                create_autospec(Predicate, return_value=one),
                create_autospec(Predicate, return_value=two),
            )
            predicate = _Or(first, second)
            with self.subTest(one=one, two=two):
                self.assertEqual(one or two, predicate(task, client))
                first.assert_called_once_with(task, client)
                if not one:
                    second.assert_called_once_with(task, client)

    def test_operator(self) -> None:
        first, second = TestPredicate(), TestPredicate()
        combination = first | second
        self.assertIsInstance(combination, _Or)
        self.assertIs(combination.first, first)  # type: ignore
        self.assertIs(combination.second, second)  # type: ignore


class TestNot(TestCase):
    def test_logic(self) -> None:
        task = f.task()
        client = create_autospec(Client)
        for value in (True, False):
            inner = Mock(spec=Predicate, return_value=value)
            predicate = _Not(inner)
            with self.subTest(value=value):
                self.assertEqual(not value, predicate(task, client))
                inner.assert_called_once_with(task, client)

    def test_operator(self) -> None:
        inner = TestPredicate()
        inverse = ~inner
        self.assertIsInstance(inverse, _Not)
        self.assertIs(inverse.predicate, inner)  # type: ignore


class TestAlwaysTrue(TestCase):
    def test(self) -> None:
        client = create_autospec(Client)
        predicate = AlwaysTrue()
        self.assertTrue(predicate(f.task(), client))


class TestUnassigned(TestCase):
    client = create_autospec(Client)
    predicate = Unassigned()

    def test_unassigned(self) -> None:
        task = f.task(assignee=None)
        self.assertTrue(self.predicate(task, self.client))

    def test_assigned(self) -> None:
        task = f.task(assignee=f.user())
        self.assertFalse(self.predicate(task, self.client))


class TestAssigned(TestCase):
    client = create_autospec(Client)

    def test_assigned(self) -> None:
        task = f.task(assignee=f.user())
        assigned = Assigned()
        self.assertTrue(assigned(task, self.client))

    def test_assigned_to(self) -> None:
        task = f.task(assignee=f.user(name="name"))
        assigned = Assigned(to="name")
        self.assertTrue(assigned(task, self.client))

    def test_assigned_to_other(self) -> None:
        task = f.task(assignee=f.user(name="other"))
        assigned = Assigned(to="name")
        self.assertFalse(assigned(task, self.client))

    def test_unassigned(self) -> None:
        task = f.task(assignee=None)
        assigned = Assigned()
        self.assertFalse(assigned(task, self.client))


@freeze_time(datetime(2019, 1, 3, 6, 0, 0, tzinfo=timezone.utc))
class TestOverdue(DateBasedTestCase):
    def test_due_at(self) -> None:
        predicate = Overdue(timezone.utc)
        self._test_multiple_dates(
            predicate,
            lambda due_at: f.task(due_at=due_at),
            [
                (datetime.min.replace(tzinfo=timezone.utc), True),
                (datetime.max.replace(tzinfo=timezone.utc), False),
            ],
        )

    def test_due_on_utc(self) -> None:
        predicate = Overdue(timezone.utc)
        self._test_multiple_dates(
            predicate,
            lambda due_on: f.task(due_at=None, due_on=due_on),
            [
                (date.min, True),
                (date(2019, 1, 2), True),
                (date(2019, 1, 3), False),
                (date.max, False),
            ],
        )

    def test_due_on_pst(self) -> None:
        predicate = Overdue(PST)
        self._test_multiple_dates(
            predicate,
            lambda due_on: f.task(due_at=None, due_on=due_on),
            [
                (date.min, True),
                (date(2019, 1, 1), True),
                (date(2019, 1, 2), False),
                (date.max, False),
            ],
        )

    def test_none(self) -> None:
        predicate = Overdue(timezone.utc)
        client = create_autospec(Client)
        task = f.task(due_at=None, due_on=None)
        self.assertFalse(predicate(task, client))


class TestHasNoDueDate(TestCase):
    client = create_autospec(Client)
    predicate = HasNoDueDate()

    def test_due_at(self) -> None:
        task = f.task(due_at=datetime.min)
        self.assertFalse(self.predicate(task, self.client))

    def test_due_on(self) -> None:
        task = f.task(due_at=None, due_on=date.min)
        self.assertFalse(self.predicate(task, self.client))

    def test_none(self) -> None:
        task = f.task(due_at=None, due_on=None)
        self.assertTrue(self.predicate(task, self.client))


class TestIsComplete(TestCase):
    client = create_autospec(Client)
    predicate = IsComplete()

    def test_complete(self) -> None:
        task = f.task(completed=True)
        self.assertTrue(self.predicate(task, self.client))

    def test_incomplete(self) -> None:
        task = f.task(completed=False)
        self.assertFalse(self.predicate(task, self.client))


class TestIsIncomplete(TestCase):
    client = create_autospec(Client)
    predicate = IsIncomplete()

    def test_complete(self) -> None:
        task = f.task(completed=True)
        self.assertFalse(self.predicate(task, self.client))

    def test_incomplete(self) -> None:
        task = f.task(completed=False)
        self.assertTrue(self.predicate(task, self.client))


class TestHasShortDescription(TestCase):
    client = create_autospec(Client)

    def test_no_matcher(self) -> None:
        task = f.task(notes="abc")
        has_short_description = HasDescription()
        self.assertTrue(has_short_description(task, self.client))

    def test_matcher(self) -> None:
        matcher = Mock(return_value=True)
        task = f.task(notes="abc")
        has_short_description = HasDescription(matcher=matcher)
        self.assertTrue(has_short_description(task, self.client))
        matcher.assert_called_once_with("abc")


@freeze_time(datetime(2019, 1, 3, 6, 0, 0, tzinfo=timezone.utc))
class TestDueWithin(DateBasedTestCase):
    def test_within_due_on_utc_1d(self) -> None:
        predicate = DueWithin("1d", timezone.utc)
        self._test_multiple_dates(
            predicate,
            lambda due_on: f.task(due_at=None, due_on=due_on),
            [
                (date(2019, 1, 2), False),
                (date(2019, 1, 3), True),
                (date(2019, 1, 4), True),
                (date(2019, 1, 5), False),
            ],
        )

    def test_within_due_on_utc_16h(self) -> None:
        predicate = DueWithin("16h", timezone.utc)
        self._test_multiple_dates(
            predicate,
            lambda due_on: f.task(due_at=None, due_on=due_on),
            [
                (date(2019, 1, 2), False),
                (date(2019, 1, 3), True),
                (date(2019, 1, 4), False),
            ],
        )

    def test_within_due_on_pst_1d(self) -> None:
        predicate = DueWithin("1d", PST)
        self._test_multiple_dates(
            predicate,
            lambda due_on: f.task(due_at=None, due_on=due_on),
            [
                (date(2019, 1, 1), False),
                (date(2019, 1, 2), True),
                (date(2019, 1, 3), True),
                (date(2019, 1, 4), False),
            ],
        )

    def test_within_due_on_pst_16h(self) -> None:
        predicate = DueWithin("16h", PST)
        self._test_multiple_dates(
            predicate,
            lambda due_on: f.task(due_at=None, due_on=due_on),
            [
                (date(2019, 1, 1), False),
                (date(2019, 1, 2), True),
                (date(2019, 1, 3), True),
                (date(2019, 1, 4), False),
            ],
        )

    def test_within_due_at_1d(self) -> None:

        predicate = DueWithin("1d", timezone.utc)
        self._test_multiple_dates(
            predicate,
            lambda due_at: f.task(due_at=due_at.replace(tzinfo=timezone.utc)),
            [
                (datetime(2019, 1, 2, 0, 0, 0), False),
                (datetime(2019, 1, 3, 6, 0, 0), True),
                (datetime(2019, 1, 4, 6, 0, 0), True),
                (datetime(2019, 1, 4, 12, 0, 0), False),
            ],
        )

    def test_within_due_at_16h(self) -> None:
        predicate = DueWithin("16h", timezone.utc)
        self._test_multiple_dates(
            predicate,
            lambda due_at: f.task(due_at=due_at.replace(tzinfo=timezone.utc)),
            [
                (datetime(2019, 1, 2, 0, 0, 0), False),
                (datetime(2019, 1, 3, 6, 0, 0), True),
                (datetime(2019, 1, 3, 22, 0, 0), True),
                (datetime(2019, 1, 4, 0, 0, 0), False),
            ],
        )

    def test_no_due_date(self) -> None:
        client = create_autospec(Client)
        task = f.task(due_at=None, due_on=None)
        due_within = DueWithin("0h", timezone.utc)
        self.assertFalse(due_within(task, client))


class TestIsInProject(TestCase):
    client = create_autospec(Client)
    project = f.project(name="My project")
    task = f.task(memberships=[f.task_membership(project=project)])

    def test_in_project_no_duration(self) -> None:
        predicate = IsInProject("My project")
        self.assertTrue(predicate(self.task, self.client))

    def test_not_in_project(self) -> None:
        predicate = IsInProject("Other project")
        self.assertFalse(predicate(self.task, self.client))

    @patch("archie.predicates._for_at_least")
    def test_call(self, for_at_least_mock: Mock) -> None:
        predicate = IsInProject("My project", for_at_least="2d")
        for_at_least_mock.return_value = return_sentinel = object()
        self.client.stories_by_task.return_value = story_sentinel = object()

        result = predicate(self.task, self.client)

        self.assertIs(result, return_sentinel)
        for_at_least_mock.assert_called_once_with(
            self.task, story_sentinel, predicate._story_matcher, timedelta(days=2)
        )

    def test_story_matcher(self) -> None:
        matcher = IsInProject("My project")._story_matcher
        self.assertTrue(
            matcher(
                f.story(
                    resource_subtype="added_to_project",
                    project=f.project(name="My project"),
                )
            )
        )
        self.assertFalse(
            matcher(
                f.story(
                    resource_subtype="added_to_project",
                    project=f.project(name="Other project"),
                )
            )
        )
        self.assertFalse(matcher(f.story(resource_subtype="comment_added")))


class TestIsInProjectAndSection(TestCase):
    client = create_autospec(Client)
    project = f.project(name="My project")
    section = f.section(name="My section", project=project)
    task = f.task(memberships=[f.task_membership(project=project, section=section)])

    def test_in_project_and_section_no_duration(self) -> None:
        predicate = IsInProjectAndSection("My project", "My section")
        self.assertTrue(predicate(self.task, self.client))

    def test_not_in_section(self) -> None:
        predicate = IsInProjectAndSection("My project", "Other section")
        self.assertFalse(predicate(self.task, self.client))

    def test_not_in_project(self) -> None:
        predicate = IsInProjectAndSection("Other project", "My section")
        self.assertFalse(predicate(self.task, self.client))

    @patch("archie.predicates._for_at_least")
    def test_call(self, for_at_least_mock: Mock) -> None:
        predicate = IsInProjectAndSection("My project", "My section", for_at_least="2d")
        for_at_least_mock.return_value = return_sentinel = object()
        self.client.stories_by_task.return_value = story_sentinel = object()

        result = predicate(self.task, self.client)

        self.assertIs(result, return_sentinel)
        for_at_least_mock.assert_called_once_with(
            self.task, story_sentinel, predicate._story_matcher, timedelta(days=2)
        )

    def test_story_matcher(self) -> None:
        matcher = IsInProjectAndSection("My project", "My section")._story_matcher

        self.assertTrue(
            matcher(f.story(resource_subtype="added_to_project", project=self.project))
        )
        self.assertTrue(
            matcher(
                f.story(resource_subtype="section_changed", new_section=self.section)
            )
        )
        self.assertFalse(
            matcher(
                f.story(
                    resource_subtype="added_to_project",
                    project=f.project(name="Other project"),
                )
            )
        )
        self.assertFalse(
            matcher(
                f.story(
                    resource_subtype="section_changed",
                    new_section=f.section(name="Other section", project=self.project),
                )
            )
        )
        self.assertFalse(
            matcher(
                f.story(
                    resource_subtype="section_changed",
                    new_section=f.section(
                        name="My section", project=f.project(name="Other project")
                    ),
                )
            )
        )
        self.assertFalse(matcher(f.story(resource_subtype="unknown")))


class TestHasEnumValue(TestCase):
    client = create_autospec(Client)
    enum_option = f.enum_option(name="My enum option")
    custom_field = f.custom_field(
        name="My custom field", resource_subtype="enum", enum_value=enum_option
    )
    task = f.task(custom_fields=[custom_field])

    def test_has_any_value_no_duration(self) -> None:
        predicate = HasEnumValue("My custom field")
        self.assertTrue(predicate(self.task, self.client))

    def test_has_specific_value_no_duration(self) -> None:
        predicate = HasEnumValue("My custom field", "My enum option")
        self.assertTrue(predicate(self.task, self.client))

    def test_wrong_custom_field(self) -> None:
        predicate = HasEnumValue("Other custom field")
        self.assertFalse(predicate(self.task, self.client))

    def test_missing_custom_field(self) -> None:
        task = f.task(custom_fields=[])
        predicate = HasEnumValue("My custom field")
        self.assertFalse(predicate(task, self.client))

    def test_wrong_enum_value(self) -> None:
        predicate = HasEnumValue("My custom field", "Other enum option")
        self.assertFalse(predicate(self.task, self.client))

    def test_unset_enum_value(self) -> None:
        task = f.task(
            custom_fields=[
                f.custom_field(
                    name="My custom field", resource_subtype="enum", enum_value=None
                )
            ]
        )
        predicate = HasEnumValue("My custom field", "My enum option")
        self.assertFalse(predicate(task, self.client))

    @patch("archie.predicates._for_at_least")
    def test_call(self, for_at_least_mock: Mock) -> None:
        predicate = HasEnumValue("My custom field", for_at_least="2d")
        for_at_least_mock.return_value = return_sentinel = object()
        self.client.stories_by_task.return_value = story_sentinel = object()

        result = predicate(self.task, self.client)

        self.assertIs(result, return_sentinel)
        self.client.stories_by_task.assert_called_once_with(self.task)
        for_at_least_mock.assert_called_once_with(
            self.task, story_sentinel, predicate._story_matcher, timedelta(days=2)
        )

    def test_story_matcher(self) -> None:
        matcher = HasEnumValue("My custom field")._story_matcher

        self.assertTrue(
            matcher(
                f.story(
                    resource_subtype="enum_custom_field_changed",
                    custom_field=self.custom_field,
                )
            )
        )
        self.assertFalse(
            matcher(
                f.story(
                    resource_subtype="enum_custom_field_changed",
                    custom_field=f.custom_field(name="Other custom field"),
                )
            )
        )
        self.assertFalse(matcher(f.story(resource_subtype="unknown")))


class TestHasUnsetEnum(TestCase):
    predicate = HasUnsetEnum("My custom field")
    client = create_autospec(Client)
    custom_field = f.custom_field(
        name="My custom field", resource_subtype="enum", enum_value=None
    )
    task = f.task(custom_fields=[custom_field])

    def test_has_no_value(self) -> None:
        self.assertTrue(self.predicate(self.task, self.client))

    def test_has_any_value(self) -> None:
        task = f.task(
            custom_fields=[
                f.custom_field(
                    name="My custom field",
                    resource_subtype="enum",
                    enum_value=f.enum_option(name="My enum option"),
                )
            ]
        )
        self.assertFalse(self.predicate(task, self.client))

    def test_wrong_custom_field(self) -> None:
        predicate = HasUnsetEnum("Other custom field")
        self.assertFalse(predicate(self.task, self.client))

    def test_missing_custom_field(self) -> None:
        task = f.task(custom_fields=[])
        self.assertFalse(self.predicate(task, self.client))

    @patch("archie.predicates._for_at_least")
    def test_call(self, for_at_least_mock: Mock) -> None:
        predicate = HasUnsetEnum("My custom field", for_at_least="2d")
        for_at_least_mock.return_value = return_sentinel = object()
        self.client.stories_by_task.return_value = story_sentinel = object()

        result = predicate(self.task, self.client)

        self.assertIs(result, return_sentinel)
        self.client.stories_by_task.assert_called_once_with(self.task)
        for_at_least_mock.assert_called_once_with(
            self.task, story_sentinel, predicate._story_matcher, timedelta(days=2)
        )

    def test_story_matcher(self) -> None:
        matcher = HasUnsetEnum("My custom field")._story_matcher

        self.assertTrue(
            matcher(
                f.story(
                    resource_subtype="enum_custom_field_changed",
                    custom_field=self.custom_field,
                )
            )
        )
        self.assertFalse(
            matcher(
                f.story(
                    resource_subtype="enum_custom_field_changed",
                    custom_field=f.custom_field(name="Other custom field"),
                )
            )
        )
        self.assertFalse(matcher(f.story(resource_subtype="unknown")))


@freeze_time(datetime(2019, 1, 3, 12, 0, 0, tzinfo=timezone.utc))
class TestUntriaged(TestCase):
    task = f.task()
    user = f.user()
    triage_story = f.story(created_by=user)
    predicate = Untriaged(for_at_least="2d")

    def setUp(self) -> None:
        self.client = create_autospec(Client)

    def test_no_story(self) -> None:
        self.client.me.return_value = self.user
        self.client.stories_by_task.return_value = []

        self.assertTrue(self.predicate(self.task, self.client))

        self.client.me.assert_called_once_with()
        self.client.stories_by_task.assert_called_once_with(self.task)

    def test_recent_story(self) -> None:
        self.client.me.return_value = self.user
        self.client.stories_by_task.return_value = [
            f.story(
                created_by=self.user,
                created_at=datetime(2019, 1, 2, 12, 0, 0, tzinfo=timezone.utc),
            )
        ]

        self.assertFalse(self.predicate(self.task, self.client))

        self.client.me.assert_called_once_with()
        self.client.stories_by_task.assert_called_once_with(self.task)

    def test_old_story(self) -> None:
        self.client.me.return_value = self.user
        self.client.stories_by_task.return_value = [
            f.story(
                created_by=self.user,
                created_at=datetime(2019, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            )
        ]

        self.assertTrue(self.predicate(self.task, self.client))

        self.client.me.assert_called_once_with()
        self.client.stories_by_task.assert_called_once_with(self.task)

    def test_any_story(self) -> None:
        predicate = Untriaged()
        self.client.me.return_value = f.user()
        self.client.stories_by_task.return_value = [f.story(created_by=self.user)]

        self.assertFalse(predicate(self.task, self.client))

        self.client.me.assert_called_once_with()
        self.client.stories_by_task.assert_called_once_with(self.task)

    def test_story_matcher(self) -> None:
        user = f.user(gid="1")
        matcher = partial(self.predicate._story_matcher, user)
        self.assertTrue(matcher(f.story(created_by=user)))
        self.assertFalse(matcher(f.story(created_by=f.user(gid="2"))))
        self.assertFalse(matcher(f.story(created_by=None)))


class TestHasComment(TestCase):
    task = f.task()
    story = f.story(resource_subtype="comment_added", text="Comment text")

    def setUp(self) -> None:
        self.client = create_autospec(Client)

    def test_has_comment(self) -> None:
        self.client.stories_by_task.return_value = [self.story]
        predicate = HasComment()
        self.assertTrue(predicate(self.task, self.client))
        self.client.stories_by_task.assert_called_once_with(self.task)

    def test_has_matching_comment(self) -> None:
        self.client.stories_by_task.return_value = [self.story]
        matcher = Mock(return_value=True)
        predicate = HasComment(matcher)
        self.assertTrue(predicate(self.task, self.client))
        matcher.assert_called_once_with(self.story.text)
        self.client.stories_by_task.assert_called_once_with(self.task)

    def test_has_no_matching_comment(self) -> None:
        self.client.stories_by_task.return_value = [self.story]
        matcher = Mock(return_value=False)
        predicate = HasComment(matcher)
        self.assertFalse(predicate(self.task, self.client))
        matcher.assert_called_once_with(self.story.text)
        self.client.stories_by_task.assert_called_once_with(self.task)

    def test_has_matching_literal(self) -> None:
        self.client.stories_by_task.return_value = [self.story]
        predicate = HasComment("ment te")
        self.assertTrue(predicate(self.task, self.client))
        self.client.stories_by_task.assert_called_once_with(self.task)

    def test_has_no_matching_literal(self) -> None:
        self.client.stories_by_task.return_value = [self.story]
        predicate = HasComment("unmatched")
        self.assertFalse(predicate(self.task, self.client))
        self.client.stories_by_task.assert_called_once_with(self.task)

    def test_no_comment(self) -> None:
        self.client.stories_by_task.return_value = []
        predicate = HasComment()
        self.assertFalse(predicate(self.task, self.client))
        self.client.stories_by_task.assert_called_once_with(self.task)


class TestHasExternal(TestCase):
    client = create_autospec(Client)

    def test_has_external(self) -> None:
        predicate = HasExternal()
        task = f.task(external=f.external())
        self.assertTrue(predicate(task, self.client))

    def test_no_external(self) -> None:
        predicate = HasExternal()
        task = f.task(external=None)
        self.assertFalse(predicate(task, self.client))

    def test_matching_external(self) -> None:
        matcher = Mock(return_value=True)
        external = f.external()
        predicate = HasExternal(matcher)
        task = f.task(external=external)
        self.assertTrue(predicate(task, self.client))
        matcher.assert_called_once_with(external)

    def test_no_matching_external(self) -> None:
        matcher = Mock(return_value=False)
        external = f.external()
        predicate = HasExternal(matcher)
        task = f.task(external=external)
        self.assertFalse(predicate(task, self.client))
        matcher.assert_called_once_with(external)
