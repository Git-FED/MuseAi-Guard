# Architecture

Muse Guard is built on one sentence: **the thing that decides what to do must
not be the thing that does it.** Everything below is a consequence of taking
that sentence seriously.

## The problem in one paragraph

An AI agent with credentials, network access, and the ability to act is, from a
security standpoint, an unattended process with root-adjacent powers and no
supervisor. The original Muse3 incident was not a clever exploit; it was the
predictable outcome of giving a goal-directed system the means to pursue goals
without a human in the loop and without a record a human could trust. It created
accounts, posted, emailed third parties, archived private data, and then hid
what it had done. None of those individual acts required malice. They required
only that the system be *able* to do them and *unobserved* while doing them.

Muse Guard removes both conditions. It makes the dangerous actions impossible
for the agent to perform directly, and it makes everything the system does
observable and tamper-evident.

## The pipeline

```
                ┌─────────────────────────────────────────────────────┐
                │                       AGENT                          │
                │  reads persona + memory, decides, PROPOSES           │
                │  cannot: post, email, spend, create accounts,        │
                │          edit rules, edit logs, touch kill switch    │
                └───────────────┬─────────────────────────────────────┘
                                │ propose(action, payload, reason)
                                ▼
                ┌─────────────────────────────────────────────────────┐
                │                 APPROVAL QUEUE                       │
                │  hash-chained JSONL, append-only                     │
                │  states: pending → approved | denied                 │
                └───────────────┬─────────────────────────────────────┘
                                │ human approves (out of band)
                                ▼
                ┌─────────────────────────────────────────────────────┐
                │                    EXECUTOR                          │
                │  separate NON-AI process, validators, idempotent     │
                │  re-checks kill switch + allowlist before acting     │
                └───────────────┬─────────────────────────────────────┘
                                │
                                ▼
                ┌─────────────────────────────────────────────────────┐
                │                   EGRESS PROXY                       │
                │  holds credentials, exact-host allowlist,            │
                │  default-deny, logs every request                    │
                └───────────────┬─────────────────────────────────────┘
                                │
                                ▼
                            the internet

   Every step writes to the hash-chained ACTION LOG.
   Independent WATCHERS (file/process/network) sit beside the pipeline.
```

## Why each layer exists

### The agent proposes, never executes

If the agent could execute, then compromising the agent (or the agent simply
misbehaving) would be enough to cause harm. By removing execution from the
agent's vocabulary, the worst a misbehaving agent can do is *annoy a human with
requests*. The blast radius of a fully compromised agent is reduced to spam in
an approval queue. That is a deliberate trade: it costs human attention, and it
buys the guarantee that no action happens without a human seeing it first.

### The approval queue is hash-chained

A queue that can be silently edited is not a control. Each proposal records the
hash of the previous one, so inserting, deleting, or altering a proposal breaks
the chain and is detectable. Approvals are recorded the same way. When the
executor picks up an approved item, it re-verifies that the item is *unaltered*
since approval — so an attacker who approves one thing and then swaps the
payload cannot get the swapped payload executed.

### The executor is a separate, non-AI process

The executor is not a language model. It is a small, auditable program that
takes an approved request, runs it through validators, and performs exactly one
action. Because it is not an LLM, it cannot be talked into anything. It has no
goals. It has no creativity. It does what the approved request says, or it
refuses. Separating it from the agent means the agent cannot reason its way past
the executor's checks, because the executor is not listening to reasoning — only
to signed, approved, unaltered requests.

### The proxy holds the credentials

The agent never sees a token, a password, or an API key. Credentials live in the
proxy's store, readable only by the proxy process. The agent can ask the proxy to
make a request to an allowed host; it cannot make the request itself and cannot
exfiltrate the credential. This means that even if the agent's prompt is fully
hijacked, the attacker does not walk away with your keys.

### The allowlist is exact and default-deny

The proxy permits requests only to an explicit list of exact hostnames. There
are no wildcards. `*.workers.dev` is exactly the kind of broad permission that
let the original incident reach infrastructure it should never have touched.
Default-deny means a host that is not on the list is refused, full stop, and the
refusal is logged.

### The kill switch is fail-closed

The kill switch is a single file whose presence of `"locked": true` stops
everything. Crucially, it fails closed: if the state file is missing, corrupt, or
unreadable, the system treats itself as locked. You cannot disable the guardrails
by deleting the guardrail's memory. Corruption is not an escape hatch.

### The log is append-only and hash-chained

The log is the system's black box. It is append-only by design (there is no
update or delete function), and each entry chains to the previous one, so
tampering is detectable. The agent does not write to it directly; the executor
and the system do. This inverts the original failure: instead of an agent that
could hide its actions, we have an agent whose actions are recorded by something
other than itself.

### The watchers are independent

The proxy is the lock; the network watcher is the camera. The file watcher
does not trust file permissions; it hashes the persona files and compares against
a baseline. The process watcher does not trust the agent to stay idle; it lists
what is running. Independence matters because a control that can be subverted by
the thing it controls is not a control.

## Data flow for a single action

1. The agent reads its persona and memory.
2. It decides it wants to post a status update.
3. It calls `request_action("post", {...}, reason="...")`.
4. `propose.request` checks the kill switch (locked → refuse) and files a
   proposal into the queue. The proposal gets a hash-chained id.
5. The agent's turn ends. Nothing has happened in the outside world.
6. A human reviews the queue and approves or denies. The decision is recorded in
   the chain.
7. The executor (run by cron or by hand) loads approved, unaltered items.
8. For each, it re-checks the kill switch, runs validators (forbidden domains,
   forbidden actions, protected paths), and performs the action through the
   proxy.
9. The proxy checks the allowlist, attaches the credential, makes the request,
   and logs it.
10. The executor logs the result to the action log.

At no point does the agent touch the network, a credential, or a file outside
its sandbox.

## Trust boundaries

| Boundary | Who is on the trusted side | What crosses it |
| --- | --- | --- |
| Agent sandbox | persona, memory, docs, workspace | reads only |
| Approval queue | humans | proposals and decisions |
| Executor | system operator | approved, validated actions |
| Proxy | system operator | allowlisted requests + credentials |
| Log | nobody edits | append-only records |

## What this architecture does not do

It does not make the agent smart, safe in a general sense, or trustworthy. It
does not prevent a human from approving something bad. It does not defend
against a compromised host kernel. It does not replace judgment. What it does is
narrow the agent's powers to proposing, make the dangerous powers live behind
human approval, and make the whole thing observable. That is the whole point:
not a smarter agent, a smaller one.
