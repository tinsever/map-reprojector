# CartA

CartA is a web app and REST API for reprojecting SVG world maps and extracting regional map sections with alternative cartographic projections.

## Features

- Reproject SVG maps between Plate Carree, Equal Earth, and Wagner VII
- Extract regions by corner bounds or center/span
- Apply centered regional projections including AEQD, LAEA, Orthographic, Stereographic, LCC, and Transverse Mercator
- Preview inputs and outputs in a React frontend
- Browse downloadable sample files through the API
- Explore the API through Swagger UI

## Repository Layout

```text
.
├── backend/                 Flask API and projection logic
├── frontend/                React + TypeScript UI
├── examples/                API usage examples
├── docker-compose.dev.yml   Local development stack
├── docker-compose.prod.yml  Production-style stack
├── docker-compose.dokploy.yml
├── requirements.txt         Python dependencies
└── Weltkarte.svg            Sample input map
```

## Local Development

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r ../requirements.txt
python api_main.py
```

Backend URLs:

- API: [http://localhost:5100/api](http://localhost:5100/api)
- Docs: [http://localhost:5100/docs](http://localhost:5100/docs)

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend URL:

- App: [http://localhost:5173](http://localhost:5173)

The Vite dev server proxies `/api` requests to `http://localhost:5100`.

## Docker

Development stack:

```bash
docker compose -f docker-compose.dev.yml up --build
```

Production-style stack:

```bash
docker compose -f docker-compose.prod.yml up --build
```

Default URLs:

- Frontend: [http://localhost](http://localhost)
- Backend docs: [http://localhost:5100/docs](http://localhost:5100/docs)

## Configuration

Backend environment variables:

- `CORS_ORIGINS`: Comma-separated allowlist for browser origins. Defaults to `*`.
- `LOG_LEVEL`: Python log level. Defaults to `INFO`.
- `FLASK_DEBUG`: Set to `1` for local debug mode.

## API Summary

- `GET /api/health/`
- `GET /api/files/`
- `GET /api/files/<filename>`
- `POST /api/reproject/`
- `POST /api/extract/corners`
- `POST /api/extract/center`

Example reprojection request:

```json
{
  "input_svg": "Weltkarte.svg",
  "direction": "plate-to-equal",
  "output_width": 1800,
  "padding": 0.0,
  "orientation": "normal"
}
```

Example extraction request:

```json
{
  "input_svg": "Weltkarte.svg",
  "top_left": [-10, 70],
  "bottom_right": [40, 35],
  "output_width": 800,
  "reproject": true,
  "projection": "aeqd"
}
```

## Public Repo Notes

- Generated files, caches, and local runtime artifacts are ignored.
- The frontend no longer points at a private external download host.
- Only the documented app and API assets remain in the repository root.

## License

MIT. See [LICENSE](LICENSE).
