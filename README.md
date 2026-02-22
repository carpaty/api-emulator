# api-emulator

Simple API emulator for **OpenAI API** and **Ollama API**, built with **FastAPI** and deployable on **Google App Engine**.

## Endpoints

OpenAI-style:
- `GET /v1/models`
- `POST /v1/chat/completions`
- `POST /v1/completions`
- `POST /v1/embeddings`

Ollama-style:
- `GET /api/tags`
- `POST /api/generate`
- `POST /api/chat`

Health:
- `GET /healthz`

Image emulation:
- `POST /image` (returns dummy `image/png`)

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

## Quick test

OpenAI chat completion:
```bash
curl -s http://127.0.0.1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o-mini",
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

Ollama generate:
```bash
curl -s http://127.0.0.1:8000/api/generate \
  -H "Content-Type: application/json" \
  -d '{"model": "llama3", "prompt": "Say hi"}'
```

## Deploy to Google App Engine

```bash
gcloud app deploy
```

After deployment, replace your client base URL with your App Engine URL.

## GitHub Actions (PR test + deploy on merge)

Workflow file: `.github/workflows/ci-cd.yml`

- On `pull_request` to `main`: installs dependencies and runs `pytest`.
- On `push` to `main` (including merged PRs): runs tests, then deploys to App Engine.

Required GitHub repository secrets:

- `GCP_SA_KEY`: Google Cloud service account key JSON (as secret value).
- `GCP_PROJECT_ID`: Google Cloud project ID.
