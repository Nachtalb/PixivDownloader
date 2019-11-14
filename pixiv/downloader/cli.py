from . import PixivDownloader
from . import PixivDownloaderError
from PyInquirer import prompt
from pathlib import Path
from pixivpy3 import PixivError
from typing import Dict
from typing import List
import argparse
import json
import logging
import sys


def menu_item(name: str, type: str, text: str, **kwargs) -> List[Dict]:
    item = {
        'type': type,
        'name': name,
        'message': text,
    }

    item.update(kwargs)
    return [item]


class Settings:
    _default = {
        'save_location': './pixiv_downloads/'
    }

    def __init__(self, location):
        self._location = Path(location).expanduser()
        self._settings = self._read()
        if not self._settings:
            self._settings = self._default.copy()
            self._write()

    def _write(self):
        if not self._location.is_file():
            self._location.touch()
        with self._location.open('w') as file:
            json.dump(self._settings, file, sort_keys=True, ensure_ascii=False, indent=4)

    def _read(self):
        if not self._location.is_file():
            return {}
        with self._location.open() as file:
            content = file.read()
            if not content:
                return {}
            return json.loads(content)

    def get(self, name):
        self.__getattr__(name)

    def set(self, name, value):
        self.__setattr__(name, value)

    def __getattr__(self, name):
        if name.startswith('_'):
            return super().__getattr__(name)
        return self._settings.get(name)

    def __setattr__(self, name, value):
        if name.startswith('_'):
            return super().__setattr__(name, value)
        self._settings[name] = value
        self._write()


class PixivDownloaderCLI:
    def __init__(self):
        self.downloader = PixivDownloader(log_level=logging.INFO)
        self.logged_in = False
        self.next = self.login_menu
        self.running = False
        self.settings = Settings('~/.pixivrc')

        login = self.settings.login
        if login:
            self.downloader.login(refresh_token=login['refresh_token'])
            self.logged_in = True

    def start(self):
        if self.logged_in:
            print('Login to Pixiv')
            self.next = self.main_menu

        self.running = True
        while self.running:
            self.next()

    def login_menu(self, username=None, password=None, try_again=True):
        self.next = self.main_menu
        username_menu = menu_item('username', 'input', 'Username:')
        password_menu = menu_item('password', 'password', 'Password:')

        while not self.logged_in:
            username = username or prompt(username_menu).get('username')
            password = password or prompt(password_menu).get('password')

            try:
                self.login(username, password)
            except PixivError:
                if not try_again:
                    print('Login failed')
                    return
                answer = prompt(menu_item('continue_menu', 'confirm', 'Login failed, try again?')).get('continue_menu')
                if not answer:
                    break

    def logout_menu(self):
        self.next = self.main_menu
        answer = prompt(menu_item('logout_menu', 'confirm', 'Are you sure you want to log out?')).get('logout_menu')
        if answer:
            self.logout()

    def main_menu(self):
        self.next = self.main_menu
        menu_items = {}
        if not self.logged_in:
            menu_items['Login'] = self.login_menu

        menu_items['Download Post'] = self.download_post_menu
        menu_items['Settings'] = self.settings_menu

        if self.logged_in:
            menu_items['Logout'] = self.logout_menu

        menu_items['Exit'] = self.exit

        menu = menu_item('main_menu', 'list', 'What do you want to do', choices=menu_items.keys())
        answer = prompt(menu)
        method = menu_items.get(answer.get('main_menu'), self.exit)
        method()

    def download_post_menu(self):
        id = prompt(menu_item('id_menu', 'input', 'Post ID:')).get('id_menu')
        if not id:
            return

        try:
            downloader = self.downloader.download_by_url(id, self.settings.save_location)
        except PixivDownloaderError as e:
            print(e.msg)
            return

        print('Downloading...')
        for path in downloader:
            print(f'Downloaded to "{path}"')

    def settings_menu(self):
        self.next = self.main_menu
        menu_items = {
            f'Save Location ({self.settings.save_location})': {
                'name': 'save_location',
                'text': 'Where should the files be stored?',
                'type': 'input',
            },
            'Back': {},
        }
        answer = prompt(menu_item('settings_overview_menu', 'list', 'What do you want to change?', choices=menu_items))
        answer = answer.get('settings_overview_menu')
        settings_args = menu_items.get(answer)

        if not settings_args:
            return
        self.settings_change_menu(**settings_args)

    def settings_change_menu(self, name, text, type, **kwargs):
        self.next = self.settings_menu
        answer = prompt(menu_item('new_value_menu', type, text, **kwargs)).get('new_value_menu')
        if answer == '' or answer is None:
            return
        self.settings.set(name, answer)

    def exit(self):
        self.running = False

    def login(self, username, password):
        result = self.downloader.login(username, password)
        self.settings.login = result.response
        self.logged_in = True

    def logout(self):
        self.downloader.logout()
        self.logged_in = False
        self.settings.login = {}


def main():
    parser = argparse.ArgumentParser(usage="""Pixiv Downloader

PixivDownloader enables you to download artworks, mangas and videos from `pixiv.net <https://pixiv.net/>`_
via CLI, CLI UI and programmatically.


Usage
-----

To start CLI UI:

$ pixiv

To start downloads directly:

$ pixiv "XXXXXXXX" "https://www.pixiv.net/en/artworks/XXXXXXXX"

If the user is not logged in yet the CLU UI starts and asks for login credentials.
This can be disabled with using --username and --password to log in. If only one
of those is given then the Login CLI UI will be started asking for the missing value. So
eg. in this case the UI will start and ask for a password:

$ pixiv "XXXXXXXX" -u my_user

If you want to disable the CLI UI completely and just exit if no username and
passwords are given then use -q.

$ pixiv "XXXXXXXX" -q

Finally, you can also use this downloader via its python interface like this:

from pixiv.downloader import PixivDownloader
pd = PixivDownloader(username='xxx', password='pwd')
downloader = pd.download_by_url('https://www.pixiv.net/en/artworks/74607898', '~/Downloads/pixiv-downloads')
# Or just by the id
downloader = pd.download_by_id(74607898, '~/Downloads/pixiv-downloads')
for path in downloader:
    print(f'Downloaded {path}')


Is my pixiv password saved?
---------------------------

TLDR: No, it is not.

For the communication between the program and Pixiv `PixivPy <https://github.com/upbit/pixivpy>`_
is used. This enables us to use a so-called "refresh token" with which we can
re-authenticate without saving the password anywhere.

This token, as well as other settings, are saved in ``~/.pixivrc``.
""")

    parser.add_argument('-u', '--username', help='Pixiv username')
    parser.add_argument('-p', '--password', help='Pixiv password')
    parser.add_argument('-q', '--quiet', help='Disable login prompt when direct download is used',
                        action='store_true')
    parser.add_argument('posts', nargs='*', help='URLs or post IDs of pixiv posts to download')

    args = parser.parse_args()
    app = PixivDownloaderCLI()
    if args.posts:
        if not app.logged_in:
            if args.quiet and (not args.username or args.password):
                sys.exit(1)
            print('Login to Pixiv')
            app.login_menu(args.username, args.password, try_again=not (args.password and args.username))

            if not app.logged_in:
                sys.exit(1)

        for post in args.posts:
            for path in app.downloader.download_by_url(post, app.settings.save_location):
                print(f'Downloaded "{path}"')
    else:
        app.start()
