import logging
import os
from pathlib import Path
import re
import shutil
from tempfile import TemporaryDirectory
from urllib.parse import urlparse
from zipfile import ZipFile

from cv2 import VideoWriter
from cv2 import VideoWriter_fourcc
from cv2 import destroyAllWindows
from cv2 import imread
from pixivpy3 import AppPixivAPI
from pixivpy3.utils import PixivError

from .common import DEFAULT_DOWNLOAD_PATH, print_upwd_deprecated_warning
from .settings import Settings


class PixivDownloaderError(Exception):
    def __init__(self, msg, data=None):
        super().__init__(msg, data)
        self.msg = msg
        self.data = data


class PixivDownloader:
    def __init__(
        self,
        client=None,
        username=None,
        password=None,
        log_level=logging.WARNING,
        refresh_token=None,
        settings=None,
        default_out_dir=None,
        auto_login=True,
    ):
        self.logger = logging.getLogger("PixivDownloader")
        stdout = logging.StreamHandler()
        self.logger.addHandler(stdout)
        self.logger.setLevel(log_level)

        self.settings = settings or Settings()

        refresh_token = refresh_token or self.settings.get("login", {}).get("refresh_token")  # type: ignore
        self.default_out_dir = Path(default_out_dir or self.settings.get("save_location") or DEFAULT_DOWNLOAD_PATH)

        if username or password:
            self.logger.warning(print_upwd_deprecated_warning())

        if client:
            self.api = client
        else:
            self.api = AppPixivAPI()

        if not client and refresh_token and auto_login:
            self.login(refresh_token=refresh_token)

    def login(self, username=None, password=None, refresh_token=None):
        if refresh_token:
            self.logger.info("Loging in with refresh_token")
        elif username or password:
            warning = print_upwd_deprecated_warning()
            self.logger.warning(warning)
            raise PixivError(f"[ERROR] login() failed. {warning}")
        else:
            self.logger.info("Loging")

        return self.api.auth(refresh_token=refresh_token)

    def logout(self):
        self.logger.info("Logout")
        self.api = AppPixivAPI()

    def get_id_from_url(self, url):
        path = urlparse(url).path
        ids = re.findall("(\\d+)", path)
        if not ids:
            raise ValueError("Url does not contain post id")

        return ids[0]

    def download_by_id(self, post_id, output_dir=None):
        data = self.api.illust_detail(post_id)
        if data.get("error"):
            raise PixivDownloaderError("Could not get post info or post doesn't exist.", data)

        return self.download(data.illust, output_dir)

    def download_by_url(self, url, output_dir=None):
        return self.download_by_id(self.get_id_from_url(url), output_dir)

    def _check_output_dir(self, output_dir=None):
        output_dir = Path(output_dir or self.default_out_dir).expanduser().absolute()

        if not output_dir.is_dir():
            output_dir.mkdir(parents=True, exist_ok=True)
            self.logger.debug('Created dir "%s"', output_dir)
        return output_dir

    def download(self, post, output_dir=None):
        output_dir = self._check_output_dir(output_dir)
        if post.type == "illust" and not post.meta_pages:
            downloader = self.download_illust
            type = "Image"
        elif post.type == "illust" and post.meta_pages:
            downloader = self.download_illust_collection
            type = "Image Collection"
        elif post.type == "ugoira":
            downloader = self.download_ugoira
            type = "Video"
        elif post.type == "manga":
            downloader = self.download_manga
            type = "Manga"
        else:
            raise PixivDownloaderError(f'Post type "{post.type}" not supported')

        self.logger.info('Initialize "%s" downloader for post %s', type, post.id)
        return downloader(post, output_dir)

    def download_illust(self, post, output_dir=None):
        output_dir = self._check_output_dir(output_dir)
        image_url = post.meta_single_page.get("original_image_url", post.image_urls.large)
        if "_webp" in image_url:
            extension = "webp"
        else:
            extension = os.path.splitext(image_url)[1].lstrip(".")
        filename = self.get_filename(post, extension)

        self.logger.info('Downloading "%s"', image_url)
        self.api.download(image_url, path=output_dir, name=filename, replace=True)
        yield (Path(output_dir) / filename).absolute()

    def download_illust_collection(self, post, output_dir=None):
        output_dir = self._check_output_dir(output_dir)
        yield from self._download_meta_pages(post, output_dir)

    def download_manga(self, post, output_dir=None):
        output_dir = self._check_output_dir(output_dir)
        output_dir = Path(output_dir) / f"{post.title}-{post.user.account}"
        if not output_dir.is_dir():
            output_dir.mkdir(parents=True, exist_ok=True)
            self.logger.debug('Created dir "%s"', output_dir)

        yield from self._download_meta_pages(post, output_dir)

    def _download_meta_pages(self, post, output_dir):
        for index, image in enumerate(post.meta_pages, 1):
            image_url = image.image_urls.get("original", image.image_urls.large)

            if "_webp" in image_url:
                extension = "webp"
            else:
                extension = os.path.splitext(image_url)[1].lstrip(".")
            filename = self.get_filename(post, extension, suffix=f"-{index:0>2}")

            self.logger.info('Downloading "%s"', image_url)
            self.api.download(image_url, path=str(output_dir), name=filename, replace=True)
            yield (output_dir / filename).absolute()

    def download_ugoira(self, post, output_dir=None):
        output_dir = self._check_output_dir(output_dir)
        ugoira_data = self.api.ugoira_metadata(post.id).ugoira_metadata
        zip_url = ugoira_data.zip_urls.get("large", ugoira_data.zip_urls.medium)

        with TemporaryDirectory() as dir:
            temp_dir = Path(dir)
            filename = "{post.id}.zip"
            self.logger.info('Downloading "%s"', zip_url)
            self.api.download(zip_url, path=str(temp_dir), name=filename)

            frames_dir = temp_dir / "frames"
            os.mkdir(frames_dir)

            self._extract_zip(temp_dir / filename, frames_dir)

            video_name = self.get_filename(post, "mp4")
            video_file = temp_dir / video_name
            self._generate_mp4_from_frames(video_file, frames_dir, ugoira_data.frames[0].delay)

            final_path = (Path(output_dir) / video_name).absolute()
            shutil.move(video_file, final_path)
            yield final_path.absolute()

    def get_filename(
        self,
        post,
        extension,
        prefix=None,
        suffix=None,
    ):
        suffix = suffix or ""
        prefix = prefix or ""
        filename = f"{prefix}{post.id}-{post.title}{suffix}.{extension}".replace("/", "_").replace(" ", "_")
        return filename

    def _extract_zip(self, zip_file, output_dir):
        self.logger.info('Extract "%s"', zip_file)
        with ZipFile(zip_file, "r") as zip_file:
            zip_file.extractall(output_dir)

    def _generate_mp4_from_frames(self, output_file, frames_dir, delay):
        self.logger.info('Generate video to "%s"', output_file)
        frames = sorted(map(lambda file: os.path.join(str(frames_dir), file), os.listdir(frames_dir)))
        frames = list(map(imread, frames))

        framerate = 1000 / delay

        height, width, _ = frames[0].shape
        video = VideoWriter(str(output_file), VideoWriter_fourcc(*"mp4v"), framerate, (width, height))

        for frame in frames:
            video.write(frame)

        destroyAllWindows()
        video.release()
