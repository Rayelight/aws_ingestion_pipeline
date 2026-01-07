from __future__ import annotations

import hashlib
from unittest.mock import patch, MagicMock

from tools.config_publisher.s3_uploader import S3Uploader, UploadResult

# Patch boto3 in the module where it is used
@patch('tools.config_publisher.s3_uploader.boto3.client')
def test_s3_uploader_put_yaml(mock_boto_client):
    """
    Tests the put_yaml method of the S3Uploader class.
    """
    # Arrange
    mock_s3 = MagicMock()
    mock_boto_client.return_value = mock_s3
    
    region = "us-east-1"
    bucket = "my-test-bucket"
    key = "my/test/key.yaml"
    content_text = "key: value"
    content_bytes = content_text.encode("utf-8")
    
    uploader = S3Uploader(region=region, bucket=bucket)

    # Act
    result = uploader.put_yaml(key, content_text)

    # Assert
    
    # 1. Check if the boto3 client was instantiated correctly
    mock_boto_client.assert_called_once_with("s3", region_name=region)
    
    # 2. Check if put_object was called with the correct parameters
    mock_s3.put_object.assert_called_once_with(
        Bucket=bucket,
        Key=key,
        Body=content_bytes,
        ContentType="text/yaml"
    )
    
    # 3. Check if the returned UploadResult object is correct
    assert isinstance(result, UploadResult)
    assert result.s3_key == key
    
    expected_sha = hashlib.sha256(content_bytes).hexdigest()[:12]
    assert result.sha256_12 == expected_sha
    
    expected_size_kb = len(content_bytes) / 1024.0
    assert result.size_kb == expected_size_kb
