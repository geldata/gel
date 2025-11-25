.. note:: Gel Cloud: Reset the default password for the admin role

    If you want to dump an existing Gel Cloud instance, you will need to change the automatically generated password for the standard admin role - ``edgedb`` or ``admin``. To do this, execute the following query in the instance:

    .. code-block:: edgeql-repl

        ALTER ROLE admin { set password := 'new_password' };
