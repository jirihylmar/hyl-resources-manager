---
description: Verify AWS resources for this project (project)
allowed-tools:
  - Read
  - mcp__aws-*__call_aws
---

# Check AWS Resources

Verify all project AWS resources are properly configured.

## Prerequisites

Before running AWS checks, environment config must exist.

**Read environment from:**
1. `input/environment.md` or `input/env.md`
2. `CLAUDE.md` Quick Reference section
3. `progress.json` context_hints

**Required for checks:**
- AWS Account ID
- AWS Region
- MCP Tool name
- Project prefix (naming convention)

**If environment missing:** STOP and direct to `/start-session` or `/setup` first.

---

## Steps

### 1. Read Environment Config
```
Read environment from standard locations.
Extract: aws_account, aws_region, mcp_tool, project_prefix
```

### 2. Verify Identity
Using MCP tool from environment:
```
{mcp_tool} aws sts get-caller-identity
```
Expected: Correct account ID and role matching environment config.

### 3. Check S3 Buckets
```
{mcp_tool} aws s3 ls
```
Filter for project buckets (matching project_prefix).

Expected buckets for this project:
- `{project}-artifacts-*` - Build artifacts
- `{project}-sessions-*` - Session files for analysis

### 4. Check DynamoDB Tables
```
{mcp_tool} aws dynamodb list-tables
```
Filter for project tables (matching project_prefix).

Expected tables for this project:
- `{project}-experts-*` - Expert profiles and expertise

### 5. Check SQS Queues
```
{mcp_tool} aws sqs list-queues
```
Filter for project queues.

Expected queues:
- `{project}-commands-*` - Command queue for Master-of-Masters
- `{project}-commands-*-dlq` - Dead letter queue

### 6. Check SNS Topics
```
{mcp_tool} aws sns list-topics
```
Filter for project topics.

Expected topics:
- `{project}-notifications-*` - Notification topic

### 7. Check Lambda Functions
```
{mcp_tool} aws lambda list-functions
```
Filter for project functions (matching project_prefix).

### 8. Check CloudFormation Stacks
```
{mcp_tool} aws cloudformation list-stacks --stack-status-filter CREATE_COMPLETE UPDATE_COMPLETE
```
Filter for project stacks.

### 9. Check IAM Roles
```
{mcp_tool} aws iam list-roles
```
Filter for project roles (matching project_prefix).

---

## Output

```
## AWS Resource Check

### Environment
- Account: {aws_account} ✓
- Region: {aws_region} ✓
- MCP Tool: {mcp_tool}
- Project: {project_prefix}

### Identity Verified
- Account ID: {actual_account} {✓ or ✗}
- Region: {actual_region} {✓ or ✗}

### Resources Found

| Type | Expected | Found | Status |
|------|----------|-------|--------|
| S3 Buckets | 2 | 2 | ✓ |
| DynamoDB Tables | 1 | 1 | ✓ |
| SQS Queues | 2 | 0 | ✗ Missing |
| SNS Topics | 1 | 0 | ✗ Missing |
| Lambda Functions | 7 | 0 | ✗ Not deployed |
| CloudFormation Stacks | 2 | 0 | ✗ Not deployed |

### Missing Resources
- SQS command queue (Phase 1.2)
- SNS notification topic (Phase 1.2)
- Lambda functions (Phase 2)

### Next Steps
- Deploy foundation stack: Task 1.4
- Or continue with current phase task
```

---

## Notes

- Always read environment config first
- Use MCP tools, never raw aws CLI
- Compare against expected resources from IMPLEMENTATION_PLAN.md
- Update this file as new resource types are added
- Use resource_inventory in progress.json as reference if it exists
