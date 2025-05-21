.. _gel-js-datatypes:

==========
Data types
==========

When producing results, the client automatically decodes |Gel| types to the corresponding JavaScript types. When you pass scalar values to the client as arguments, the client automatically encodes them to the corresponding |Gel| types.

The table below shows the correspondence between |Gel| and JavaScript data types.

.. list-table::

  * - **Gel Type**
    - **JavaScript Type**
  * - ``multi`` set
    - ``Array``
  * - ``array<anytype>``
    - ``Array``
  * - ``anytuple``
    - ``Array``
  * - ``anyenum``
    - ``string``
  * - ``Object``
    - ``object``
  * - ``bool``
    - ``boolean``
  * - ``bytes``
    - ``Uint8Array``
  * - ``str``
    - ``string``
  * - ``float32``,  ``float64``, ``int16``, ``int32``, ``int64``
    - ``number``
  * - ``bigint``
    - ``BigInt``
  * - ``decimal``
    - n/a
  * - ``json``
    - ``unknown``
  * - ``uuid``
    - ``string``
  * - ``datetime``
    - ``Date``
  * - ``cal::local_date``
    - :js:class:`LocalDate`
  * - ``cal::local_time``
    - :js:class:`LocalTime`
  * - ``cal::local_datetime``
    - :js:class:`LocalDateTime`
  * - ``duration``
    - :js:class:`Duration`
  * - ``cal::relative_duration``
    - :js:class:`RelativeDuration`
  * - ``cal::date_duration``
    - :js:class:`DateDuration`
  * - ``range<anytype>``
    - :js:class:`Range`
  * - ``cfg::memory``
    - :js:class:`ConfigMemory`

.. note::

    Inexact single-precision ``float`` values may have a different representation when decoded into a JavaScript number.  This is inherent to the implementation of limited-precision floating point types.  If you need the decimal representation to match, cast the expression to ``float64`` in your query.

.. note::

    Due to precision limitations the ``decimal`` type cannot be decoded to a JavaScript number. Use an explicit cast to ``float64`` if the precision degradation is acceptable or a cast to ``str`` for an exact decimal representation.

Arrays
======

Gel ``array``  maps onto the JavaScript ``Array``.

.. code-block:: javascript

  await client.querySingle<number[]>("select [1, 2, 3];");
  // number[]: [1, 2, 3]


.. _gel-js-types-object:

Objects
=======

``Object`` represents an object instance returned from a query. The value of an
object property or a link can be accessed through a corresponding object key:

.. code-block:: typescript

    await client.query<{
      title: string;
      characters: {
        name: string;
        "@character_name": string;
      }[];
    }>(`
      select Movie {
        title,
        characters: {
          name,
          @character_name
        }
      };
    `);

Tuples
======

A regular |Gel| ``tuple`` becomes an ``Array`` in JavaScript. A |Gel| ``namedtuple`` becomes an object with properties corresponding to the tuple elements.

.. code-block:: typescript

  await client.queryRequiredSingle<[number, string]>(`select (1, "hello");`);
  // [number, string]: [1, 'hello']

  await client.queryRequiredSingle<{
    foo: number;
    bar: string;
  }>(`select (foo := 1, bar := "hello");`);
  // { foo: number; bar: string }: { foo: 1; bar: 'hello' }

Local Date
==========

.. js:class:: LocalDate(\
        year: number, \
        month: number, \
        day: number)

    A JavaScript representation of a |Gel| ``local_date`` value. Implements a subset of the `TC39 Temporal Proposal`_ ``PlainDate`` type.

    Assumes the calendar is always `ISO 8601`_.

    .. js:attribute:: year: number

        The year value of the local date.

    .. js:attribute:: month: number

        The numerical month value of the local date.

        .. note::

            Unlike the JS ``Date`` object, months in ``LocalDate`` start at 1.  ie. Jan = 1, Feb = 2, etc.

    .. js:attribute:: day: number

        The day of the month value of the local date (starting with 1).

    .. js:attribute:: dayOfWeek: number

        The weekday number of the local date. Returns a value between 1 and 7 inclusive, where 1 = Monday and 7 = Sunday.

    .. js:attribute:: dayOfYear: number

        The ordinal day of the year of the local date. Returns a value between 1 and 365 (or 366 in a leap year).

    .. js:attribute:: weekOfYear: number

        The ISO week number of the local date. Returns a value between 1 and 53, where ISO week 1 is defined as the week containing the first Thursday of the year.

    .. js:attribute:: daysInWeek: number

        The number of days in the week of the local date. Always returns 7.

    .. js:attribute:: daysInMonth: number

        The number of days in the month of the local date. Returns a value between 28 and 31 inclusive.

    .. js:attribute:: daysInYear: number

        The number of days in the year of the local date. Returns either 365 or 366 if the year is a leap year.

    .. js:attribute:: monthsInYear: number

        The number of months in the year of the local date. Always returns 12.

    .. js:attribute:: inLeapYear: boolean

        Return whether the year of the local date is a leap year.

    .. js:method:: toString(): string

        Get the string representation of the ``LocalDate`` in the ``YYYY-MM-DD`` format.

    .. js:method:: toJSON(): number

        Same as :js:meth:`~LocalDate.toString`.

    .. js:method:: valueOf(): never

        Always throws an Error. ``LocalDate`` objects are not comparable.


Local Time
==========

.. js:class:: LocalTime(\
        hour: number = 0, \
        minute: number = 0, \
        second: number = 0, \
        millisecond: number = 0, \
        microsecond: number = 0, \
        nanosecond: number = 0)

    A JavaScript representation of a Gel ``local_time`` value. Implements a subset of the `TC39 Temporal Proposal`_ ``PlainTime`` type.

    .. note::

        The Gel ``local_time`` type only has microsecond precision, any nanoseconds specified in the ``LocalTime`` will be ignored when encoding to a Gel ``local_time``.

    .. js:attribute:: hour: number

        The hours component of the local time in 0-23 range.

    .. js:attribute:: minute: number

        The minutes component of the local time in 0-59 range.

    .. js:attribute:: second: number

        The seconds component of the local time in 0-59 range.

    .. js:attribute:: millisecond: number

        The millisecond component of the local time in 0-999 range.

    .. js:attribute:: microsecond: number

        The microsecond component of the local time in 0-999 range.

    .. js:attribute:: nanosecond: number

        The nanosecond component of the local time in 0-999 range.

    .. js:method:: toString(): string

        Get the string representation of the ``local_time`` in the ``HH:MM:SS`` 24-hour format.

    .. js:method:: toJSON(): string

        Same as :js:meth:`~LocalTime.toString`.

    .. js:method:: valueOf(): never

        Always throws an Error. ``LocalTime`` objects are not comparable.


Local Date and Time
===================

.. js:class:: LocalDateTime(\
        year: number, \
        month: number, \
        day: number, \
        hour: number = 0, \
        minute: number = 0, \
        second: number = 0, \
        millisecond: number = 0, \
        microsecond: number = 0, \
        nanosecond: number = 0) extends LocalDate, LocalTime

    A JavaScript representation of a |Gel| ``local_datetime`` value.  Implements a subset of the `TC39 Temporal Proposal`_ ``PlainDateTime`` type.

    Inherits all properties from the :js:class:`~LocalDate` and :js:class:`~LocalTime` types.

    .. js:method:: toString(): string

        Get the string representation of the ``local_datetime`` in the ``YYYY-MM-DDTHH:MM:SS`` 24-hour format.

    .. js:method:: toJSON(): string

        Same as :js:meth:`~LocalDateTime.toString`.

    .. js:method:: valueOf(): never

        Always throws an Error. ``LocalDateTime`` objects are not comparable.


Duration
========

.. js:class:: Duration(\
        years: number = 0, \
        months: number = 0, \
        weeks: number = 0, \
        days: number = 0, \
        hours: number = 0, \
        minutes: number = 0, \
        seconds: number = 0, \
        milliseconds: number = 0, \
        microseconds: number = 0, \
        nanoseconds: number = 0)

    A JavaScript representation of a Gel ``duration`` value. This class attempts to conform to the `TC39 Temporal Proposal`_ ``Duration`` type as closely as possible.

    No arguments may be infinite and all must have the same sign. Any non-integer arguments will be rounded towards zero.

    .. note::

        The Temporal ``Duration`` type can contain both absolute duration components, such as hours, minutes, seconds, etc. and relative duration components, such as years, months, weeks, and days, where their absolute duration changes depending on the exact date they are relative to (eg. different months have a different number of days).

        The Gel ``duration`` type only supports absolute durations, so any ``Duration`` with non-zero years, months, weeks, or days will throw an error when trying to encode them.

    .. note::

        The Gel ``duration`` type only has microsecond precision, any nanoseconds specified in the ``Duration`` will be ignored when encoding to a Gel ``duration``.

    .. note::

        Temporal ``Duration`` objects can be unbalanced_, (ie. have a greater value in any property than it would naturally have, eg. have a seconds property greater than 59), but Gel ``duration`` objects are always balanced.

        Therefore in a round-trip of a ``Duration`` object to Gel and back, the returned object, while being an equivalent duration, may not have exactly the same property values as the sent object.

    .. js:attribute:: years: number

        The number of years in the duration.

    .. js:attribute:: months: number

        The number of months in the duration.

    .. js:attribute:: weeks: number

        The number of weeks in the duration.

    .. js:attribute:: days: number

        The number of days in the duration.

    .. js:attribute:: hours: number

        The number of hours in the duration.

    .. js:attribute:: minutes: number

        The number of minutes in the duration.

    .. js:attribute:: seconds: number

        The number of seconds in the duration.

    .. js:attribute:: milliseconds: number

        The number of milliseconds in the duration.

    .. js:attribute:: microseconds: number

        The number of microseconds in the duration.

    .. js:attribute:: nanoseconds: number

        The number of nanoseconds in the duration.

    .. js:attribute:: sign: number

        Returns -1, 0, or 1 depending on whether the duration is negative, zero or positive.

    .. js:attribute:: blank: boolean

        Returns ``true`` if the duration is zero.

    .. js:method:: toString(): string

        Get the string representation of the duration in `ISO 8601 duration`_ format.

    .. js:method:: toJSON(): number

        Same as :js:meth:`~Duration.toString`.

    .. js:method:: valueOf(): never

        Always throws an Error. ``Duration`` objects are not comparable.


Relative Duration
=================

.. js:class:: RelativeDuration(\
        years: number = 0, \
        months: number = 0, \
        weeks: number = 0, \
        days: number = 0, \
        hours: number = 0, \
        minutes: number = 0, \
        seconds: number = 0, \
        milliseconds: number = 0, \
        microseconds: number = 0)

  A JavaScript representation of a Gel :eql:type:`cal::relative_duration` value. This type represents a non-definite span of time such as "2 years 3 days". This cannot be represented as a :eql:type:`duration` because a year has no absolute duration; for instance, leap years are longer than non-leap years.

  This class attempts to conform to the `TC39 Temporal Proposal`_ ``Duration`` type as closely as possible.

  Internally, a ``cal::relative_duration`` value is represented as an integer number of months, days, and seconds. During encoding, other units will be normalized to these three. Sub-second units like ``microseconds`` will be ignored.

  .. js:attribute:: years: number

      The number of years in the relative duration.

  .. js:attribute:: months: number

      The number of months in the relative duration.

  .. js:attribute:: weeks: number

      The number of weeks in the relative duration.

  .. js:attribute:: days: number

      The number of days in the relative duration.

  .. js:attribute:: hours: number

      The number of hours in the relative duration.

  .. js:attribute:: minutes: number

      The number of minutes in the relative duration.

  .. js:attribute:: seconds: number

      The number of seconds in the relative duration.

  .. js:attribute:: milliseconds: number

      The number of milliseconds in the relative duration.

  .. js:attribute:: microseconds: number

      The number of microseconds in the relative duration.

  .. js:method:: toString(): string

      Get the string representation of the duration in `ISO 8601 duration`_
      format.

  .. js:method:: toJSON(): string

      Same as :js:meth:`~Duration.toString`.

  .. js:method:: valueOf(): never

      Always throws an Error. ``RelativeDuration`` objects are not
      comparable.


Date Duration
=============

.. js:class:: DateDuration( \
      years: number = 0, \
      months: number = 0, \
      weeks: number = 0, \
      days: number = 0, \
    )

  A JavaScript representation of a Gel :eql:type:`cal::date_duration` value. This type represents a non-definite span of time consisting of an integer number of *months* and *days*.

  This type is primarily intended to simplify logic involving :eql:type:`cal::local_date` values.

  .. code-block:: edgeql-repl

    db> select <cal::date_duration>'5 days';
    {<cal::date_duration>'P5D'}
    db> select <cal::local_date>'2022-06-25' + <cal::date_duration>'5 days';
    {<cal::local_date>'2022-06-30'}
    db> select <cal::local_date>'2022-06-30' - <cal::local_date>'2022-06-25';
    {<cal::date_duration>'P5D'}

  Internally, a ``cal::relative_duration`` value is represented as an integer number of months and days. During encoding, other units will be normalized to these two.

  .. js:attribute:: years: number

      The number of years in the relative duration.

  .. js:attribute:: months: number

      The number of months in the relative duration.

  .. js:attribute:: weeks: number

      The number of weeks in the relative duration.

  .. js:attribute:: days: number

      The number of days in the relative duration.

  .. js:method:: toString(): string

      Get the string representation of the duration in `ISO 8601 duration`_ format.

  .. js:method:: toJSON(): string

      Same as :js:meth:`~Duration.toString`.

  .. js:method:: valueOf(): never

      Always throws an Error. ``DateDuration`` objects are not comparable.


Memory
======

.. js:class:: ConfigMemory(bytes: BigInt)

  A JavaScript representation of a Gel ``cfg::memory`` value.

  .. js:attribute:: bytes: number

      The memory value in bytes (B).

      .. note::

          The Gel ``cfg::memory`` represents a number of bytes stored as an ``int64``. Since JS the ``number`` type is a ``float64``, values above ``~8191TiB`` will lose precision when represented as a JS ``number``. To keep full precision use the ``bytesBigInt`` property.

  .. js::attribute:: bytesBigInt: BigInt

      The memory value in bytes represented as a ``BigInt``.

  .. js:attribute:: kibibytes: number

      The memory value in kibibytes (KiB).

  .. js:attribute:: mebibytes: number

      The memory value in mebibytes (MiB).

  .. js:attribute:: gibibytes: number

      The memory value in gibibytes (GiB).

  .. js:attribute:: tebibytes: number

      The memory value in tebibytes (TiB).

  .. js:attribute:: pebibytes: number

      The memory value in pebibytes (PiB).

  .. js:method:: toString(): string

      Get the string representation of the memory value. Format is the same as returned by string casting a ``cfg::memory`` value in Gel.

Range
=====

.. js:class:: Range(\
        lower: T | null, \
        upper: T | null, \
        incLower: boolean = true, \
        incUpper: boolean = false \
    )

  A JavaScript representation of a Gel ``std::range`` value. This is a generic TypeScript class with the following type signature.

  .. code-block:: typescript

      class Range<
          T extends number | Date | LocalDate | LocalDateTime | Duration
      >{
          // ...
      }

  .. js:attribute:: lower: T

      The lower bound of the range value.

  .. js:attribute:: upper: T

      The upper bound of the range value.

  .. js:attribute:: incLower: boolean

      Whether the lower bound is inclusive.

  .. js:attribute:: incUpper: boolean

      Whether the upper bound is inclusive.

  .. js:attribute:: empty: boolean

      Whether the range is empty.

  .. js:method:: toJSON(): { \
        lower: T | null; \
        upper: T | null; \
        inc_lower: boolean; \
        inc_upper: boolean; \
        empty?: undefined; \
      }

      Returns a JSON-encodable representation of the range.

  .. js:method:: empty(): Range

      A static method to declare an empty range (no bounds).

      .. code-block:: typescript

          Range.empty();

.. _TC39 Temporal Proposal: https://tc39.es/proposal-temporal/docs/
.. _ISO 8601: https://en.wikipedia.org/wiki/ISO_8601#Dates
.. _ISO 8601 duration: https://en.wikipedia.org/wiki/ISO_8601#Durations
.. _unbalanced: https://tc39.es/proposal-temporal/docs/balancing.html
