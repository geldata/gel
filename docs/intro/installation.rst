.. _ref_cli_gel_install:

============
Installation
============

We provide a :ref:`CLI for managing and interacting with local and remote databases <ref_cli_overview>`. If you're using JavaScript or Python, our client libraries will handle downloading and running the CLI for you using tools like ``npx`` and ``uvx``.

For everyone else, or if you wish to install the CLI globally, you can install using our bash installer or your operating system's package manager.

.. tabs::

  .. code-tab:: bash
    :caption: bash

    $ curl https://www.geldata.com/sh --proto "=https" -sSf1 | sh

  .. code-tab:: powershell
    :caption: Powershell

    PS> irm https://www.geldata.com/ps1 | iex

  .. code-tab:: bash
    :caption: Homebrew

    $ brew install geldata/tap/gel-cli

  .. code-tab:: bash
    :caption: Nixpkgs

    $ nix-shell -p gel

  .. code-tab:: bash
    :caption: JavaScript

    $ npx gel --version

  .. code-tab:: bash
    :caption: Python

    $ uvx gel --version
