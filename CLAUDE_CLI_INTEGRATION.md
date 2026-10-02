# Claude CLI integration

GovOS has exactly one AI integration: **the Claude CLI installed on the machine that runs `app.py`**,
called server-side through one gateway and one persistent job queue. There is no local model, no
model server, no search API, no API key and no SDK. Authentication is the host CLI's own login.

> **Claude is machinery, never a source of truth.** It may find candidate sources, classify text,
> compare a value with its quotation, judge whether a unit of text is complete, propose values *with
> quotations*, and write clearly labelled guidance. It never supplies a date, a vacancy count, a fee,
> an eligibility rule, a URL that is trusted because Claude named it, or an official instruction.
> Everything it returns is checked by deterministic code, and the publication gate decides what is
> published. Claude cannot publish anything, and an unavailable Claude can never turn a missing fact
> into "not published".

```
SOURCE -> SOURCE IDENTITY -> EXAM/CYCLE IDENTITY -> QUOTED EVIDENCE -> EXTRACTION
       -> DETERMINISTIC VALIDATION -> CLAUDE REVIEW (only when needed) -> PUBLICATION GATE
```

## 1. Set it up

Claude is **off by default**. With it off, GovOS runs on its deterministic logic alone and every
Claude feature says "disabled" instead of failing.

```bash
# 1. Install the Claude CLI (see https://docs.claude.com/claude-code) and check it runs:
claude --version

# 2. Sign in once, on this machine, with your own Claude account. No API key is used anywhere:
claude auth login
claude auth status

# 3. Turn the integration on (copy .env.example to .env first; .env is never committed):
#    GOVOS_CLAUDE_ENABLED=1

# 4. Install and start GovOS:
pip install -r requirements.txt
npm install
npm run build
python app.py
```

Check readiness (no path, command line, account or secret is ever in this response):

```bash
curl http://localhost:5000/api/claude/health
```

```json
{"enabled": true, "installed": true, "authenticated": true, "ready": true,
 "executable": "claude", "version": "2.1.285 (Claude Code)", "busy": false,
 "status": "OK", "message": "", "adminTokenRequired": false}
```

`ready` is the only field a feature should branch on. When it is false, `status` says why
(`CLAUDE_DISABLED`, `CLAUDE_CLI_NOT_INSTALLED`, `CLAUDE_CLI_NOT_AUTHENTICATED`,
`CLAUDE_CLI_UNSUPPORTED`) and `message` is a fixed, safe sentence.

For development run both servers (`npm run dev` on :3000 proxies `/api` to :5000, and `python app.py`).
`npm run build` also runs `tools/export_authored_exams.mjs`, which writes
`exam_data/authored_exams.json` (a projection of `src/data.ts`, gitignored) so the server can build an
Ask AI fact sheet for the authored exams; without it Ask AI simply falls back to the deterministic
assistant for them. Run it alone with `npm run export:authored`.

## 2. How the CLI is found and called

**Location.** `GOVOS_CLAUDE_CLI_PATH` if set, otherwise `claude` on `PATH`. The path is never taken
from an HTTP request. On Windows it must be the native executable: a `.cmd`/`.bat` shim is refused
(`CLAUDE_CLI_UNSUPPORTED`) because it cannot be launched with an argument array without a shell.

**Capability detection.** The gateway reads the installed CLI's own `--help` and refuses (`CLAUDE_CLI_UNSUPPORTED`)
a CLI that lacks a flag the hardened call needs, rather than calling it with weaker isolation. Login
state is read from `claude auth status` and cached briefly.

**Invocation** (verified against Claude Code 2.1.285; the prompt is delivered on **stdin**):

```
claude -p
  --output-format json
  --json-schema <the operation's schema>
  --system-prompt <the operation's fixed system prompt>
  --tools <"" for none, or the operation's read-only web tools>
  [--allowedTools <the same tools>]
  --no-session-persistence
  --permission-mode dontAsk
  --setting-sources local --strict-mcp-config --disable-slash-commands
  [--no-chrome] [--exclude-dynamic-system-prompt-sections] [--model <GOVOS_CLAUDE_MODEL>]
```

* `--bare` is deliberately **not** used: it forbids the account login and would require an API key.
* Arguments are an array (`shell=False`); the prompt is never on the command line.
* The working directory is an empty scratch directory outside the repository
  (`GOVOS_CLAUDE_JOB_WORKDIR`, default `<temp>/govos-claude-work`), so the CLI discovers no project
  files, no `CLAUDE.md` and no settings.
* The environment is a short allowlist (`PATH`, `SYSTEMROOT`, `HOME`/`USERPROFILE`, `APPDATA`,
  temp dirs, proxy and CA variables, `CLAUDE_CONFIG_DIR`). `ANTHROPIC_*`, `OPENAI_*`, `AWS_*`,
  `AZURE_*`, `GOOGLE_*`, `GOVOS_*` and every other variable are dropped, so no key or admin token
  reaches the child process.
* Stdout and stderr are read separately. Stdout is untrusted: it must be one JSON object, is stripped
  of reasoning-like fields, and is validated against the operation's schema before any caller sees
  it. Stderr, command lines and paths are never returned, logged or audited.
* A call that exceeds `GOVOS_CLAUDE_TIMEOUT_SECONDS` (times the operation's factor; web discovery
  gets 4x) kills the **whole process tree** (`taskkill /T /F` on Windows, `killpg` elsewhere).
  Output beyond `GOVOS_CLAUDE_MAX_OUTPUT_BYTES` is rejected.

**Results** are typed (`ClaudeResult`): job id, operation, status, start/end time, duration, CLI
version, exit category, whether it timed out, the parsed output, validation errors, a safe message,
the prompt-template version and fingerprints of the input and output.

### Infrastructure states

None of these is ever a factual state. They are never `VERIFIED`, `NOT_PUBLISHED` or `NEEDS_REVIEW`,
never cached, and never turn a published fact into a missing one.

| status | meaning | retried? |
|---|---|---|
| `CLAUDE_DISABLED` | `GOVOS_CLAUDE_ENABLED` is not true | no |
| `CLAUDE_CLI_NOT_INSTALLED` | no executable found | no |
| `CLAUDE_CLI_NOT_AUTHENTICATED` | the CLI is not signed in | no |
| `CLAUDE_CLI_UNSUPPORTED` | missing a required flag, or a `.cmd` shim | no |
| `CLAUDE_CLI_BUSY` | no free slot in time, or the account is rate/usage limited | yes (bounded) |
| `CLAUDE_CLI_TIMEOUT` | the call ran past its limit and was killed | yes (bounded) |
| `CLAUDE_CLI_FAILED` | non-zero exit or the process could not start | yes (bounded) |
| `CLAUDE_INVALID_OUTPUT` | not one JSON object, or over the size limit | **never** |
| `CLAUDE_SCHEMA_REJECTED` | valid JSON of the wrong shape | **never** |
| `CLAUDE_INPUT_REJECTED` | the input was over the template's limit, or the operation is unknown | **never** |
| `CLAUDE_DISCOVERY_UNAVAILABLE` | discovery needs web tools the CLI did not provide | no |
| `CANCELLED` | cancelled by a person or by a changed exam | no |

A malformed or schema-rejected reply is a verdict on that reply, not a transient failure, so it is
never retried as if it were one.

## 3. The job queue

Anything slow or expensive runs as a **job** in SQLite (`claude_jobs`, `claude_job_events`), never
inside a Flask request. A request creates a job and returns `202` with a poll URL.

| endpoint | who | purpose |
|---|---|---|
| `GET /api/claude/health` | anyone | readiness (safe fields only) |
| `POST /api/claude/jobs` | admin | create a job from the operation allowlist |
| `GET /api/claude/jobs` | admin | recent jobs and a count per status |
| `GET /api/claude/jobs/<id>` | admin, or the candidate holding that job's token | state, stage, result, safe error |
| `POST /api/claude/jobs/<id>/cancel` | admin, or the job's token | cancel (a running job's process tree is killed) |
| `POST /api/claude/jobs/<id>/retry` | admin | re-queue the input of a FAILED/CANCELLED job |
| `POST /api/claude/ask` | candidate (rate limited 8/min) | a question about one exam |
| `POST /api/claude/practice` | candidate (rate limited 4/min) | practice questions on a verified syllabus topic |
| `POST /api/research/search` | admin | discovery job |
| `POST /api/research/facts/extract` with `"claude": true` | admin | reading one stored page for facts |
| `POST /api/exams/build` | admin | gate-controlled exam build (`authorityDiscovery: true` walks the authority's site first) |
| `POST /api/sources/discover` | admin | `DISCOVER_AUTHORITY`: a bounded walk of one exam's authority site, from that exam's official address |

A job records its id, operation, exam and cycle, requester, sanitised input, input fingerprint,
status, stage, result, error category and message, template version, timestamps, retry count, cancel
state, evidence links and audit metadata.

* **Operations are an allowlist.** A request chooses one and supplies schema fields; it never supplies
  a prompt, flags, tools, a working directory, a system prompt, a model or an executable path.
* **Bounded concurrency** (`GOVOS_CLAUDE_MAX_CONCURRENCY`, 1-4). Identical *active* jobs from the same
  requester are de-duplicated. At most one build per exam and cycle runs at a time; different cycles
  may run together. At most one authority walk per exam runs at a time.
* **Retries** only for infrastructure states, with backoff (5, 20, 60 seconds) and a per-operation bound.
* **Cancellation.** A queued job is cancelled at once; a running job's CLI process tree is killed, and a
  cancelled build can never register anything.
* **Restart safety.** Workers heartbeat; a job left `RUNNING` by a dead process is recovered on the
  next start (`app.py` calls `ensure_started()`).
* **Candidates** get a per-job token when they create a job; only its SHA-256 hash is stored. Another
  candidate, or no token, gets `404` (indistinguishable from "no such job"). Candidate job inputs are
  purged 24 hours after the job was created.
* **A finished job publishes nothing.** Results wait for a person (Trust Panel) or pass through the
  publication gate.

## 4. What goes through Claude, and what does not

| area | Claude's part | what stays deterministic |
|---|---|---|
| Source discovery (replaces the former search API) | proposes candidate URLs with web search/fetch | URL syntax, public-address (SSRF) check on every hop, host classification by suffix, reachability, redirects, page identity hint; nothing is "official" because Claude said so; the manifest records everything proposed and everything rejected |
| Extraction from a page | proposes values **with exact quotations** from supplied text | the quotation must be printed verbatim in the page text the *server* fetched, and must state the value; else the value is discarded; kept values enter `research_facts` as pending, never approved |
| Semantic fact verification (`VERIFY_CLAIM`) | judges whether the quoted evidence supports the claim | identity, cycle, quotation-in-source and contradiction checks run first; Claude is not called if they fail; Claude can only withhold |
| Completeness, attribution, date role, designation, recruitment match | classify a bounded unit of text | every answer is re-checked (its evidence span must be in the source, its role must fit); a failure holds the value, an outage never upgrades it |
| Study-roadmap order | reorders the supplied verified topic ids (GovOS guidance, never official) | any invented/dropped id rejects the whole reply; the deterministic order stands |
| **Ask AI** (candidate) | answers an unplaced question from a **server-built fact sheet of one exam** | the deterministic assistant answers everything it can place; cited fact ids must exist in the sheet, figures/URLs/other exam names must appear in it; otherwise the deterministic reply is shown |
| **Practice questions** (candidate) | writes new questions on one verified syllabus topic (`GENERATE_PRACTICE`), then a **second, independent call** (`SOLVE_PRACTICE`) solves each one without being shown the key | topic must be in that exam's syllabus; four distinct options; no official-origin claims or links; an explanation that corrects itself is dropped; a question is served only where the independent solve reaches the key's option, and if that check cannot run nothing is served; always labelled `GOVOS_AUTHORED`, never a previous-year question; not scored or saved |
| Authority source discovery (`CLASSIFY_SOURCE`, only when a walk asks for it) | names the role of official links whose own words the rules could not read ("Click here", "Downloads 2019"), from a fixed vocabulary, in one batched call | link extraction, the walk and its limits, every source class (official / trusted / secondary / lead), duplicate detection, exam identity (`discover.gate`) and the search states; a role outside the vocabulary or an index not asked about is ignored; disabled, slow or rejected leaves the role UNKNOWN; the walk itself never needs Claude |
| Trust Panel | job status, safe errors, retry/cancel, evidence preview | human approval of every fact, finding and revision |

Deliberately **not** sent to Claude: arithmetic, eligibility and age calculation, date comparison,
localStorage and CRUD, schema checks, rendering, resource ranking/search, and the formatting of a
value the register already holds. "Claude is not asked to format a known value."

## 5. Evidence and publication safety

* Claude's output is data. It is parsed as untrusted text, validated against a strict schema
  (unknown keys are errors) and checked by code that does not trust it.
* A value reaches the runtime registry only through the existing publication gate with source, page and
  quotation. Claude's `SUPPORTED` cannot override missing evidence; `CONTRADICTED`/`INSUFFICIENT`
  withholds.
* Decisions are cached by input fingerprint **and prompt-template version**; infrastructure failures are
  never cached. The audit trail (`claude_invocations`) records operation, status, durations and
  fingerprints. It never records prompt text, source text or output text.
* The UI labels what a candidate is looking at: verified official record, GovOS calculation,
  Claude-assisted interpretation (`CLAUDE_ASSISTED`), GovOS-authored guidance/practice
  (`GOVOS_AUTHORED`), or a human-reviewed change.

## 6. Security boundaries

* **Prompt injection.** Every piece of source material is wrapped in a block whose delimiter carries a
  fresh random nonce; every system prompt says delimited text is data to be ignored as instruction;
  templates are fixed and server-owned. Candidate text fills schema fields only and is never placed in a
  shell, an argument or a path. Injected instructions in a document cannot change what is published,
  because the deterministic checks (quotation present, value stated, identity, cycle, gate) do not
  consult Claude's opinion.
* **No tools for candidate-facing jobs.** `ANSWER_QUESTION` and `GENERATE_PRACTICE` run with `--tools ""`:
  no Bash, no file read or write, no code edit, no web. Only `DISCOVER_SOURCES` gets read-only web
  search and fetch.
* **Claude's URLs are candidates.** They pass syntax checks (http/https, no credentials, no IP literals,
  no private/loopback/link-local addresses, length), are resolved and re-checked on every redirect hop,
  and are classified by host suffix (`*.gov.in` and `*.nic.in` official; `.gov` without `.in` is not).
  A redirect can lower a source's trust, never raise it.
* **Limits.** Per-template input size limits, an output size limit, rate limits on candidate endpoints
  (ask 8/min, practice 4/min per client) and on the expensive admin ones (discovery and reading 20/min,
  builds 6/min), and a bounded queue (200 queued jobs, at most 20 of them from candidates).
* **Privacy.** Ask AI sends only the question, the last few turns, and a fact sheet built from one exam's
  public record. It never sends the whole database, the candidate's profile, date of birth or contact
  details. Scorecard uploads are parsed locally and never sent to Claude.
* **Admin protection is a local guard, not production authentication.** GovOS has no user accounts.
  Operations that spend Claude usage or change canonical information (`/api/research/*` writes,
  `/api/exams/build`, `/api/claude/jobs` create/list/retry, syllabus revisions, resource additions,
  overlays, retire and report-status routes) require either `GOVOS_CLAUDE_ADMIN_TOKEN` presented in the
  `X-GovOS-Admin-Token` header, or - only when no token is configured - a request that arrives directly
  from the loopback interface with no proxy headers and no foreign `Origin`. `app.py` binds all
  interfaces, so a deployment reachable by others **must** set a token; without one, remote and proxied
  admin requests are refused. CORS is limited to localhost origins. This does not identify people or
  isolate candidates from each other beyond the per-job tokens; put real authentication in front of it
  before any multi-user deployment.

## 7. Configuration

All names are read from the process environment (and from `.env` for `GOVOS_*` and `PORT` only).
There is deliberately no API-key setting, and no alias for the removed names.

| variable | default | meaning |
|---|---|---|
| `GOVOS_CLAUDE_ENABLED` | off | master switch |
| `GOVOS_CLAUDE_CLI_PATH` | `claude` on `PATH` | absolute path of the native CLI executable |
| `GOVOS_CLAUDE_TIMEOUT_SECONDS` | 120 (10-900) | base per-call limit; operations scale it |
| `GOVOS_CLAUDE_MAX_CONCURRENCY` | 2 (1-4) | simultaneous CLI processes |
| `GOVOS_CLAUDE_MAX_OUTPUT_BYTES` | 262144 | largest accepted reply |
| `GOVOS_CLAUDE_JOB_WORKDIR` | `<temp>/govos-claude-work` | empty directory the CLI runs in |
| `GOVOS_CLAUDE_MODEL` | CLI default | optional model alias |
| `GOVOS_CLAUDE_ADMIN_TOKEN` | unset | admin token (see section 6) |

## 8. Account usage and limits

Claude runs on **your own Claude account** through the CLI, so every call counts against that account's
usage allowance and rate limits. It is not free and not unlimited. Source discovery is the heaviest
operation (web search and fetch plus several turns); the job queue, concurrency cap, de-duplication,
decision cache and candidate rate limits exist to keep usage proportionate, and a limit being hit
shows as `CLAUDE_CLI_BUSY` and falls back, never as a factual result. Reasoning-heavy operations (Ask AI,
practice, discovery) are on demand only; nothing runs on a timer.

## 9. If Claude is unavailable

| feature | behaviour |
|---|---|
| Ask AI | the deterministic assistant answers, exactly as before |
| Practice from Claude | the panel is hidden |
| Trust Panel discovery / reading | shows the safe state and the setup steps; nothing is recorded as "not published" |
| Builds with `claude` | refused with a clear state; builds without Claude still run |
| Attribution, date-role, completeness and designation checks, when Claude is enabled for a build | an outage **holds** the field for review (`NEEDS_REVIEW`/`NOT_EXTRACTED`), never `NOT_PUBLISHED`, never upgraded |
| The orchestrator's optional verification pass (`--claude`) | an outage leaves the deterministic reading exactly as it was (it is not upgraded to anything); only an explicit `CONTRADICTED` withholds a field |
| Everything else | unchanged |

## 10. Developing and testing

Automated tests never start the real CLI. `tools/claude_cli/testing.py` provides `FakeClaude` (the real
gateway over a scripted runner, so command construction, parsing, stripping and validation still run),
`ByOperation`, `ForbiddenClaude` (fails the test if Claude is called) and `use_gateway`.
`tools/claude_cli/fake_cli.py` is a scenario-driven child process for tests that need a real process
(timeouts, process-tree kill, stdin, environment). The root `conftest.py` and a test-mode flag make
`SubprocessRunner` refuse any program except the Python interpreter running the tests.

```bash
python -m compileall -q tools app.py
python -m pytest tools test_research_facts.py test_app_claude.py -q
npx tsc --noEmit
npm run check:frontend
npm run build
```

## 11. Production limitations

* Admin protection is local, not user authentication (section 6).
* One machine, one Claude account, SQLite. The queue is process-local workers over a shared file.
* Discovery depends on the installed CLI exposing web search/fetch; without them it reports
  `CLAUDE_DISCOVERY_UNAVAILABLE` and does nothing else. There is no silent fallback to any paid API.
* The authored exams reach Ask AI through `exam_data/authored_exams.json`, generated at build time.
* The SSRF guard validates every redirect hop and resolves hosts to public addresses before the server
  fetches anything for discovery or page text, but the page text is then read by the document loader from
  the validated final URL, so a DNS answer that changes between the check and the read (DNS rebinding) is
  not fully closed off. Run the server without access to internal networks if that matters.
* Claude's review is a filter on what deterministic code already read, and some fields never reach it:
  `officialName` and `authority` are cited to the resolution page, and for a notice seeded from a PDF the
  citation title is only a file name, so most fields are judged by the deterministic checks alone. An
  `INSUFFICIENT` verdict does not withhold (`test_orchestrate` pins this). The attribution check accepts any
  printed evidence span whose role fits, so it can only withhold, never change a value.
* A quotation copied from an injected sentence on a page passes the quote check by design; it is stored as a
  `pending` proposal with the quotation visible to the reviewer, never approved or registered.
* Practice answer keys are written by a model, and a real run produced a question whose key contradicted its own explanation. The second, independent solve and the self-correction filter catch that kind of error (the real solver disagreed with that key), but two calls to one model can still agree on a wrong answer, so the panel keeps telling the candidate to check answers against their study material. A practice request costs two CLI calls (about 15-20 s).
* A build job retries every `INFRASTRUCTURE_FAILURE` once, including a not-signed-in or disabled Claude.
* * The CLI's flags and envelope were verified on Claude Code 2.1.285; the gateway detects flags from the
  installed CLI and fails safe (`CLAUDE_CLI_UNSUPPORTED`) when they differ.

## 12. Migration from the local model and the search API

Removed: llama.cpp / `llama-server`, Qwen and GGUF model files, the OpenAI-compatible local endpoint
(`/v1/models`, `/v1/chat/completions`), `LocalQwenVerificationProvider`, `verification/client.py`,
`llm_verifier.py`, `prompts.py`, `test_local_llm.py`, the `*.gguf` ignore rule, the Tavily client,
`TAVILY_API_KEY` and its routes' dependency on it, and the environment variables
`GOVOS_LLM_ENABLED`, `GOVOS_LLM_URL`, `GOVOS_LLM_MODEL`, `GOVOS_LLM_MODEL_PATH`,
`GOVOS_LLM_TIMEOUT_SECONDS`. **None of these is read any more and none has an alias.** A leftover
`TAVILY_API_KEY` in your `.env` is ignored (the loader reads only `GOVOS_*` and `PORT`) and can be deleted.

Renamed: `use_llm` -> `use_claude`, `--llm` -> `--claude`, `Stage.QWEN` ->
`Stage.CLAUDE_VERIFICATION`, `LLM_*` infrastructure states -> `CLAUDE_*` (see section 2), `Verdict.llm` ->
`Verdict.claude`.

`GET /api/llm/health` now answers `410 Gone` naming `/api/claude/health`.

Database: `init_database()` adds `research_runs.engine/job_id/manifest_json` and
`research_findings.meta_json`, labels every existing run `LEGACY_SEARCH` (their findings and extracted
facts are untouched and still shown, marked as archived), and creates `claude_jobs`,
`claude_job_events`, `claude_invocations` and `claude_decision_cache`. The migration is idempotent.

Historical audit documents are kept as written and carry an archival banner; the frozen TGPSC fixture
keeps two search notes recorded before the migration.

## 13. Troubleshooting

| symptom | check |
|---|---|
| health says `CLAUDE_DISABLED` | set `GOVOS_CLAUDE_ENABLED=1`, restart |
| `CLAUDE_CLI_NOT_INSTALLED` | `claude --version` in the same shell/service account as `python app.py`; or set `GOVOS_CLAUDE_CLI_PATH` to the native executable |
| `CLAUDE_CLI_NOT_AUTHENTICATED` | run `claude auth login` as the user that runs `app.py` |
| `CLAUDE_CLI_UNSUPPORTED` | the CLI is old, or the path is a `.cmd` shim: update it or point `GOVOS_CLAUDE_CLI_PATH` at `claude.exe` |
| `CLAUDE_CLI_BUSY` | the account's usage/rate limit, or all slots busy; wait, or lower load |
| `CLAUDE_DISCOVERY_UNAVAILABLE` | the CLI/account did not provide web search/fetch; discovery cannot run |
| admin routes return 403 | request is not from this machine; set `GOVOS_CLAUDE_ADMIN_TOKEN` and send `X-GovOS-Admin-Token` (the Trust Panel has a field for it) |
