.. _getting-started:

Getting Started
===============

Installation
------------

Archie is published on `PyPI`_ under the name ``asana-archie``, and can be installed
with Pip or your favorite package manager: ``python -m pip install asana-archie``.

Configuration
-------------

First, create a ``Triager`` that will run your rules. You'll need the GID of the Asana
project you're working with, as well as a `personal access token`_ for the Asana API.

.. code-block:: python

   from archie import Triager
   from archie.sources import PollingSource

   project = PollingSource("<project-gid>")
   archie = Triager(access_token="<access-token>", task_source=project)

Triaging
--------

With that, you can begin defining triage rules that will be applied to incomplete tasks
in the project:

.. code-block:: python

   from datetime import timezone, timedelta

   from archie.predicates import DueWithin, Overdue, Unassigned
   from archie.actions import AddComment, AddFollower, AssignTo

   PST = timezone(offset=timedelta(hours=-8), name="PST")

   @archie.when(Overdue(timezone=PST))
   def comment_on_overdue(task):
       return [AddComment("This task is overdue!"), AddFollower("user1@domain.com")]

   @archie.when(Unassigned() & DueWithin("2d", timezone=PST))
   def comment_on_due_soon(task):
       return [AddComment("This is due soon and needs an owner."), AssignTo("user2@domain.com")]

   archie.triage()

Sorting
-------

Archie will also sort the tasks in your project on multiple levels. Each section in your
project can have different sorts defined.

.. code-block:: python

   from archie.sorters import DueDateSorter, EnumCustomFieldSorter, LikeSorter

   priority = EnumCustomFieldSorter("Priority", ["High", "Medium", "Low"])
   due_date = DueDateSorter()

   archie.order("Backlog", by=priority.and_then(due_date))
   archie.order("Feature Requests", by=LikeSorter())
   archie.sort()

Workflows
---------

For more complex processes, you can define a multi-stage workflow and have the triager
push tasks through it. Stages are defined by their name, entry criteria, and actions. A
task will automatically be moved between sections or have its custom fields changed to
reflect its stage in the workflow.

.. code-block:: python

   from archie.actions import AddComment, AssignTo
   from archie.predicates import AlwaysTrue, Assigned, HasComment, IsComplete
   from archie.workflows import SectionWorkflow, WorkflowStage

   stages = [
       WorkflowStage(
         name="Inbox",
         to_enter=AlwaysTrue(),
         on_enter=[],
       ),
       WorkflowStage(
         name="In Progress",
         to_enter=Assigned(),
         on_enter=[],
       ),
       WorkflowStage(
         name="In Review",
         to_enter=HasComment("github.com/org/repo/pull/"),
         on_enter=[AssignTo("someone@domain.com")],
       ),
       WorkflowStage(
         name="Done",
         to_enter=IsComplete(),
         on_enter=[AddComment("Good work! 🎉")],
       ),
   ]

   workflow = SectionWorkflow("My process", stages)
   triager.apply(workflow)

Running
-------

Once your rules are defined, simply run your file as any other script with ``python``.

Caveats
-------

* This framework will only operate correctly on projects that can be viewed as a
  board—it will not work correctly on old-style list projects.
* Some components of this framework rely on inspecting tasks' stories. Deleting stories
  on tasks may result in incorrect behavior of the predicates.
* You may run into issues in projects that have a large number of incomplete tasks. In
  mild cases, there will be performance issues where it will take a significant amount
  of time to sort sections and triage tasks. In extreme cases, components may time out
  and raise exceptions.


.. _PyPI: https://pypi.org/project/asana-archie
.. _personal access token: https://developers.asana.com/docs/#authentication-basics#personal-access-token
