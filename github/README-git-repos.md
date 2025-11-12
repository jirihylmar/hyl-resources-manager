# GitHub Repository Management Scripts

This directory contains scripts to manage and clone all accessible GitHub repositories.

## Files

### 1. `generate-clone-list.sh`
**Purpose**: Automated script to query GitHub API and generate a list of all accessible repositories.

**Features**:
- Automatically reads GitHub token from `~/.git-credentials`
- Queries all organizations you're a member of
- Fetches all repositories from each organization
- Includes your personal repositories
- Removes duplicates
- Sorts repositories by organization and name
- Generates executable clone script

**Usage**:
```bash
./generate-clone-list.sh
```

**Output**: Creates/updates `git-clone-commands.sh`

---

### 2. `git-clone-commands.sh`
**Purpose**: Generated script containing all git clone commands for accessible repositories.

**Structure**:
- Organized by organization
- Alphabetically sorted within each organization
- Contains summary statistics
- Ready to execute

**Usage Options**:

**Clone all repositories**:
```bash
./git-clone-commands.sh
```

**Clone specific organization** (copy relevant section):
```bash
# Example: Clone only BM-Nutritech repos
git clone git@github.com:BM-Nutritech/nutritech-base.git
git clone git@github.com:BM-Nutritech/nutritech-kms.git
# ... etc
```

**Clone with custom directory structure**:
```bash
# Create org directories first
mkdir -p repos/{BM-Nutritech,Danse4mobility,DigitalHorizonCz,MasterIT-technologies-a-s,jirihylmar}

# Then clone into respective directories
cd repos/BM-Nutritech && git clone git@github.com:BM-Nutritech/nutritech-base.git
# ... etc
```

---

## Current Repository Count

| Organization | Repository Count |
|-------------|------------------|
| BM-Nutritech | 6 |
| Danse4mobility | 87 |
| DigitalHorizonCz | 16 |
| MasterIT-technologies-a-s | 4 |
| jirihylmar (personal) | 6 |
| **Total** | **119** |

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
3. **Personal repos**: `GET /users/{username}/repos` - User's personal repositories
4. **Org repos**: `GET /orgs/{org}/repos` - Organization repositories

### Deduplication
Uses `sort -u` to remove duplicate entries that may appear in both personal and organization queries.

---

## Regenerating the List

When to regenerate:
- New repositories are created
- You join new organizations
- Repository access changes

Simply run:
```bash
./generate-clone-list.sh
```

The script will:
1. Query GitHub API for latest repository list
2. Remove duplicates
3. Sort by organization and name
4. Regenerate `git-clone-commands.sh`
5. Display summary statistics

---

## Notes

- **SSH URLs**: All clone commands use SSH URLs (`git@github.com:...`)
- **Token Security**: Token is read from git credentials; keep `~/.git-credentials` secure
- **API Limits**: GitHub API has rate limits; this script makes ~5-10 API calls
- **Pagination**: Currently fetches first 100 repos per organization (increase if needed)

---

## Troubleshooting

### "GitHub token not found"
Ensure `~/.git-credentials` contains your GitHub token:
```bash
cat ~/.git-credentials | grep github.com
```

### Missing repositories
- Check if you have access to the repository
- Verify organization membership
- Increase pagination limit in `generate-clone-list.sh` if org has >100 repos

### "Permission denied (publickey)"
- Ensure SSH keys are set up: `ssh -T git@github.com`
- Add SSH key to GitHub: https://github.com/settings/keys

---

## Maintenance

**Recommended**: Run `generate-clone-list.sh` monthly to keep repository list up-to-date.

**Last generated**: Check the timestamp in `git-clone-commands.sh` header.
