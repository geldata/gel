.. _ref_running_index:

===========
Running Gel
===========

.. toctree::
    :maxdepth: 2
    :hidden:

    local
    deployment/index
    configuration
    http
    backend_ha
    admin/index

This section provides comprehensive guidance for deploying and managing Gel database instances.

Get your instance running
=========================

While running local project instances with the CLI is low maintenance and easy to get started, Gel also makes it easy to configure your production deployment through:

* Environment variables
* Configuration files
* Server CLI arguments

These configuration mechanisms allow you to tailor your Gel deployment to your specific needs. Operations teams can control everything from memory usage, connection limits, to TLS and network settings, ensuring your Gel deployment aligns with organizational policies and infrastructure constraints while maintaining optimal performance.

.. include:: ./deployment/note_cloud.rst

And keep it humming
===================

Running Gel in production requires effective management and monitoring capabilities. Gel provides a comprehensive set of tools for these purposes:

- **HTTP endpoints** for health checks and metrics collection that integrate with your monitoring infrastructure
- **Administrative commands** for:
  - Role management (creating, altering, and dropping roles)
  - Branch operations (creating, dropping, and managing branches)
  - Database maintenance operations like vacuum for reclaiming space
  - Updating internal statistics used by the query planner

These tools enable you to maintain optimal performance, manage access control, and troubleshoot issues in your Gel deployments. The reference documentation for these features is organized in the sections that follow.
