"""Offline lifecycle coverage for the executor-thread bridge guardrails."""

import pytest

from robots_and_cubes_ui_gateway.ros_bridge import BridgeUnavailable, RosApplicationBridge


def test_bridge_rejects_web_requests_before_start_and_after_clean_shutdown():
    bridge = RosApplicationBridge(rows=6, columns=6)
    with pytest.raises(BridgeUnavailable):
        bridge.request('get_state').result()
    bridge.shutdown()
    with pytest.raises(BridgeUnavailable):
        bridge.request('get_state').result()


def test_bridge_rejects_arbitrary_ros_operation_names():
    bridge = RosApplicationBridge(rows=6, columns=6)
    with pytest.raises(ValueError, match='unsupported browser operation'):
        bridge.request('arbitrary_ros_service')
