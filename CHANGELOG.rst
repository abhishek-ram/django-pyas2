Release History
===============

1.2.3 - 2023-02-25
------------------

* Bump version of pyas2lib to 1.4.3
* Update variables in run_post_receive to fit the meaning (#82 by @timfanda35)
* Fix link to AUTHORS since now it's a Markdown file (#85 by @adiroiban)
* Update the lengths of the payload fields to allow longer file names (#87 by @pouldenton)
* Update documentation to use django-admin instead of django-admin.py (#89 by @bkc)

1.2.2 - 2022-02-06
------------------

* Bump version of pyas2lib to 1.4.0 (PR #70 )
* Use github actions for running test pipeline instead of travis
* Add support for python 3.10 and upgrade pytest* packages
* Deprecate support for python 3.6
* Replace deprecated ugettext with gettext_lazy (PR #68 by @liquidxinc )

1.2.1 - 2021-05-08
------------------

* Bump version of pyas2lib to 1.3.3
* Use orig_message_id as Message ID for MDN if no message_id was provided
* Retry when no ASYNC MDN is received, before finally failing after retries
* Bump version of django to 2.2.18

1.2.0 - 2020-04-12
------------------

* Bump version of pyas2lib to 1.3.1
* Improve the test coverage for the repo
* Use django storage framework when dealing with the file system
* Handle cases where we get a 200 response without an MDN when sending messages
* Set login required for the download and send message endpoints

1.1.1 - 2019-06-25
------------------

* Bump version of pyas2lib to 1.2.2
* Add more logging for better debugging
* Removing X-Frame-Options header from AS2 response object


1.1.0 - 2019-06-13
------------------

* Use original filename when saving to store and allow search by filename.
* Bump version of pyas2lib to 1.2.0 to fix issue #5
* Minimum version of django is now 2.1.9 which fixes issue #8
* Extract and save certificate information on upload.

1.0.2 - 2019-05-16
------------------

* Add command `sendas2bulk` for sending messages in the outbox folders.
* Add command `manageas2server` for cleanup, async mdns and retries.

1.0.1 - 2019-05-02
------------------

* Use current date as sub-folder in message store
* Use password widget for `key_pass` field of PrivateKey
* Better rendering of headers and payload in messages
* Include templates in the distribution

1.0.0 - 2018-05-01
------------------

* Initial release.
