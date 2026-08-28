# SecureCore Live Agents

This directory is the staging home for agents intended to become live runtime
agents.

Current rule:

```text
Drop candidates here.
Review contracts here.
Test here.
Promote into securecore/agents only after explicit approval.
```

Nothing in this directory is wired into the running organism by directory
presence alone. Runtime activation still requires explicit registration in the
application factory and tests proving the agent's read/write boundaries.

Promotion checklist:

- agent purpose is documented
- watched substrates are named
- emitted decisions are named
- allowed reads/writes are declared
- user-approval requirements are declared for security-impacting actions
- tests prove no direct mutation of evidence, firewall, lexicon, or substrates
- app factory registration is reviewed before activation

