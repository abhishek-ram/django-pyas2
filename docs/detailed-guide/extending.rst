Extending django-pyas2
======================
A use case for extending django-pyas2 may be to have additional connectors, from which files are
received, such as a message queue, or to run a directory monitor as a daemon to send messages as
soon as a message has been written to an outbound directory (see directory structure), or to add
additional functionalities, like a custom website to the root of the url etc.

One way to extend ``django-pyas2`` is to use the django startapp command, that will create the
directory structure needed for an app. In this example we call the app "extend_pyas2".

Please consult the extensive django documentation to learn more about these command. Below simply
a description for your convenience to get started:

In the django_pyas2 project directory invoke the script as follows:

.. code-block:: console

    $ python manage.py startapp extend_pyas2


This has now created a new directory containing files that may be used for apps:

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
        └── extend_pyas2
            ├── apps.py
            ├── migrations
            ├── models.py
            ├── tests.py
            └── views.py

In our example, we will add a new admin command that should monitor directories and trigger
the sending of files to partners when they are written. For that purpose, we need to create
some subfolders "management/commands" and a python file with the management command:

.. code-block:: console

        │       └── wsgi.py
        └── extend_pyas2
            ├── apps.py
            ├── migrations
            ├── models.py
            ├── tests.py
            ├── views.py
            └── management
                └── commands
                    └── filewatcher.py

Add ``extend_pyas2`` to your ``INSTALLED_APPS`` settings, after ``pyas2``.

.. code-block:: python

    INSTALLED_APPS = (
        ...
        'pyas2',
        'extend_pyas2',
    )


An example content for the filewatcher.py may be as follows and can be run with Django's manage
command:

.. code-block:: console

    $ python manage.py filewatcher


.. code-block:: python

    from django.core.management.base import BaseCommand, CommandError
    from django.core.management import call_command
    from django.utils.translation import ugettext as _
    from pyas2.models import Organization
    from pyas2.models import Partner
    from pyas2 import settings
    from watchdog.observers import Observer
    from watchdog.observers.polling import PollingObserverVFS
    from watchdog.events import PatternMatchingEventHandler
    import time
    import atexit
    import socket
    import os
    import sys
    import logging

    logger = logging.getLogger('django')

    DAEMONPORT = 16388


    class FileWatchHandle(PatternMatchingEventHandler):
        """
        FileWatchHandler that ignores directories. No Patterns defined by default. Any file in the
        directory will be sent.
        """
        def __init__(self, tasks, dir_watch):
            super(FileWatchHandle, self).__init__(ignore_directories=True)
            self.tasks = tasks
            self.dir_watch = dir_watch

        def handle_event(self, event):
            self.tasks.add(
                (self.dir_watch['organization'], self.dir_watch['partner'], event.src_path))
            logger.info(u' "%(file)s" created. Adding to Task Queue.', {'file': event.src_path})

        def on_modified(self, event):
            self.handle_event(event)

        def on_created(self, event):
            self.handle_event(event)


    class WatchdogObserversManager:
        """
        Creates and manages a list of watchdog observers as daemons. All daemons will have the same
        settings. By default, subdirectories are not searched.
        :param: force_vfs : if the underlying filesystem is a network share, OS events cannot be
                            used reliably. Polling to be done, which is expensive.
        """
        def __init__(self, is_daemon=True, force_vfs=False):
            self.observers = []
            self.is_daemon = is_daemon
            self.force_vfs = force_vfs

        def add_observer(self, tasks, dir_watch):
            if self.force_vfs:
                new_observer = PollingObserverVFS(stat=os.stat, listdir=os.listdir)
            else:
                new_observer = Observer()
            new_observer.daemon = self.is_daemon
            new_observer.schedule(FileWatchHandle(tasks, dir_watch),
                                  dir_watch['path'], recursive=False)
            new_observer.start()
            self.observers.append(new_observer)

        def stop_all(self):
            for observer in self.observers:
                observer.stop()

        def join_all(self):
            for observer in self.observers:
                observer.join()


    class Command(BaseCommand):
        help = _(u'Daemon process that watches the outbox of all as2 partners and '
                 u'triggers sendmessage when files become available')

        def handle(self, *args, **options):
            logger.info(_(u'Starting PYAS2 send Watchdog daemon.'))
            engine_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                engine_socket.bind(('127.0.0.1', DAEMONPORT))
            except socket.error:
                engine_socket.close()
                raise CommandError(_(u'An instance of the send daemon is already running'))
            else:
                atexit.register(engine_socket.close)

            tasks = set()
            dir_watch_data = []

            for partner in Partner.objects.all():
                for org in Organization.objects.all():
                    outboxDir  = os.path.join(settings.DATA_DIR,
                                          'messages',
                                          partner.as2_name,
                                          'outbox',
                                          org.as2_name)
                    if os.path.isdir(outboxDir):
                        dir_watch_data.append({})
                        dir_watch_data[-1]['path'] = outboxDir
                        dir_watch_data[-1]['organization'] = org.as2_name
                        dir_watch_data[-1]['partner'] = partner.as2_name

            if not dir_watch_data:
                logger.error(_(u'No partners have been configured!'))
                sys.exit(0)

            logger.info(_(u'Process existing files in the directory.'))
            for dir_watch in dir_watch_data:
                files = [f for f in os.listdir(dir_watch['path']) if
                         os.path.isfile(os.path.join(dir_watch['path'], f))]
                for file in files:
                    logger.info(u'Send as2 message "%(file)s" from "%(org)s" to "%(partner)s".',
                                {'file': file,
                                 'org': dir_watch['organization'],
                                 'partner': dir_watch['partner']})

                    call_command('sendas2message', dir_watch['organization'], dir_watch['partner'],
                                 os.path.join(dir_watch['path'], file), delete=True)

            """Add WatchDog Thread Here"""
            logger.info(_(u'PYAS2 send Watchdog daemon started.'))
            active_receiving = False
            watchdog_file_observers = WatchdogObserversManager(is_daemon=True, force_vfs=True)
            for dir_watch in dir_watch_data:
                watchdog_file_observers.add_observer(tasks, dir_watch)
            try:
                logger.info(_(u'Watchdog awaiting tasks...'))
                while True:
                    if tasks:
                        if not active_receiving:
                            # first request (after tasks have been fired, or startup of dirmonitor)
                            active_receiving = True
                        else:  # active receiving events
                            for task in tasks:
                                logger.info(
                                    u'Send as2 message "%(file)s" from "%(org)s" to "%(partner)s".',
                                    {'file': task[2],
                                     'org': task[0],
                                     'partner': task[1]})

                                call_command('sendas2message', task[0], task[1], task[2],
                                             delete=True)
                            tasks.clear()
                            active_receiving = False
                    time.sleep(2)

            except (Exception, KeyboardInterrupt) as msg:
                logger.info(u'Error in running task: "%(msg)s".', {'msg': msg})
                logger.info(u'Stopping all running Watchdog threads...')
                watchdog_file_observers.stop_all()
                logger.info(u'All Watchdog threads stopped.')

            logger.info(u'Waiting for all Watchdog threads to finish...')
            watchdog_file_observers.join_all()
            logger.info(u'All Watchdog threads finished. Exiting...')
            sys.exit(0)

