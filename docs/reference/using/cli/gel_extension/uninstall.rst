.. _ref_cli_gel_extension_uninstall:

=======================
gel extension uninstall
=======================

Uninstall an extension.

.. cli:synopsis::

  gel extension uninstall <extension> [<options>]

Arguments
=========

:cli:synopsis:`<extension>`
    The name of the extension to uninstall.

Options
=======

See :ref:`Connection options <ref_cli_gel_connopts>` for global options.

Examples
========

Uninstall the ``postgis`` extension:

.. code-block:: bash

  $ gel extension uninstall postgis
  Extension 'postgis' uninstalled successfully.
