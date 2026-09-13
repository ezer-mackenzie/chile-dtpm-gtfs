# Security policy

## Supported versions

Security fixes target the latest released version. During the initial 0.x series,
upgrade to the latest patch/minor release when a fix is announced.

## Reporting a vulnerability

Send a private report to the maintainer at
ramirez.ruiz.eliezer.reuven@gmail.com. Include the affected version, reproduction
steps, expected impact, and a minimal synthetic example when possible. Do not
include credentials, personal data, or large untrusted feeds in public issues.
There is no guaranteed response SLA; this is a community-maintained project.

For ordinary parser failures or invalid upstream feeds, use a GitHub issue with
sanitized reproduction details. This repository cannot correct DTPM source data.

## Input handling

Downloads have configurable byte limits. ZIP tables are streamed without archive
extraction; duplicate/unsafe paths and excessive declared expanded sizes are
rejected. Outputs do not replace existing files unless explicitly requested.
These controls do not make arbitrary untrusted archives risk-free or certify full
GTFS compliance. Applications accepting user-controlled URLs should enforce their
own network access policy; this library follows HTTP redirects.
