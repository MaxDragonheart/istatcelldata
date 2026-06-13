#!/usr/bin/env bash
#
# Script di rilascio per il progetto istat-census-data:
# - build + pubblicazione del pacchetto su PyPI usando Poetry
# - deploy documentazione su GitHub Pages tramite MkDocs
#
# Uso:
#   ./release.sh
#   RUN_TESTS=1 ./release.sh   # per eseguire i test
#   PYPI_DRY_RUN=1 ./release.sh # build e publish dry-run, senza deploy docs
#   DEPLOY_DOCS=0 ./release.sh  # pubblica su PyPI senza deploy docs
#

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

echo "🔎 Verifica presenza pyproject.toml..."
if [[ ! -f "pyproject.toml" ]]; then
  echo "❌ Errore: pyproject.toml non trovato in $PROJECT_ROOT"
  exit 1
fi

# -------------------------------------------------------------
# 1️⃣ Estrarre versione da pyproject.toml
# -------------------------------------------------------------
echo "📄 Lettura versione da pyproject.toml..."
PACKAGE_NAME=$(python3 - << 'EOF'
import tomllib, pathlib
data = tomllib.loads(pathlib.Path("pyproject.toml").read_text())
print(data["tool"]["poetry"]["name"])
EOF
)

VERSION=$(python3 - << 'EOF'
import tomllib, pathlib
data = tomllib.loads(pathlib.Path("pyproject.toml").read_text())
print(data["tool"]["poetry"]["version"])
EOF
)

echo "📦 Distribuzione PyPI: $PACKAGE_NAME"
echo "📦 Versione trovata: $VERSION"

# -------------------------------------------------------------
# 2️⃣ Verificare che esista un tag git corrispondente
# -------------------------------------------------------------
echo "🔍 Controllo tag git corrispondente..."

if git rev-parse "v$VERSION" >/dev/null 2>&1; then
    TAG="v$VERSION"
elif git rev-parse "$VERSION" >/dev/null 2>&1; then
    TAG="$VERSION"
else
    echo "❌ Nessun tag git trovato per la versione $VERSION"
    echo ""
    echo "💡 Crea un tag prima di rilasciare:"
    echo "   git tag v$VERSION"
    echo "   git push origin v$VERSION"
    exit 1
fi

echo "✅ Trovato tag git corretto: $TAG"

# -------------------------------------------------------------
# 3️⃣ Chiedere il token PyPI
# -------------------------------------------------------------
if [[ -z "${POETRY_PYPI_TOKEN_PYPI:-}" ]]; then
    echo ""
    echo "🔐 Nessun token PyPI trovato."
    echo "Inserisci un token PyPI valido per il progetto '$PACKAGE_NAME'."
    echo "Se usi un token project-scoped, deve essere scoped esattamente a '$PACKAGE_NAME'."
    echo "Per la prima pubblicazione del progetto rinominato può servire un token account-wide."
    echo "Il token deve iniziare per 'pypi-'."
    read -rsp "Token: " TOKEN
    echo ""

    if [[ -z "$TOKEN" ]]; then
        echo "❌ Nessun token inserito. Pubblicazione annullata."
        exit 1
    fi

    echo "🔑 Token salvato per questa sessione."
else
    echo "🔑 Token PyPI rilevato dalla variabile d'ambiente."
    TOKEN="$POETRY_PYPI_TOKEN_PYPI"
fi

if [[ "$TOKEN" != pypi-* ]]; then
    echo "❌ Token PyPI non valido: deve iniziare per 'pypi-'."
    exit 1
fi

export POETRY_PYPI_TOKEN_PYPI="$TOKEN"
echo "🔐 Token usato solo da POETRY_PYPI_TOKEN_PYPI per questa sessione."
echo "ℹ️ Non salvo il token nella config di Poetry per evitare credenziali persistenti."

# -------------------------------------------------------------
# 4️⃣ Installare dipendenze Poetry
# -------------------------------------------------------------
echo "📦 Installazione/aggiornamento dipendenze..."
poetry install --no-interaction --no-root

# -------------------------------------------------------------
# 5️⃣ Esecuzione facoltativa dei test
# -------------------------------------------------------------
if [[ "${RUN_TESTS:-0}" == "1" ]]; then
  echo "🧪 Esecuzione test (RUN_TESTS=1)..."
  poetry run pytest
else
  echo "⏭  Test disattivati (default). Imposta RUN_TESTS=1 per abilitarli."
fi

# -------------------------------------------------------------
# 6️⃣ Build pulita + publish su PyPI (verbose)
# -------------------------------------------------------------
echo "🏗️ Build pulita del pacchetto..."
poetry build --clean

PUBLISH_ARGS=(publish --no-interaction -vvv)
if [[ "${PYPI_DRY_RUN:-0}" == "1" ]]; then
  echo "🧪 Dry run PyPI attivo: nessun file verrà caricato."
  PUBLISH_ARGS+=(--dry-run)
fi

PUBLISH_LOG="$(mktemp "${TMPDIR:-/tmp}/istat-census-data-publish.XXXXXX.log")"
cleanup_publish_log() {
  rm -f "$PUBLISH_LOG"
}
trap cleanup_publish_log EXIT

echo "🚀 Pubblicazione su PyPI..."
set +e
poetry "${PUBLISH_ARGS[@]}" 2>&1 | tee "$PUBLISH_LOG"
PUBLISH_STATUS=${PIPESTATUS[0]}
set -e

if [[ "$PUBLISH_STATUS" -ne 0 ]]; then
  echo ""
  echo "❌ Pubblicazione PyPI fallita."

  if grep -qi "project-scoped token is not valid for project" "$PUBLISH_LOG"; then
    echo "💡 Il token PyPI inserito è project-scoped ma non è valido per '$PACKAGE_NAME'."
    echo "   Crea un token scoped al progetto PyPI '$PACKAGE_NAME'."
    echo "   Se '$PACKAGE_NAME' non esiste ancora su PyPI, usa un token account-wide"
    echo "   per la prima pubblicazione, poi crea un token project-scoped per i rilasci successivi."
  elif grep -qi "Invalid API Token" "$PUBLISH_LOG"; then
    echo "💡 PyPI ha rifiutato il token. Verifica che non sia scaduto o revocato"
    echo "   e che abbia permessi di pubblicazione per '$PACKAGE_NAME'."
  fi

  exit "$PUBLISH_STATUS"
fi

# -------------------------------------------------------------
# 7️⃣ Deploy documentazione MkDocs
# -------------------------------------------------------------
DOCS_STATUS="Documentazione aggiornata su GitHub Pages"

if [[ "${PYPI_DRY_RUN:-0}" == "1" ]]; then
  DOCS_STATUS="Deploy documentazione saltato perché PYPI_DRY_RUN=1"
  echo "⏭  $DOCS_STATUS."
elif [[ "${DEPLOY_DOCS:-1}" == "1" ]]; then
  echo "📚 Deploy documentazione su GitHub Pages..."
  poetry run mkdocs gh-deploy --clean
else
  DOCS_STATUS="Deploy documentazione saltato perché DEPLOY_DOCS=0"
  echo "⏭  $DOCS_STATUS."
fi

if [[ "${PYPI_DRY_RUN:-0}" == "1" ]]; then
  PYPI_STATUS="Dry run PyPI completato (nessun upload)"
else
  PYPI_STATUS="Pubblicato su PyPI"
fi

echo ""
echo "🎉 Rilascio completato con successo!"
echo "   - Versione: $VERSION"
echo "   - Tag git trovato: $TAG"
echo "   - $PYPI_STATUS"
echo "   - $DOCS_STATUS"
echo ""
