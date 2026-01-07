from __future__ import annotations

import json
from typing import List

from .config import PublisherConfig
from .discovery import discover_datasets
from .models import PublishArtifact, PublishReport, ValidationError
from .s3_uploader import S3Uploader
from .validators import validate_contract, validate_pair, validate_schema
from .yaml_io import read_yaml


def publish_all(cfg: PublisherConfig) -> List[PublishReport]:
    uploader = S3Uploader(region=cfg.region, bucket=cfg.datalake_bucket)

    datasets = discover_datasets(cfg.local_contracts_dir, cfg.local_schema_dir)
    if not datasets:
        raise ValidationError(f"No datasets found under: {cfg.local_contracts_dir}")

    reports: List[PublishReport] = []
    errors: List[str] = []

    for ds in datasets:
        ctx = f"{ds.source}/{ds.entity}"
        try:
            # --- validate files exist / parse yaml
            contract_raw = read_yaml(ds.contract_path)
            schema_raw = read_yaml(ds.schema_path)

            # --- validate objects
            contract = validate_contract(contract_raw, ds.source, ds.entity, ctx=f"{ctx} contract")
            schema = validate_schema(schema_raw, ds.source, ds.entity, ctx=f"{ctx} schema", strict=cfg.strict)
            validate_pair(contract, schema, ctx=f"{ctx} pair", strict=cfg.strict)

            # --- upload
            contract_key = f"{cfg.s3_contracts_prefix}{ds.source}/{ds.entity}.yaml"
            schema_key = f"{cfg.s3_schema_prefix}{ds.source}/{ds.entity}.yaml"

            contract_text = ds.contract_path.read_text(encoding="utf-8")
            schema_text = ds.schema_path.read_text(encoding="utf-8")

            up_c = uploader.put_yaml(contract_key, contract_text)
            up_s = uploader.put_yaml(schema_key, schema_text)

            reports.append(
                PublishReport(
                    dataset=ctx,
                    contract=PublishArtifact(
                        s3_key=up_c.s3_key,
                        size_kb=round(up_c.size_kb, 2),
                        sha256_12=up_c.sha256_12,
                    ),
                    schema=PublishArtifact(
                        s3_key=up_s.s3_key,
                        size_kb=round(up_s.size_kb, 2),
                        sha256_12=up_s.sha256_12,
                    ),
                )
            )

        except Exception as e:
            errors.append(f"{ctx}: {e}")

    if errors:
        raise ValidationError("Publishing failed:\n" + "\n".join(errors))

    return reports


def reports_to_json(reports: List[PublishReport]) -> str:
    payload = [
        {
            "dataset": r.dataset,
            "contract": {
                "s3_key": r.contract.s3_key,
                "size_kb": r.contract.size_kb,
                "sha256": r.contract.sha256_12,
            },
            "schema": {
                "s3_key": r.schema.s3_key,
                "size_kb": r.schema.size_kb,
                "sha256": r.schema.sha256_12,
            },
        }
        for r in reports
    ]
    return json.dumps(payload, indent=2, ensure_ascii=False)
