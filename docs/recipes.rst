.. _recipes:

Recipes
=======

Here are some recipes to get you started. Contributions are welcome.

Running your rules periodically
-------------------------------

.. code-block:: python

   # Create the source and triager
   from archie import Triager
   from archie.sources import PollingSource

   task_source = PollingSource("<project-gid>", repeat_after="5m")
   archie = Triager(access_token="<access-token>", task_source=task_source)

   # Add rules
   from datetime import timezone, timedelta

   from archie.actions import AddComment
   from archie.predicates import Overdue

   PST = timezone(offset=timedelta(hours=-8), name="PST")

   @archie.when(Overdue(timezone=PST))
   def comment_on_overdue(task):
       return [AddComment("This task is overdue!")]

   # Set up other rules...

   if __name__ == "__main__":
       archie.triage()

Applying the same rules to multiple projects
--------------------------------------------

.. code-block:: python

   # Create the source and triager
   from archie import Triager
   from archie.sources import PollingSource

   archie = Triager(
       access_token="<access-token>",
       task_source=PollingSource("<project-gid>")
   )
   snacks = Triager(
       access_token="<access-token>",
       task_source=PollingSource("<other-project-gid>")
   )
   all_dogs = [archie, snacks]

   # Define rules
   from datetime import timezone, timedelta

   from archie.predicates import Overdue
   from archie.actions import AddComment

   PST = timezone(offset=timedelta(hours=-8), name="PST")

   def comment_on_overdue(task):
       return [AddComment("This task is overdue!")]

   def add_rules(dog):
       dog.when(Overdue(timezone=PST))(comment_on_overdue)
       # Add other common rules...

   # Add all rules to all triagers
   for dog in all_dogs:
       add_rules(dog)

   if __name__ == "__main__":
       for dog in all_dogs:
           dog.sort()
           dog.triage()
