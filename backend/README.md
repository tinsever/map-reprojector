# CartA Backend

Flask API for SVG map reprojection, section extraction, and downloadable sample files.

## Run Locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r ../requirements.txt
python api_main.py
```

URLs:

- API: [http://localhost:5100/api](http://localhost:5100/api)
- Docs: [http://localhost:5100/docs](http://localhost:5100/docs)

## Environment Variables

- `CORS_ORIGINS`: Comma-separated browser origin allowlist. Defaults to `*`.
- `LOG_LEVEL`: Logging level. Defaults to `INFO`.
- `FLASK_DEBUG`: Set to `1` to run the development server in debug mode.

## Endpoints

- `GET /api/health/`
- `GET /api/files/`
- `GET /api/files/<filename>`
- `POST /api/reproject/`
- `POST /api/extract/corners`
- `POST /api/extract/center`

## Docker

Build from the repository root:

```bash
docker build -f backend/Dockerfile -t carta-api:latest backend
```

## License

MIT. See [LICENSE](../LICENSE).
