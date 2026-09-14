# Detached TruePlug reference boundary

Everything below this directory is historical source or design evidence.

- Never import, register, mount, execute, package, or expose these files through
  TrueCore, TrueMachine, the control API, or any other TrueSystems runtime.
- Never add this directory to `PYTHONPATH`, plugin discovery paths, test
  discovery paths, application routes, service units, or production build
  inputs.
- Treat the copied runner and HTML applications as untrusted archaeology. Their
  presence in Git proves custody only; it does not qualify their behavior.
- Any future experiment must copy the needed material into a disposable,
  externally tested workspace and must not grant it access to canonical
  TrueSystems data, credentials, or live operations.
- A future TruePlug implementation must be new, separately bounded code. It may
  study these materials but may not make this reference tree callable.
