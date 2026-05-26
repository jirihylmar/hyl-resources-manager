# Incident: Recursive Lambda invocation loop — recordings-enricher

| Field | Value |
|---|---|
| Date | 2026-05-20 |
| AWS Account | 299025166536 (vsb-299) |
| Region | eu-central-1 |
| Amplify App | `d2thadu8jkg00`, branch `main` |
| Lambda function | `amplify-d2thadu8jkg00-mai-recordingsenricherlambda-7hdomPr9REk9` (friendly name `recordings-enricher`) |
| CloudFormation stack | `amplify-d2thadu8jkg00-main-branch-3aaa05dd55-storage0EC3F24A-12J292RLQU334` |
| Storage bucket | `amplify-d2thadu8jkg00-mai-recordingsbucket304ae6cd-wec5ccmzzyi2` |
| AWS Health event ARN | `arn:aws:notifications::299025166536:managed-notification-configuration/category/AWS-Health/sub-category/Operations/event/a01ks3h6ekfjgzyjqq1vvm2dskr` |

## What happened

On 2026-05-20, Lambda's recursive-loop protection detected and stopped the `recordings-enricher` function. Approximate billed scope:

| Time (UTC) | Invocations | Notes |
|---|---|---|
| 2026-05-20 17:00 | 626,704 | loop active |
| 2026-05-20 18:00 | 270,995 | loop active (+274,209 dropped by guard) |
| 2026-05-20 19:00 | 2 | loop neutralised |

Approximately **898k invocations were charged** before AWS dropped the rest. The guard auto-disabled recursive invocations for this function. AWS Lambda will keep that protection until the loop is fixed and the function is re-enabled from the AWS Health console.

## Root cause

The recordings bucket (`amplify-d2thadu8jkg00-mai-recordingsbucket304ae6cd-wec5ccmzzyi2`) had an `S3 → Lambda` notification that invoked the enricher on `PutObject` events. The Lambda writes four sidecar objects back to the same bucket on every invocation:

- `documents/<resourceId>/<file>.txt`
- `metadata/audio/<resourceId>/<file>.metadata.json`
- `metadata/datasets/<resourceId>/<file>.metadata.json`
- `metadata/documents/<resourceId>/<file>.metadata.json`

Each sidecar write re-triggered the Lambda → unbounded self-recursion until the guard tripped.

Sample log evidence (RequestId `5039b2ad-ae83-405f-b236-a8421ecd23fb`):

```
read transcript 0 chars for resourceId=f8b54a03-… from
  s3://resources-extite-ss0-infdev-565393049593/datasets/…/short-recording.wav.json
wrote sidecars for f8b54a03-…: documents/…/short-recording.wav.txt,
  metadata/audio/…/short-recording.wav.metadata.json,
  metadata/datasets/…/short-recording.wav.json.metadata.json,
  metadata/documents/…/short-recording.wav.txt.metadata.json
```

The fact that the upstream transcript is read from a different account (`565393049593`) does not prevent the loop — the loop is purely between the Lambda and its own write target.

## Current state

- Bucket notification configuration is now **empty** (someone removed it after the incident).
- **No EventBridge rules** target the function.
- Last invocation **2026-05-21 10:00 UTC**; silent since.
- Lambda code was redeployed **2026-05-21 10:01 UTC**.
- Feature is effectively **offline** — no trigger is wired up.

## Required fix

Re-introduce the trigger in a way that cannot self-feed. Any one of:

### Option A — Trigger on the upstream bucket only (recommended)

Notification on `resources-extite-ss0-infdev-565393049593`, prefix `datasets/`, suffix `.json`. The Lambda writes only to the recordings bucket, so there is no path back to the trigger source.

### Option B — Trigger on the recordings bucket but scope by prefix

S3 notification: `prefix=audio/`, `suffix=.wav` (or whatever the ingress prefix is). Lambda writes are confined to `documents/` and `metadata/` — those prefixes must never overlap the trigger prefix. Add a guard at the top of the handler that returns early if the incoming key starts with `documents/` or `metadata/`.

### Option C — Use EventBridge with explicit prefix/suffix filters

Same constraints as B but configured in EventBridge rather than S3 notifications. Easier to audit.

Whatever you pick, **codify it in the Amplify backend** (CDK / `amplify/storage` definition) so the next deploy doesn't recreate the broken notification.

## Verification (run after deploy)

1. Upload one test object that should trigger enrichment.
2. Confirm exactly **one** Lambda invocation in CloudWatch `Invocations` metric.
3. Confirm `RecursiveInvocationsDropped` stays at 0.
4. Confirm sidecars land in the expected prefixes.
5. Re-enable invocations in the AWS Health console if Lambda is still blocking them.

## Owner action items

- [ ] Acknowledge the AWS Health event in the console for `299025166536` so it stops re-surfacing.
- [ ] Apply one of the fix options above in the Amplify backend.
- [ ] Provide a postmortem entry once the fix is deployed.
