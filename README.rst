===============
PixivDownloader
===============

A small script that helps you download artwork from `pixiv.net <https://pixiv.net/>`_

Usage
-----

To start CLI UI:

.. code-block:: bash

    python app.py

To start downloads directly:

.. code-block:: bash

    python app.py "XXXXXXXX" "https://www.pixiv.net/en/artworks/XXXXXXXX"

If the user is not logged in yet the CLU UI starts and asks for login credentials.
This can be disabled with useing --username and --password to log in. If only one
of those is given then the Login CLI UI will be started asking for the missing value. So
eg. in this case the UI will start and ask for a password:

.. code-block:: bash

    pytohn app.py "XXXXXXXX" -u my_user

If you want to disable the CLI UI completly and just exit if no username and
passords are given then use -q.

.. code-block:: bash

    python app.py "XXXXXXXX" -q


Installation
------------

.. code-block:: bash

    pip install -r requirements.txt
    python app.py
