Release History
===============

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
