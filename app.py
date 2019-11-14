from PyInquirer import prompt
from pathlib import Path
from pixivpy3 import AppPixivAPI
from typing import Dict
from typing import List
import json
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
        self.username = ''

    @property
    def logged_in(self):
        return bool(self.username)

    def main_menu(self):
        menu_items = {}
        if not self.logged_in:
            menu_items['Login'] = self.login_menu
        else:
            menu_items['Logout'] = self.logout_menu

        menu_items['Get Media'] = self.get_media_menu
        menu_items['Settings'] = self.settings_menu
        menu_items['Exit'] = self.exit

        menu = menu_item('main_menu', 'list', 'What do you want to do', choices=menu_items.keys())
        answer = prompt(menu)
        method = menu_items.get(answer.get('main_menu'), self.exit)
        method()

    def login_menu(self):
        pass

    def logout_menu(self):
        pass

    def get_media_menu(self):
        pass

    def settings_menu(self):
        pass

    def exit(self):
        self.running = False
        sys.exit()


if __name__ == '__main__':
    app = App()
    app.main_menu()
