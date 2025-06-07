#!/usr/bin/env python3

import json
import os
from datetime import datetime, timedelta
from typing import Dict, Optional


class CostTracker:
    """
    Cost tracking and budget management for Summit AI operations.

    Prevents runaway costs from recursive AI calls and provides
    detailed monitoring of API usage and expenses.
    """

    def __init__(
        self,
        daily_budget: float = 10.0,
        hourly_budget: float = 2.0,
        max_recursion_depth: int = 3,
        data_file: Optional[str] = None,
    ):

        # Set default path to data directory
        if data_file is None:
            base_dir = os.path.dirname(os.path.dirname(__file__))
            data_file = os.path.join(base_dir, "data", "summit_costs.json")

        self.daily_budget = daily_budget
        self.hourly_budget = hourly_budget
        self.max_recursion_depth = max_recursion_depth
        self.data_file = data_file

        # Claude 3.5 Sonnet pricing (per 1M tokens)
        self.input_cost_per_token = 3.0 / 1_000_000  # $3 per 1M input tokens
        self.output_cost_per_token = (
            15.0 / 1_000_000
        )  # $15 per 1M output tokens

        self.load_data()

    def load_data(self):
        """Load cost tracking data from file"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, "r") as f:
                    data = json.load(f)
                    self.daily_costs = data.get("daily_costs", {})
                    self.hourly_costs = data.get("hourly_costs", {})
                    self.total_costs = data.get("total_costs", 0.0)
                    self.call_history = data.get("call_history", [])
            else:
                self.reset_data()
        except Exception as e:
            print(f"Error loading cost data: {e}")
            self.reset_data()

    def reset_data(self):
        """Reset all cost tracking data"""
        self.daily_costs = {}
        self.hourly_costs = {}
        self.total_costs = 0.0
        self.call_history = []

    def save_data(self):
        """Save cost tracking data to file"""
        try:
            data = {
                "daily_costs": self.daily_costs,
                "hourly_costs": self.hourly_costs,
                "total_costs": self.total_costs,
                "call_history": self.call_history,
            }
            with open(self.data_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving cost data: {e}")

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Estimate cost for a given number of tokens"""
        input_cost = input_tokens * self.input_cost_per_token
        output_cost = output_tokens * self.output_cost_per_token
        return input_cost + output_cost

    def get_today_key(self) -> str:
        """Get today's date key for tracking"""
        return datetime.now().strftime("%Y-%m-%d")

    def get_hour_key(self) -> str:
        """Get current hour key for tracking"""
        return datetime.now().strftime("%Y-%m-%d-%H")

    def get_daily_spent(self) -> float:
        """Get amount spent today"""
        today = self.get_today_key()
        return self.daily_costs.get(today, 0.0)

    def get_hourly_spent(self) -> float:
        """Get amount spent this hour"""
        hour = self.get_hour_key()
        return self.hourly_costs.get(hour, 0.0)

    def can_make_call(
        self, estimated_cost: float, recursion_depth: int = 0
    ) -> tuple[bool, str]:
        """
        Check if we can make an API call within budget constraints

        Returns:
            (can_call, reason) - Boolean and reason string
        """

        # Check recursion depth
        if recursion_depth >= self.max_recursion_depth:
            return (
                False,
                f"Maximum recursion depth ({
                    self.max_recursion_depth}) exceeded",
            )

        # Check daily budge
        daily_spent = self.get_daily_spent()
        if daily_spent + estimated_cost > self.daily_budget:
            return (
                False,
                f"Daily budget exceeded: ${
                    daily_spent:.4f} + ${
                    estimated_cost:.4f} > ${
                    self.daily_budget}",
            )

        # Check hourly budge
        hourly_spent = self.get_hourly_spent()
        if hourly_spent + estimated_cost > self.hourly_budget:
            return (
                False,
                f"Hourly budget exceeded: ${
                    hourly_spent:.4f} + ${
                    estimated_cost:.4f} > ${
                    self.hourly_budget}",
            )

        return True, "OK"

    def record_call(
        self,
        input_tokens: int,
        output_tokens: int,
        model: str,
        recursion_depth: int = 0,
        call_type: str = "advice",
    ) -> float:
        """
        Record an API call and its cos

        Returns:
            actual_cost - The cost of the call
        """

        cost = self.estimate_cost(input_tokens, output_tokens)

        # Update daily costs
        today = self.get_today_key()
        self.daily_costs[today] = self.daily_costs.get(today, 0.0) + cost

        # Update hourly costs
        hour = self.get_hour_key()
        self.hourly_costs[hour] = self.hourly_costs.get(hour, 0.0) + cost

        # Update total costs
        self.total_costs += cost

        # Record call history
        call_record = {
            "timestamp": datetime.now().isoformat(),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost": cost,
            "model": model,
            "recursion_depth": recursion_depth,
            "call_type": call_type,
        }
        self.call_history.append(call_record)

        # Keep only last 1000 calls to prevent file bloa
        if len(self.call_history) > 1000:
            self.call_history = self.call_history[-1000:]

        self.save_data()
        return cost

    def get_status(self) -> Dict:
        """Get current cost tracking status"""
        return {
            "daily_budget": self.daily_budget,
            "daily_spent": self.get_daily_spent(),
            "daily_remaining": self.daily_budget - self.get_daily_spent(),
            "hourly_budget": self.hourly_budget,
            "hourly_spent": self.get_hourly_spent(),
            "hourly_remaining": self.hourly_budget - self.get_hourly_spent(),
            "total_lifetime_cost": self.total_costs,
            "max_recursion_depth": self.max_recursion_depth,
            "total_calls_today": len(
                [
                    c
                    for c in self.call_history
                    if c["timestamp"].startswith(self.get_today_key())
                ]
            ),
        }

    def cleanup_old_data(self, days_to_keep: int = 30):
        """Clean up old cost data to prevent file bloat"""
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        cutoff_str = cutoff_date.strftime("%Y-%m-%d")

        # Clean daily costs
        self.daily_costs = {
            k: v for k, v in self.daily_costs.items() if k >= cutoff_str
        }

        # Clean hourly costs
        cutoff_hour = cutoff_date.strftime("%Y-%m-%d-%H")
        self.hourly_costs = {
            k: v for k, v in self.hourly_costs.items() if k >= cutoff_hour
        }

        self.save_data()
