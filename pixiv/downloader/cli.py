import argparse
import logging
import sys
from typing import Dict
from typing import List

from PyInquirer.prompt import prompt
from pixivpy3 import PixivError

from . import PixivDownloader
from . import PixivDownloaderError
from .common import REFRESH_TOKEN_LINK, print_upwd_deprecated_warning
from .settings import Settings


def menu_item(name: str, type: str, text: str, **kwargs) -> List[Dict]:
    item = {
        "type": type,
        "name": name,
        "message": text,
    }

    item.update(kwargs)
    return [item]


class PixivDownloaderCLI:
    def __init__(self):
        self.downloader = PixivDownloader(log_level=logging.INFO, auto_login=False)
        self.logged_in = False
        self.next = self.login_menu
        self.running = False
        self.settings = Settings("~/.pixivrc")

        if self.settings.login:
            self.downloader.login(refresh_token=self.settings.login["refresh_token"])
            self.logged_in = True

    def start(self):
        if self.logged_in:
            self.next = self.main_menu

        self.running = True
        while self.running:
            self.next()

    def login_menu(self, refresh_token, try_again=True):
        self.next = self.main_menu
        refresh_token_menu = menu_item("refresh_token", "input", f"Refresh Token: ({REFRESH_TOKEN_LINK}):")

        while not self.logged_in:
            refresh_token = refresh_token or prompt(refresh_token_menu).get("refresh_token")

            try:
                self.login(refresh_token=refresh_token)
            except PixivError:
                if not try_again:
                    print("Login failed")
                    return
                answer = prompt(menu_item("continue_menu", "confirm", "Login failed, try again?")).get("continue_menu")
                if not answer:
                    break

    def logout_menu(self):
        self.next = self.main_menu
        answer = prompt(menu_item("logout_menu", "confirm", "Are you sure you want to log out?")).get("logout_menu")
        if answer:
            self.logout()

    def main_menu(self):
        self.next = self.main_menu
        menu_items = {}
        if not self.logged_in:
            menu_items["Login"] = self.login_menu

        menu_items["Download Post"] = self.download_post_menu
        menu_items["Settings"] = self.settings_menu

        if self.logged_in:
            menu_items["Logout"] = self.logout_menu

        menu_items["Exit"] = self.exit

        menu = menu_item("main_menu", "list", "What do you want to do", choices=menu_items.keys())
        answer = prompt(menu)
        method = menu_items.get(answer.get("main_menu"), self.exit)
        method()

    def download_post_menu(self):
        id = prompt(menu_item("id_menu", "input", "Post ID:")).get("id_menu")
        if not id:
            return

        try:
            downloader = self.downloader.download_by_url(id, self.settings.save_location)
        except PixivDownloaderError as e:
            print(e.msg)
            return

        print("Downloading...")
        for path in downloader:
            print(f'Downloaded to "{path}"')

    def settings_menu(self):
        self.next = self.main_menu
        menu_items = {
            f"Save Location ({self.settings.save_location})": {
                "name": "save_location",
                "text": "Where should the files be stored?",
                "type": "input",
            },
            "Back": {},
        }
        answer = prompt(
            menu_item(
                "settings_overview_menu",
                "list",
                "What do you want to change?",
                choices=menu_items,
            )
        )
        answer = answer.get("settings_overview_menu")
        settings_args = menu_items.get(answer)

        if not settings_args:
            return
        self.settings_change_menu(**settings_args)

    def settings_change_menu(self, name, text, type, **kwargs):
        self.next = self.settings_menu
        answer = prompt(menu_item("new_value_menu", type, text, **kwargs)).get("new_value_menu")
        if answer == "" or answer is None:
            return
        self.settings.set(name, answer)

    def exit(self):
        self.running = False

    def login(self, refresh_token):
        result = self.downloader.login(refresh_token=refresh_token)
        self.settings.login = result.response
        self.logged_in = True

    def logout(self):
        self.downloader.logout()
        self.logged_in = False
        self.settings.login = {}


def main():
    parser = argparse.ArgumentParser(
        usage=f"""Pixiv Downloader

PixivDownloader enables you to download artworks, mangas and videos from `pixiv.net <https://pixiv.net/>`_
via CLI, CLI UI and programmatically.


Usage
-----

To start CLI UI:

$ pixiv

To start downloads directly:

$ pixiv "XXXXXXXX" "https://www.pixiv.net/en/artworks/XXXXXXXX"

If the user is not logged in yet the CLU UI starts and asks for login credentials.
Sadly login via Username + Password is not possible anymore. And you have to perform
some additional steps to get a so called refresh_token. Here is a manual on how to get
it: {REFRESH_TOKEN_LINK}
You can also use --refresh-token XXXX to directly login without the CLI asking you to
enter it.

$ pixiv "XXXXXXXX" -r [YOUR_TOKEN]

If you want to disable the CLI UI completely and just exit if no token is given, use -q

$ pixiv "XXXXXXXX" -q

Finally, you can also use this downloader via its python interface like this:

from pixiv.downloader import PixivDownloader
pd = PixivDownloader(refresh_token='xxx')
downloader = pd.download_by_url('https://www.pixiv.net/en/artworks/74607898', '~/Downloads/pixiv-downloads')
# Or just by the id
downloader = pd.download_by_id(74607898, '~/Downloads/pixiv-downloads')
for path in downloader:
    print(f'Downloaded {{path}}')


Is my pixiv password saved?
---------------------------

TLDR: No, it is not.

For the communication between the program and Pixiv `PixivPy <https://github.com/upbit/pixivpy>`_
is used. With this after the first login, your above mentioned token is stored and you don't have
to care about it anymore.

This token, as well as other settings, are saved in ``~/.pixivrc``.
"""
    )

    parser.add_argument("-r", "--refresh-token", help="Refresh Token")
    parser.add_argument("-u", "--username", help="Pixiv username [Deprecated]")
    parser.add_argument("-p", "--password", help="Pixiv password [Deprecated]")
    parser.add_argument(
        "-q",
        "--quiet",
        help="Disable login prompt when direct download is used",
        action="store_true",
    )
    parser.add_argument("posts", nargs="*", help="URLs or post IDs of pixiv posts to download")

    args = parser.parse_args()
    app = PixivDownloaderCLI()
    if args.posts:
        if not app.logged_in:
            if args.username or args.password:
                print_upwd_deprecated_warning()
            if args.quiet and not args.refresh_token:
                sys.exit(1)
            print("Login to Pixiv")
            app.login_menu(args.refresh_token, try_again=not args.refresh_token)

            if not app.logged_in:
                sys.exit(1)

        for post in args.posts:
            for path in app.downloader.download_by_url(post, app.settings.save_location):
                print(f'Downloaded "{path}"')
    else:
        app.start()
