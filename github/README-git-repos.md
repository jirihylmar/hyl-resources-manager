# GitHub Repository Management Scripts

This directory contains scripts to manage and clone all accessible GitHub repositories across multiple organizations.

## Files

### 1. `generate-clone-list.sh`
**Purpose**: Automated script to query GitHub API and generate repository lists and mappings.

**Features**:
- Automatically reads GitHub token from `~/.git-credentials`
- Queries all organizations you're a member of
- Fetches all repositories from each organization
- Includes your personal repositories
- Removes duplicates
- Sorts repositories by organization and name
- Generates both clone script and JSON mapping file

**Usage**:
```bash
./generate-clone-list.sh
```

**Output**: Creates/updates:
- `git-clone-commands.sh` - Clone commands for all repositories
- `workspace-repos.json` - JSON mapping of repo names to HTTPS URLs

---

### 2. `git-clone-commands.sh`
**Purpose**: Generated script containing all git clone commands for accessible repositories.

**Structure**:
- Organized by organization
- Alphabetically sorted within each organization
- Contains summary statistics
- Uses HTTPS URLs for cloning

**Usage**:
```bash
# Clone all repositories
./git-clone-commands.sh

# Clone specific organization (edit script to select repos)
```

---

### 3. `workspace-repos.json`
**Purpose**: JSON mapping file that maps repository names to their HTTPS clone URLs.

**Structure**:
```json
{
  "repo-name": "https://github.com/org/repo-name.git",
  ...
}
```

**Used by**: `git-clone-commands-workspace-subset.sh` to determine correct clone URLs for repositories across different organizations.

---

### 4. `git-clone-commands-workspace-subset.sh`
**Purpose**: Smart repository manager for VS Code workspace files.

**Features**:
- Inspects all `.code-workspace` files in `$HOME`
- Extracts repository names from workspace folders
- Checks if repos exist in `$HOME` or `/mnt/c/Users/jirih`
- **Updates** existing repos (git pull) if clean
- **Clones** missing repos using correct organization URLs from mapping
- Uses HTTPS URLs for all clone operations
- Validates all repos exist in GitHub mapping
- Provides detailed logging of missing repositories

**Workspaces processed**:
- metadata.code-workspace
- goldsport.code-workspace
- manufacturing.code-workspace
- models.code-workspace
- databridge.code-workspace
- docs.code-workspace
- system.code-workspace
- digital-horizon.code-workspace
- iot.code-workspace

**Usage**:
```bash
./git-clone-commands-workspace-subset.sh
```

**Output**:
- Updates existing repositories with latest changes
- Clones missing repositories to `$HOME`
- Reports any repos not found in GitHub mapping
- Summary of processed repositories

---

### 5. `check-workspaces.sh`
**Purpose**: Validation script to check workspace integrity.

**Features**:
- Extracts all repositories from workspace files
- Compares against GitHub mapping
- Reports missing repositories
- Shows which workspaces reference missing repos

**Usage**:
```bash
./check-workspaces.sh
```

---

## Current Repository Count

| Organization | Repository Count |
|-------------|------------------|
| BM-Nutritech | 6 |
| Danse4mobility | 87 |
| DigitalHorizonCz | 16 |
| MasterIT-technologies-a-s | 4 |
| jirihylmar (personal) | 40 |
| **Total** | **153** |

**Workspace repositories**: 48 unique repositories across 9 workspaces

---

## Workflow

### Initial Setup
1. Run `generate-clone-list.sh` to create mapping file:
   ```bash
   ./generate-clone-list.sh
   ```
   This creates `workspace-repos.json` with all 153 repos from GitHub.

2. Run workspace script to clone/update workspace repos:
   ```bash
   ./git-clone-commands-workspace-subset.sh
   ```
   This processes all 9 workspaces and manages 48 repositories.

### Regular Updates
Simply run the workspace script to update all repos:
```bash
./git-clone-commands-workspace-subset.sh
```

This will:
- Update existing repos with `git pull` (if working directory is clean)
- Clone any new repos added to workspaces
- Report repos missing from GitHub

### Adding New Repositories
1. Add repository to GitHub
2. Regenerate mapping:
   ```bash
   ./generate-clone-list.sh
   ```
3. Update workspace repos:
   ```bash
   ./git-clone-commands-workspace-subset.sh
   ```

---

## How It Works

### Authentication
The scripts use the GitHub personal access token stored in `~/.git-credentials`:
```
https://jirihylmar:ghp_XXX...@github.com
```

### API Endpoints Used
1. **User info**: `GET /user` - Get authenticated username
2. **Organizations**: `GET /user/orgs` - List all organizations
3. **Personal repos**: `GET /user/repos` - User's personal repositories (owner only)
4. **Org repos**: `GET /orgs/{org}/repos` - Organization repositories

### Clone URL Selection
- Uses **HTTPS URLs** (`https://github.com/...`) for all clones
- Organization is determined from GitHub API (not guessed)
- Mapping file ensures correct organization for each repository

### Deduplication
Uses `sort -u` to remove duplicate entries that may appear in both personal and organization queries.

---

## Repository Location Strategy

The workspace script searches for existing repositories in:
1. `$HOME` (primary location for Linux/WSL)
2. `/mnt/c/Users/jirih` (Windows user directory via WSL)

New repositories are cloned to `$HOME` by default.

---

## Notes

- **HTTPS URLs**: All clone commands use HTTPS URLs (`https://github.com/...`)
- **No Guessing**: Organization is always resolved from GitHub API mapping
- **Token Security**: Token is read from git credentials; keep `~/.git-credentials` secure
- **API Limits**: GitHub API has rate limits; scripts make ~5-10 API calls per run
- **Pagination**: Handles 100 repos per page (sufficient for current org sizes)
- **Safe Updates**: Won't pull if working directory has uncommitted changes

---

## Missing Repositories

Some workspace repositories are not in GitHub (local-only or private):

| Repository | Workspace | Status |
|-----------|-----------|--------|
| `mitt-databridge-phase-1-reports` | databridge.code-workspace | Not in GitHub mapping |
| `_scratch` | system.code-workspace | Not in GitHub mapping |

These repos are skipped during clone/update operations.

---

## Troubleshooting

### "GitHub token not found"
Ensure `~/.git-credentials` contains your GitHub token:
```bash
cat ~/.git-credentials | grep github.com
```

### "Repository not found in mapping"
This means the repository doesn't exist in your GitHub account/organizations:
1. Check if repo exists on GitHub
2. Verify you have access
3. Run `generate-clone-list.sh` to refresh mapping
4. If repo is local-only, it will be skipped (this is expected)

### "Repository not found in mapping file"
The workspace script requires `workspace-repos.json`:
```bash
./generate-clone-list.sh  # Generate the mapping first
```

### Missing repositories in workspaces
Run the check script to see which repos are missing:
```bash
./check-workspaces.sh
```

### Authentication errors
- **HTTPS**: Ensure git credentials are configured
- Check: `git config --global credential.helper`

### Uncommitted changes prevent update
The script won't pull if you have uncommitted changes (safety feature).
Commit or stash changes first.

---

## Maintenance

**Recommended workflow**:
1. **Monthly**: Run `generate-clone-list.sh` to refresh GitHub mapping
2. **Daily/Weekly**: Run `git-clone-commands-workspace-subset.sh` to update workspace repos

**Check mapping freshness**:
```bash
ls -lh workspace-repos.json  # Check last modified date
```

**Validate workspaces**:
```bash
./check-workspaces.sh  # Shows missing repos
```

---

## File Permissions

All scripts should be executable:
```bash
chmod +x generate-clone-list.sh
chmod +x git-clone-commands-workspace-subset.sh
chmod +x check-workspaces.sh
```
