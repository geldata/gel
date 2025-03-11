.. _ref_guide_deployment_aws_aurora_ecs:

===
AWS
===

:edb-alt-title:  Deploying Gel to AWS

In this guide we show how to deploy Gel on AWS using Amazon Aurora and
Elastic Container Service.

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

It's often convenient to create an alias for the remote instance using
:gelcmd:`instance link`.

.. code-block:: bash

   $ gel instance link \
        --trust-tls-cert \
        --dsn gel://admin:<password>@<hostname> \
        my_aws_instance

This aliases the remote instance to ``my_aws_instance`` (this name can be
anything). You can now use the ``-I my_aws_instance`` flag to run CLI commands
against this instance, as with local instances.

.. note::

   The command groups :gelcmd:`instance` and :gelcmd:`project` are not
   intended to manage production instances.

.. code-block:: bash

  $ gel -I my_aws_instance
  Gel x.x
  Type \help for help, \quit to quit.
  gel>

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

Health Checks
=============

Using an HTTP client, you can perform health checks to monitor the status of
your Gel instance. Learn how to use them with our :ref:`health checks guide
<ref_guide_deployment_health_checks>`.
