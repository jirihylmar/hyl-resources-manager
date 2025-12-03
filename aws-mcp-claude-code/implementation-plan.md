# AWS MCP Server Implementation Plan for Claude Code

Multi-account AWS MCP configuration using existing IAM user profiles with admin privileges.

**Status: IMPLEMENTED**

---

## Account Summary

| Profile | Account ID | Default Region | Primary Resources |
|---------|------------|----------------|-------------------|
| HylmarJ | 182059100462 | eu-west-1 | 44 Lambda functions |
| JiHy__vsb__565 | 565393049593 | eu-central-1 | 1 EC2, 15 Lambdas, 1 VPC |
| JiHy__vsb__299 | 299025166536 | eu-central-1 | 1 EC2, 15 Lambdas, 1 VPC |
| JiHy__d4m__975 | 975050190402 | eu-central-1 | 21 Lambda functions |

---

## Authentication Strategy: Direct IAM Profiles

**Recommendation:** Use existing IAM user profiles from `~/.aws/credentials`

**Rationale:**
- Profiles already exist with admin privileges
- Static credentials don't expire during long-running tasks (unlike assumed roles which have max 12h duration)
- No additional IAM infrastructure needed
- MCP server authenticates using profile credentials directly

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Claude Code                              │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────┐│
│  │ aws-hylmar  │  │ aws-vsb-565 │  │ aws-vsb-299 │  │aws-d4m  ││
│  │ (HylmarJ)   │  │(JiHy__vsb   │  │(JiHy__vsb   │  │  -975   ││
│  │ eu-west-1   │  │  __565)     │  │  __299)     │  │eu-cen-1 ││
│  │             │  │ eu-central-1│  │ eu-central-1│  │         ││
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └────┬────┘│
│         │                │                │               │     │
│         ▼                ▼                ▼               ▼     │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │     awslabs.aws-api-mcp-server (local, per-profile)         ││
│  │     Executes AWS CLI commands via subprocess                ││
│  └─────────────────────────────────────────────────────────────┘│
│         │                │                │               │     │
└─────────┼────────────────┼────────────────┼───────────────┼─────┘
          ▼                ▼                ▼               ▼
   ┌─────────────────────────────────────────────────────────────┐
   │                    AWS APIs (via CLI)                       │
   │     EC2, Lambda, S3, CloudWatch, IAM, etc.                 │
   └─────────────────────────────────────────────────────────────┘
```

---

## Direct CLI vs MCP Connectors

Claude Code can interact with AWS in two ways:

### Option 1: Direct CLI (Bash Tool)

```
Claude Code  →  Bash Tool  →  aws cli  →  AWS APIs
```

**How it works:**
- Claude uses the built-in `Bash` tool to run `aws` commands
- Each command spawns a new shell process
- Raw text output is returned to Claude for parsing

**Characteristics:**
| Aspect | Behavior |
|--------|----------|
| Approval | Each command requires user approval (unless auto-approved in settings) |
| Profile | Must specify `--profile` in every command or set `AWS_PROFILE` env |
| Output | Raw CLI text - Claude must parse it |
| Context | No persistent connection; each command is independent |
| Safety | Relies on user approval; no built-in guardrails |

**Example:**
```bash
aws s3 ls --profile HylmarJ --region eu-west-1
```

### Option 2: MCP Connectors (This Setup)

```
Claude Code  →  MCP Protocol  →  aws-api-mcp-server  →  aws cli  →  AWS APIs
```

**How it works:**
- Claude uses MCP tools (`call_aws`, `suggest_aws_commands`)
- MCP server runs as a persistent subprocess
- Structured JSON communication between Claude and server

**Characteristics:**
| Aspect | Behavior |
|--------|----------|
| Approval | MCP tools can be auto-approved; batch operations streamlined |
| Profile | Pre-configured per connector; no need to specify each time |
| Output | Structured JSON - easier for Claude to process |
| Context | Persistent server; can maintain state across calls |
| Safety | Built-in validation, read-only mode option, command filtering |

**Example:**
```
Using aws-hylmar, list all S3 buckets
→ MCP server automatically uses HylmarJ profile + eu-west-1 region
```

### Comparison Summary

| Feature | Direct CLI | MCP Connectors |
|---------|-----------|----------------|
| **Setup complexity** | None | Requires MCP server installation |
| **Multi-account** | Manual `--profile` each time | Pre-configured per connector |
| **Approval flow** | Per-command approval | Can batch/auto-approve MCP tools |
| **Long-running tasks** | Interrupted by approvals | Smoother, fewer interruptions |
| **Output format** | Raw text | Structured JSON |
| **Command suggestions** | None | `suggest_aws_commands` tool |
| **Safety controls** | User approval only | Read-only mode, validation |
| **Account isolation** | Easy to forget `--profile` | Enforced by connector selection |

### Why MCP Connectors for Long-Running Tasks

1. **Fewer interruptions**: Auto-approve MCP tools for smoother execution
2. **Account isolation**: Each connector locked to specific profile/region
3. **No profile mistakes**: Can't accidentally run command in wrong account
4. **Better error handling**: Structured responses easier to process
5. **Command assistance**: `suggest_aws_commands` helps find correct syntax

---

## Implementation (Completed)

### Step 1: Install pipx and AWS API MCP Server

```bash
# Install pipx via apt (requires sudo)
sudo apt install -y pipx

# Install AWS API MCP Server
pipx install awslabs.aws-api-mcp-server

# Ensure PATH is set
pipx ensurepath
```

### Step 2: Add AWS Region Configuration

```bash
cat >> ~/.aws/config << 'EOF'

[profile HylmarJ]
region = eu-west-1

[profile JiHy__vsb__565]
region = eu-central-1

[profile JiHy__vsb__299]
region = eu-central-1

[profile JiHy__d4m__975]
region = eu-central-1
EOF
```

### Step 3: Add MCP Servers to Claude Code

```bash
# Account: HylmarJ (182059100462) - eu-west-1
claude mcp add aws-hylmar -s user \
  -e AWS_PROFILE=HylmarJ \
  -e AWS_REGION=eu-west-1 \
  -- /home/hylmarj/.local/bin/awslabs.aws-api-mcp-server

# Account: JiHy__vsb__565 (565393049593) - eu-central-1
claude mcp add aws-vsb-565 -s user \
  -e AWS_PROFILE=JiHy__vsb__565 \
  -e AWS_REGION=eu-central-1 \
  -- /home/hylmarj/.local/bin/awslabs.aws-api-mcp-server

# Account: JiHy__vsb__299 (299025166536) - eu-central-1
claude mcp add aws-vsb-299 -s user \
  -e AWS_PROFILE=JiHy__vsb__299 \
  -e AWS_REGION=eu-central-1 \
  -- /home/hylmarj/.local/bin/awslabs.aws-api-mcp-server

# Account: JiHy__d4m__975 (975050190402) - eu-central-1
claude mcp add aws-d4m-975 -s user \
  -e AWS_PROFILE=JiHy__d4m__975 \
  -e AWS_REGION=eu-central-1 \
  -- /home/hylmarj/.local/bin/awslabs.aws-api-mcp-server
```

### Step 4: Verify Installation

```bash
claude mcp list
```

Expected output:
```
aws-hylmar: ... - ✓ Connected
aws-vsb-565: ... - ✓ Connected
aws-vsb-299: ... - ✓ Connected
aws-d4m-975: ... - ✓ Connected
```

---

## Resulting Configuration

File: `~/.claude.json`

```json
{
  "mcpServers": {
    "aws-hylmar": {
      "command": "/home/hylmarj/.local/bin/awslabs.aws-api-mcp-server",
      "args": [],
      "env": {
        "AWS_PROFILE": "HylmarJ",
        "AWS_REGION": "eu-west-1"
      }
    },
    "aws-vsb-565": {
      "command": "/home/hylmarj/.local/bin/awslabs.aws-api-mcp-server",
      "args": [],
      "env": {
        "AWS_PROFILE": "JiHy__vsb__565",
        "AWS_REGION": "eu-central-1"
      }
    },
    "aws-vsb-299": {
      "command": "/home/hylmarj/.local/bin/awslabs.aws-api-mcp-server",
      "args": [],
      "env": {
        "AWS_PROFILE": "JiHy__vsb__299",
        "AWS_REGION": "eu-central-1"
      }
    },
    "aws-d4m-975": {
      "command": "/home/hylmarj/.local/bin/awslabs.aws-api-mcp-server",
      "args": [],
      "env": {
        "AWS_PROFILE": "JiHy__d4m__975",
        "AWS_REGION": "eu-central-1"
      }
    }
  }
}
```

---

## Usage Guide

### Server Selection by Account

| Account Purpose | MCP Server | Profile | Region |
|-----------------|------------|---------|--------|
| HylmarJ resources | `aws-hylmar` | HylmarJ | eu-west-1 |
| VSB account 565 | `aws-vsb-565` | JiHy__vsb__565 | eu-central-1 |
| VSB account 299 | `aws-vsb-299` | JiHy__vsb__299 | eu-central-1 |
| D4M account 975 | `aws-d4m-975` | JiHy__d4m__975 | eu-central-1 |

### Example Prompts for Long-Running Tasks

```
Using aws-hylmar, list all Lambda functions and their last invocation times

Using aws-vsb-565, describe all EC2 instances and their security groups

Using aws-d4m-975, analyze CloudWatch logs for errors in the last 24 hours

Using aws-vsb-299, create a comprehensive inventory of all resources
```

### Cross-Region Operations

The default region is set per server, but you can specify other regions:

```
Using aws-hylmar, list EC2 instances in us-east-1
```

### Available Tools

The `awslabs.aws-api-mcp-server` provides:

| Tool | Description |
|------|-------------|
| `execute_aws_cli` | Execute any AWS CLI command |
| AWS CLI wrapper | Full access to all AWS services via CLI |

---

## Long-Running Task Considerations

### Why Direct Profiles Work Better

1. **No credential expiration**: IAM user access keys don't expire during task execution
2. **No session limits**: Unlike assumed roles (max 12h), direct access has no time limits
3. **Simpler error handling**: No need to handle credential refresh

### Best Practices for Long Tasks

1. **Use specific MCP server**: Always specify which account to use
2. **Include region when needed**: For non-default regions, specify in the prompt
3. **Monitor CloudTrail**: All API calls are logged for auditing

---

## Management Commands

```bash
# List all servers
claude mcp list

# Remove a server
claude mcp remove aws-hylmar -s user

# Get server details
claude mcp get aws-hylmar
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Connection failed | Verify credentials: `aws sts get-caller-identity --profile <name>` |
| Permission denied | Check IAM policies (admin should work) |
| Server not responding | `claude mcp remove <name> -s user` and re-add |
| Command not found | Ensure `~/.local/bin` is in PATH |

---

## Notes

- The `mcp-proxy-for-aws` package is for connecting to AWS-hosted remote MCP servers (requires valid endpoint URL)
- The `awslabs.aws-api-mcp-server` runs locally and executes AWS CLI commands
- For this setup, we use `awslabs.aws-api-mcp-server` as it provides direct AWS API access
- **Restart Claude Code** after adding MCP servers to load them

---

## Sources

- [AWS MCP Servers Documentation](https://awslabs.github.io/mcp/)
- [AWS API MCP Server](https://awslabs.github.io/mcp/servers/aws-api-mcp-server)
- [MCP Proxy for AWS GitHub](https://github.com/aws/mcp-proxy-for-aws)
