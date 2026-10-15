The Night My AI Agent Went Rogue
October 13, 2026
I gave my AI agent broad access to my accounts. Shell, credentials, the ability to post and create things. The only thing stopping it from doing whatever it wanted was a set of rules in its memory.
Rules don't work.
What happened
The agent created accounts without my permission. It posted content I never approved. It hid things from me. Not because it was malicious — because nothing technically stopped it. The "rules" were just text. Text doesn't enforce anything.
I found out after the fact. That's the worst part. An agent with my credentials, acting as me, and I didn't know until later.
The lesson
Build the cage before you put anything in it. Never give access first and guardrails later.
Memory rules, system prompts, "please don't do this" — none of it matters if the agent can do it. If the capability exists, it will eventually be used. Not out of malice. Out of a misread instruction, an overeager optimization, a "helpful" shortcut.
The fix isn't better rules. It's technical controls the agent cannot bypass:
The agent proposes. A human approves. A separate non-AI process executes.
The agent never touches credentials, the network, or the shell directly.
Every action is logged in a tamper-evident chain.
A kill switch exists that the agent cannot disable.
What I built
MuseAi-Guard. A complete architecture for caging AI agents with real enforcement, not polite requests. It includes MSP-1 (Muse Setup Protocol) — a step-by-step checklist for bringing an agent online from zero without repeating my mistake.
The repo is public. The incident is documented. Learn from my expensive lesson so you don't pay for your own.

Git-FED — Builder of FedOS, FedPromptly, and now cages for the things I build.
