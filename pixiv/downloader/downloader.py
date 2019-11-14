from cv2 import VideoWriter
from cv2 import VideoWriter_fourcc
from cv2 import destroyAllWindows
from cv2 import imread
from pathlib import Path
from pixivpy3 import AppPixivAPI
from tempfile import TemporaryDirectory
from urllib.parse import urlparse
from zipfile import ZipFile
import os
import re
import shutil


class PixivDownloaderError(Exception):
    def __init__(self, msg, data=None):
        super().__init__(msg, data)
        self.msg = msg
        self.data = data


class PixivDownloader:
    def __init__(self, client=None, username=None, password=None):
        if not client and (bool(username) != bool(password)):
            raise AttributeError('If no client is given both username and password must be given')

        if client:
            self.api = client
        else:
            self.api = AppPixivAPI()

        if not client and username and password:
            self.api.login(username, password)

    def login(self, username=None, password=None, refresh_token=None):
        return self.api.auth(username=username, password=password, refresh_token=refresh_token)

    def logout(self):
        self.api = AppPixivAPI()

    def get_id_from_url(self, url):
        path = urlparse(url).path
        ids = re.findall('(\\d+)', path)
        if not ids:
            raise ValueError('Url does not contain post id')

        return ids[0]

    def download_by_id(self, post_id, output_dir):
        data = self.api.illust_detail(post_id)
        if data.get('error'):
            raise PixivDownloaderError('Could not get post info or post doesn\'t exist.', data)

        return self.download(data.illust, output_dir)

    def download_by_url(self, url, output_dir):
        return self.download_by_id(self.get_id_from_url(url), output_dir)

    def download(self, post, output_dir):
        if not os.path.isdir(output_dir):
            os.makedirs(output_dir)

        if post.type == 'illust' and not post.meta_pages:
            downloader = self.download_illust
        elif post.type == 'illust' and post.meta_pages:
            downloader = self.download_illust_collection
        elif post.type == 'ugoira':
            downloader = self.download_ugoira
        elif post.type == 'manga':
            downloader = self.download_manga
        else:
            raise PixivDownloaderError(f'Post type "{post.type}" not supported')

        return downloader(post, output_dir)

    def download_illust(self, post, output_dir):
        image_url = post.meta_single_page.get('original_image_url', post.image_urls.large)
        if '_webp' in image_url:
            extension = 'webp'
        else:
            extension = os.path.splitext(image_url)[1].lstrip('.')
        filename = self.get_filename(post, extension)

        self.api.download(image_url, path=output_dir, name=filename, replace=True)
        yield (Path(output_dir) / filename).absolute()

    def download_illust_collection(self, post, output_dir):
        out_path = Path(output_dir)
        yield from self._downloade_meta_pages(post, output_dir)

    def download_manga(self, post, output_dir):
        output_dir = Path(output_dir) / f'{post.title}-{post.user.account}'
        if not output_dir.is_dir():
            output_dir.mkdir(parents=True, exist_ok=True)

        yield from self._downloade_meta_pages(post, output_dir)

    def _downloade_meta_pages(self, post, output_dir):
        for index, image in enumerate(post.meta_pages, 1):
            image_url = image.image_urls.get('original', image.image_urls.large)

            if '_webp' in image_url:
                extension = 'webp'
            else:
                extension = os.path.splitext(image_url)[1].lstrip('.')
            filename = self.get_filename(post, extension, suffix=f'-{index:0>2}')

            self.api.download(image_url, path=str(output_dir), name=filename, replace=True)
            yield (output_dir / filename).absolute()

    def download_ugoira(self, post, output_dir):
        ugoira_data = self.api.ugoira_metadata(post.id).ugoira_metadata
        zip_url = ugoira_data.zip_urls.get('large', ugoira_data.zip_urls.medium)

        with TemporaryDirectory() as dir:
            temp_dir = Path(dir)
            filename = '{post.id}.zip'
            self.api.download(zip_url, path=str(temp_dir), name=filename)

            frames_dir = temp_dir / 'frames'
            os.mkdir(frames_dir)

            self._extract_zip(temp_dir / filename, frames_dir)

            video_name = self.get_filename(post, 'mp4')
            video_file = temp_dir / video_name
            self._generate_mp4_from_frames(video_file, frames_dir, ugoira_data.frames[0].delay)

            final_path = (Path(output_dir) / video_name).absolute()
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
