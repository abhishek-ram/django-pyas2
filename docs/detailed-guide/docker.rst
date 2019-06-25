Docker
======
``django-pyas2`` can easily be run as a docker container. Following instruction can be used to
configure a Dockerfile for the application.

The assumption is that a directory containtain the django-project exists already, as described in
the installation section. Create a Dockerfile in the project path and the directory should look as
follows:

.. code-block:: console

    {PROJECT DIRECTORY}
    └──django_pyas2
        ├── django_pyas2
        │   ├── db.sqlite3
        │   ├── manage.py
        │   └── django_pyas2
        │       ├── settings.py
        │       ├── urls.py
        │       └── wsgi.py
        └── Dockerfile


Populate the Dockerfile with following content:

.. code-block:: docker

    FROM python:3.7-alpine3.9

    # Update the index of available packages
    RUN apk update

    # Install packages required for Python cryptography
    RUN apk add --no-cache openssl-dev gcc libffi-dev musl-dev

    # Install django-pyas2 with pip
    RUN pip install django-pyas2

    # Copy the files from the project directory to the container
    WORKDIR /
    COPY django_pyas2 django_pyas2
    CMD ["/usr/local/bin/python", "/django_pyas2/manage.py", "runserver", "0.0.0.0:8000"]

    # AS2 Server
    EXPOSE 8000


Then build and run the container from the command line as follows:

.. code-block:: console

    $ docker build -t docker_pyas2 . && docker run -p 8000:8000 docker_pyas2


In case the files on the host file system should be used, connect the directory to the host by
running to docker run command with the -v option:

.. code-block:: console

    $ docker build -t docker_pyas2 . && docker run -p 8000:8000 -v $PWD/django_pyas2:/django_pyas2 docker_pyas2


