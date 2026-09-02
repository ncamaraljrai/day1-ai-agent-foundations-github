# Day 1 — Foundations Lab Submission

**Learner:** Nilson Cardoso Amaral Junior  
**Course day:** Day 1 — Foundations  
**Submission status:** Written exercises complete. Code-analysis answers complete. Labs 1.2 and 1.3 still require one real model run for trace/path and token-count evidence.

> **Execution integrity note:** I did not fabricate model traces or token counts. The current execution environment does not have a reachable Ollama runtime, and no Anthropic API key is available here. Where the lab explicitly requires an observed run, I distinguish **code-derived analysis** from **run evidence still to capture**.

---

# Lab 1.1 — Plain call vs. agent: the gap on paper

## Task

**“Summarize what changed in our repository this week and tell me whether anything looks risky.”**

This is a realistic engineering task because “what changed” is factual and current, while “what looks risky” may require following evidence discovered during the investigation.

## 1. The plain-call ceiling

A single model call using only pretrained knowledge could explain **how** to review a repository for risk: inspect recent commits, dependency changes, security-sensitive files, database migrations, tests, deployment configuration, and large or unusual diffs.

What it could **not** know is what actually changed in my repository this week. It has not seen the private repository, the current commit history, the CI results, the open incidents, or the deployment state. If it supplied filenames, commit hashes, failures, or risk conclusions without those inputs, those details would be fabricated.

A plain call becomes valid if I paste a complete, bounded diff and ask the model only to review that supplied text. In that variant, the current facts are already in the prompt.

## 2. Missing-facts inventory

| Missing fact | Why the model cannot know it |
|---|---|
| Commits merged during the target week | Private and continuously changing |
| Exact code diff for each relevant commit | Private repository data |
| CI/test results for those commits | Private and changing after model training |
| Dependency/version changes | Current repository state |
| Security scanner findings | Private current system output |
| Database/schema migrations | Private repository state |
| Deployment status by environment | Operational state that changes continuously |
| Production errors after deployment | Current telemetry/private logs |
| Open incidents related to changed components | Private and current |
| Ownership of risky components | Organisation-specific/private |

## 3. Tool list

1. `list_commits(repo, branch, start_date, end_date)`
2. `get_commit_diff(repo, commit_sha)`
3. `get_ci_status(repo, commit_sha)`
4. `get_dependency_changes(repo, base_ref, head_ref)`
5. `get_security_findings(repo, commit_sha)`
6. `list_database_migrations(repo, base_ref, head_ref)`
7. `get_deployment_status(service, environment)`
8. `search_runtime_errors(service, start_time, end_time)`
9. `list_open_incidents(service, start_time, end_time)`
10. `get_code_owners(repo, paths)`

For a first production version I would keep these **read-only**.

## 4. Loop sketch

1. The agent starts by listing commits for the requested week.
2. It identifies the changed paths and sizes of the diffs.
3. Based on what it finds, it chooses which evidence to inspect next:
   - dependency-file change → inspect dependency/security findings;
   - database migration → inspect migration and deployment status;
   - auth/security-sensitive code → inspect tests and security findings;
   - high-risk service change → inspect runtime errors/incidents.
4. Each tool result is added to history.
5. It continues until every material change has either:
   - enough evidence for a risk assessment, or
   - an explicit “insufficient evidence” flag.
6. It returns a short weekly change summary, risk items, supporting evidence, and unresolved questions.

### Could the entire sequence be written in advance?

**Not completely.** The first collection step can be fixed, but the investigation path should branch based on what the changed files and test/deployment evidence reveal.

A good production design could therefore be **hybrid**: a deterministic workflow gathers the standard weekly evidence first, and an agent performs bounded, read-only investigation only for items that trigger risk rules.

## Value and risk

The agent adds value by deciding which evidence to inspect next when the relevant path depends on what the repository changes reveal. It adds risk because it can choose the wrong investigation path, misread evidence, waste calls, or produce an unsupported risk conclusion, so every finding should carry source evidence and the agent should have no write/deploy authority.

---

# Lab 1.2 — Build and run a real agent loop

## Structural observations from the supplied code

### 1. How many steps and which tools?

**Actual model-run evidence: TO CAPTURE LOCALLY.**

The intended successful path is approximately:

1. `lookup_order(order_id="4471")`
2. `get_today()`
3. derive the due date from the invoice date + payment terms
4. `count_business_days(start=<today>, end=<due_date>)`
5. produce final answer

The exact number of model-loop iterations can differ because the model may call more than one tool in a turn, may choose a different order, or may stop once it recognizes the invoice is already overdue.

### Important date note

The course example is written around **24 March 2026**, but the current date is later than the invoice due date. `lookup_order("4471")` returns an invoice date of **2026-03-03** with **30-day terms**, so the due date is **2026-04-02**. If the script is run today without freezing the date, `get_today()` will return a date after the due date. That changes the exercise outcome. For a reproducible comparison with the theory example, run once as-is and once with `get_today()` temporarily frozen to `2026-03-24`, clearly labelling the second run as a reproducibility modification.

### 2. Find the dependency

The arguments to:

`count_business_days(start=<today>, end=<due_date>)`

cannot be filled until earlier evidence is available:

- `start` depends on `get_today()`.
- `end` depends on the invoice date and terms returned by `lookup_order()`.

**Course-framing answer:** this demonstrates why later work depends on earlier observations.

**Engineering nuance:** argument dependency alone does not make a fixed workflow impossible; a fixed workflow can pass outputs from one step into the next. The stronger reason to use an agent is when the **next action itself** can change—for example, an order-not-found result should lead to clarification/recovery rather than continuing the same fixed happy path.

### 3. Who decides to stop?

The model makes the semantic decision by returning a response whose `stop_reason` is no longer `"tool_use"`.

The loop reads that decision here:

```python
if response.stop_reason != "tool_use":
```

So:

- **model:** decides “I have enough; I am done” versus “I need a tool”;
- **code:** enforces that decision and also enforces the independent hard ceiling `MAX_STEPS`.

### 4. Run it twice

**Actual two-run comparison: TO CAPTURE LOCALLY.**

What to record:
- run 1 step count;
- run 1 tool order;
- run 2 step count;
- run 2 tool order;
- whether either run combined tool calls in one assistant turn;
- whether either run took an unnecessary step.

Expected lesson: the path may differ because the model is making runtime decisions.

---

## Required modification (a) — break `get_today` description

Change:

```python
"description": "Returns a date."
```

**Actual result: TO CAPTURE LOCALLY.**

What I am testing: whether weakening the tool description makes the model fail to recognize when the tool should be used and instead guess or omit the current date.

**Interpretation:** if behavior degrades while the Python function is unchanged, the experiment shows that tool descriptions are part of agent behavior and safety.

---

## Required modification (b) — order `#9999`

Goal uses an order that does not exist.

`lookup_order("9999")` returns an informative error instead of crashing.

**Actual result: TO CAPTURE LOCALLY.**

A good behavior would be to stop and explain that the order is unknown or ask for a corrected id. A bad behavior would be to invent invoice details, continue with unrelated calculations, or repeatedly call tools without making progress.

The point is that an informative tool error gives the model something it can reason over.

---

## Required modification (c) — `MAX_STEPS = 2`

**Actual result: TO CAPTURE LOCALLY.**

Expected result for the intended multi-step path: the agent reaches the step ceiling before completing the task.

**Why production still needs the limit:** the ceiling can stop a correct but long run, but without a hard limit a wandering model can continue making calls indefinitely, increasing cost and latency and potentially repeating unsafe or useless behavior.

---

# Lab 1.3 — Plain call versus agent

## 1. What did the plain call do?

**Actual plain-call output: TO CAPTURE LOCALLY.**

Valid observed outcomes include:
- refuse because it lacks the order/date/calendar facts;
- ask for the missing facts;
- fabricate plausible invoice details and compute from them.

The important evaluation is not whether the prose sounds reasonable, but whether every required factual input is grounded.

## 2. If it produced numbers, are they real?

The source-of-truth fixture in `agent_loop.py` is:

- order: `4471`
- invoice date: `2026-03-03`
- terms: `30 days`
- customer: `Northwind Ltd`

Any different invoice date, payment term, customer, due date, or holiday fact produced by the plain call without being supplied is unsupported/fabricated.

## 3. Token comparison

| Run | Input tokens | Output tokens | Total |
|---|---:|---:|---:|
| Plain call | **TO MEASURE** | **TO MEASURE** | **TO MEASURE** |
| Agent | **TO MEASURE** | **TO MEASURE** | **TO MEASURE** |

The extra spend buys access to current/private facts, tool execution, iterative recovery, and evidence-grounded reasoning. It is justified only if those capabilities are actually necessary.

## 4. Variant where the plain call is correct

> “Given this invoice date, due date, holiday list, and today’s date pasted below, explain the business-day calculation in two sentences.”

All required facts are already present, so no lookup or adaptive tool loop is needed.

---

# Lab 1.4 — Design with the patterns

## Task

**Prepare a short research brief comparing three agent frameworks for an enterprise AI project.**

The required output is:
- three concrete options;
- current capabilities relevant to the project;
- trade-offs;
- evidence links;
- one recommendation with assumptions.

## Reason–act–observe

### Current history

Goal says the enterprise needs:
- Python support;
- tool calling;
- human approval for state-changing actions;
- tracing/evaluation;
- Azure-friendly deployment.

The history currently contains no verified current framework information.

### Reason

The agent decides that the first unresolved requirement is current support for human-in-the-loop and tracing in Framework A.

### Act

```text
search_official_docs(
    product="Framework A",
    query="human approval tool calls tracing evaluation"
)
```

### Observe

Suppose the tool returns:
- official documentation for approval checkpoints;
- a tracing feature;
- no evidence of one Azure-specific capability that had been assumed.

### Next decision

The agent updates the comparison: the first two requirements are supported, but it now needs a targeted search for deployment/integration evidence rather than assuming compatibility.

The new evidence changed the next action.

---

## Planning

A useful high-level plan:

1. **Define evaluation criteria from the project's requirements.**
   - Output: an explicit comparison rubric before researching products.

2. **Collect official evidence for each framework against each criterion.**
   - Output: capability matrix with one or more sources per material claim.

3. **Identify decision-changing gaps and constraints.**
   - Output: unsupported capabilities, deployment constraints, governance gaps, and lock-in concerns.

4. **Produce recommendation and sensitivity analysis.**
   - Output: preferred option plus “choose B instead if assumption X changes.”

These sub-tasks are actionable enough that another engineer could execute them.

---

## Replanning

### Discovery

During research, one candidate framework is found to have been deprecated or merged into a successor.

### Original later task

“Compare production deployment patterns for Framework A, B and C.”

### Replanned sequence

1. Verify deprecation/migration status from an official source.
2. Replace the deprecated option with its supported successor if that matches the original comparison intent.
3. Record the change explicitly rather than silently swapping products.
4. Re-run the capability matrix for the new candidate.
5. Update only recommendation sections affected by the replacement.

### What survived?

The evaluation criteria, evidence requirements, security criteria and recommendation format still survive.

**Lesson:** plan stable decision structure up front; keep volatile research targets easy to revise.

---

## Reflection

Two checkable questions:

1. **Does every material capability claim cite an official source that was actually retrieved during this run?**
2. **Does the recommendation depend on any requirement that one of the compared products was never evaluated against?**

### Error reflection would likely catch

A paragraph says Framework B is recommended for its tracing capability, but the evidence table contains no tracing source for B. A whole-draft review can notice that inconsistency.

### Error reflection may miss

The agent misunderstood an ambiguous requirement—e.g., interpreted “human approval” as approval of generated text instead of approval before a state-changing tool call. The same misunderstanding can survive both draft and self-critique.

That requires external verification: requirement-owner review or a concrete acceptance test.

---

## Pattern decision

**Use upfront planning + reason-act-observe + checkpoint replanning + reflection, with external source verification.**

- Planning buys consistent comparison criteria.
- Reason-act-observe buys adaptive research.
- Replanning handles deprecated products, missing evidence and newly discovered constraints.
- Reflection catches incomplete/internally inconsistent reporting.
- External verification is still required for current product claims and the final recommendation.

The extra model calls are justified because this is a current, evidence-sensitive decision rather than a one-shot writing transformation.

---

# Lab 1.5 — The checklist on my own work

## Task 1 — Rewrite a technical discovery note into a concise executive summary

**Verdict:** **Plain model call**

**Why:** it is a bounded transformation of supplied text. The sequence does not need to branch, and the model does not need external tools if the source note is already in the prompt.

**Risk:** omission or distortion.

**Control:** human review against the source note before client delivery. This is verification, not a reason to turn the task into an agent.

---

## Task 2 — Process an incoming support ticket by classifying it, retrieving relevant approved documentation, and drafting a response

**Verdict:** **Fixed workflow**

**Why:** the sequence is known in advance:

1. classify;
2. retrieve approved documents;
3. draft using retrieved evidence;
4. run deterministic checks;
5. route to human/send according to policy.

The models perform linguistic/retrieval work, but runtime autonomy is not required to choose the sequence.

---

## Task 3 — Investigate why a production integration pipeline processed only half the expected records

**Verdict:** **Agent**

**Why:** the investigation path cannot be predetermined. The next step depends on what the first evidence shows: ingestion counts, queue lag, schema errors, deployment changes, partition imbalance, downstream rejection, or another cause.

### Biggest risk

The agent concludes that a component is defective and modifies production configuration or data incorrectly.

### Reversibility × impact

**High impact + potentially irreversible** if the system has write/redeploy/delete capabilities.

### Guardrail

**Give the agent read-only access to logs, metrics, schemas, deployment history and query tools. It may propose a remediation, but it has no production write/deploy/delete tools. A human approves and executes any state-changing action.**

Additional guardrails:
- `MAX_STEPS`;
- tool allow-list;
- query time/range limits;
- source citations in the final diagnosis;
- explicit “insufficient evidence” state.

---

## Closing paragraph

Two of my three tasks came out as something other than an agent: one plain call and one fixed workflow. That is the expected result of applying the escalation ladder honestly. The agent is reserved for the production investigation because flexibility in choosing the next diagnostic step is essential there; using that same autonomy for rewriting or for a known ticket-processing sequence would add cost, latency and failure modes without adding useful capability.

---

# Remaining run evidence checklist

Before final submission, run the supplied code with Anthropic or the course Ollama adapter and replace every **TO CAPTURE / TO MEASURE** field above.

Minimum evidence to paste:

## Lab 1.2
- normal run 1: step count + tool order
- normal run 2: step count + tool order
- modification (a) observed behavior
- modification (b) observed behavior
- modification (c) observed behavior

## Lab 1.3
- plain-call output behavior
- plain-call input/output token counts
- agent total token counts

Do not replace these blanks with expected behavior and call it measured. The assessment explicitly asks for what happened in the real run.
