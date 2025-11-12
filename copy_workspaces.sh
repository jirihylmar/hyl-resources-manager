#!/bin/bash

# Script to find and copy all .code-workspace files from $HOME to Windows directory
# Destination: c:\Users\jirih\Documents\_local_settings\workspaces\
# Excludes .vscode-server history files

# Convert Windows path to WSL path
DEST_DIR="/mnt/c/Users/jirih/Documents/_local_settings/workspaces"

# Create destination directory if it doesn't exist
mkdir -p "$DEST_DIR"

# Find and copy all .code-workspace files, excluding .vscode-server/data/User/History
echo "Searching for .code-workspace files in $HOME (excluding history)..."
find "$HOME" -type f -name "*.code-workspace" -not -path "*/.vscode-server/data/User/History/*" -print0 | while IFS= read -r -d '' file; do
    echo "Copying: $file"
    cp "$file" "$DEST_DIR/"
done

echo "Done! All .code-workspace files have been copied to $DEST_DIR"
