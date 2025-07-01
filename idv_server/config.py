from logging.config import _LoggerConfiguration
from typing import Any
from pydantic import PostgresDsn
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict, TomlConfigSettingsSource


class Config(BaseSettings):
    model_config = SettingsConfigDict(
        env_nested_delimiter="__",
        toml_file="config.toml"
    )

    postgres_connection_string: PostgresDsn
    logging_config: dict[str, Any] = {
        "version": 1,
        "disable_existing_loggers": False,
        "handlers": {
            "rich_console": {
                "class": "rich.logging.RichHandler",
                "level": "DEBUG",
                
                "rich_tracebacks": True,
                "show_path": False,
                "markup": True
            },
            "rich_third_party": {
                "class": "rich.logging.RichHandler",
                "level": "WARNING",
                
                "rich_tracebacks": True,
                "show_path": False,
                "markup": False
            }
        },
        "loggers": {
            "idv_server": {
                "level": "DEBUG",
                "handlers": ["rich_console"],
                "propagate": False
            }
        }
    }

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            env_settings,
            dotenv_settings,
            TomlConfigSettingsSource(settings_cls),
        )


config = Config()  # type: ignore
