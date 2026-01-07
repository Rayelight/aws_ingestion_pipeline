import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    datalake_bucket: str

    config_prefix_contracts: str
    config_prefix_schema: str

    data_prefix_bronze: str
    transform_queue_url: str

    tracking_table: str

    api_timeout_sec: float
    api_max_retries: int


def load_config() -> Config:
    return Config(
        datalake_bucket=os.environ["DATALAKE_BUCKET"],

        config_prefix_contracts=os.environ.get("CONFIG_PREFIX_CONTRACTS", "configs/contracts/"),
        config_prefix_schema=os.environ.get("CONFIG_PREFIX_SCHEMA", "configs/schema/"),

        data_prefix_bronze=os.environ.get("DATA_PREFIX_BRONZE", "data/bronze/"),
        transform_queue_url=os.environ["TRANSFORM_QUEUE_URL"],

        tracking_table=os.environ["TRACKING_TABLE"],

        api_timeout_sec=float(os.environ.get("API_TIMEOUT_SEC", "15")),
        api_max_retries=int(os.environ.get("API_MAX_RETRIES", "3")),
    )
