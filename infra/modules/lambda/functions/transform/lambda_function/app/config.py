import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    datalake_bucket: str

    config_prefix_schema: str

    data_prefix_bronze: str
    data_prefix_silver: str

    tracking_table: str


def load_config() -> Config:
    return Config(
        datalake_bucket=os.environ["DATALAKE_BUCKET"],
        config_prefix_schema=os.environ.get("CONFIG_PREFIX_SCHEMA", "configs/schema/"),
        data_prefix_bronze=os.environ.get("DATA_PREFIX_BRONZE", "data/bronze/"),
        data_prefix_silver=os.environ.get("DATA_PREFIX_SILVER", "data/silver/"),
        tracking_table=os.environ["TRACKING_TABLE"],
    )
