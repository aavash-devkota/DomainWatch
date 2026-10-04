# Contributing

1. Fork → branch (`feat/…`, `fix/…`)
2. `pip install -e ".[dev]"`, keep `pytest` and `ruff` green
3. One logical change per PR; explain why
4. New providers/notifiers: implement the SDK protocol, register via entry points
5. Update CHANGELOG.md, docs/, and README

Release: tag `vX.Y.Z`, push tags — CI publishes the Docker image via `docker build`.
