.. _ref_eql_statements_for:

For
===

:eql-statement:
:eql-haswith:


``for``--compute a union of subsets based on values of another set

.. eql:synopsis::

    [ with <with-item> [, ...] ]

    for <variable> in <iterator-expr>

    union <output-expr> ;

:eql:synopsis:`for <variable> in <iterator-expr>`
    The ``for`` clause has this general form:

    .. TODO: rewrite this

    .. eql:synopsis::

        for <variable> in <iterator-expr>

    where :eql:synopsis:`<iterator-expr>` is a
	:ref:`literal <ref_eql_literals>`,
	a :ref:`function call <ref_reference_function_call>`,
	a :ref:`set constructor <ref_eql_set_constructor>`,
	a :ref:`path <ref_reference_paths>`,
	or any parenthesized expression or statement.

:eql:synopsis:`union <output-expr>`
    The ``union`` clause of the ``for`` statement has this general form:

    .. TODO: rewrite this

    .. eql:synopsis::

        union <output-expr>

    Here, :eql:synopsis:`<output-expr>`
    is an arbitrary expression that is evaluated for
    every element in a set produced by evaluating the ``for`` clause.
    The results of the evaluation are appended to the result set.


.. _ref_eql_forstatement:

Usage of ``for`` statement
++++++++++++++++++++++++++

``for`` statement has some powerful features that deserve to be
considered in detail separately. However, the common core is that
``for`` iterates over elements of some arbitrary expression. Then for
each element of the iterator some set is computed and combined via a
:eql:op:`union` with the other such computed sets.

The simplest use case is when the iterator is given by a set
expression and it follows the general form of ``for x in A ...``:

.. code-block:: edgeql

    with module example
    # the iterator is an explicit set of tuples, so x is an
    # element of this set, i.e. a single tuple
    for x in {
        (name := 'Alice', theme := 'fire'),
        (name := 'Bob', theme := 'rain'),
        (name := 'Carol', theme := 'clouds'),
        (name := 'Dave', theme := 'forest')
    }
    # typically this is used with an INSERT, DELETE or UPDATE
    union (
        insert
            User {
                name := x.name,
                theme := x.theme,
            }
    );

Since ``x`` is an element of a set it is guaranteed to be a non-empty
singleton in all of the expressions used by the ``union`` and later
clauses of ``for``.

Another variation this usage of ``for`` is a bulk ``update``. There
are cases when a bulk update involves a lot of external data that
cannot be derived from the objects being updated. That is a good
use-case when a ``for`` statement is appropriate.

.. code-block:: edgeql

    # Here's an example of an update that is awkward to
    # express without the use of FOR statement
    with module example
    update User
    filter .name in {'Alice', 'Bob', 'Carol', 'Dave'}
    set {
        theme := 'red'  if .name = 'Alice' else
                 'star' if .name = 'Bob' else
                 'dark' if .name = 'Carol' else
                 'strawberry'
    };

    # Using a FOR statement, the above update becomes simpler to
    # express or review for a human.
    with module example
    for x in {
        (name := 'Alice', theme := 'red'),
        (name := 'Bob', theme := 'star'),
        (name := 'Carol', theme := 'dark'),
        (name := 'Dave', theme := 'strawberry')
    }
    union (
        update User
        filter .name = x.name
        set {
            theme := x.theme
        }
    );

When updating data that mostly or completely depends on the objects
being updated there's no need to use the ``for`` statement and it is not
advised to use it for performance reasons.

.. code-block:: edgeql

    with module example
    update User
    filter .name in {'Alice', 'Bob', 'Carol', 'Dave'}
    set {
        theme := 'halloween'
    };

    # The above can be accomplished with a for statement,
    # but it is not recommended.
    with module example
    for x in {'Alice', 'Bob', 'Carol', 'Dave'}
    union (
        update User
        filter .name = x
        set {
            theme := 'halloween'
        }
    );

Another example of using a ``for`` statement is working with link
properties. Specifying the link properties either at creation time or
in a later step with an update is often simpler with a ``for``
statement helping to associate the link target to the link property in
an intuitive manner.

.. code-block:: edgeql

    # Expressing this without for statement is fairly tedious.
    with
        module example,
        U2 := User
    for x in {
        (
            name := 'Alice',
            friends := [('Bob', 'coffee buff'),
                        ('Carol', 'dog person')]
        ),
        (
            name := 'Bob',
            friends := [('Alice', 'movie buff'),
                        ('Dave', 'cat person')]
        )
    }
    union (
        update User
        filter .name = x.name
        set {
            friends := assert_distinct(
                (
                    for f in array_unpack(x.friends)
                    union (
                        select U2 {@nickname := f.1}
                        filter U2.name = f.0
                    )
                )
            )
        }
    );


.. list-table::
  :class: seealso

  * - **See also**
  * - :ref:`EdgeQL > For <ref_eql_for>`
