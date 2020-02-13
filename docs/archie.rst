.. _archie:

:tocdepth: 1

Archie
======

Triager
-------

.. currentmodule:: archie.triager

.. autosummary::
   :nosignatures:

   Triager

Models
------

.. currentmodule:: archie.asana.models

.. autosummary::
   :nosignatures:

   CustomField
   EnumOption
   Event
   EventAction
   External
   Project
   ResourceType
   Section
   Story
   Task
   TaskMembership
   User
   Workspace

Sources
-------

.. currentmodule:: archie.sources

.. autosummary::
   :nosignatures:

   PollingSource
   ModifiedSinceSource

Predicates
----------

.. currentmodule:: archie.predicates

.. autosummary::
   :nosignatures:

   AlwaysTrue
   Assigned
   DueToday
   DueWithin
   HasComment
   HasEnumValue
   HasExternal
   HasNoDueDate
   HasDescription
   HasUnsetEnum
   IsComplete
   IsIncomplete
   IsInProject
   IsInProjectAndSection
   Overdue
   Unassigned
   Untriaged

Actions
-------

.. currentmodule:: archie.actions

.. autosummary::
   :nosignatures:

   AddComment
   AddFollower
   AssignTo
   SetEnumCustomField
   SetExternal

Sorters
-------

.. currentmodule:: archie.sorters

.. autosummary::
   :nosignatures:

   AssigneeSorter
   DueDateSorter
   EnumCustomFieldSorter
   LikeSorter
   NumberCustomFieldSorter
   StartDateSorter

Workflows
---------

.. currentmodule:: archie.workflows

.. autosummary::
   :nosignatures:

   EnumCustomFieldWorkflow
   ExternalDataWorkflow
   SectionWorkflow
