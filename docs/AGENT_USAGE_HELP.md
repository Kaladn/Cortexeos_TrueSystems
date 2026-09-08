# Creation-bound code help

`truecore.live_agents.creator.materialize` extracts each selected callable's
exact source, coordinates, signature expressions and source/runtime hashes.
It embeds `truecore.agent_usage@1` and its hash in the created `.agent.json`.
Catalog prose does not populate usage facts. Source annotations and default
expressions are copied, not evaluated or interpreted.

The existing HelpCorpus exposes `agent:<id>` through help show/search. Set
`TRUECORE_HELP_AGENT_DIR` to the creator's `--agent-dir` in the host configuration.
The default is TrueCore's existing live-agent manifest directory. Help and
execution metadata share one manifest publication; no second help copy exists.

Generated manifests without usage, with broken bindings, or changed usage hashes
are rejected by the manifest validator. Existing non-generated agents without
usage are explicitly shown as unresolved, not silently qualified.

Purpose, effects, permissions, prerequisites, failure semantics and retry remain
unresolved. Neither source text nor catalog metadata proves backend behavior.
No inference may fill these fields. A later explicit executable contract can
supply facts only with direct code bindings and acceptance coverage.

General HelpCorpus entries now use authored files solely as a topic-to-source
map. Their prose and example commands are not returned. The control-API help
likewise returns exact Python excerpts with current hashes and coordinates,
never its former authored quick/operate summaries or documentation citations.
Topic selection is navigation, not evidence of relevance or behavior.

The existing TrueCore `help.query` operation also accepts exact `agent:<id>`
queries. This exposes help only, never a new execution operation or permission.
Host configuration controls `TRUECORE_HELP_AGENT_DIR`; the model cannot select
an arbitrary agent directory. Generated help is validated against the current
source at load time, including recomputation after a self-consistent hash edit.

All layers currently expose static facts, not inferred tutorials. This deliberate
limit means the help cannot yet explain effects or safe retry where executable
contracts are absent. Backend instruction qualification must be added with each
actual agent; neither this release nor a successful source check supplies it.
