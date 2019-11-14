===============
PixivDownloader
===============

PixivDownloader enables you to download artworks, mangas and videos from `pixiv.net <https://pixiv.net/>`_
via CLI, CLI UI and programmatically.

.. contents:: Table of Contents


Usage
=====

To start CLI UI:

.. code-block:: bash

    pixiv

To start downloads directly:

.. code-block:: bash

    pixiv "XXXXXXXX" "https://www.pixiv.net/en/artworks/XXXXXXXX"

If the user is not logged in yet the CLU UI starts and asks for login credentials.
This can be disabled with using --username and --password to log in. If only one
of those is given then the Login CLI UI will be started asking for the missing value. So
eg. in this case the UI will start and ask for a password:

.. code-block:: bash

    pixiv "XXXXXXXX" -u my_user

If you want to disable the CLI UI completely and just exit if no username and
passwords are given then use -q.

.. code-block:: bash

    pixiv "XXXXXXXX" -q

Finally, you can also use this downloader via its python interface like this:

.. code-block:: python

    from pixiv.downloader import PixivDownloader
    pd = PixivDownloader(username='xxx', password='pwd')
    downloader = pd.download_by_url('https://www.pixiv.net/en/artworks/74607898', '~/Downloads/pixiv-downloads')
    # Or just by the id
    downloader = pd.download_by_id(74607898, '~/Downloads/pixiv-downloads')
    for path in downloader:
        print(f'Downloaded {path}')


Is my pixiv password saved?
===========================

TLDR: No, it is not.

For the communication between the program and Pixiv `PixivPy <https://github.com/upbit/pixivpy>`_
is used. This enables us to use a so-called "refresh token" with which we can
re-authenticate without saving the password anywhere.

This token, as well as other settings, are saved in ``~/.pixivrc``.


Installation
============

With pip:

.. code-block:: bash

    pip install pixivdownloader
    pixiv

From source:

.. code-block:: bash

    git clone https://github.com/Nachtalb/PixivDownloader.git
    cd PixivDownloader
    python setup.py install
    pixiv


Links
=====

- Github: https://github.com/Nachtalb/PixivDownloader
- Issues: https://github.com/Nachtalb/PixivDownloader/issues


Thirdparty packages used:

- Pixiv API: https://github.com/upbit/pixivpy
- CLI UI library: https://github.com/CITGuru/PyInquirer
- Video library: https://github.com/skvark/opencv-python


Copyright
=========

This package is copyrighted by `Nachtalb <https://github.com/Nachtalb/>`_.

`PixivDownloader <https://github.com/Nachtalb/PixivDownloader>`_ is licensed under GNU General Public License, version 3.
Terms
