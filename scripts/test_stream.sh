#!/usr/bin/env bash
#
# Test manuel de POST /api/v1/analyses/temporary/stream (SSE).
# Remplace Insomnia, qui envoie du JSON alors que l'endpoint attend du multipart/form-data.
#
# Usage :
#   ./scripts/test_stream.sh <cv.pdf> <offre.txt>
#   ./scripts/test_stream.sh <cv.pdf> <offre.txt> --pretty     # formate chaque event JSON
#
# Variables d'environnement :
#   API_URL   (défaut: http://localhost:8000)
#   USER_ID   (défaut: premier utilisateur trouvé en base)
#   API_TOKEN (si fourni, on ne génère pas de token)
#
set -euo pipefail

API_URL="${API_URL:-http://localhost:8000}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="$ROOT/.venv/bin/python"

CV_FILE="${1:-}"
JOB_FILE="${2:-}"
PRETTY="${3:-}"

if [[ -z "$CV_FILE" || -z "$JOB_FILE" ]]; then
  echo "Usage: $0 <cv.pdf> <offre.txt> [--pretty]" >&2
  exit 1
fi
for f in "$CV_FILE" "$JOB_FILE"; do
  [[ -f "$f" ]] || { echo "Fichier introuvable : $f" >&2; exit 1; }
done

# ── Token ───────────────────────────────────────────────────────────────────
if [[ -z "${API_TOKEN:-}" ]]; then
  echo "→ Génération d'un token API..." >&2
  API_TOKEN="$(
    USER_ID="${USER_ID:-}" "$PYTHON" - <<'PY' 2>/dev/null | tail -1
import asyncio, os, sys
from app.core.config import settings
from app.core.security import create_api_token
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

async def first_user() -> str:
    engine = create_async_engine(settings.database_url)
    try:
        async with engine.connect() as conn:
            row = (await conn.execute(text("select id from users limit 1"))).first()
    finally:
        await engine.dispose()
    if row is None:
        sys.exit("Aucun utilisateur en base — passe USER_ID=<uuid>")
    return str(row[0])

user_id = os.environ.get("USER_ID") or asyncio.run(first_user())
print(create_api_token(user_id))
PY
  )"
  [[ -n "$API_TOKEN" ]] || { echo "Échec de génération du token" >&2; exit 1; }
fi

# ── Type MIME du CV ─────────────────────────────────────────────────────────
# (tr plutôt que ${var,,} : le bash 3.2 livré avec macOS ne le supporte pas)
case "$(printf '%s' "$CV_FILE" | tr '[:upper:]' '[:lower:]')" in
  *.pdf)  MIME="application/pdf" ;;
  *.docx) MIME="application/vnd.openxmlformats-officedocument.wordprocessingml.document" ;;
  *.txt)  MIME="text/plain" ;;
  *)      MIME="application/octet-stream" ;;
esac

echo "→ POST $API_URL/api/v1/analyses/temporary/stream" >&2
echo "  cv_file        = $CV_FILE ($MIME)" >&2
echo "  job_description= $JOB_FILE ($(wc -c < "$JOB_FILE" | tr -d ' ') octets)" >&2
echo >&2

# -N : pas de buffering, indispensable pour voir le flux SSE arriver en direct.
# -F "champ=<fichier" : envoie le CONTENU du fichier comme valeur texte du champ.
# -F "champ=@fichier" : envoie le fichier comme upload.
curl -sN --max-time 300 \
  -X POST "$API_URL/api/v1/analyses/temporary/stream" \
  -H "Authorization: Bearer $API_TOKEN" \
  -F "job_description=<$JOB_FILE" \
  -F "cv_file=@$CV_FILE;type=$MIME" \
| if [[ "$PRETTY" == "--pretty" ]]; then
    while IFS= read -r line; do
      [[ "$line" == data:* ]] || continue
      payload="${line#data: }"
      echo "$payload" | "$PYTHON" -c 'import json,sys; print(json.dumps(json.load(sys.stdin), indent=2, ensure_ascii=False))' 2>/dev/null \
        || echo "$payload"
      echo "───"
    done
  else
    cat
  fi
