from PyInquirer import prompt
from cv2 import VideoWriter
from cv2 import VideoWriter_fourcc
from cv2 import destroyAllWindows
from cv2 import imread
from pathlib import Path
from pixivpy3 import AppPixivAPI
from pixivpy3 import PixivError
from tempfile import TemporaryDirectory
from typing import Dict
from typing import List
from urllib.parse import urlparse
from zipfile import ZipFile
import json
import os
import re
import shutil


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
        else:
            print(f'At the moment "{post.type}" posts are not supported')

    def download_illust(self, post):
        image_url = post.meta_single_page.get('original_image_url', post.image_urls.large)
        extension = os.path.splitext(image_url)[1]
        filename = f'{post.id}_{post.title}{extension}'.replace(' ', '_')
        print(f'Downloading "{post.title}" ({post.id}) from "{post.user.name}" ({post.user.account})')

        self.api.download(image_url, path=self.settings.save_location, name=filename, replace=True)
        full_path = (Path(self.settings.save_location) / filename).absolute()
        print(f'Downloaded to "{full_path}"')

    def download_ugoira(self, post):
        ugoira_data = self.api.ugoira_metadata(post.id).ugoira_metadata
        zip_url = ugoira_data.zip_urls.get('large', ugoira_data.zip_urls.medium)

        with TemporaryDirectory() as dir:
            temp_dir = Path(dir)
            filename = '{post.id}.zip'
            print(f'Downloading "{post.title}" ({post.id}) from "{post.user.name}" ({post.user.account})')
            self.api.download(zip_url, path=str(temp_dir), name=filename)

            frames_dir = temp_dir / 'frames'
            os.mkdir(frames_dir)

            print('Extracting downloaded images')
            with ZipFile(temp_dir / filename, 'r') as zip_file:
                zip_file.extractall(frames_dir)

            print('Generating mp4')
            video_name = f'{post.id}_{post.title}.mp4'.replace(' ', '_')
            video_file = temp_dir / video_name

            frames = sorted(map(lambda file: frames_dir / file, os.listdir(frames_dir)))
            frames = list(map(imread, map(str, frames)))

            framerate = 1000 / ugoira_data.frames[0].delay

            height, width, layers = frames[0].shape
            video = VideoWriter(str(video_file), VideoWriter_fourcc(*'mp4v'), framerate, (width, height))

            for frame in frames:
                video.write(frame)

            destroyAllWindows()
            video.release()

            final_path = (Path(self.settings.save_location) / video_name).absolute()
            shutil.move(video_file, final_path)
        print(f'Downloaded to "{final_path}"')

    def settings_menu(self):
        pass

    def exit(self):
        self.running = False


if __name__ == '__main__':
    app = App()
    app.start()
