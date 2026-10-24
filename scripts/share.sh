#!/usr/bin/env bash
# Share the running demo with teammates through the Vercel site.
#   make demo     (first terminal: API :8100 + local models)
#   make share    (second terminal; Ctrl+C stops sharing)
# Opens a Cloudflare quick tunnel to the API, points the Vercel project's BACKEND_URL at
# it and redeploys the site. A quick tunnel gets a new address each time, which is why
# every run updates Vercel. The site only works while both terminals stay open.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
API_PORT="${API_PORT:-8100}"
CLOUDFLARED="${CLOUDFLARED:-$(command -v cloudflared || echo "$HOME/.local/bin/cloudflared")}"
LINK="$ROOT/frontend/.vercel/project.json"

if ! curl -s -m 3 "localhost:$API_PORT/health/ready" >/dev/null; then
  echo "The API is not running on :$API_PORT. Start it first with: make demo" >&2
  exit 1
fi
[ -x "$CLOUDFLARED" ] || { echo "cloudflared not found (expected at $CLOUDFLARED)." >&2; exit 1; }
[ -f "$LINK" ] || { echo "Vercel project not linked: run 'npx vercel link' in frontend/." >&2; exit 1; }
# Vercel ignores .gitignore: without this file the upload would include .env
[ -f "$ROOT/.vercelignore" ] || { echo "Missing .vercelignore: refusing to upload .env and the backend to Vercel." >&2; exit 1; }

LOG="$(mktemp -t tunnel)"
"$CLOUDFLARED" tunnel --no-autoupdate --url "http://localhost:$API_PORT" >"$LOG" 2>&1 &
TUNNEL_PID=$!
trap 'kill $TUNNEL_PID 2>/dev/null; rm -f "$LOG"' EXIT INT TERM

URL=""
for _ in $(seq 1 30); do
  URL="$(grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' "$LOG" | head -1 || true)"
  [ -n "$URL" ] && break
  sleep 1
done
[ -n "$URL" ] || { echo "The tunnel did not start:" >&2; cat "$LOG" >&2; exit 1; }
echo "Tunnel: $URL — waiting until it answers…"
for _ in $(seq 1 30); do
  curl -s -m 5 "$URL/health/ready" >/dev/null && break
  sleep 2
done

export VERCEL_ORG_ID VERCEL_PROJECT_ID
VERCEL_ORG_ID="$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['orgId'])" "$LINK")"
VERCEL_PROJECT_ID="$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['projectId'])" "$LINK")"
cd "$ROOT"  # the Vercel project's root directory is frontend/, relative to the repo
echo "Pointing Vercel at the tunnel and redeploying (about a minute)…"
npx -y vercel@latest env add BACKEND_URL production --value "$URL" --force --yes >/dev/null
DEPLOY_LOG="$(mktemp -t deploy)"
if ! npx -y vercel@latest deploy --prod --yes >"$DEPLOY_LOG" 2>&1; then
  echo "The Vercel deployment failed:" >&2
  cat "$DEPLOY_LOG" >&2
  exit 1
fi
rm -f "$DEPLOY_LOG"

echo
echo "Shared: https://patent-intelligence-rag.vercel.app"
echo "Keep this terminal and 'make demo' open. Ctrl+C stops sharing."
wait $TUNNEL_PID
