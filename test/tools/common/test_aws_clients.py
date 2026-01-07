from __future__ import annotations

from unittest.mock import patch, MagicMock

from tools.common.aws_clients import make_aws_clients, get_account_id, AwsClients

# By patching 'boto3.client' in the same module where it's used ('tools.common.aws_clients'),
# we can intercept the calls it makes.
@patch('tools.common.aws_clients.boto3.client')
def test_make_aws_clients(mock_boto_client):
    """
    Tests that make_aws_clients creates all required clients using boto3,
    and passes the correct region and config.
    """
    # Arrange
    mock_s3 = MagicMock()
    mock_sqs = MagicMock()
    mock_sts = MagicMock()
    mock_dynamodb = MagicMock()

    # Set the side_effect to return a different mock depending on the service name
    def client_side_effect(service_name, *args, **kwargs):
        if service_name == "s3":
            return mock_s3
        if service_name == "sqs":
            return mock_sqs
        if service_name == "sts":
            return mock_sts
        if service_name == "dynamodb":
            return mock_dynamodb
        return MagicMock()

    mock_boto_client.side_effect = client_side_effect
    
    region = "eu-west-1"

    # Act
    clients = make_aws_clients(region=region)

    # Assert
    assert isinstance(clients, AwsClients)
    assert clients.s3 == mock_s3
    assert clients.sqs == mock_sqs
    assert clients.sts == mock_sts
    assert clients.dynamodb == mock_dynamodb

    # Check that boto3.client was called for each service with the correct region
    mock_boto_client.assert_any_call("s3", region_name=region, config=unittest.mock.ANY)
    mock_boto_client.assert_any_call("sqs", region_name=region, config=unittest.mock.ANY)
    mock_boto_client.assert_any_call("sts", region_name=region, config=unittest.mock.ANY)
    mock_boto_client.assert_any_call("dynamodb", region_name=region, config=unittest.mock.ANY)
    assert mock_boto_client.call_count == 4


def test_get_account_id(mock_sts_client):
    """
    Tests that get_account_id correctly calls the sts client and extracts the account ID.
    Uses the mock_sts_client fixture from conftest.py.
    """
    # Arrange
    expected_account_id = "123456789012"
    mock_sts_client.get_caller_identity.return_value = {'Account': expected_account_id}
    
    # Act
    account_id = get_account_id(mock_sts_client)
    
    # Assert
    assert account_id == expected_account_id
    mock_sts_client.get_caller_identity.assert_called_once()
