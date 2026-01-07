from __future__ import annotations

from unittest.mock import patch, MagicMock
import pytest

from tools.main import run_plan, Step

@pytest.fixture
def mock_actions():
    """Mocks the _actions dictionary to return mock functions."""
    mock_publish = MagicMock()
    mock_request = MagicMock()
    mock_smoke = MagicMock()
    
    actions = {
        "publish_configs": mock_publish,
        "request_ingestion": mock_request,
        "smoke_tests": mock_smoke,
    }
    
    with patch('tools.main._actions', return_value=actions):
        yield actions

def test_run_plan_runs_enabled_steps(mock_actions):
    """
    Tests that run_plan executes steps that are enabled.
    """
    # Arrange
    plan = [
        Step(name="publish_configs", enabled=True),
        Step(name="request_ingestion", enabled=True),
    ]

    # Act
    run_plan(plan)

    # Assert
    mock_actions["publish_configs"].assert_called_once()
    mock_actions["request_ingestion"].assert_called_once()
    mock_actions["smoke_tests"].assert_not_called()

def test_run_plan_skips_disabled_steps(mock_actions):
    """
    Tests that run_plan skips steps that are disabled.
    """
    # Arrange
    plan = [
        Step(name="publish_configs", enabled=True),
        Step(name="request_ingestion", enabled=False), # Disabled
    ]

    # Act
    run_plan(plan)

    # Assert
    mock_actions["publish_configs"].assert_called_once()
    mock_actions["request_ingestion"].assert_not_called()
    mock_actions["smoke_tests"].assert_not_called()
    
def test_run_plan_all_enabled(mock_actions):
    """
    Tests a plan where all steps are enabled.
    """
    # Arrange
    plan = [
        Step(name="publish_configs", enabled=True),
        Step(name="request_ingestion", enabled=True),
        Step(name="smoke_tests", enabled=True),
    ]

    # Act
    run_plan(plan)

    # Assert
    mock_actions["publish_configs"].assert_called_once()
    mock_actions["request_ingestion"].assert_called_once()
    mock_actions["smoke_tests"].assert_called_once()

def test_run_plan_empty_plan(mock_actions):
    """
    Tests that run_plan handles an empty plan gracefully.
    """
    # Arrange
    plan = []

    # Act
    run_plan(plan)

    # Assert
    for action in mock_actions.values():
        action.assert_not_called()
        
def test_run_plan_unknown_action(mock_actions):
    """
    Tests that run_plan raises a ValueError for an unknown action name.
    """
    # Arrange
    plan = [
        Step(name="publish_configs", enabled=True),
        Step(name="unknown_action", enabled=True),
    ]

    # Act & Assert
    with pytest.raises(ValueError, match="Unknown action: unknown_action"):
        run_plan(plan)
        
    # Ensure that steps before the error were still executed
    mock_actions["publish_configs"].assert_called_once()
