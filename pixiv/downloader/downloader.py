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
        'save_location': './pixiv_downloads/'
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


class PixivDownloader:
    def __init__(self):
        self.api = AppPixivAPI()
        self.running = False
        self.settings = Settings('./settings.json')
        self.next = self.main_menu

        self.logged_in = False
        login = self.settings.login
        if login:
            self.api.set_auth(login['access_token'], login['refresh_token'])
            self.api.auth()
            self.logged_in = True

    def start(self):
        if not self.logged_in:
            print('Login to Pixiv')
            self.login_menu()

        self.running = True
        while self.running:
            self.next()

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

    def login(self, username, password):
        result = self.api.login(username, password)
        self.settings.login = result.response
        self.logged_in = True

    def login_menu(self, username=None, password=None, try_again=True):
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
        answer = prompt(menu_item('logout_menu', 'confirm', 'Are you sure you want to log out?')).get('logout_menu')
        if answer:
            self.logout()

    def logout(self):
        self.api = AppPixivAPI()
        self.logged_in = False
        self.settings.login = {}

    def download_post_menu(self):
        url_or_id = prompt(menu_item('id_menu', 'input', 'Post ID:')).get('id_menu')
        if not url_or_id:
            return

        self.download_by_url_or_id(url_or_id)

    def download_by_url_or_id(self, url_or_id):
        path = urlparse(url_or_id).path

        ids = re.findall('(\\d+)', path)
        if not ids:
            print(f'Not a valid id or pixiv post url')
            return

        id = ids[0]
        post = self.api.illust_detail(id)
        if post.get('error'):
            print(f'Post with id: {id} not found')
            return

        return self.download(post.illust)

    def download(self, post):
        if not os.path.isdir(self.settings.save_location):
            os.makedirs(self.settings.save_location)

        if post.type == 'illust' and not post.meta_pages:
            downloader = self.download_illust
            type = 'Image'
        elif post.type == 'illust' and post.meta_pages:
            downloader = self.download_illust_collection
            type = 'Image Collection'
        elif post.type == 'ugoira':
            downloader = self.download_ugoira
            type = 'Video'
        else:
            print(f'At the moment "{post.type}" posts are not supported')
            return

        print(f'Downloading "{post.title}" ({post.id}) of type "{type}" from user "{post.user.name}" ({post.user.account})')
        saved_to = downloader(post)
        for path in saved_to:
            print(f'Downloaded to "{path}"')

    def download_illust(self, post):
        image_url = post.meta_single_page.get('original_image_url', post.image_urls.large)
        if '_webp' in image_url:
            extension = 'webp'
        else:
            extension = os.path.splitext(image_url)[1].lstrip('.')
        filename = self.get_filename(post, extension)

        self.api.download(image_url, path=self.settings.save_location, name=filename, replace=True)
        yield (Path(self.settings.save_location) / filename).absolute()

    def download_illust_collection(self, post):
        out_path = Path(self.settings.save_location)
        for index, image in enumerate(post.meta_pages, 1):
            image_url = image.image_urls.get('original', image.image_urls.large)

            if '_webp' in image_url:
                extension = 'webp'
            else:
                extension = os.path.splitext(image_url)[1].lstrip('.')
            filename = self.get_filename(post, extension, suffix=f'-{index:0>2}')

            self.api.download(image_url, path=str(out_path), name=filename, replace=True)
            yield (out_path / filename).absolute()

    def download_ugoira(self, post):
        ugoira_data = self.api.ugoira_metadata(post.id).ugoira_metadata
        zip_url = ugoira_data.zip_urls.get('large', ugoira_data.zip_urls.medium)

        with TemporaryDirectory() as dir:
            temp_dir = Path(dir)
            filename = '{post.id}.zip'
            self.api.download(zip_url, path=str(temp_dir), name=filename)

            frames_dir = temp_dir / 'frames'
            os.mkdir(frames_dir)

            print('Extracting downloaded images')
            self._extract_zip(temp_dir / filename, frames_dir)

            print('Generating mp4')
            video_name = self.get_filename(post, 'mp4')
            video_file = temp_dir / video_name
            self._generate_mp4_from_frames(video_file, frames_dir, ugoira_data.frames[0].delay)

            final_path = (Path(self.settings.save_location) / video_name).absolute()
            shutil.move(video_file, final_path)
            yield final_path.absolute()

    def get_filename(self, post, extension, prefix=None, suffix=None,):
        suffix = suffix or ''
        prefix = prefix or ''
        filename = f'{prefix}{post.id}-{post.title}{suffix}.{extension}'.replace(' ', '_')
        return filename

    def _extract_zip(self, zip_file, output_dir):
        with ZipFile(zip_file, 'r') as zip_file:
            zip_file.extractall(output_dir)

    def _generate_mp4_from_frames(self, output_file, frames_dir, delay):
        frames = sorted(map(lambda file: os.path.join(str(frames_dir), file), os.listdir(frames_dir)))
        frames = list(map(imread, frames))

        framerate = 1000 / delay

        height, width, layers = frames[0].shape
        video = VideoWriter(str(output_file), VideoWriter_fourcc(*'mp4v'), framerate, (width, height))

        for frame in frames:
            video.write(frame)

        destroyAllWindows()
        video.release()

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
