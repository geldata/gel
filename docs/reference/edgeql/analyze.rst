.. _ref_eql_analyze:

Analyze
=======

:eql-statement:

``analyze`` -- trigger performance analysis of the appended query

Overview
--------

.. index:: explain, performance, postgres query planner
.. api-index:: analyze

Prefix an EdgeQL query with ``analyze`` to run a performance analysis of that query.

.. code-block:: edgeql-repl

  db> analyze select Hero {
  ...   name,
  ...   secret_identity,
  ...   villains: {
  ...     name,
  ...     nemesis: {
  ...       name
  ...     }
  ...   }
  ... };
  ────────────────────────────────── Query ──────────────────────────────────
  analyze select ➊  Hero {name, secret_identity, ➋  villains:
  {name, ➌  nemesis: {name}}};

  ──────────────────────── Coarse-grained Query Plan ────────────────────────
                    │ Time     Cost Loops Rows Width │ Relations
  ➊ root            │  0.0 69709.48   1.0  0.0    32 │ Hero
  ╰──➋ .villains    │  0.0     92.9   0.0  0.0    32 │ Villain, Hero.villains
  ╰──➌ .nemesis     │  0.0     8.18   0.0  0.0    32 │ Hero


.. note::

    In addition to using the ``analyze`` statement in the CLI or UI's REPL, you may also run performance analysis via our CLI's :gelcmd:`analyze` command and the UI's query builder (accessible by running :ref:`ref_cli_gel_ui` to invoke your instance's UI) by prepending your query with ``analyze``. This method offers helpful visualizations to to make it easy to understand your query's performance.

After analyzing a query, you may run the ``\expand`` command in the REPL to see
more fine-grained performance metrics on the previously analyzed query.


.. _ref_eql_statements_analyze:

EdgeQL Syntax
-------------

.. eql:synopsis::

    analyze <query>;

    # where <query> is any EdgeQL query

``analyze`` returns a table with performance metrics broken down by node.

You may prepend the ``analyze`` keyword in either of our REPLs (CLI or :ref:`UI
<ref_cli_gel_ui>`) or you may prepend in the UI's query builder for a
helpful visualization of your query's performance.

After any ``analyze`` in a REPL, run the ``\expand`` command to see
fine-grained performance analysis of the previously analyzed query.
