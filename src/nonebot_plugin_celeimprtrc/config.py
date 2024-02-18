import os

from pydantic import BaseModel, SecretStr, ValidationError, NonNegativeInt

from .common import plugin_root

config_path = plugin_root / 'config.toml'


class GithubAppInfoConfig(BaseModel):
    app_name: str
    app_website: str


class GithubConfig(BaseModel):
    app_info: GithubAppInfoConfig
    app_id: SecretStr
    private_key: SecretStr


class Config(BaseModel):
    max_file_size_kib: NonNegativeInt = 128
    github: GithubConfig


if not os.getenv('NONEBOT_PLUGIN_CELEIMPRTRC_DEV'):
    import tomllib

    from nonebot import logger

    try:
        config_path.touch(exist_ok=True)
        config = Config.parse_obj(tomllib.loads(config_path.read_text(encoding='utf-8')))
    except ValidationError as e:
        logger.error('Invalid config! Plugin will NOT work!')
        raise
