.. _introduction:

Introduction
============

Archie is your faithful companion in `Asana`_. Teams of people develop different
processes for different needs or different projects, but maintaining these processes can
create "work about work" which is contrary to Asana's mission. Archie is a framework
that allows you to easily define the rules that drive your workflow, allowing your team
to spend time on the work itself while it triages tasks and takes care of the process.

Archie is canonically a golden retriever (or golden "re-triage-r" if you will), but we
encourage you to give your automations new names and dog breeds that delight you
personally.

.. note::

   Archie is still in beta and under active development as we learn about new use cases
   and needs. The APIs and functionality are subject to change prior to a stable
   release. This package uses `semantic versioning`_ to express compatibility.

Motivation
----------

Workflow automation is not a new problem, but there are currently no software frameworks
that make solutions to this problem easy and simple for Asana. Even internally at Asana,
we haven't had any framework that generically solves this problem for all our various
teams. Archie, though built to operate on `Asana's API`_, abstracts away those details
and lets you think in terms of the steps and rules that define your process.

The goal of this project is to provide an easy way for developers to build custom
workflows and other solutions out of composable parts that provide all or most of the
desired behavior, while also being extensible for those that need a little bit more. By
making automation through the API more easily accessible to customer developers, we hope
that users of Asana will more readily realize the value in Asana and its API.

In October of 2019, Asana launched `Automation`_, a feature in the web app that allows
construction of basic "trigger-action" style rules that apply to Asana tasks. While this
covers a large number of use cases, it is limited in customization—it cannot integrate
with external systems, have extra conditional logic, access the full range of Asana's
data model, or drive a multi-stage sequential workflow. We encourage non-developers to
investigate this feature or other non-developer `alternatives`_ before attempting to
build a solution with Archie.

Use Cases
---------

Here are some example situations in which you might find Archie useful.

* **You want to maintain a backlog prioritized by multiple criteria.** If you rank work
  items both by priority and cost, you might want to sort your backlog so that the top
  of the list are the high-priority, low-cost tasks. The Asana web app will let you sort
  by at most one custom field, but Archie can have multi-level sorts that provide the
  clear structure that you want.
* **You want to integrate a workflow with an external tool.** If you want to update
  tasks based on data in another system, such as completing tasks when a corresponding
  ticket in another system is closed, or to change custom fields based on a ticket's
  status, you can create custom predicates and actions that use your own code to read
  and write external data.
* **You want to maintain a sequential workflow for tasks.** If a task must progress
  through a sequence of stages and not skip any, you can define the conditions for
  advancing from each stage to the next and Archie will push tasks through while making
  sure that no stages are skipped.

If you think Archie might be right for you and your team, see the :ref:`getting-started`
pages.

Design Principles
-----------------

* **Readability over robustness.** Processes and workflows will change and evolve over
  time, and it's important that configurations can be updated easily. As a concrete
  example, suppose you are sorting by a enum custom field with three values in it. If we
  define that as ``EnumCustomFieldSorter("5463185", ["5463186", "5463187", "5463188"])``
  but then later add a new option to the custom field, not only is it difficult to find
  which sorter corresponds to what custom field, it's not clear how the configuration
  should change. However, if the sorter is defined as ``EnumCustomFieldSorter("Priority", ["High", "Medium", "Low"])``
  then it becomes extremely obvious what this configuration does and how you should
  update it with the new option, e.g., ``EnumCustomFieldSorter("Priority", ["P0", "P1", "P2", "P3"])``.
  Rules and configurations will break no matter what, and so this framework favors ease
  of repair for when things do break.
* **Warnings over crashing.** In the case of broken configuration or unexpected data,
  the framework will try to apply as many rules as possible to as many tasks as possible
  to keep processes moving and unblocked for users. For example, if an action says to
  set a custom field named "Priority" to "High", but there is either no field named
  "Priority" or no enum option named "High", then the framework will log a warning and
  continue operating. Looking at warnings in the logs should give a complete picture of
  what configuration is incorrect.

Requirements
------------

* Archie currently requires Python 3.7, and will soon be made to require Python 3.8.
  Due to changes in Python's annotations, it does not support 3.8 in its current state.
* You will need to have an Asana account for Archie to interact with. You can `sign up`_
  for a free Asana account to get started.
* Once you have an Asana account, you will need a `personal access token`_ to allow
  Archie to access and modify your data in Asana.

.. _alternatives:

Non-developer alternatives
--------------------------

If you aren't a developer or don't have access to a developer to help you set up your
own Archie, there are a number of alternative solutions for building workflows. In
particular, the following solutions are reputable options:

* Asana's own `Automation`_ feature, which allows users to build rules within the Asana
  UI, but cannot yet integrate directly with other products.
* `Zapier`_ is a multi-purpose connector that can build workflows across multiple
  different products.
* `IFTTT`_ is an easy-to-use "trigger-action" model for setting up simple steps.
* `Tray.io`_ is a powerful tool that allows extremely intricate and highly customizable
  automations and workflows, again offering cross-product connections.
* `Flowsana`_ is a new, Asana-specific automation app built by one of Asana's trusted,
  champion developers.

.. _Asana: https://asana.com/
.. _semantic versioning: https://semver.org/
.. _Asana's API: https://developers.asana.com/docs/
.. _Automation: https://blog.asana.com/2019/10/automation-launch/
.. _sign up: https://asana.com/create-account
.. _personal access token: https://developers.asana.com/docs/#authentication-basics#personal-access-token
.. _Zapier: https://zapier.com/apps/asana/integrations
.. _IFTTT: https://ifttt.com/asana
.. _Tray.io: https://tray.io/connectors/asana-integrations
.. _Flowsana: https://flowsana.net/
