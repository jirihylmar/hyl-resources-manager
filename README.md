# HYL Resources Manager

Infrastructure and resource management for AWS accounts and services.

## Repository Contents

### Documentation

- **amplify.md** - Inventory of all AWS Amplify apps across multiple accounts, including domain mappings and CloudFront distributions
- **accounts.md** - AWS account information and credentials
- **dynamodb-optimization.md** - DynamoDB cost optimization notes and settings
- **DOMAIN_TEST_RESULTS.md** - Latest domain configuration test results (2025-10-20)
- **CLAUDE.md** - Project-specific instructions for Claude Code

### Scripts

- **fix-all-domains.sh** - Automated script to recreate Amplify domain associations with correct configuration

### Configuration

- **.claude/** - Claude Code configuration directory

---

## AWS Account Structure

### HylmarJ (182059100462)
- **Region:** eu-west-1
- **Services:** AWS Amplify (7 apps)
- **Domain:** hub440.cz (managed via Route 53 in account 565393049593)

### JiHy__vsb__565 (565393049593)
- **Region:** eu-central-1
- **Services:** AWS Amplify (1 app), Route 53 (hub440.cz hosted zone)

### JiHy__vsb__299 (299025166536)
- **Region:** eu-central-1
- **Services:** AWS Amplify (12 apps), DynamoDB
- **Domains:** digital-horizon.cz, classicskischool.cz, zoneiot.cz

### JiHy__d4m__975 (975050190402)
- **Region:** eu-central-1
- **Services:** AWS Amplify (8 apps)

---

## Domain Management

### hub440.cz Domain Configuration

All subdomains are managed through AWS Amplify in account **HylmarJ (182059100462)** with DNS hosted in **JiHy__vsb__565 (565393049593)**.

**Route 53 Hosted Zone:** Z103393610EOYEE6MZJ2X

#### Active Domains

| Domain | App | CloudFront Distribution |
|--------|-----|------------------------|
| hub440.cz | fro-danse | dt8w87ml4ovg8.cloudfront.net |
| www.hub440.cz | fro-danse | dt8w87ml4ovg8.cloudfront.net |
| dev.hub440.cz | fro-danse | dt8w87ml4ovg8.cloudfront.net |
| next.hub440.cz | fro-danse-portal | d9d8ovyq1m7i0.cloudfront.net |
| prototype.hub440.cz | web-danse-tech | d3q7z0mr9k62v.cloudfront.net |
| doc-ropid.hub440.cz | doc-ropid | d25x1b4rejcxjp.cloudfront.net |
| doc-dataprocessing-lab.hub440.cz | doc-data-processing | d1dkjpu8nm4yf.cloudfront.net |
| doc-ipr.hub440.cz | doc-ipr | d2t0qwqov4592q.cloudfront.net |
| doc-internship.hub440.cz | doc-internship | d2zr0y5q3xz05c.cloudfront.net |

---

## Common Operations

### Recreate Amplify Domain Associations

If domain associations need to be recreated (e.g., to change subdomain configuration):

```bash
./fix-all-domains.sh
```

This script:
1. Deletes existing domain associations
2. Waits for rate limits to clear
3. Recreates domains with correct configuration
4. Logs all operations to `domain-fix.log`

### Update DNS Records

After recreating Amplify domains, DNS records may need updating in Route 53:

```bash
# List current DNS records
aws route53 list-resource-record-sets \
  --hosted-zone-id Z103393610EOYEE6MZJ2X \
  --profile JiHy__vsb__565

# Update a specific record (example for www.hub440.cz)
aws route53 change-resource-record-sets \
  --hosted-zone-id Z103393610EOYEE6MZJ2X \
  --profile JiHy__vsb__565 \
  --change-batch '{
    "Changes": [{
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "www.hub440.cz",
        "Type": "CNAME",
        "TTL": 300,
        "ResourceRecords": [{"Value": "dt8w87ml4ovg8.cloudfront.net"}]
      }
    }]
  }'
```

### Check Amplify Domain Status

```bash
# Check specific app domain
aws amplify get-domain-association \
  --app-id d3hgg9jtwyuijn \
  --domain-name hub440.cz \
  --profile HylmarJ \
  --region eu-west-1 \
  --query 'domainAssociation.{Status:domainStatus,SubDomains:subDomains[]}' \
  --output json
```

### Test Domain Connectivity

```bash
# DNS resolution
dig +short hub440.cz
dig +short www.hub440.cz CNAME

# HTTPS connectivity
curl -sL -o /dev/null -w "%{http_code}\n" https://hub440.cz
curl -sL -o /dev/null -w "%{http_code}\n" https://www.hub440.cz
```

---

## Notes

- **SSL Certificates:** Managed automatically by AWS Amplify (can take 15-40 minutes for new domains)
- **DNS Propagation:** Typically 5-10 minutes after Route 53 updates
- **Amplify Limitations:** Subdomain prefixes cannot contain dots (e.g., "www.prototype" not allowed)
- **Password Protected Sites:** Some documentation sites return HTTP 401 (expected behavior)

---

## Last Updated

2025-10-20 - Domain configuration updated and repository cleaned
