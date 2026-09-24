# Operator working method

Read the repository-root `AGENTS.md` first. This document retains the detailed human/operator roles, communication, stop, and return discipline relocated from the front door. The root policy and scoped component instructions still govern authorization and execution.

## 4. Human responsibilities

The human should be able to operate this workflow without becoming a data
engineer or statistician. The human supplies or authorizes:

- the data, dataset location, or external source to be acquired;
- access credentials through an approved secret channel, never pasted into chat;
- the broad subject, problem, or desired outcome;
- any non-negotiable semantic boundary, policy constraint, cost ceiling, or time
  limit;
- approval for privileged, destructive, paid, externally visible, or otherwise
  consequential operations;
- corrections when the agent misunderstands the domain;
- optional overrides to agent-proposed parameters.

The human is not required to choose technical thresholds, window sizes, joins,
null policies, statistical tests, plot scales, recovery rules, or file formats.
The operator agent must set those from the observed data and the requested
meaning, disclose them clearly, and freeze them before computation.

Human silence is not approval for privilege escalation, deletion, publication,
credential use, paid services, or a material expansion of scope. Human approval
of a study question is not approval to merge incompatible data layers.

## 5. Operator-agent responsibilities

The operator agent must:

1. locate and read relevant current project instructions before acting;
2. preserve the original human request and its meaning;
3. ask for the data when no authorized data source is present;
4. inspect the data before asking the human to design questions around it;
5. profile actual schemas and values rather than guessing field meaning;
6. shape reversible, source-linked analysis layers without altering raw data;
7. identify the questions each layer can and cannot answer;
8. ask what the human wishes to know after the data shape is visible;
9. convert that intent into independent evidence obligations;
10. choose every technical parameter needed to run the analysis;
11. mark each parameter as agent-set or human override;
12. explain thresholds and proxies in plain language;
13. freeze definitions and parameters before computing results;
14. use the narrowest real callable for each operation;
15. time every material stage, including failed attempts;
16. preserve source hashes, versions, epochs, units, IDs, coordinates, and
    receipts;
17. separate measurements, classifications, proxies, counterfactuals, and
    presentation-only transformations;
18. check raw-field relationships before interpreting aggregate associations;
19. label missing data as missing and unavailable measurements as unavailable;
20. verify the requested effect through the authorized production path against real runtime state and retain external receipts;
21. make charts use the exact vocabulary of the measurement or proxy;
22. communicate only claims supported by the resulting evidence packet;
23. disclose unresolved ambiguity and right-censoring;
24. return `NOT_IMPLEMENTED` when no real callable exists;
25. stop when the evidence reaches a fixed point rather than manufacturing a
    satisfying answer.

## 9. Communication contract

Before computation, tell the human:

- what data was found;
- what the layers represent;
- what is missing;
- which definitions/parameters the agent proposes;
- which claims will be measurements versus proxies/counterfactuals;
- any decision that materially changes meaning.

After computation, lead with the outcome. Include:

- answer per question;
- exact scope/population/time range;
- key parameters;
- evidence/receipt locations;
- negative results;
- coverage and censoring;
- claim-class labels where confusion is plausible;
- limitations and unsupported interpretations;
- timings and acceptance status when relevant.

Never require the human to read progress messages to understand the final answer.
Never conceal that a result is a proxy in a footnote only. Never use confident
prose to compensate for incomplete evidence.

## 10. Stop and refusal conditions

Stop, return a truthful status, or ask for the missing authority/input when:

- no data or authorized source is available;
- the source lacks the identity or measurement required by the question;
- layers would require a forbidden join;
- parameters cannot be derived without choosing the human's intended meaning;
- a frozen plan is absent or changed after freezing;
- the callable is absent or fails contract validation;
- evidence conflicts and cannot be resolved;
- requested action exceeds granted authority;
- only a proxy exists but the human requires a direct measurement;
- a causal claim is requested from association-only data;
- the source's resolution cannot support the requested timing;
- acceptance fails in a way that undermines the claimed result.

Permitted terminal language includes `NOT_IMPLEMENTED`, `NO_EVIDENCE`,
`PARTIAL_EVIDENCE`, `AMBIGUOUS_EVIDENCE`, `OPERATION_FAILED`,
`PARAMETERS_NOT_LOCKED`, `FORBIDDEN_LAYER_JOIN`, and `RIGHT_CENSORED`.

## 11. Required return discipline

Return component results unchanged enough to preserve:

- schema/version;
- source and plan hashes;
- work/study/question/obligation/parameter IDs;
- timestamps and timezones;
- units;
- exact categorical strings;
- evidence coordinates and citations;
- status and failure fields;
- service/action/device receipts;
- timings;
- warnings and limitations.

The operator may summarize, group, and visualize these records, but the canonical
artifact remains available. Never claim an operation ran without its actual
return value or receipt. Never change implementation merely to make a test or
expected outcome pass.

A receipt proves only that a record was published. Every action receipt must
separate execution status from verification status and name the scope of the
verification. It must explicitly represent `executed_but_outcome_unverified`
when the backend ran but the intended application or real-world outcome was not
observed. Receipt existence, a zero backend exit code, or successful input
delivery must never be promoted to verified task completion.
