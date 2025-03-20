.. _gel-js-intro:

========================
Gel TypeScript/JS Client
========================

.. toctree::
   :maxdepth: 3
   :hidden:

   connection
   client
   generation
   queries
   interfaces
   querybuilder
   literals
   types
   funcops
   parameters
   objects
   select
   insert
   update
   delete
   with
   for
   group
   reference

.. _gel-js-installation:


Installation
============

You can install the published database driver and optional (but recommended!)
generators from npm using your package manager of choice.

.. tabs::

    .. code-tab:: bash
      :caption: npm

      $ npm install --save-prod gel          # database driver
      $ npm install --save-dev @gel/generate # generators

    .. code-tab:: bash
      :caption: yarn

      $ yarn add gel                 # database driver
      $ yarn add --dev @gel/generate # generators

    .. code-tab:: bash
      :caption: pnpm

      $ pnpm add --save-prod gel          # database driver
      $ pnpm add --save-dev @gel/generate # generators

    .. code-tab:: typescript
      :caption: deno

      import * as gel from "http://deno.land/x/gel/mod.ts";

    .. code-tab:: bash
      :caption: bun

      $ bun add gel                 # database driver
      $ bun add --dev @gel/generate # generators

    .. code-tab:: bash
      :caption: deno

      $ deno add npm:gel                 # database driver
      $ deno add --dev npm:@gel/generate # generators
