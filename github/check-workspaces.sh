#!/bin/bash
# Check all workspace repos against mapping file

WORKSPACE_DIR="$HOME"
MAPPING_FILE="workspace-repos.json"
WORKSPACE_FILES=(
    "metadata.code-workspace"
    "goldsport.code-workspace"
    "manufacturing.code-workspace"
    "models.code-workspace"
    "databridge.code-workspace"
    "docs.code-workspace"
    "system.code-workspace"
    "digital-horizon.code-workspace"
    "iot.code-workspace"
)

echo "============================================"
echo "Checking all workspace repositories"
echo "============================================"
echo ""

declare -A all_repos
declare -A missing_repos
declare -A workspace_source

# Extract repos from all workspaces
for ws_file in "${WORKSPACE_FILES[@]}"; do
    ws_path="$WORKSPACE_DIR/$ws_file"
    if [[ -f "$ws_path" ]]; then
        while IFS= read -r path; do
            repo_name=$(basename "$path")
            all_repos["$repo_name"]=1
            workspace_source["$repo_name"]="${workspace_source[$repo_name]:-}${ws_file},"
        done < <(grep -oP '"path":\s*"\K[^"]+' "$ws_path")
    fi
done

echo "Found ${#all_repos[@]} unique repositories across ${#WORKSPACE_FILES[@]} workspaces"
echo ""

# Check each repo against mapping
echo "Checking against mapping file..."
echo ""

for repo_name in "${!all_repos[@]}"; do
    if ! jq -e --arg repo "$repo_name" '.[$repo]' "$MAPPING_FILE" > /dev/null 2>&1; then
        missing_repos["$repo_name"]="${workspace_source[$repo_name]}"
    fi
done

# Report results
if [ ${#missing_repos[@]} -eq 0 ]; then
    echo "✓ All workspace repositories exist in mapping!"
else
    echo "✗ MISSING REPOSITORIES: ${#missing_repos[@]}"
    echo "============================================"
    echo ""
    for repo in "${!missing_repos[@]}"; do
        workspaces=$(echo "${missing_repos[$repo]}" | sed 's/,$//' | tr ',' '\n' | sort -u | paste -sd,)
        echo "  - $repo"
        echo "    Workspaces: $workspaces"
    done
fi

echo ""
echo "============================================"
echo "Summary:"
echo "  Total repos in workspaces: ${#all_repos[@]}"
echo "  Missing from mapping: ${#missing_repos[@]}"
echo "  Available in mapping: $((${#all_repos[@]} - ${#missing_repos[@]}))"
echo "============================================"
