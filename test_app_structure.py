"""
Basic structure tests for the Streamlit app.

These tests verify that the app module can be imported and has the expected
structure without actually running the Streamlit server.
"""

import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(__file__))


def test_app_imports():
    """Test that the app module can be imported."""
    import app
    assert app is not None


def test_app_has_main_function():
    """Test that the app has a main function."""
    import app
    assert hasattr(app, 'main')
    assert callable(app.main)


def test_app_has_helper_functions():
    """Test that the app has expected helper functions."""
    import app
    
    expected_functions = [
        'initialize_session_state',
        'get_agent_status_color',
        'get_agent_status_icon',
        'create_agent_instance',
        'check_aws_credentials',
        'render_header',
        'render_aws_configuration',
        'render_file_upload',
        'render_agent_reasoning',
        'render_agent_insights',
        'render_user_feedback',
        'render_visualizations',
        'render_export_options'
    ]
    
    for func_name in expected_functions:
        assert hasattr(app, func_name), f"Missing function: {func_name}"
        assert callable(getattr(app, func_name)), f"Not callable: {func_name}"


def test_get_agent_status_color():
    """Test agent status color mapping."""
    import app
    
    assert app.get_agent_status_color('ready') == 'green'
    assert app.get_agent_status_color('analyzing') == 'orange'
    assert app.get_agent_status_color('complete') == 'blue'
    assert app.get_agent_status_color('error') == 'red'
    assert app.get_agent_status_color('unknown') == 'gray'


def test_get_agent_status_icon():
    """Test agent status icon mapping."""
    import app
    
    assert app.get_agent_status_icon('ready') == '✅'
    assert app.get_agent_status_icon('analyzing') == '⚙️'
    assert app.get_agent_status_icon('complete') == '🎉'
    assert app.get_agent_status_icon('error') == '❌'
    assert app.get_agent_status_icon('unknown') == '❓'


def test_check_aws_credentials():
    """Test AWS credentials check function."""
    import app
    
    # This should return a boolean
    result = app.check_aws_credentials()
    assert isinstance(result, bool)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
