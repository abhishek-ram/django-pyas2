Installation
============

Install using ``pip``...

.. code-block:: console

    $ pip install django-pyas2

Create a new ``django`` project

.. code-block:: console

    $ django-admin startproject django_pyas2 .

Add ``pyas2`` to your ``INSTALLED_APPS`` setting.

.. code-block:: python

    INSTALLED_APPS = (
        ...
        'pyas2',
    )

Include the pyAS2 URL configuration in your project's ``urls.py``.

.. code-block:: python

  from django.urls import include
  urlpatterns = [
      path('pyas2/', include('pyas2.urls')),
      ...
  ]

Run the following commands to complete the installation and start the server.

.. code-block:: console

    $ python manage.py migrate
    Operations to perform:
      Apply all migrations: admin, auth, contenttypes, pyas2, sessions
    Running migrations:
      Applying contenttypes.0001_initial... OK
      Applying auth.0001_initial... OK
      Applying admin.0001_initial... OK
      Applying admin.0002_logentry_remove_auto_add... OK
      Applying admin.0003_logentry_add_action_flag_choices... OK
      Applying contenttypes.0002_remove_content_type_name... OK
      Applying auth.0002_alter_permission_name_max_length... OK
      Applying auth.0003_alter_user_email_max_length... OK
      Applying auth.0004_alter_user_username_opts... OK
      Applying auth.0005_alter_user_last_login_null... OK
      Applying auth.0006_require_contenttypes_0002... OK
      Applying auth.0007_alter_validators_add_error_messages... OK
      Applying auth.0008_alter_user_username_max_length... OK
      Applying auth.0009_alter_user_last_name_max_length... OK
      Applying auth.0010_alter_group_name_max_length... OK
      Applying auth.0011_update_proxy_permissions... OK
      Applying pyas2.0001_initial... OK
      Applying sessions.0001_initial... OK

    $ python manage.py createsuperuser
    Username (leave blank to use 'abhishekram'): admin
    Email address: admin@domain.com
    Password:
    Password (again):
    Superuser created successfully.

    $ python manage.py runserver
    Watching for file changes with StatReloader
    Performing system checks...

    System check identified no issues (0 silenced).
    May 01, 2019 - 07:33:27
    Django version 2.2, using settings 'django_pyas2.settings'
    Starting development server at http://127.0.0.1:8000/
    Quit the server with CONTROL-C.

The ``django-pyas2`` server is now up and running, the web UI for configuration and monitoring can be accessed at
``http://localhost:8000/admin/pyas2/`` and the endpoint for receiving AS2 messages from your partners will be at
``http://localhost:8080/pyas2/as2receive``
