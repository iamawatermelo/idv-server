from typing import Any
from pydantic import BaseModel, Field, PostgresDsn, computed_field
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    TomlConfigSettingsSource,
)
import strawberry
import hypercorn
import sqlalchemy
import sqlmodel
import anyio
import click
import graphql


class Auth(BaseModel):
    pdp_endpoint: str
    forwarded_headers: list[str] = ["authorization"]
    subject_header: str = "x-authenticated-subject"
    root_subjects: list[str] = [""]


class Config(BaseSettings):
    model_config = SettingsConfigDict(
        env_nested_delimiter="__", env_prefix="IDV_", toml_file="config.toml"
    )

    hostname: str = "0.0.0.0"
    port: int = Field(default=8080, alias="PORT")

    postgres_connection_string: PostgresDsn
    log_level: str = "WARNING"
    logging_config: dict[str, Any] | None = None

    auth: Auth | None = None

    @computed_field
    @property
    def _logging_config(self) -> dict[str, Any]:
        return self.logging_config or {
            "version": 1,
            "disable_existing_loggers": False,
            "handlers": {
                "rich_console": {
                    "class": "rich.logging.RichHandler",
                    "level": self.log_level,
                    "rich_tracebacks": True,
                    "show_path": True,
                    "markup": True,
                    "tracebacks_suppress": [
                        strawberry,
                        hypercorn,
                        sqlalchemy,
                        sqlmodel,
                        anyio,
                        click,
                        graphql,
                    ],
                }
            },
            "loggers": {
                "hypercorn": {
                    "level": "INFO",
                    "propagate": False,
                    "handlers": ["rich_console"],
                },
            },
            "root": {"level": "DEBUG", "handlers": ["rich_console"]},
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
