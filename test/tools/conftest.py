from __future__ import annotations

from unittest.mock import MagicMock

import pytest

# This conftest.py provides common fixtures for all tests under the test/tools/ directory.

@pytest.fixture
def mock_s3_client():
    """Provides a mock S3 client."""
    client = MagicMock()
    # Simulate get_object response structure
    client.get_object.return_value = {
        'Body': MagicMock(read=MagicMock(return_value=b'---\nkey: value'))
    }
    return client

@pytest.fixture
def mock_sqs_client():
    """Provides a mock SQS client."""
    client = MagicMock()
    client.send_message.return_value = {'MessageId': 'mock-message-id-123'}
    return client

@pytest.fixture
def mock_sts_client():
    """Provides a mock STS client."""
    client = MagicMock()
    client.get_caller_identity.return_value = {'Account': '123456789012'}
    return client
    
@pytest.fixture
def mock_dynamodb_client():
    """Provides a mock DynamoDB client."""
    client = MagicMock()
    return client


@pytest.fixture
def mock_aws_clients(
    mock_s3_client,
    mock_sqs_client,
    mock_sts_client,
    mock_dynamodb_client
):
    """
    A fixture that provides a collection of mocked AWS clients,
    simulating the AwsClients dataclass from the application.
    """
    clients = MagicMock()
    clients.s3 = mock_s3_client
    clients.sqs = mock_sqs_client
    clients.sts = mock_sts_client
    clients.dynamodb = mock_dynamodb_client
    return clients
