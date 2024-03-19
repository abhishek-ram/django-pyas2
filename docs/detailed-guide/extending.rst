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

    import atexit
    import logging
    import os
    import socket
    import sys
    import time
    from cachetools import TTLCache
    from django.core.management import call_command
    from django.core.management.base import BaseCommand, CommandError
    from django.db import close_old_connections
    from django.utils.translation import gettext as _
    from pyas2 import settings
    from pyas2.models import Organization, Partner
    from watchdog.events import PatternMatchingEventHandler
    from watchdog.observers import Observer
    from watchdog.observers.polling import PollingObserverVFS

    logger = logging.getLogger("filewatcher")

    DAEMONPORT = 16388
    PAUSED = False
    CACHE = TTLCache(maxsize=2048, ttl=1200)


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
            global PAUSED

            if PAUSED:
                return
            else:
                self.tasks.add(
                    (
                        self.dir_watch["organization"],
                        self.dir_watch["partner"],
                        event.src_path,
                    )
                )
                logger.info(f' "{event.src_path}" created. Adding to Task Queue.')

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
                new_observer = PollingObserverVFS(stat=os.stat, listdir=os.scandir)
            else:
                new_observer = Observer()
            new_observer.daemon = self.is_daemon
            new_observer.schedule(
                FileWatchHandle(tasks, dir_watch), dir_watch["path"], recursive=False
            )
            new_observer.start()
            self.observers.append(new_observer)

        def stop_all(self):
            for observer in self.observers:
                observer.stop()

        def join_all(self):
            for observer in self.observers:
                observer.join()


    class Command(BaseCommand):
        help = _(
            "Daemon process that watches the outbox of all as2 partners and "
            "triggers sendmessage when files become available"
        )

        @staticmethod
        def send_message(organization, partner, filepath):
            global CACHE
            max_attempts = 1
            attempt = 1

            if filepath in CACHE:
                logger.info(f' "{filepath}" already in cache, skipping.')
                return
            else:
                CACHE.__setitem__(key=filepath, value=None)

            filesize_probe_counter = 1
            filesize_probe_max = 10

            while filesize_probe_counter <= filesize_probe_max:
                if os.path.getsize(filepath) > 10:
                    # give os time to finish writing if not done already
                    time.sleep(1)
                    break

                if filesize_probe_counter >= filesize_probe_max:
                    logger.info(
                        _(
                            f"Max attempts reached {filesize_probe_max}, giving up. "
                            f"Filesize stayed below 10 bytes for {filepath}. Leave it for bulk cleanup to handle."
                        )
                    )
                    CACHE.__delitem__(key=filepath)
                    return
                else:
                    time.sleep(1)

                filesize_probe_counter += 1

            while attempt <= max_attempts:
                try:
                    call_command(
                        "sendas2message", organization, partner, filepath, delete=True
                    )
                    if attempt > 1:
                        logger.info(_(f"Successfully retried on attempt {attempt}"))
                    break

                # Attention: Retrying should only be considered when neither the retry of the AS2 server, nor the
                # cleanup job would be picking up the file (as an AS2 message ID was already created and it might cause
                # duplicate submission or wrong async responses). The cases where a retry should be done from here
                # are currently not clear/known.
                except Exception as e:
                    if attempt >= max_attempts:
                        logger.info(
                            _(
                                f"Max attempts reached {max_attempts}, giving up. "
                                f"Exception detail: {e}"
                            )
                        )
                        close_old_connections()
                    else:
                        logger.info(
                            _(
                                f"Hit exception on attempt {attempt}/{max_attempts}. "
                                f"Retrying in 5 seconds. Exception detail: {e}"
                            )
                        )
                        # https://developpaper.com/django-database-connection-loss-problem/
                        close_old_connections()
                        time.sleep(5)
                attempt += 1

        def clean_out(self, dir_watch_data):
            global PAUSED
            PAUSED = True

            for dir_watch in dir_watch_data:
                files = [
                    f
                    for f in os.listdir(dir_watch["path"])
                    if os.path.isfile(os.path.join(dir_watch["path"], f))
                ]
                for file in files:
                    logger.info(
                        f"Send as2 message '{file}' "
                        f"from '{dir_watch['organization']}' "
                        f"to '{dir_watch['partner']}'"
                    )

                    self.send_message(
                        dir_watch["organization"],
                        dir_watch["partner"],
                        os.path.join(dir_watch["path"], file),
                    )

            PAUSED = False

        def handle(self, *args, **options):
            logger.info(_("Starting PYAS2 send Watchdog daemon."))
            engine_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                engine_socket.bind(("127.0.0.1", DAEMONPORT))
            except socket.error:
                engine_socket.close()
                raise CommandError(_("An instance of the send daemon is already running"))
            else:
                atexit.register(engine_socket.close)

            tasks = set()

            # initialize the list containing the outbox directories
            dir_watch_data = []

            # build the paths for partners and organization and attach them to dir_watch_data
            for partner in Partner.objects.all():
                for org in Organization.objects.all():

                    outbox_folder = os.path.join(
                        settings.DATA_DIR,
                        "messages",
                        partner.as2_name,
                        "outbox",
                        org.as2_name,
                    )
                    if not os.path.isdir(outbox_folder):
                        os.makedirs(outbox_folder)

                    dir_watch_data.append(
                        {
                            "path": outbox_folder,
                            "organization": org.as2_name,
                            "partner": partner.as2_name,
                        }
                    )

            if not dir_watch_data:
                logger.error(_("No partners have been configured!"))
                sys.exit(0)

            logger.info(_("Process existing files in the directory."))

            # process any leftover files in the directories

            self.clean_out(dir_watch_data)

            """Add WatchDog Thread Here"""
            logger.info(_(f"PYAS2 send Watchdog daemon started."))
            watchdog_file_observers = WatchdogObserversManager(
                is_daemon=True, force_vfs=True
            )
            for dir_watch in dir_watch_data:
                watchdog_file_observers.add_observer(tasks, dir_watch)
            try:
                logger.info(_("Watchdog awaiting tasks..."))
                start_time = time.time()
                last_clean_time = time.time()
                while True:
                    if tasks:
                        task = tasks.pop()
                        logger.info(
                            f"Send as2 message '{task[2]}' "
                            f"from '{task[0]}' "
                            f"to '{task[1]}'"
                        )

                        self.send_message(task[0], task[1], task[2])

                    if (
                        time.time() - start_time > 86400
                    ):  # 24 hours * 60 minutes * 60 seconds
                        logger.info("Time out - 24 hours are through")
                        raise KeyboardInterrupt

                    time.sleep(2)

                    if time.time() - last_clean_time > 600:  # every 10 minutes
                        logger.info("Clean up start.")
                        self.clean_out(dir_watch_data)
                        last_clean_time = time.time()
                        logger.info("Clean up done.")

            except (Exception, KeyboardInterrupt) as msg:
                logger.info(f'Error in running task: "{msg}".')
                logger.info("Stopping all running Watchdog threads...")
                watchdog_file_observers.stop_all()
                logger.info("All Watchdog threads stopped.")

            logger.info("Waiting for all Watchdog threads to finish...")
            watchdog_file_observers.join_all()
            logger.info("All Watchdog threads finished. Exiting...")
            sys.exit(0)

