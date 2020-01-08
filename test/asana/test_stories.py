from test import fixtures as f
from unittest import TestCase
from unittest.mock import create_autospec

from archie.asana._stories import comments_by_task, subtype_filter
from archie.asana.client import Client


class TestFilters(TestCase):
    def test_subtype_filter(self) -> None:
        filt = subtype_filter("subtype_a")

        stories = [
            f.story(gid="1", resource_subtype="subtype_a"),
            f.story(gid="2", resource_subtype="subtype_b"),
            f.story(gid="3", resource_subtype="subtype_c"),
            f.story(gid="4", resource_subtype="subtype_a"),
        ]

        filtered = list(filter(filt, stories))
        self.assertListEqual(filtered, [stories[0], stories[3]])


class TestCommentsByTask(TestCase):
    def test(self) -> None:
        task = f.task()
        stories = [
            f.story(resource_subtype="comment_added"),
            f.story(resource_subtype="section_changed"),
            f.story(resource_subtype="enum_custom_field_changed"),
        ]
        client = create_autospec(Client)
        client.stories_by_task.return_value = stories
        comments = comments_by_task(task, client)
        self.assertListEqual(comments, [stories[0]])
        client.stories_by_task.assert_called_once_with(task)
