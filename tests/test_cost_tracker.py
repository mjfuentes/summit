#!/usr/bin/env python3

import pytest

from src.cost_tracker import CostTracker


def test_cost_tracker(tmp_path):
    """Test the cost tracking functionality"""

    # Use a temporary file so tests don't interfere with real data
    data_file = tmp_path / "costs.json"
    ct = CostTracker(data_file=str(data_file))

    # Estimate cost should use configured token prices
    assert ct.estimate_cost(50, 100) == pytest.approx(0.00165)

    # A small call should be allowed
    can_call, reason = ct.can_make_call(0.01, 0)
    assert can_call is True
    assert reason == "OK"

    # Calls beyond recursion depth should be blocked
    can_call, reason = ct.can_make_call(0.01, ct.max_recursion_depth + 1)
    assert can_call is False
    assert "Maximum recursion depth" in reason

    # Status fields should mirror tracker values
    status = ct.get_status()
    assert status["daily_budget"] == ct.daily_budget
    assert status["hourly_budget"] == ct.hourly_budget
    assert status["max_recursion_depth"] == ct.max_recursion_depth
    assert status["daily_spent"] == ct.get_daily_spent()
    assert status["hourly_spent"] == ct.get_hourly_spent()
    assert status["total_lifetime_cost"] == ct.total_costs
    assert status["total_calls_today"] == 0


if __name__ == "__main__":
    test_cost_tracker()
