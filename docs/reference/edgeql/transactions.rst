..
    Portions Copyright (c) 2019 MagicStack Inc. and the Gel authors.

    Portions Copyright (c) 1996-2018, PostgreSQL Global Development Group
    Portions Copyright (c) 1994, The Regents of the University of California

    Permission to use, copy, modify, and distribute this software and its
    documentation for any purpose, without fee, and without a written agreement
    is hereby granted, provided that the above copyright notice and this
    paragraph and the following two paragraphs appear in all copies.

    IN NO EVENT SHALL THE UNIVERSITY OF CALIFORNIA BE LIABLE TO ANY PARTY FOR
    DIRECT, INDIRECT, SPECIAL, INCIDENTAL, OR CONSEQUENTIAL DAMAGES, INCLUDING
    LOST PROFITS, ARISING OUT OF THE USE OF THIS SOFTWARE AND ITS
    DOCUMENTATION, EVEN IF THE UNIVERSITY OF CALIFORNIA HAS BEEN ADVISED OF THE
    POSSIBILITY OF SUCH DAMAGE.

    THE UNIVERSITY OF CALIFORNIA SPECIFICALLY DISCLAIMS ANY WARRANTIES,
    INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY
    AND FITNESS FOR A PARTICULAR PURPOSE.  THE SOFTWARE PROVIDED HEREUNDER IS
    ON AN "AS IS" BASIS, AND THE UNIVERSITY OF CALIFORNIA HAS NO OBLIGATIONS TO
    PROVIDE MAINTENANCE, SUPPORT, UPDATES, ENHANCEMENTS, OR MODIFICATIONS.


.. _ref_eql_transactions:

Transactions
============

.. api-index:: start transaction, declare savepoint, release savepoint,
               rollback to savepoint, rollback, commit

Overview
--------

EdgeQL supports atomic transactions. The transaction API consists
of several commands:

:eql:stmt:`start transaction`
  Start a transaction, specifying the isolation level, access mode (``read
  only`` vs ``read write``), and deferrability.

:eql:stmt:`declare savepoint`
  Establish a new savepoint within the current transaction. A savepoint is a
  intermediate point in a transaction flow that provides the ability to
  partially rollback a transaction.

:eql:stmt:`release savepoint`
  Destroys a savepoint previously defined in the current transaction.

:eql:stmt:`rollback to savepoint`
  Rollback to the named savepoint. All changes made after the savepoint
  are discarded. The savepoint remains valid and can be rolled back
  to again later, if needed.

:eql:stmt:`rollback`
  Rollback the entire transaction. All updates made within the transaction are
  discarded.

:eql:stmt:`commit`
  Commit the transaction. All changes made by the transaction become visible
  to others and will persist if a crash occurs.


Client libraries
----------------

There is rarely a reason to use EdgeQL commands directly. All Gel client
libraries provide dedicated transaction APIs that handle transaction creation
under the hood.


Let's use the following example schema to demonstrate the transaction API:

.. code-block:: sdl

  module default {
    type BankCustomer {
      required name: str;
      required balance: int64;
    }
  }

Examples below show a transaction that sends 10 cents from the account
of a ``BankCustomer`` called ``'Customer1'`` to ``BankCustomer`` called
``'Customer2'``:

.. code-tabs::

  .. code-tab:: edgeql

    start transaction;

    update BankCustomer
      filter .name = 'Customer1'
      set { bank_balance := .bank_balance -10 };

    update BankCustomer
      filter .name = 'Customer2'
      set { bank_balance := .bank_balance +10 };

    commit;

  .. code-tab:: python

    # Python client needs to automatically repeat
    # transaction in case of a database serialization
    # error, hence the unusual API:

    async for tx in client.transaction():
        async with tx:

            await tx.execute("""
                update BankCustomer
                filter .name = 'Customer1'
                set {
                    bank_balance := .bank_balance -10
                };
            """)

            await tx.execute("""
                update BankCustomer
                filter .name = 'Customer2'
                set {
                    bank_balance := .bank_balance +10
                };""")

  .. code-tab:: typescript
    :title: TS

    const query1 = e.update(e.BankCustomer, () => ({
      filter_single: { name: "Customer1" },
      set: {
        bank_balance: { "-=":  10 }
      },
    }));
    const query2 = e.update(e.BankCustomer, () => ({
      filter_single: { name: "Customer2" },
      set: {
        bank_balance: { "+=":  10 }
      },
    }));

    client.transaction(async (tx) => {
      await query1.run(tx);
      await query2.run(tx);
    });

    //
    // OR using raw queries:
    //

    client.transaction(async tx => {
      await tx.execute(`update BankCustomer
        filter .name = 'Customer1'
        set { bank_balance := .bank_balance -10 }`);
      await tx.execute(`update BankCustomer
        filter .name = 'Customer2'
        set { bank_balance := .bank_balance +10 }`);
    });


  .. code-tab:: go

    err = client.Tx(ctx, func(ctx context.Context, tx *gel.Tx) error {
      query1 := `update BankCustomer
        filter .name = 'Customer1'
        set { bank_balance := .bank_balance -10 };`
      if e := tx.Execute(ctx, query1); e != nil {
        return e
      }
      query2 := `update BankCustomer
        filter .name = 'Customer2'
        set { bank_balance := .bank_balance +10 };`
      if e := tx.Execute(ctx, query2); e != nil {
        return e
      }
      return nil
    })
    if err != nil {
      log.Fatal(err)
    }

  .. code-tab:: rust

    let balance_change_query = "update BankCustomer
      filter .name = <str>$0
      set { bank_balance := .bank_balance + <int32>$1 }";

    client
        .transaction(|mut conn| async move {
            conn.execute(balance_change_query, &("Customer1", -10))
                .await
                .expect("Execute should have worked");
            conn.execute(balance_change_query, &("Customer2", 10))
                .await
                .expect("Execute should have worked");
            Ok(())
        })
        .await
        .expect("Transaction should have worked");

Note that with Gel you rarely need to use transactions, as EdgeQL allows
you to easily group multiple operations in one query or batch multiple queries
together in a single "implicit" transaction, e.g. for Python:

.. code-block:: python

    client.execute("""
        update BankCustomer
        filter .name = 'Customer1'
        set {
            bank_balance :=
                .bank_balance -<int64>$balance
        };

        update BankCustomer
        filter .name = 'Customer2'
        set {
            bank_balance :=
                .bank_balance +<int64>$balance
        };
    """, balance=10)

Dedicated transaction API documentation:

* :ref:`TypeScript/JS <gel-js-intro>`
* :ref:`Python <gel-python-intro>`
* `Go <https://pkg.go.dev/github.com/geldata/gel-go>`_.
* `Rust <https://docs.rs/gel-tokio/latest/gel_tokio/>`_.


EdgeQL Syntax
-------------


.. _ref_eql_statements_start_tx:

start transaction
^^^^^^^^^^^^^^^^^

:eql-statement:


``start transaction`` -- start a transaction

.. eql:synopsis::

    start transaction <transaction-mode> [ , ... ] ;

    # where <transaction-mode> is one of:

    isolation serializable
    read write | read only
    deferrable | not deferrable


Description
~~~~~~~~~~~

This command starts a new transaction block.

Any Gel command outside of an explicit transaction block starts
an implicit transaction block; the transaction is then automatically
committed if the command was executed successfully, or automatically
rollbacked if there was an error.  This behavior is often called
"autocommit".


Parameters
~~~~~~~~~~

The :eql:synopsis:`<transaction-mode>` can be one of the following:

:eql:synopsis:`isolation serializable`
    All statements in the current transaction can only see data
    changes that were committed before the first query or data
    modification statement was executed within this transaction.
    If a pattern of reads and writes among concurrent serializable
    transactions creates a situation that could not have occurred
    in any serial (one-at-a-time) execution of those transactions,
    one of them will be rolled back with a serialization_failure error.

:eql:synopsis:`read write`
    Sets the transaction access mode to read/write.

    This is the default.

:eql:synopsis:`read only`
    Sets the transaction access mode to read-only.  Any data
    modifications with :eql:stmt:`insert`, :eql:stmt:`update`, or
    :eql:stmt:`delete` are disallowed. Schema mutations via :ref:`DDL
    <ref_eql_ddl>` are also disallowed.

:eql:synopsis:`deferrable`
    The transaction can be set to deferrable mode only when it is
    ``serializable`` and ``read only``.  When all three of these
    properties are selected for a transaction, the transaction
    may block when first acquiring its snapshot, after which it is
    able to run without the normal overhead of a ``serializable``
    transaction and without any risk of contributing to or being
    canceled by a serialization failure. This mode is well suited
    for long-running reports or backups.


Examples
~~~~~~~~

Start a new transaction and rollback it:

.. code-block:: edgeql

    start transaction;
    select 'Hello World!';
    rollback;

Start a serializable deferrable transaction:

.. code-block:: edgeql

    start transaction isolation serializable, read only, deferrable;


.. _ref_eql_statements_commit_tx:

commit
^^^^^^

:eql-statement:


``commit`` -- commit the current transaction

.. eql:synopsis::

    commit ;


Example
~~~~~~~

Commit the current transaction:

.. code-block:: edgeql

    commit;


Description
~~~~~~~~~~~

The ``commit`` command  commits the current transaction. All changes
made by the transaction become visible to others and are guaranteed to
be durable if a crash occurs.


.. _ref_eql_statements_rollback_tx:

rollback
^^^^^^^^

:eql-statement:


``rollback`` -- abort the current transaction

.. eql:synopsis::

    rollback ;


Example
~~~~~~~

Abort the current transaction:

.. code-block:: edgeql

    rollback;


Description
~~~~~~~~~~~

The ``rollback`` command rolls back the current transaction and causes all
updates made by the transaction to be discarded.


.. _ref_eql_statements_declare_savepoint:

declare savepoint
^^^^^^^^^^^^^^^^^

:eql-statement:


``declare savepoint`` -- declare a savepoint within the current transaction

.. eql:synopsis::

    declare savepoint <savepoint-name> ;


Description
~~~~~~~~~~~

``savepoint`` establishes a new savepoint within the current
transaction.

A savepoint is a special mark inside a transaction that allows all
commands that are executed after it was established to be rolled back,
restoring the transaction state to what it was at the time of the
savepoint.

It is an error to declare a savepoint outside of a transaction.


Example
~~~~~~~

.. code-block:: edgeql

    # Will select no objects:
    select test::TestObject { name };

    start transaction;

        insert test::TestObject { name := 'q1' };
        insert test::TestObject { name := 'q2' };

        # Will select two TestObjects with names 'q1' and 'q2'
        select test::TestObject { name };

        declare savepoint f1;
            insert test::TestObject { name:='w1' };

            # Will select three TestObjects with names
            # 'q1' 'q2', and 'w1'
            select test::TestObject { name };
        rollback to savepoint f1;

        # Will select two TestObjects with names 'q1' and 'q2'
        select test::TestObject { name };

    rollback;


.. _ref_eql_statements_release_savepoint:

release savepoint
^^^^^^^^^^^^^^^^^

:eql-statement:


``release savepoint`` -- release a previously declared savepoint

.. eql:synopsis::

    release savepoint <savepoint-name> ;


Description
~~~~~~~~~~~

``release savepoint`` destroys a savepoint previously defined in the
current transaction.

Destroying a savepoint makes it unavailable as a rollback point,
but it has no other user visible behavior. It does not undo the effects
of commands executed after the savepoint was established.
(To do that, see :eql:stmt:`rollback to savepoint`.)

``release savepoint`` also destroys all savepoints that were
established after the named savepoint was established.


Example
~~~~~~~

.. code-block:: edgeql

    start transaction;
    # ...
    declare savepoint f1;
    # ...
    release savepoint f1;
    # ...
    rollback;

.. list-table::
  :class: seealso

  * - **See also**
  * - :ref:`Reference > EdgeQL > Start transaction
      <ref_eql_statements_start_tx>`
  * - :ref:`Reference > EdgeQL > Commit
      <ref_eql_statements_commit_tx>`
  * - :ref:`Reference > EdgeQL > Rollabck
      <ref_eql_statements_rollback_tx>`
  * - :ref:`Reference > EdgeQL > Declare savepoint
      <ref_eql_statements_declare_savepoint>`
  * - :ref:`Reference > EdgeQL > Rollback to savepoint
      <ref_eql_statements_rollback_savepoint>`


.. _ref_eql_statements_rollback_savepoint:

rollback to savepoint
^^^^^^^^^^^^^^^^^^^^^

:eql-statement:


``rollback to savepoint`` -- rollback to a savepoint within the current
transaction


.. eql:synopsis::

    rollback to savepoint <savepoint-name> ;


Description
~~~~~~~~~~~

Rollback all commands that were executed after the savepoint
was established. The savepoint remains valid and can be rolled back
to again later, if needed.

``rollback to savepoint`` implicitly destroys all savepoints that
were established after the named savepoint.


Example
~~~~~~~

.. code-block:: edgeql

    start transaction;
    # ...
    declare savepoint f1;
    # ...
    rollback to savepoint f1;
    # ...
    rollback;
