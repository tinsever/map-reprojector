# Frontend Smoke Test

## Preconditions

- Backend running on `http://localhost:5100`
- Frontend dev server running on `http://localhost:5173`
- Sample file available: `Weltkarte.svg`

## Checks

- Open the app and confirm the navbar shows a healthy API state.
- Upload `Weltkarte.svg` and verify the preview renders.
- Run `plate-to-equal` reprojection and download the result.
- Run `plate-to-wagner` reprojection and download the result.
- Extract a Europe region with corner coordinates and confirm the output preview updates.
- Open the Downloads page and confirm sample files are listed from `/api/files/`.
- Stop the backend briefly and confirm the health indicator switches to an error state.

## Build Verification

```bash
npm run build
```

**Tester:** _____________

**Passed:** ____ / 16

**Failed:** ____ / 16

**Notes:**
_______________________________________
_______________________________________
_______________________________________
