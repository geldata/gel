.. _ref_using_index:

=========
Using Gel
=========

.. toctree::
    :maxdepth: 2
    :hidden:

    connection
    projects
    cli/index
    clients
    js/index
    python/index
    Go <https://pkg.go.dev/github.com/geldata/gel-go>
    Rust <https://docs.rs/gel-tokio/latest/gel_tokio/>
    sql_adapter
    http
    graphql/index
    datetime

This section covers how to connect to and interact with a running Gel instance, whether it's hosted locally or on a remote server like our Cloud service. This section covers how to establish connections, send queries to retrieve and manipulate data, and use the Gel CLI to manage your running database.

Connecting to Gel
=================

Gel clients and tools have a unique system for resolving connections to the appropriate Gel instance.

Working with Projects
=====================

For local development, Gel offers project-based workflows that simplify connection configuration  and streamline development tasks. Tools like the Gel CLI, the language server, and the language-specific client libraries all use the concept of projects to manage connections. You can use projects to run a local instance, or link your local environment to a remote instance.

Command Line interface
======================

The Gel CLI provides powerful tools for database administration, schema management, REPL-based data exploration, and more - all from your terminal. It's an essential companion for both development and operational tasks.

Client Libraries
================

Choose from a variety of language-specific client libraries (JavaScript, Python, Go, Rust) to integrate Gel into your applications. Our clients are higher-level than most database drivers, providing integrated pooling, connection management, transaction retries, and more. Many languages also offer code generation tools that integrate your queries more tightly into your codebase.