from __future__ import annotations

from pathlib import Path
from tools.common.app_config import load_app_config, AppConfig, AwsConfig, RepoConfig, PrefixConfig

def test_load_app_config():
    """
    Tests that load_app_config returns a well-formed AppConfig object.
    Since the values are hardcoded, this test mainly serves as a structural integrity check.
    """
    config = load_app_config()

    assert isinstance(config, AppConfig)
    
    # Test nested objects
    assert isinstance(config.aws, AwsConfig)
    assert isinstance(config.repo, RepoConfig)
    assert isinstance(config.prefixes, PrefixConfig)
    
    # Test some example values
    assert config.aws.region == "eu-west-3"
    assert config.aws.datalake_bucket == "ingesteur-dev-datalake"
    assert config.strict is True
    
    # Test that path objects are correctly constructed
    assert isinstance(config.repo.repo_root, Path)
    assert isinstance(config.repo.configs_local_root, Path)
    assert "configs_local" in str(config.repo.configs_local_root)
