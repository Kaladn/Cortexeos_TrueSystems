# TrueSystems control API

Thin localhost API over the existing Linux TrueSystems Python interfaces.
It contains no cognition, retrieval, security-agent, or chat-chain business logic.

```bash
PYTHONPATH=control-api/src python -m truesystems_api.server
```

Default address: `http://127.0.0.1:3220`.

Endpoints:

- `GET /health` and `GET /api/v1/systems`
- `POST /api/v1/truemachine/pulse`
- `POST /api/v1/truemem/query`
- `POST /api/v1/truemem/deeper-wider`
- `POST /api/v1/memory/ask`
- `GET|POST /api/v1/chat/conversations`
- `POST /api/v1/chat/turns`
- `POST /api/v1/chat/continue`
- `GET /api/v1/help/topics`
- `POST /api/v1/help/query`

Chat turns sent through this API may select the read-only `truesystems-help`
provider with model `quick`, `operate`, or `source`. See
`../docs/HELP_SYSTEM.md`.

TrueCore remains its own organism and is observed through its existing local
health endpoint. Importing its Flask app here would start agents as an API import
side effect, so the control layer intentionally does not do that.
