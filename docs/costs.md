# What does the Orca workstation cost?

The reference GPU workstation costs an estimated **$940.91 per month** to keep online around the clock. Of that, **$884.76** keeps EC2 running and **$33.00** pays for the example Bedrock workload. The GPU is for project code that needs CUDA. A CPU-only host can call the same Bedrock model for the same token price.

All figures are USD. Public rates are for US East (N. Virginia), with Linux On-Demand shared tenancy for EC2. Prices were checked on **20 November 2026** using AWS Pricing MCP. The workload and operator hours below are planning assumptions. Use your own usage and labor rate for a budget.

## Choose an operating schedule

| Host and availability | EC2 hours/month | AWS/month | AWS/year | Year-one total with operator time |
| --- | ---: | ---: | ---: | ---: |
| G5 GPU · always available | 730 | $940.91 | $11,290.92 | $12,490.92 |
| G5 GPU · 8 hours × 20 days | 160 | $245.58 | $2,946.96 | $4,146.96 |
| T3 CPU · always available | 730 | $116.89 | $1,402.63 | $2,602.63 |
| T3 CPU · 8 hours × 20 days | 160 | $64.97 | $779.67 | $1,979.67 |

The 160-hour GPU schedule saves **$695.33 per month**. It means stopping EC2. Closing an Orca client leaves the instance running and billing continues. While EC2 is stopped, neither client can reach Orca, scheduled bots cannot run, and any work that relied on local instance storage is lost. EBS volumes and their retained backups continue to accrue charges. An always-on T3 preserves remote access for projects that fit its CPU and memory.

## Monthly cost breakdown

| Item | Unit price and assumed usage | Always-on G5 | 160-hour G5 |
| --- | --- | ---: | ---: |
| EC2 compute | `g5.2xlarge` at $1.212/hour | $884.76 | $193.92 |
| Encrypted gp3 volumes | 30 GiB root + 150 GiB workspace at $0.08 per provisioned GB-month, baseline performance | $14.40 | $14.40 |
| Workspace backups | 60 GB-month of standard EBS snapshot data at $0.05/GB-month | $3.00 | $3.00 |
| Public IPv4 | One auto-assigned address at $0.005 per running hour | $3.65 | $0.80 |
| EC2 detailed monitoring | Seven billable CloudWatch metrics at $0.30/metric-month, prorated by hours emitting | $2.10 | $0.46 |
| Bedrock inference | GPT-6.2 Sol, 10 million uncached input tokens at $2.20/million + 1 million output tokens at $11.00/million | $33.00 | $33.00 |
| Internet data out | 20 GB covered by the remaining shared AWS monthly allowance | $0.00 | $0.00 |
| **Monthly AWS estimate** | | **$940.91** | **$245.58** |

For the T3 rows, substitute **$0.0832/hour** for a `t3.large` and assume the workload stays within its CPU credit budget. Every other quantity is held constant so the comparison isolates the cost of EC2 capacity and uptime. AWS publishes the unit rates and billing rules. [EC2 and data transfer](https://aws.amazon.com/ec2/pricing/on-demand/) · [EBS](https://aws.amazon.com/ebs/pricing/) · [AWS Backup](https://aws.amazon.com/backup/pricing/) · [public IPv4](https://aws.amazon.com/vpc/pricing/) · [CloudWatch](https://aws.amazon.com/cloudwatch/pricing/) · [Amazon Bedrock pricing](https://aws.amazon.com/bedrock/pricing/).

## Adapt the estimate

- **Backups.** The reference takes one daily backup of the workspace and retains it for 14 days. The first snapshot stores written blocks and later snapshots add changed blocks. The example allows for 60 GB-month across all retained recovery points. Use your stored snapshot usage if you frequently replace datasets, build artifacts or model weights. [EBS incremental snapshots](https://docs.aws.amazon.com/ebs/latest/userguide/how_snapshots_work.html)
- **Inference.** The example uses Standard regional, short-context inference. Count input and output separately, including history resent to the model. Long-context requests, caching, service tier and model choice can all change the unit price. If other agents call Bedrock, add each model’s billable tokens at its own rate. Price a Kiro subscription separately if you use one. [GPT-6.2 Sol model card](https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-openai-gpt-6-2-sol.html)
- **Network and monitoring.** AWS pools its 100 GB/month internet data-out allowance across eligible services and regions. At the first paid tier here, each additional billable GB is $0.09. The estimate assumes the CloudWatch free metric allowance is already consumed. Substitute your actual number of detailed metrics. The reference has one auto-assigned IPv4 address and no NAT gateway or load balancer. A retained Elastic IP also accrues charges while the instance is stopped.
- **Operator time.** Allow four hours once for setup, pairing and validation, plus one hour each month for updates, access review and recovery checks. At an illustrative $75/hour, that is **$300 once + $900/year**. The year-one total adds $1,200 to twelve months of AWS usage. Use the AWS/year column for a cash budget when you absorb this work yourself. Annual totals use unrounded monthly costs.
- **Scope.** The estimate assumes existing client devices, connectivity and access plans. Add any incremental third-party fees, taxes, paid AWS Support, surplus T3 CPU credits, extra gp3 IOPS or throughput, restore-test capacity, cross-region copies, custom logging and resources deployed by your projects. Spot, Savings Plans and negotiated discounts can change the compute rate.

To recalculate the monthly AWS charge in USD, use your running hours, stored quantities and token counts in millions. Keep the 730-hour denominator for the normalized month used here, or use the actual hours in the billing month when prorating monitoring.

```text
monthly AWS = running hours × (instance hourly rate + 0.005)
            + provisioned gp3 GB × 0.08 + stored snapshot GB-month × 0.05
            + billed metrics × 0.30 × running hours / 730
            + input millions × 2.20 + output millions × 11.00
            + billable internet GB × 0.09
year-one TCO = 12 × monthly AWS + (setup hours + 12 × monthly upkeep hours) × hourly labor rate
```
