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
- `POST /api/v1/awrag/query`
- `POST /api/v1/awrag/deeper-wider`
- `POST /api/v1/memory/ask`
- `GET|POST /api/v1/chat/conversations`
- `POST /api/v1/chat/turns`
- `POST /api/v1/chat/continue`

SecureCore remains its own organism and is observed through its existing local
health endpoint. Importing its Flask app here would start agents as an API import
side effect, so the control layer intentionally does not do that.
