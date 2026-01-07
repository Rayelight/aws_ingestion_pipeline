from __future__ import annotations

import json
from unittest.mock import patch, MagicMock
import pytest

from tools.ingestion_requester.requester import (
    build_request_from_contract,
    send_request,
    request_and_send,
    request_hourly,
    _default_run_id,
    _derive_time_window_ms_from_date_hour,
    RequestValidationError,
)
from tools.common.contracts_loader import ContractSpec
from tools.ingestion_requester.models import IngestionRequest

# --- Mocks and Fixtures ---

@pytest.fixture
def mock_requester_dependencies():
    """Mocks all external dependencies for the requester module."""
    with patch('tools.ingestion_requester.requester.load_requester_config') as mock_load_cfg, \
         patch('tools.ingestion_requester.requester.make_aws_clients') as mock_make_clients, \
         patch('tools.ingestion_requester.requester.load_contract_from_s3') as mock_load_contract, \
         patch('tools.ingestion_requester.requester._head_s3_object', return_value=True) as mock_head:

        # Mock the config object
        mock_config = MagicMock()
        mock_config.region = "eu-west-1"
        mock_config.datalake_bucket = "test-bucket"
        mock_config.ingest_queue_name = "test-queue"
        mock_config.default_time_window_minutes = 60
        mock_load_cfg.return_value = mock_config

        # Mock the AWS clients
        mock_clients = MagicMock()
        mock_clients.sqs.send_message.return_value = {'MessageId': 'mock-id'}
        mock_make_clients.return_value = mock_clients

        # Mock the S3 contract loader
        mock_contract = ContractSpec(
            version=1,
            id="test-id",
            source="test-source",
            entity="test-entity",
            raw={},
            required_params={"p1"},
            optional_params={"opt1"},
            query_placeholders={"p2"}
        )
        mock_load_contract.return_value = mock_contract
        
        yield {
            "load_cfg": mock_load_cfg,
            "make_clients": mock_make_clients,
            "load_contract": mock_load_contract,
            "head_object": mock_head,
            "clients": mock_clients,
            "contract": mock_contract
        }

# --- Tests ---

def test_build_request_from_contract_success(mock_requester_dependencies):
    """Tests that a valid request can be built from a contract."""
    req = build_request_from_contract(
        source="test-source",
        entity="test-entity",
        params={"p1": "val1", "p2": "val2"}
    )
    assert isinstance(req, IngestionRequest)
    assert req.source == "test-source"
    assert req.entity == "test-entity"
    assert req.params["p1"] == "val1"

def test_build_request_from_contract_missing_s3_object(mock_requester_dependencies):
    """Tests that a runtime error is raised if the contract is missing in S3."""
    mock_requester_dependencies["head_object"].return_value = False
    with pytest.raises(RuntimeError, match="Missing contract in S3"):
        build_request_from_contract(
            source="test-source",
            entity="test-entity",
            params={"p1": "val1", "p2": "val2"}
        )

def test_build_request_from_contract_validation_error(mock_requester_dependencies):
    """Tests that a RequestValidationError is raised if params don't match the contract."""
    with pytest.raises(RequestValidationError, match="Missing required params"):
        build_request_from_contract(
            source="test-source",
            entity="test-entity",
            params={"p2": "val2"} # Missing required param 'p1'
        )

def test_derive_time_window_ms():
    """Tests the derivation of start/end timestamps from date and hour."""
    start_ms, end_ms = _derive_time_window_ms_from_date_hour("2023-01-01", "01", 60)
    # 2023-01-01 01:00:00 UTC -> 1672534800000
    # 2023-01-01 02:00:00 UTC -> 1672538400000
    assert start_ms == 1672534800000
    assert end_ms == 1672538400000

def test_send_request(mock_requester_dependencies):
    """Tests that send_request calls the SQS client with the correct payload."""
    # Arrange
    req = IngestionRequest(
        source="test-source",
        entity="test-entity",
        run_id="test-run",
        params={"p1": "v1"}
    )
    mock_sqs = mock_requester_dependencies["clients"].sqs
    
    # Mock account_id since it's an external call
    with patch('tools.ingestion_requester.requester.get_account_id', return_value="123456789012"):
        # Act
        message_id = send_request(req)

    # Assert
    assert message_id == "mock-id"
    mock_sqs.send_message.assert_called_once()
    
    # Check the body of the SQS message
    call_args = mock_sqs.send_message.call_args
    sent_body = json.loads(call_args.kwargs['MessageBody'])
    
    assert sent_body['source'] == req.source
    assert sent_body['entity'] == req.entity
    assert sent_body['run_id'] == req.run_id
    assert sent_body['params'] == req.params

@patch('tools.ingestion_requester.requester.send_request')
@patch('tools.ingestion_requester.requester.build_request_from_contract')
def test_request_and_send(mock_build, mock_send, mock_requester_dependencies):
    """Tests the convenience wrapper `request_and_send`."""
    # Arrange
    mock_req = IngestionRequest("s", "e", "r", {})
    mock_build.return_value = mock_req
    mock_send.return_value = "mock-id"

    # Act
    request_and_send(source="s", entity="e", params={})
    
    # Assert
    mock_build.assert_called_once_with(source="s", entity="e", params={}, run_id=None)
    mock_send.assert_called_once_with(mock_req)

@patch('tools.ingestion_requester.requester.send_request')
@patch('tools.ingestion_requester.requester.build_request_from_contract')
def test_request_hourly(mock_build, mock_send, mock_requester_dependencies):
    """Tests the hourly batch requester."""
    # Arrange
    mock_req = IngestionRequest("s", "e", "r", {})
    mock_build.return_value = mock_req
    
    # Act
    request_hourly(
        source="binance_api",
        entity="aggTrades",
        date="2025-05-03",
        endpoint="aggTrades",
        base_params={"symbol": "BTCUSDT"},
        hours=[0, 1] # Test with 2 hours
    )

    # Assert
    assert mock_build.call_count == 2
    assert mock_send.call_count == 2
    
    # Check one of the calls
    first_call_params = mock_build.call_args_list[0].kwargs['params']
    assert first_call_params['date'] == '2025-05-03'
    assert first_call_params['hour'] == '00'
    assert first_call_params['symbol'] == 'BTCUSDT'
