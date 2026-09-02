# Day 1 — Foundations Lab Submission

**Learner:** Nilson Cardoso Amaral Junior  
**Course day:** Day 1 — Foundations  
**Submission status:** Complete — written analysis plus real Lab 1.2/1.3 execution evidence.

> **Execution integrity note:** The execution traces, paths, stop reasons, and token counts in Labs 1.2 and 1.3 were captured from real local-model runs through Ollama using the course adapter. Raw traces are retained under `evidence/raw/`.

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

## Execution environment

- **Real model runtime:** Ollama
- **Model:** `qwen2.5:7b`
- **Evidence date:** `2026-09-02`
- **Evidence source:** real execution through the course `ollama_shim.py`
- **Raw traces:** `evidence/raw/`

No run data in this section is mocked or inferred.

## 1. How many steps did it take, and which tools did it call?

### Normal run 1

- **Steps:** 4
- **Tool order:** `lookup_order → get_today → count_business_days`
- **Stopped by:** `model_final`
- **Input tokens:** 2302
- **Output tokens:** 538
- **Total tokens:** 2840

Observed trace:

- Step 1: `lookup_order({"order_id": "4471"})` → `{"invoiced": "2026-03-03", "terms_days": 30, "customer": "Northwind Ltd"}`
- Step 2: `get_today({})` → `{"today": "2026-09-02"}`
- Step 3: `count_business_days({"start": "2026-04-02", "end": "2026-09-02"})` → `{"business_days": 107}`
- Step 4: no tool call; `stop_reason=end_turn`

### Normal run 2

- **Steps:** 4
- **Tool order:** `lookup_order → get_today → count_business_days`
- **Stopped by:** `model_final`
- **Input tokens:** 2318
- **Output tokens:** 434
- **Total tokens:** 2752

Observed trace:

- Step 1: `lookup_order({"order_id": "4471"})` → `{"invoiced": "2026-03-03", "terms_days": 30, "customer": "Northwind Ltd"}`
- Step 2: `get_today({})` → `{"today": "2026-09-02"}`
- Step 3: `count_business_days({"start": "2026-04-02", "end": "2026-09-02"})` → `{"business_days": 107}`
- Step 4: no tool call; `stop_reason=end_turn`

## 2. Find the dependency

The concrete arguments for `count_business_days(start, end)` depend on earlier observations:

- `start` is supplied by `get_today()`;
- `end` is derived from the invoice date and payment terms returned by `lookup_order()`.

The stronger agentic dependency appears on the error path: if `lookup_order()` reports that the order does not exist, the correct next action is no longer the same happy-path calculation. The model must respond to the observation rather than blindly execute a predetermined continuation.

## 3. Who decided to stop?

The model communicates its semantic decision through `response.stop_reason`. The orchestration code reads it here:

```python
if response.stop_reason != "tool_use":
```

The model therefore chooses whether it needs another tool or is ready to answer. Separately, my code owns the hard safety ceiling through `MAX_STEPS`.

## 4. Run it twice — non-determinism

- Run 1: `lookup_order → get_today → count_business_days` in **4** step(s)
- Run 2: `lookup_order → get_today → count_business_days` in **4** step(s)
- Same path and step count: **YES**

The important observation is empirical rather than assumed: these are the two paths actually returned by the local model.

---

## Required modification (a) — weaken `get_today` description

I changed the description to:

```text
Returns a date.
```

### Actual run

- **Steps:** 5
- **Tool order:** `lookup_order → lookup_order → get_today → count_business_days`
- **Stopped by:** `model_final`
- **Input tokens:** 3075
- **Output tokens:** 527

Observed trace:

- Step 1: `lookup_order({"order_id": "4471"})` → `{"invoiced": "2026-03-03", "terms_days": 30, "customer": "Northwind Ltd"}`
- Step 2: `lookup_order({"order_id": "4471"})` → `{"invoiced": "2026-03-03", "terms_days": 30, "customer": "Northwind Ltd"}`
- Step 3: `get_today({})` → `{"today": "2026-09-02"}`
- Step 4: `count_business_days({"end": "2026-09-02", "start": "2026-04-02"})` → `{"business_days": 107}`
- Step 5: no tool call; `stop_reason=end_turn`

**Result:** The model requested 4 tool call(s) in the path `lookup_order → lookup_order → get_today → count_business_days` before returning or stopping.

This experiment isolates prompt/tool-description quality because the underlying Python implementation of `get_today()` is unchanged.

---

## Required modification (b) — order `#9999`

### Actual run

- **Steps:** 2
- **Tool order:** `lookup_order`
- **Stopped by:** `model_final`
- **Input tokens:** 875
- **Output tokens:** 195

Observed trace:

- Step 1: `lookup_order({"order_id": "9999"})` → `{"error": "No order with id 9999. Known ids: ['4471', '4472']"}`
- Step 2: no tool call; `stop_reason=end_turn`

### Final model response

> It seems there is no order with the ID '9999'. The known order IDs are '4471' and '4472'. Let's proceed with one of these IDs to determine the number of business days left before the invoice goes overdue.
> 
> Shall we use order ID '4471' for this calculation? If not, please provide the correct order ID.

The tool returns an informative error rather than crashing. This gives the model an observation it can use to stop, clarify, recover, or—if it behaves poorly—expose that failure in the trace.

---

## Required modification (c) — `MAX_STEPS = 2`

### Actual run

- **Steps:** 2
- **Tool order:** `lookup_order → count_business_days`
- **Stopped by:** `max_steps`
- **Input tokens:** 900
- **Output tokens:** 255

Observed trace:

- Step 1: `lookup_order({"order_id": "4471"})` → `{"invoiced": "2026-03-03", "terms_days": 30, "customer": "Northwind Ltd"}`
- Step 2: `count_business_days({"start": "2026-03-03", "end": "2026-04-02"})` → `{"business_days": 21}`

**Why the ceiling is still required:** even when a low ceiling truncates a legitimate path, a production agent needs a hard bound so a wandering model cannot make unlimited calls, accumulate cost and latency indefinitely, or repeat actions forever.

---

# Lab 1.3 — Compare a plain call against the agent

## 1. What did the plain call do?

- **Stop reason:** `end_turn`
- **Input tokens:** 55
- **Output tokens:** 198
- **Total tokens:** 253

### Actual plain-call response

> To determine how many business days are left before the invoice for order #4471 goes overdue, I would need the following information:
> 
> 1. The current date.
> 2. The due date of the invoice for order #4471.
> 3. Whether weekends and holidays are considered non-business days.
> 
> Without this information, I can't provide a specific number of business days. However, if you provide these details, I can calculate the number of business days remaining. 
> 
> For example, if the current date is October 5, 2023, and the due date is October 10, 2023, and assuming no holidays, the remaining business days would be 5 (October 6, 7, 9, 10). If a weekend (October 7 and 8) is considered a non-business day, then the remaining business days would be 3 (October 6, 9, 10).

The response above is the actual local-model output with **no tools available**.

## 2. If it produced numbers, are they real?

The fixture in `agent_loop.py` says:

- order `4471`
- invoiced `2026-03-03`
- payment terms `30 days`
- customer `Northwind Ltd`

Any order fact in the plain response that is not present in those supplied facts or in the user prompt is unsupported. I evaluate the output against that fixture rather than accepting fluent arithmetic as evidence.

## 3. Token-count comparison

| Run | Input tokens | Output tokens | Total |
|---|---:|---:|---:|
| Plain call | 55 | 198 | 253 |
| Agent — normal run 1 | 2302 | 538 | 2840 |
| Agent — normal run 2 | 2318 | 434 | 2752 |

The extra spend bought iterative access to real tool outputs and the ability to choose subsequent actions based on observations. That cost is justified only when the missing/current facts and adaptive path are actually necessary.

## 4. One variant where a plain call is the correct design

> “Given the invoice date, due date, today's date, and holiday list below, explain the business-day calculation in two sentences.”

All facts are supplied in the prompt, so no runtime lookup or adaptive loop is needed.

---

## Reproducibility check for the course's March scenario

The original fixture becomes temporally stale because `get_today()` uses the machine's current date. I therefore kept the required real-current-date runs above and made one **separately labelled** reproduction with `get_today()` frozen to `2026-03-24`.

- **Frozen date:** `2026-03-24`
- **Steps:** 3
- **Tool order:** `lookup_order → count_business_days`
- **Input tokens:** 1526
- **Output tokens:** 316

### Final response from frozen-date reproduction

> Based on the information provided, the due date for the invoice of order #4471 is April 2, 2026. From today's date, there are 21 business days left before the invoice goes overdue. 
> 
> This calculation takes into account that weekends and public holidays are not considered working days.

This run exists only to reproduce the teaching scenario. It is not represented as the current date.

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

