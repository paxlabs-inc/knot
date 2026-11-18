# Knot Space

Online repository server for Knot packages.

## Features

- Package registry API
- Health check endpoint
- JSON-based package metadata
- RESTful API design

## API Endpoints

- `GET /` - Service information
- `GET /health` - Health check
- `GET /packages` - List all packages
- `GET /packages/<name>` - Get specific package
- `POST /packages` - Create new package

## Development

```bash
# Run the server
cargo run

# The server will start on http://localhost:8000
```

## Package Format

```json
{
  "name": "package-name",
  "version": "1.0.0",
  "team": "optional-team-name",
  "description": "Package description",
  "download_url": "https://example.com/package.tar.gz"
}
```
## Mirroring popular packages

`scripts/import-popular.ts` publishes the most-downloaded npm, crates.io, PyPI and Go
packages (curated lists in `scripts/popular-packages.ts`) under the `mirror` user,
tagged `mirror` + `npm` / `crates` / `pypi` / `go`.

```bash
# from apps/backend, on the machine/volume that serves ./uploads
DATABASE_URL=... KNOT_SPACE_URL=https://<registry-domain> bun run import:popular
bun run import:popular -- --ecosystems npm,crates --limit 20 --dry-run
```

Re-running is idempotent (already-present versions are skipped). Names are normalised to
Knot's rules (`socket.io` -> `socket-io`, `serde_json` -> `serde-json`, Go modules use
their last path segment); when two ecosystems share a name, the first one imported keeps it.
