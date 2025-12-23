.. _ref_guide_deployment_aws_aurora_ecs:

===
AWS
===

:edb-alt-title:  Deploying Gel to AWS

.. note::

   We recomend using our `helm chart <helm-chart_>`_ to deploy gel on AWS EKS.  The
   CloudFormation guide below does not configure TLS certificates correctly.

.. _helm-chart:
   https://github.com/geldata/helm-charts/blob/main
   /charts/gel-server/README.md

In this guide we show how to deploy Gel on AWS using Amazon Aurora and
Elastic Container Service.

.. include:: ./note_cloud_reset_password.rst

Prerequisites
=============

* AWS account with billing enabled (or a `free trial <aws-trial_>`_)
* (optional) ``aws`` CLI (`install <awscli-install_>`_)

.. _aws-trial: https://aws.amazon.com/free
.. _awscli-install:
   https://docs.aws.amazon.com
   /cli/latest/userguide/getting-started-install.html

Quick Install with CloudFormation
=================================

We maintain a `CloudFormation template <cf-template_>`_ for easy automated
deployment of Gel in your AWS account.  The template deploys Gel
to a new ECS service and connects it to a newly provisioned Aurora PostgreSQL
cluster. The created instance has a public IP address with TLS configured and
is protected by a password you provide.

CloudFormation Web Portal
-------------------------

Click `here <cf-deploy_>`_ to start the deployment process using CloudFormation
portal and follow the prompts. You'll be prompted to provide a value for the
following parameters:

- ``DockerImage``: defaults to the latest version (``geldata/gel``), or you
  can specify a particular tag from the ones published to `Docker Hub
  <https://hub.docker.com/r/geldata/gel/tags>`_.
- ``InstanceName``: ⚠️ Due to limitations with AWS, this must be 22 characters
  or less!
- ``SuperUserPassword``: this will be used as the password for the new Gel
  instance. Keep track of the value you provide.

Once the deployment is complete, follow these steps to find the host name that
has been assigned to your Gel instance:

.. lint-off

1. Open the AWS Console and navigate to CloudFormation > Stacks. Click on the
   newly created Stack.
2. Wait for the status to read ``CREATE_COMPLETE``—it can take 15 minutes or
   more.
3. Once deployment is complete, click the ``Outputs`` tab. The value of
   ``PublicHostname`` is the hostname at which your Gel instance is
   publicly available.
4. Copy the hostname and run the following command to open a REPL to your
   instance.

   .. code-block:: bash

     $ gel --dsn gel://admin:<password>@<hostname> --tls-security insecure
     Gel x.x
     Type \help for help, \quit to quit.
     gel>

.. lint-on

To make changes to your Gel deployment like upgrading the Gel version or
enabling the UI you can follow the CloudFormation
`Updating a stack <stack-update_>`_ instructions. Search for
``ContainerDefinitions`` in the template and you will find where Gel's
:ref:`environment variables <ref_guides_deployment_docker_customization>` are
defined. To upgrade the Gel version specify a
`docker image tag <docker-tags_>`_ with the image name ``geldata/gel`` in the
second step of the update workflow.

CloudFormation CLI
------------------

Alternatively, if you prefer to use AWS CLI, run the following command in
your terminal:

.. code-block:: bash

    $ aws cloudformation create-stack \
        --stack-name Gel \
        --template-url \
          https://gel-deployment.s3.us-east-2.amazonaws.com/gel-aurora.yml \
        --capabilities CAPABILITY_NAMED_IAM \
        --parameters ParameterKey=SuperUserPassword,ParameterValue=<password>


.. _cf-template: https://github.com/geldata/gel-deploy/tree/dev/aws-cf
.. _cf-deploy:
   https://console.aws.amazon.com
   /cloudformation/home#/stacks/new?stackName=Gel&templateURL=
   https%3A%2F%2Fgel-deployment.s3.us-east-2.amazonaws.com%2Fgel-aurora.yml
.. _aws_console:
   https://console.aws.amazon.com
   /ec2/v2/home#NIC:search=ec2-security-group
.. _stack-update:
   https://docs.aws.amazon.com
   /AWSCloudFormation/latest/UserGuide/cfn-whatis-howdoesitwork.html
.. _docker-tags: https://hub.docker.com/r/geldata/gel/tags


Connecting your application
===========================

To connect your application to the Gel instance, you'll need to provide
connection parameters. Gel client libraries can be configured using either
a DSN (connection string) or individual environment variables.

Obtaining connection parameters
-------------------------------

Your connection requires the following components:

- **Host**: The ``PublicHostname`` value from the CloudFormation Stack's
  ``Outputs`` tab.
- **Port**: ``5656`` (the default Gel port)
- **Username**: |admin| (the default superuser)
- **Password**: The ``SuperUserPassword`` you specified during deployment
- **Branch**: |main| (the default branch)

Construct the DSN using these values:

.. code-block:: bash

    $ GEL_DSN="gel://admin:<password>@<hostname>:5656"

Obtaining the TLS certificate
-----------------------------

.. warning::

    The CloudFormation template does not configure TLS certificates correctly.
    We recommend using ``--tls-security insecure`` for testing, but for
    production you should use our `helm chart <helm-chart_>`_ or configure
    TLS manually.

To connect securely, your application needs the server's TLS certificate.
For self-signed certificates, you can retrieve the certificate by connecting
to the instance and extracting it:

.. code-block:: bash

    $ gel --dsn $GEL_DSN --tls-security insecure \
        query "SELECT sys::get_tls_certificate()"

Store this certificate and provide it to your application via the
:gelenv:`TLS_CA` or :gelenv:`TLS_CA_FILE` environment variable.

Using in your application
-------------------------

Set these environment variables where you deploy your application:

.. code-block:: bash

    GEL_DSN="gel://admin:<password>@<hostname>:5656"
    # For self-signed certificates:
    GEL_CLIENT_TLS_SECURITY=insecure
    # Or with a proper TLS certificate:
    GEL_TLS_CA="<certificate content>"

Gel's client libraries will automatically read these environment variables.

Local development with the CLI
------------------------------

To make your remote instance easier to work with during local development,
create an alias using :gelcmd:`instance link`.

.. note::

   The command groups :gelcmd:`instance` and :gelcmd:`project` are not
   intended to manage production instances.

.. code-block:: bash

    $ gel instance link \
        --dsn $GEL_DSN \
        --non-interactive \
        --trust-tls-cert \
        my_aws_instance

You can now refer to the remote instance using the alias ``my_aws_instance``.
Use this alias wherever an instance name is expected:

.. code-block:: bash

    $ gel -I my_aws_instance
    Gel x.x
    Type \help for help, \quit to quit.
    gel>

Or apply migrations:

.. code-block:: bash

    $ gel -I my_aws_instance migrate


Health Checks
=============

Using an HTTP client, you can perform health checks to monitor the status of
your Gel instance. Learn how to use them with our :ref:`health checks guide
<ref_guide_deployment_health_checks>`.
