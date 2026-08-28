# SecureCore ChatGPT Prompt Library

This directory holds selectable prompt contracts for the OpenAI-backed SecureCore chat path.

Only lightweight identity and catalog metadata are included in the model instructions by default. Prompt bodies stay here until SecureCore deliberately selects or loads them.

Prompt docs should use front matter:

```text
---
prompt_id: short_stable_id
title: Human Title
when_to_use: One sentence describing the routing condition.
---
Prompt body here.
```

Rules:
- Keep identity small.
- Do not paste every doctrine file into every request.
- Prompt bodies are contracts, not proof.
- SecureCore gates all real actions.
- Receipts and ledgers remain source truth.

Imported packs:
- `Kaladn/Prompts` factual codebase audit prompt pack, split into selectable prompt contracts with stable `prompt_id` values.

Architecture docs do not belong in this prompt library. They live under `securecore/architecture_docs` and are loaded as selected reference documents, not prompt contracts.
