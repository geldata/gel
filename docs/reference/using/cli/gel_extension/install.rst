.. _ref_cli_gel_extension_install:

=====================
gel extension install
=====================

Install an extension.

.. cli:synopsis::

  gel extension install <extension> [<options>]

Arguments
=========

:cli:synopsis:`<extension>`
    The name of the extension to install.

Options
=======

See :ref:`Connection options <ref_cli_gel_connopts>` for global options.

Examples
========

Install the ``postgis`` extension:

.. code-block:: bash

  $ gel extension install postgis
  Found extension package: postgis version 3.4.3+6b82d77
  00:00:03 [====================] 22.49 MiB/22.49 MiB
  Extension 'postgis' installed successfully.
