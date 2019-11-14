from PyInquirer import prompt
from pathlib import Path
from pixivpy3 import AppPixivAPI
from pixivpy3 import PixivError
from typing import Dict
from typing import List
from urllib.parse import urlparse
import json
import os
import re


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
        'save_location': './pixiv/'
    }

    def __init__(self, location):
        self._location = Path(location)
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

    def __getattr__(self, name):
        if name.startswith('_'):
            return super().__getattr__(name)
        return self._settings.get(name)

    def __setattr__(self, name, value):
        if name.startswith('_'):
            return super().__setattr__(name, value)
        self._settings[name] = value
        self._write()


class App:
    def __init__(self):
        self.api = AppPixivAPI()
        self.running = False
        self.settings = Settings('./settings.json')

        self.logged_in = False
        login = self.settings.login
        if login:
            self.api.set_auth(login['access_token'], login['refresh_token'])
            self.logged_in = True

    def start(self):
        self.running = True
        while self.running:
            self.main_menu()

    def main_menu(self):
        menu_items = {}
        if not self.logged_in:
            menu_items['Login'] = self.login_menu

        menu_items['Get Media'] = self.get_media_menu
        menu_items['Settings'] = self.settings_menu

        if self.logged_in:
            menu_items['Logout'] = self.logout_menu

        menu_items['Exit'] = self.exit

        menu = menu_item('main_menu', 'list', 'What do you want to do', choices=menu_items.keys())
        answer = prompt(menu)
        method = menu_items.get(answer.get('main_menu'), self.exit)
        method()

    def login_menu(self):
        username_menu = menu_item('username', 'input', 'Username:')
        password_menu = menu_item('password', 'password', 'Password:')

        while not self.logged_in:
            username = prompt(username_menu).get('username')
            password = prompt(password_menu).get('password')

            try:
                result = self.api.login(username, password)
                self.settings.login = result.response
                self.logged_in = True
            except PixivError:
                answer = prompt(menu_item('continue_menu', 'confirm', 'Login failed, try again?')).get('continue_menu')
                if not answer:
                    break

    def logout_menu(self):
        answer = prompt(menu_item('logout_menu', 'confirm', 'Are you sure you want to log out?')).get('logout_menu')
        if answer:
            self.logout()

    def logout(self):
        self.api = AppPixivAPI()
        self.logged_in = False
        self.settings.login = {}

    def get_media_menu(self):
        url_or_id = prompt(menu_item('id_menu', 'input', 'Post ID')).get('id_menu')
        path = urlparse(url_or_id).path

        ids = re.findall('(\\d+)', path)
        if not ids:
            print(f'Not a valid id or pixiv post url')
            return

        id = ids[0]
        try:
            post = self.api.illust_detail(id)
            self.download(post.illust)
        except PixivError:
            print(f'Post with id: {id} not found')

    def download(self, post):
        if not os.path.isdir(self.settings.save_location):
            os.makedirs(self.settings.save_location)
        if post.type == 'illust':
            self.download_illust(post)
        elif post.type == 'ugoira':
            self.download_ugoira(post)

    def download_illust(self, post):
        image_url = post.meta_single_page.get('original_image_url', post.image_urls.large)
        extension = os.path.splitext(image_url)[1]
        filename = f'{post.id}_{post.title}{extension}'.replace(' ', '_')
        print(f'Downloading "{post.title}" ({post.id}) from "{post.user.name}" ({post.user.account})')

        self.api.download(image_url, path=self.settings.save_location, name=filename, replace=True)
        full_path = (Path(self.settings.save_location) / filename).absolute()
        print(f'Downloaded to "{full_path}"')

    def download_ugoira(self, post):
        pass

    def settings_menu(self):
        pass

    def exit(self):
        self.running = False


if __name__ == '__main__':
    app = App()
    app.start()
