.. note:: Gel Cloud: Reset the default password for the admin role

    If you want to dump an existing Gel Cloud instance and restore it to a new self-managed instance, you need to change the automatically generated password for the default admin role - ``edgedb`` or ``admin``.
    The administrator role name and its password used in the dump/restore process must be the same in both the Cloud and self-managed instances for the Gel tooling to continue functioning properly.
    To change the default password in the Cloud instance, execute the following query in the instance:

    .. code-block:: edgeql-repl

        ALTER ROLE admin { set password := 'new_password' };
