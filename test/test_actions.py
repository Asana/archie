import logging
from test import fixtures as f
from unittest import TestCase
from unittest.mock import create_autospec

from archie.actions import (
    AddComment,
    AddFollower,
    AssignTo,
    SetEnumCustomField,
    SetExternal,
    _logger,
)
from archie.asana.client import Client

task = f.task()


class TestAddComment(TestCase):
    def test(self) -> None:
        client = create_autospec(Client)
        action = AddComment("Some comment")
        action(task, client)
        client.add_comment.assert_called_once_with(task, "Some comment")


class TestAddFollower(TestCase):
    def test(self) -> None:
        client = create_autospec(Client)
        action = AddFollower("user@domain.com")
        action(task, client)
        client.add_follower.assert_called_once_with(task, "user@domain.com")


class TestSetExternal(TestCase):
    def test(self) -> None:
        external = f.external()
        client = create_autospec(Client)
        action = SetExternal(external)
        action(task, client)
        client.set_external.assert_called_once_with(task, external)


class TestAssignTo(TestCase):
    def setUp(self) -> None:
        self.client = create_autospec(Client)

    def test_set_assignee(self) -> None:
        action = AssignTo("user@domain.com")
        action(task, self.client)
        self.client.set_assignee.assert_called_once_with(task, "user@domain.com")

    def test_clear_assignee(self) -> None:
        action = AssignTo(None)
        action(task, self.client)
        self.client.set_assignee.assert_called_once_with(task, None)


class TestSetEnumCustomField(TestCase):
    enum_option = f.enum_option(name="My enum option")
    custom_field = f.custom_field(name="My custom field", enum_options=[enum_option])
    task = f.task(custom_fields=[custom_field])
    task_with_field_set = f.task(
        custom_fields=[
            f.custom_field(
                name="My custom field",
                enum_options=[enum_option],
                enum_value=enum_option,
            )
        ]
    )

    def setUp(self) -> None:
        self.client = create_autospec(Client)

    def test_success(self) -> None:
        action = SetEnumCustomField("My custom field", "My enum option")
        action(self.task, self.client)
        self.client.set_enum_custom_field.assert_called_once_with(
            self.task, self.custom_field, self.enum_option
        )

    def test_already_set(self) -> None:
        action = SetEnumCustomField("My custom field", "My enum option")
        action(self.task_with_field_set, self.client)
        self.client.set_enum_custom_field.assert_not_called()

    def test_missing_enum_option(self) -> None:
        action = SetEnumCustomField("My custom field", "Other enum option")

        with self.assertLogs(_logger, logging.WARNING) as logs:
            action(self.task_with_field_set, self.client)
        self.assertListEqual(
            logs.output,
            [
                "WARNING:archie.actions:CustomField(custom-field-gid) "
                "has no enum option 'Other enum option'"
            ],
        )
        self.client.set_enum_custom_field.assert_not_called()

    def test_missing_custom_field(self) -> None:
        action = SetEnumCustomField("Other custom field", "My enum option")
        with self.assertLogs(_logger, logging.WARNING) as logs:
            action(self.task, self.client)
        self.assertListEqual(
            logs.output,
            [
                "WARNING:archie.actions:Task(task-gid) "
                "has no custom field 'Other custom field'"
            ],
        )
        self.client.set_enum_custom_field.assert_not_called()
