import json
from pathlib import Path

from pixiv.downloader.common import DEFAULT_DOWNLOAD_PATH, DEFAULT_SETTINGS_PATH


class Settings:
    _default = {"save_location": str(DEFAULT_DOWNLOAD_PATH)}

    def __init__(self, location=DEFAULT_SETTINGS_PATH):
        self._location = Path(location).expanduser()
        self._settings = self._read()
        if not self._settings:
            self._settings = self._default.copy()
            self._write()

    def _write(self):
        if not self._location.is_file():
            self._location.touch()
        with self._location.open("w") as file:
            json.dump(self._settings, file, sort_keys=True, ensure_ascii=False, indent=4)

    def _read(self):
        if not self._location.is_file():
            return {}
        with self._location.open() as file:
            content = file.read()
            if not content:
                return {}
            return json.loads(content)

    def get(self, name, default=None):
        return self.__getattr__(name) or default

    def set(self, name, value):
        self.__setattr__(name, value)

    def __getattr__(self, name):
        if name.startswith("_"):
            return super().__getattr__(name)
        return self._settings.get(name)

    def __setattr__(self, name, value):
        if name.startswith("_"):
            return super().__setattr__(name, value)
        self._settings[name] = value
        self._write()
