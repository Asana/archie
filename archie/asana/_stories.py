from typing import Callable, List

from archie.asana.client import Client
from archie.asana.models import Story, Task


def subtype_filter(resource_subtype: str) -> Callable[[Story], bool]:
    def story_filter(story: Story) -> bool:
        return story.resource_subtype == resource_subtype

    return story_filter


def comments_by_task(task: Task, client: Client) -> List[Story]:
    comment_filter = subtype_filter("comment_added")
    return list(filter(comment_filter, client.stories_by_task(task)))
