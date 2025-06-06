#!/usr/bin/env python3

from cost_tracker import CostTracker

def test_cost_tracker():
    """Test the cost tracking functionality"""
    
    print("Testing Summit Cost Tracker")
    print("=" * 40)
    
    # Initialize cost tracker
    ct = CostTracker()
    
    print(f"Daily budget: ${ct.daily_budget}")
    print(f"Hourly budget: ${ct.hourly_budget}")
    print(f"Max recursion depth: {ct.max_recursion_depth}")
    
    # Test cost estimation
    cost = ct.estimate_cost(50, 100)
    print(f"Estimated cost (50→100 tokens): ${cost:.6f}")
    
    # Test budget checking
    can_call, reason = ct.can_make_call(0.01, 0)
    print(f"Can make $0.01 call: {can_call} ({reason})")
    
    # Test recursion limit
    can_call, reason = ct.can_make_call(0.01, 5)
    print(f"Can make call at depth 5: {can_call}")
    print(f"   Reason: {reason}")
    
    # Test status
    status = ct.get_status()
    print(f"Daily spent: ${status['daily_spent']:.4f}")
    print(f"Total lifetime cost: ${status['total_lifetime_cost']:.4f}")
    
    print("\nCost tracker functionality verified successfully.")

if __name__ == "__main__":
    test_cost_tracker() 