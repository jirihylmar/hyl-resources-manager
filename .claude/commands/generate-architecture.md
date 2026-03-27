---
description: Generate architecture diagram from Python diagrams script (project)
allowed-tools:
  - Read
  - Bash
  - Write
  - Edit
---

# Generate Architecture Diagram

Generate a visual architecture diagram using Python diagrams library and update README.md.

---

## Prerequisites

Ensure dependencies are installed:
```bash
pip3 install --break-system-packages diagrams
sudo apt-get install -y graphviz
```

---

## Usage

```
/generate-architecture [name]
```

**Arguments:**
- `name` - Optional. Name for the diagram (default: project name from progress.json)
  - Output: `docs/architecture/{name}_architecture.png`

---

## Steps

### 1. Determine Diagram Name

If name argument provided, use it. Otherwise:
- Read `progress.json` for project name
- Fall back to directory name

### 2. Verify Directory Structure

Check `docs/architecture/` exists:
```bash
ls -la docs/architecture/
```

If missing, create it:
```bash
mkdir -p docs/architecture
```

### 3. Check for generate.py

If `docs/architecture/generate.py` does NOT exist:

```
## Architecture Script Missing

No generate.py found at docs/architecture/generate.py

Would you like me to create a template based on your IMPLEMENTATION_PLAN.md?
```

Use AskUserQuestion. If yes:
- Read `IMPLEMENTATION_PLAN.md` for architecture context
- Create a starter `generate.py` with relevant components
- Include common AWS icons and cluster patterns

### 4. Run Generator

```bash
python3 docs/architecture/generate.py
```

Expected output: `docs/architecture/{name}_architecture.png`

### 5. Verify Output

```bash
ls -la docs/architecture/*.png
```

Confirm the PNG was created.

### 6. Update README.md

Check if README.md already has architecture image reference.

**If architecture section missing**, add near the top (after title/overview):

```markdown
## Architecture

![{Project Name} Architecture](docs/architecture/{name}_architecture.png)

See [Architecture Documentation](docs/architecture/README.md) for details.
```

**If architecture section exists**, verify image path is correct.

### 7. Create/Update docs/architecture/README.md

If `docs/architecture/README.md` doesn't exist, create it with:

```markdown
# Architecture Documentation

## Diagram

![{Project Name} Architecture]({name}_architecture.png)

## Overview

[Architecture overview from IMPLEMENTATION_PLAN.md or brief summary]

## Components

[List key components shown in diagram]

## Regenerating

To regenerate the diagram:
```bash
python3 docs/architecture/generate.py
```

Requirements:
- `pip3 install diagrams`
- `apt-get install graphviz`
```

---

## Output

```
## Architecture Generated

### Diagram
- File: docs/architecture/{name}_architecture.png
- Size: [file size]

### README Updates
- Root README.md: [updated/already current]
- docs/architecture/README.md: [created/updated]

### Preview
[If terminal supports it, mention the file can be viewed]

To view: open docs/architecture/{name}_architecture.png
```

---

## generate.py Template

When creating a new generate.py, use this structure:

```python
#!/usr/bin/env python3
"""
{{PROJECT_NAME}} - Architecture Diagram

Generates AWS architecture diagram using Python diagrams library.

Usage:
    python3 docs/architecture/generate.py

Requirements:
    pip3 install --break-system-packages diagrams
    sudo apt-get install -y graphviz

Output:
    docs/architecture/{{name}}_architecture.png
"""

from pathlib import Path

from diagrams import Cluster, Diagram, Edge
from diagrams.aws.compute import Lambda, ECS
from diagrams.aws.database import Dynamodb
from diagrams.aws.integration import SQS, SNS
from diagrams.aws.network import APIGateway, CloudFront
from diagrams.aws.storage import S3
from diagrams.aws.security import IAM, SecretsManager
from diagrams.onprem.client import User

# Output path relative to script location
SCRIPT_DIR = Path(__file__).parent
OUTPUT_FILE = SCRIPT_DIR / "{{name}}_architecture"

# Diagram configuration
graph_attr = {
    "fontsize": "14",
    "bgcolor": "white",
    "pad": "0.5",
    "splines": "ortho",
    "nodesep": "0.8",
    "ranksep": "1.0",
}

node_attr = {
    "fontsize": "10",
}

edge_attr = {
    "fontsize": "8",
}

with Diagram(
    "{{PROJECT_NAME}}",
    filename=str(OUTPUT_FILE),
    show=False,
    direction="TB",
    graph_attr=graph_attr,
    node_attr=node_attr,
    edge_attr=edge_attr,
):
    # TODO: Define your architecture components here
    user = User("Client")

    with Cluster("AWS Account ({{AWS_ACCOUNT_ID}}, {{AWS_REGION}})"):
        # Add your components
        pass

if __name__ == "__main__":
    print(f"Diagram generated: {OUTPUT_FILE}.png")
```

---

## Notes

- The `diagrams` library uses Graphviz for rendering
- Common AWS icons: Lambda, ECS, S3, DynamoDB, SQS, SNS, APIGateway
- Use `Cluster()` to group related resources
- Use `Edge()` for labeled connections
- Direction: "TB" (top-bottom), "LR" (left-right)
- Script should be idempotent (can run multiple times)
