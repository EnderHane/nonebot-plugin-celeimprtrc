import os
from pathlib import Path
import json
from threading import Lock

from .common import plugin_root

data_dir_path = plugin_root / 'data'
satori_data_path = data_dir_path / 'satori.json'


class ListeningData:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        if not self.path.exists():
            self.path.touch()
        if not self.path.read_text():
            self.path.write_text(json.dumps({}))
        self.lock = Lock()

    def __setitem__(self, key, value):
        with self.lock:
            d = json.loads(self.path.read_text())
            d[key] = value
            self.path.write_text(json.dumps(d))

    def __getitem__(self, key: str) -> list[dict[str, str]] | None:
        with self.lock:
            d = json.loads(self.path.read_text())
            return d.get(key)

    def __delitem__(self, key):
        with self.lock:
            d = json.loads(self.path.read_text())
            d.pop(key)
            self.path.write_text(json.dumps(d))

    def __contains__(self, item) -> bool:
        with self.lock:
            d = json.loads(self.path.read_text())
            return item in d


if not os.getenv('NONEBOT_PLUGIN_CELEIMPRTRC_DEV'):
    data_dir_path.mkdir(parents=True, exist_ok=True)
    satori_data_path.touch(exist_ok=True)
    satori_listening_data = ListeningData(satori_data_path)
