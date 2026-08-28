# Privacy Boundary

Local Memory Chat is designed so the public repo can be shared without private memory.

## Public Repo May Contain

```text
synthetic demo chats
sample project notes
schemas
tests
operator guides
import examples
```

## Public Repo Must Not Contain

```text
real user chats
private chat exports
private project notes
private receipts
API keys
machine-specific paths
runtime memory
generated indexes from private data
```

## Runtime Boundary

Private memory belongs under a local runtime path chosen by the operator.

Runtime data is ignored by Git.

The repo should be able to run its demo without private memory.

## Renderer Boundary

The renderer receives a cited memory packet.

The renderer may not search the web by default.

The renderer may not invent memory citations.

Returned citation IDs must already exist in the packet.

## Demo Boundary

Demo memory must be synthetic.

Synthetic demo records should be obvious, small, and replaceable.
