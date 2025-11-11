# DynamoDB Cost Optimization - August 2025

## Changes Made
- Converted all 3 tables from **Provisioned** to **On-Demand** billing mode:
  - `booking-gsp`
  - `configuration-digital-horizon` 
  - `digital-horizon-metadata-repository`

## Cost Impact
- **Before**: $7.61/month (40 RCU/WCU exceeding free tier)
- **After**: $0.00 when not in use
- **On-Demand Pricing**: $0.25/million reads, $1.25/million writes

## Behavior Changes

### Limits & Throttling
- **No explicit limits** on read/write capacity
- **Auto-scaling**: DynamoDB handles capacity automatically
- **Burst capacity**: Can handle sudden traffic spikes up to 4,000 RCU/WCU per partition
- **Sustained traffic**: Automatically scales to accommodate any level of traffic

### Performance Considerations
- **Cold start**: First requests may have slightly higher latency as capacity scales
- **Warm tables**: Tables with consistent traffic maintain optimal performance
- **WarmThroughput**: Still configured (5-10 RPS) - provides consistent low-latency performance

### When to Consider Reverting to Provisioned
- Predictable, steady workloads > 200 RCU/WCU
- Cost becomes > provisioned equivalent
- Need guaranteed consistent performance (no cold starts)

## Monitoring
Monitor costs in AWS billing dashboard. Switch back to provisioned if on-demand costs exceed $7.61/month.