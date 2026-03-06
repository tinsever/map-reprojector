# CartA Frontend

React + TypeScript frontend for the CartA API.

## Development

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173).

The dev server proxies `/api` to `http://localhost:5100`.

## Scripts

- `npm run dev`
- `npm run build`
- `npm run preview`
- `npm run lint`

## Features

- SVG upload and preview
- Reprojection workflows
- Regional extraction workflows
- Local download browser backed by `/api/files/`
- Health indicator for backend connectivity

## Production Build

```bash
npm run build
```

Build output is written to `frontend/dist/` and is intentionally ignored by git.

## License

MIT. See [LICENSE](../LICENSE).
