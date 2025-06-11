# Summit Cost Control System

## Overview

Summit includes a comprehensive cost tracking and budget management system to prevent runaway expenses from AI API calls, especially important for recursive AI-to-AI communication.

## Key Features

### Budget Controls
- **Daily Budget**: $10.00 default (configurable)
- **Hourly Budget**: $2.00 default (configurable)  
- **Recursion Depth Limit**: 3 levels maximum
- **Automatic Cost Estimation**: Pre-call cost calculation
- **Real-time Tracking**: Live budget monitoring

### Safety Mechanisms
- **Circuit Breakers**: Automatic stops when budgets exceeded
- **Loop Detection**: Prevents infinite recursion
- **Cost Transparency**: Every response shows actual cost
- **Historical Tracking**: Detailed call history and analytics

## Cost Structure (Claude 3.5 Sonnet)

| Token Type | Cost per 1M tokens | Cost per token |
|------------|-------------------|----------------|
| Input      | $3.00             | $0.000003      |
| Output     | $15.00            | $0.000015      |

### Example Costs
- **Simple question** (50 input, 100 output tokens): ~$0.0018
- **Complex advice** (200 input, 500 output tokens): ~$0.0081
- **Daily budget** allows ~1,200-5,500 queries depending on complexity

## Configuration

### Default Settings
```python
cost_tracker = CostTracker(
    daily_budget=10.0,      # $10 per day
    hourly_budget=2.0,      # $2 per hour  
    max_recursion_depth=3   # Max AI-to-AI call depth
)
```

### Customization
Edit `summit.py` to adjust budgets:
```python
# Conservative settings
daily_budget=5.0, hourly_budget=1.0

# Development settings  
daily_budget=20.0, hourly_budget=5.0

# Production settings
daily_budget=50.0, hourly_budget=10.0
```

## Monitoring Tools

### 1. Status Check
Use `summit_status` tool to see:
- Current budget usage
- Remaining budget
- Total calls today
- Lifetime costs

### 2. Detailed Report
Use `summit_cost_report` tool for:
- Percentage budget usage
- Recent call history
- Cost per call breakdown
- Token usage statistics

### 3. Cost Data File
All data saved to `summit_costs.json`:
```json
{
  "daily_costs": {"2024-06-06": 2.45},
  "hourly_costs": {"2024-06-06-14": 0.32},
  "total_costs": 15.67,
  "call_history": [...]
}
```

## Error Handling

### Budget Exceeded
```
Summit's cost controls prevented this call: 
Daily budget exceeded: $9.85 + $0.25 > $10.00
```

### Recursion Limit
```
Summit's cost controls prevented this call: 
Maximum recursion depth (3) exceeded
```

### Hourly Limit
```
Summit's cost controls prevented this call: 
Hourly budget exceeded: $1.95 + $0.15 > $2.00
```

## Best Practices

### For Development
1. **Start Conservative**: Use default $10 daily budget
2. **Monitor Closely**: Check `summit_status` regularly
3. **Test Incrementally**: Small changes, observe costs
4. **Use Cost Reports**: Analyze spending patterns

### For Production
1. **Set Appropriate Budgets**: Based on expected usage
2. **Implement Alerts**: Monitor for unusual spending
3. **Regular Cleanup**: Use `cleanup_old_data()` monthly
4. **Backup Cost Data**: Save `summit_costs.json` regularly

### For Recursive AI Systems
1. **Low Recursion Limits**: Start with depth=2, increase carefully
2. **Tight Hourly Budgets**: Prevent cascade failures
3. **Loop Detection**: Monitor for A→B→A patterns
4. **Emergency Stops**: Manual override capabilities

## Troubleshooting

### High Costs
- Check recursion depth in cost reports
- Look for repeated similar calls
- Verify no infinite loops
- Consider reducing max_tokens

### Budget Too Restrictive
- Analyze actual usage patterns
- Increase budgets gradually
- Consider time-based adjustments
- Monitor cost per value delivered

### Data File Issues
- Check file permissions
- Verify JSON format validity
- Use `reset_data()` if corrupted
- Backup before major changes

## Future Enhancements

### Planned Features
- **Smart Budgeting**: AI-driven budget optimization
- **Cost Prediction**: ML-based usage forecasting  
- **Alert System**: Email/SMS notifications
- **Multi-Model Support**: Different pricing for different models
- **Team Budgets**: Shared budget pools
- **Cost Analytics**: Advanced reporting and insights

### Integration Points
- **MCP-to-MCP**: Cost tracking across agent networks
- **GitHub Actions**: Budget monitoring in CI/CD
- **Monitoring Tools**: Prometheus/Grafana integration
- **Billing Systems**: Automated invoice generation

## Security Considerations

### Data Protection
- Cost data contains usage patterns
- Store `summit_costs.json` securely
- Consider encryption for sensitive environments
- Regular data cleanup prevents information leakage

### Access Control
- Protect cost configuration
- Monitor budget modifications
- Audit cost report access
- Secure API keys properly

## Emergency Procedures

### Runaway Costs
1. **Immediate**: Kill Summit process
2. **Check**: Review `summit_costs.json`
3. **Analyze**: Identify cost spike cause
4. **Adjust**: Lower budgets before restart
5. **Monitor**: Watch closely after restart

### Budget Reset
```python
# Emergency budget reset
cost_tracker.reset_data()
cost_tracker.daily_budget = 1.0  # Very conservative
cost_tracker.save_data()
```

This cost control system ensures Summit can operate autonomously while maintaining strict financial boundaries, essential for any AI system that can modify and improve itself. 