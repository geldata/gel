.. _ref_guide_deployment_azure_flexibleserver:

=====
Azure
=====

:edb-alt-title: Deploying Gel to Azure

In this guide we show how to deploy Gel using Azure's `Postgres
Flexible Server
<https://docs.microsoft.com/en-us/azure/postgresql/flexible-server>`_ as the
backend.

.. include:: ./note_cloud_reset_password.rst

Prerequisites
=============

* Valid Azure Subscription with billing enabled or credits (`free trial
  <azure-trial_>`_).
* Azure CLI (`install <azure-install_>`_).

.. _azure-trial: https://azure.microsoft.com/en-us/free/
.. _azure-install: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli


Provision a Gel instance
=========================

Login to your Microsoft Azure account.

.. code-block:: bash

   $ az login

Create a new resource group.

.. code-block:: bash

   $ GROUP=my-group-name
   $ az group create --name $GROUP --location westus

Provision a PostgreSQL server.

.. note::

   If you already have a database provisioned you can skip this step.

For convenience, assign a value to the ``PG_SERVER_NAME`` environment
variable; we'll use this variable in multiple later commands.

.. code-block:: bash

   $ PG_SERVER_NAME=postgres-for-gel

Use the ``read`` command to securely assign a value to the ``PASSWORD``
environment variable.

.. code-block:: bash

   $ echo -n "> " && read -s PASSWORD

Then create a Postgres Flexible server.

.. code-block:: bash

   $ az postgres flexible-server create \
       --resource-group $GROUP \
       --name $PG_SERVER_NAME \
       --location westus \
       --admin-user gel_admin \
       --admin-password $PASSWORD \
       --sku-name Standard_D2s_v3 \
       --version 14 \
       --yes

.. note::

   If you get an error saying ``"Specified server name is already used."``
   change the value of ``PG_SERVER_NAME`` and rerun the command.

Allow other Azure services access to the Postgres instance.

.. code-block:: bash

   $ az postgres flexible-server firewall-rule create \
       --resource-group $GROUP \
       --name $PG_SERVER_NAME \
       --rule-name allow-azure-internal \
       --start-ip-address 0.0.0.0 \
       --end-ip-address 0.0.0.0

|Gel| requires Postgres' ``uuid-ossp`` extension which needs to be enabled.

.. code-block:: bash

   $ az postgres flexible-server parameter set \
       --resource-group $GROUP \
       --server-name $PG_SERVER_NAME \
       --name azure.extensions \
       --value uuid-ossp

Azure is not able to reliably pull docker images `because of rate limits
<azure-cli-issue_>`_, so you will need to provide docker hub login credentials
to create a container. If you don't already have a docker hub account you can
create one `here <https://app.docker.com/signup>`_.

.. _azure-cli-issue: https://github.com/Azure/azure-cli/issues/29300

.. code-block:: bash

   $ echo -n "docker user> " && read -s DOCKER_USER
   $ echo -n "docker password> " && read -s DOCKER_PASSWORD

Start a Gel container.

.. code-block:: bash

   $ PG_HOST=$(
       az postgres flexible-server list \
         --resource-group $GROUP \
         --query "[?name=='$PG_SERVER_NAME'].fullyQualifiedDomainName | [0]" \
         --output tsv
     )
   $ DSN="postgresql://gel_admin:$PASSWORD@$PG_HOST/postgres?sslmode=require"
   $ az container create \
       --registry-username $DOCKER_USER \
       --registry-password $DOCKER_PASSWORD \
       --registry-login-server index.docker.io \
       --os-type Linux \
       --cpu 1 \
       --memory 1 \
       --resource-group $GROUP \
       --name gel-container-group \
       --image geldata/gel \
       --dns-name-label geldb \
       --ports 5656 \
       --secure-environment-variables \
         "GEL_SERVER_PASSWORD=$PASSWORD" \
         "GEL_SERVER_BACKEND_DSN=$DSN" \
       --environment-variables \
         GEL_SERVER_TLS_CERT_MODE=generate_self_signed

Persist the SSL certificate. We have configured Gel to generate a self
signed SSL certificate when it starts. However, if the container is restarted a
new certificate would be generated. To preserve the certificate across failures
or reboots copy the certificate files and use their contents in the
:gelenv:`SERVER_TLS_KEY` and :gelenv:`SERVER_TLS_CERT` environment variables.

.. code-block:: bash

   $ key="$( az container exec \
               --resource-group $GROUP \
               --name gel-container-group \
               --exec-command "cat /tmp/gel/edbprivkey.pem" \
             | tr -d "\r" )"
   $ cert="$( az container exec \
                --resource-group $GROUP \
                --name gel-container-group \
                --exec-command "cat /tmp/gel/edbtlscert.pem" \
             | tr -d "\r" )"
   $ az container delete \
       --resource-group $GROUP \
       --name gel-container-group \
       --yes
   $ az container create \
       --registry-username $DOCKER_USER \
       --registry-password $DOCKER_PASSWORD \
       --registry-login-server index.docker.io \
       --os-type Linux \
       --cpu 1 \
       --memory 1 \
       --resource-group $GROUP \
       --name gel-container-group \
       --image geldata/gel \
       --dns-name-label geldb \
       --ports 5656 \
       --secure-environment-variables \
         "GEL_SERVER_PASSWORD=$PASSWORD" \
         "GEL_SERVER_BACKEND_DSN=$DSN" \
         "GEL_SERVER_TLS_KEY=$key" \
       --environment-variables \
         "GEL_SERVER_TLS_CERT=$cert"


Connecting your application
===========================

To connect your application to the Gel instance, you'll need to provide
connection parameters. Gel client libraries can be configured using either
a DSN (connection string) or individual environment variables.

Obtaining connection parameters
-------------------------------

Your connection requires the following components:

- **Host**: The FQDN of your Azure container instance. Retrieve it with:

  .. code-block:: bash

      $ az container list \
          --resource-group $GROUP \
          --query "[?name=='gel-container-group'].ipAddress.fqdn | [0]" \
          --output tsv

- **Port**: ``5656`` (the default Gel port)
- **Username**: |admin| (the default superuser)
- **Password**: The password you set in the ``$PASSWORD`` variable
- **Branch**: |main| (the default branch)

Construct the DSN using these values:

.. code-block:: bash

    $ GEL_HOST=$(az container list \
        --resource-group $GROUP \
        --query "[?name=='gel-container-group'].ipAddress.fqdn | [0]" \
        --output tsv)
    $ GEL_DSN="gel://admin:$PASSWORD@$GEL_HOST:5656"

Obtaining the TLS certificate
-----------------------------

Since we configured Gel with a self-signed TLS certificate, your application
needs the certificate to connect securely. Retrieve it from the container:

.. code-block:: bash

    $ az container exec \
        --resource-group $GROUP \
        --name gel-container-group \
        --exec-command "cat /tmp/gel/edbtlscert.pem" \
      | tr -d "\r" > gel-tls-cert.pem

Alternatively, you can retrieve it using the Gel CLI:

.. code-block:: bash

    $ gel --dsn $GEL_DSN --tls-security insecure \
        query "SELECT sys::get_tls_certificate()" > gel-tls-cert.pem

Using in your application
-------------------------

Set these environment variables where you deploy your application:

.. code-block:: bash

    GEL_DSN="gel://admin:<password>@<hostname>:5656"
    # For self-signed certificates, either trust the cert:
    GEL_TLS_CA_FILE="/path/to/gel-tls-cert.pem"
    # Or (for development only) disable TLS verification:
    GEL_CLIENT_TLS_SECURITY=insecure

Gel's client libraries will automatically read these environment variables.

Local development with the CLI
------------------------------

To make your remote instance easier to work with during local development,
create an alias using :gelcmd:`instance link`.

.. note::

   The command groups :gelcmd:`instance` and :gelcmd:`project` are not
   intended to manage production instances.

.. code-block:: bash

    $ printf $PASSWORD | gel instance link \
        --dsn $GEL_DSN \
        --password-from-stdin \
        --non-interactive \
        --trust-tls-cert \
        my_azure_instance

You can now refer to the remote instance using the alias ``my_azure_instance``.
Use this alias wherever an instance name is expected:

.. code-block:: bash

    $ gel -I my_azure_instance
    Gel x.x
    Type \help for help, \quit to quit.
    gel>

Or apply migrations:

.. code-block:: bash

    $ gel -I my_azure_instance migrate


Health Checks
=============

Using an HTTP client, you can perform health checks to monitor the status of
your Gel instance. Learn how to use them with our :ref:`health checks guide
<ref_guide_deployment_health_checks>`.
