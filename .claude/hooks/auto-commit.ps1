# Stop-hook checkpoint: commit + push when the work tree is dirty AND the last
# commit is older than 10 minutes (throttle, so we don't commit every turn).
# Silent and non-fatal by design — always exits 0.
$ErrorActionPreference = 'SilentlyContinue'

# Must be inside a git work tree
$null = git rev-parse --is-inside-work-tree 2>$null
if ($LASTEXITCODE -ne 0) { exit 0 }

# Nothing changed -> nothing to do
$changes = git status --porcelain 2>$null
if (-not $changes) { exit 0 }

# Throttle: if a commit landed within the last 10 minutes, skip this turn
$recent = git log -1 --since='10 minutes ago' --format=%H 2>$null
if ($recent) { exit 0 }

$stamp = Get-Date -Format 'yyyy-MM-dd HH:mm'
git add -A 2>$null
git commit -m "chore: checkpoint $stamp" 2>$null | Out-Null
git push 2>$null | Out-Null
exit 0
