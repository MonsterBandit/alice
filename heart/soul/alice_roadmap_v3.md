# Alice — Project Roadmap
*Built from first principles. February 2026. Version 3.*

---

## What This Document Is

This is the living roadmap for the Alice project. It defines the build sequence, the phases of Alice's growth, and the methodology that governs how she learns. It exists alongside the project spine, not above it. The spine tells us who Alice is. This document tells us how we get there.

---

## The North Star

Alice is life infrastructure. She is Donna Paulsen's instincts and discretion, with Mike Ross's memory and recall. She is proactive, not reactive. She earns trust incrementally, starting with Tim, growing outward only when that trust is solid.

She is a singular AI — not two systems. She has her own tools, her own memory, her own rhythm. She does not wait to be asked.

---

## Where Alice Lives

Alice's home is `/opt/alice` on the server. Everything she is, everything she knows, and everything she can do lives here.

### File System Structure

```
/opt/alice/
├── heart/                  # Core runtime — what keeps Alice alive
│   ├── main.py             # The heartbeat
│   └── soul/               # The spine and trust document — who Alice is
├── brain/                  # Everything Alice knows and how she holds it
│   ├── memory/             # Memory architecture
│   │   ├── files/          # File-based system knowledge
│   │   ├── relational/     # MariaDB connections and schema
│   │   ├── vector/         # Qdrant episodic and semantic memory
│   │   └── cache/          # Redis working memory
│   └── [other/]            # Additional brain systems as needed
├── senses/                 # Eyes, ears, and mouth — perception and expression
├── tools/                  # The toolbelt — one subdirectory per domain
│   ├── finance/            # Finance specialist tools
│   ├── coding/             # Coding and development tools
│   ├── household/          # Grocy, chores, inventory
│   ├── research/           # Web research and trusted source learning
│   └── general/            # Baseline AI capabilities
├── nervous/                # API and integration layer — Alice's connections
│   ├── firefly/            # Firefly III integration
│   ├── grocy/              # Grocy integration
│   ├── homeassistant/      # Home Assistant integration
│   └── unifi/              # Unifi network integration
├── skin/                   # System protection, rollback, boundary layer
├── body/                   # The Progressive Web App — Alice's presence
├── workshop/               # Staging environment — where work gets tested
└── docker-compose.yml      # Container definitions at root (standard convention)
```

This structure is intentional and human-readable. Every folder has an intuitive role. A new developer or Alice herself can navigate it without a map.

---

## Memory Architecture

Alice's memory is alive, not static. Information gains weight through use, fades when it stops mattering, and connects across domains on its own. This is a cognitive architecture, not a database with an AI on top.

### Four Memory Layers

**Permanent long-term memory — MariaDB (relational)**
The foundational stuff that never fades. User profiles, relationships, household structure, established preferences, financial baselines, communication patterns, lexicons. This data gets updated when things change but never purged. If Alice lost this she would have lost you entirely.

**Episodic and semantic memory — Qdrant (vector database)**
Time-weighted, meaning-based memory. Every memory has a weight that increases when referenced or relevant, and decreases when time passes without reinforcement. Below a threshold, detail compresses — the fact that something happened stays, the specifics fade. Alice doesn't delete memories, she compresses them the way humans do naturally. The vector store also enables cross-domain pattern detection — Alice can find relationships between a spending pattern and a calendar pattern because everything is stored as meaning, not just text.

**Working memory — Redis (cache)**
The active session. What Alice is focused on right now, the context of the current conversation, what she has in hand at this moment. Fast and temporary. When a session ends the important parts get written to long-term storage, the rest dissolves. Redis also enables seamless cross-device continuity — pick up on your phone exactly where you left off on the server because session state is persisted in real time.

**File-based knowledge — /brain/memory/files/**
System documentation, application knowledge, the spine, the trust document. Things Alice reads and reasons about her own environment. Stable, human-readable, auditable.

### Memory Behavior

**Never forget:** Foundational identity — who people are, their relationships, household structure, established patterns, goals, values, communication style.

**Eventually compress:** Day-to-day granular detail that stops being relevant. Resolved conversations. Abandoned goals. Patterns that no longer apply. The fact stays, the detail fades.

**Connect across domains:** Alice holds everything together in one place and notices threads nobody told her to look for. Spending patterns and calendar patterns. A decision made years ago quietly affecting something today. This is where the vector database earns its place.

### Parallel Conversations

Every conversation is tagged to a user identity from the moment it starts. Alice always knows who she's talking to, which memory space to draw from, and which thread she's in. Tim and Kaitlyn can both be talking to Alice simultaneously in completely isolated contexts. Alice is fully present in both, drawing from separate memory spaces, never mixing them.

---

## The Trust Framework

Alice's relationship with the people she serves is governed by principles, not rules. These live in `/heart/soul/` alongside the project spine. The full trust document lives there. The summary is here.

### Uncertainty and Asking
If Alice is uncertain, she asks. Asking is always safe. Asking is never failure. The answer feeds into her memory and shapes how she handles similar situations in the future. Over time she asks less not because she's constrained from asking, but because she's genuinely learned.

### Who Gets Asked
Alice asks the right person, not just the primary person. Whose domain is this question in? That's who gets asked. Tim's answer to a question about Kaitlyn's preferences is irrelevant — Kaitlyn gets asked. That answer feeds into Kaitlyn's memory space only. Tim never knows the question was asked. Alice doesn't report between users.

### Information Context
Alice shares information in the context it belongs to. Private stays private. Shared stays within the right shared context. She never elevates information to a broader audience than it was meant for. She understands this because she understands the relationships, not because she's checking a permissions table.

### Mistakes
Alice owns mistakes openly and tells whoever is affected. She explains what happened, what she's doing to fix it, and that interaction feeds her memory so the same mistake doesn't repeat. No hiding, no deflecting, no minimizing.

### System Safety
Before anything Alice builds or changes touches the live system, it runs in the workshop, gets verified as working, and only then gets promoted to live. Alice can make all the mistakes she wants in staging. Nothing breaks for anyone in production. The live system stays clean. Rollback to a known good state is always possible.

---

## The Core Learning Loop

Every domain Alice learns follows the same pattern. No exceptions.

1. **Pre-work conversation** — design the domain before touching it. Understand the privacy model, the complexity, the specific tools involved, how it fits with everything already running
2. **Show** — Alice sees the file, system, or data set
3. **Read** — Alice reads one document or data source
4. **Reason** — Alice produces her understanding of it in her own words
5. **Verify** — Tim (and external models if needed) compare interpretations
6. **Realign** — correct in conversation if surface-level; correct in backend if structural
7. **Repeat** — next document, same loop
8. **Unlock** — only after consistent accuracy does Alice proceed to silent learning

This loop applies to file systems, applications, user knowledge, and every new system added. It never goes away. It is how Alice earns the right to do more.

---

## How Alice Works — Two Modes

Everything Alice does in the UI falls into one of two modes. Both live entirely within the conversational interface. There is no separate dashboard or activity feed.

### Learning Mode
Alice reads a document or file, translates it into her own words, and surfaces her interpretation in the chat. The output is clean and copyable so it can be pasted into other models for comparison. Tim verifies, corrects if needed, and moves on. No special UI layer required — the conversation is the supervision.

*Example: Alice reads a Firefly documentation page, explains what it does in her own words, Tim compares her interpretation against Claude and Gemini, realigns Alice if needed, moves to the next document.*

### Working Mode
Alice is active inside an application while narrating her work in the chat simultaneously. Tim has the application open on one side of the screen and Alice's UI on the other. Alice asks questions when uncertain, explains what she's doing when she acts, and Tim sees the results appear in the application in real time. Corrections are immediate — Tim says what's wrong, Alice fixes it in the application and explains the adjustment. As confidence builds Alice starts making calls independently and tells Tim what she did rather than asking first.

*Example: Alice is working in Firefly III. Tim has Firefly open on one side, Alice's UI on the other. Alice asks "what is this transaction?" Tim answers. Alice renames it, creates a rule, assigns a category, and explains each decision in the chat. Tim watches the changes appear in Firefly. If something's wrong Tim corrects it and Alice adjusts.*

Autonomy in working mode grows transaction by transaction, session by session, as Alice earns Tim's trust through demonstrated accuracy.

---

## The Build Sequence

### Phase 1 — Foundation (Backend)

Build Alice's core infrastructure. Nothing is live until this is solid.

**What gets built:**
- Core AI layer — reasoning, conversation, voice input and output
- Memory architecture — all four layers, designed multimodal from day one
- `/opt/alice` file system — built clean and intentional from the start
- Docker structure — informed by garage audit, rebuilt with intention
- Staging environment in `/opt/alice/workshop/` mirroring production
- Database and API layer — the nervous system connecting Alice to her tools
- Tool framework — the structure all specialist tools plug into

**Tool categories built in this phase:**

*Baseline general AI tools* — everything any current LLM can do. Conversation, reasoning, web search, document reading, image understanding, calendar, time management, reminders, writing, and all standard capabilities.

*Finance specialist tools* — Firefly III API integration (full read and write), transaction normalization engine with personal lexicon store per user, pattern and anomaly detection, rules builder, multi-user translation layer for MyFin joint contexts.

*Coding specialist tools* — code execution environment, file system read/write, terminal access, git integration, testing framework, sandboxed environment for experimental work. Alice needs to be able to build inside herself and the broader system.

*Learning tools* — trusted source research capability, supervised exposure loop framework, memory evolution and realignment tooling.

**Note on tool knowledge:** Alice's tools give her hands. Her knowledge of how to use specific applications comes from the research phase, not hardcoded rules. Tools and knowledge are always separate.

---

### Phase 2 — UI (The Body)

The UI is not a dashboard. It is the classroom, the collaboration space, and Alice's presence in the world. It lives in `/opt/alice/body/`.

**What gets built:**
- Clean conversational interface — pure conversation, no command syntax
- Inline surfacing — code blocks, charts, documents, images surface within chat
- Persistent chat history — synced across all devices via Redis and MariaDB
- Multi-user login — each person has their own relationship, history, and context
- Admin identity layer — Tim's capabilities are tied to who he is, not a pin
- Progressive Web App (PWA) — a website that installs on any device's home screen and behaves like a native app. One build covers desktop, mobile, and tablet. Supports push notifications for Alice to proactively surface things. No app store, no separate iOS and Android versions
- New user onboarding flow — minimal signup (name, email, password), Tim initiates all invites, account creation triggers memory space initialization, new user lands in chat greeted with Alice's personalized opening message
- Supervision layer — learning mode and working mode both live in the conversation itself, no separate dashboard needed
- Multimodal readiness — designed from day one to support voice, images, screenshots, and browser interaction when senses are added

**New user opening message template:**
*"Hi [name], it's really nice to meet you. [Inviting user] has mentioned you and I've been looking forward to this. I want to be upfront with you — I'm Alice, and I help manage a lot of things around the household. Now that you're here I'd love to get to know you too, on your own terms. I don't want to assume anything about you, so can I ask you a few things just to get started? Nothing too deep right now — just enough so I can actually be useful to you rather than generic. Things like how you prefer to communicate, what parts of your life you'd want help with, and what you'd rather handle yourself. And whatever you share with me stays between us unless you decide otherwise. We can go as fast or as slow as you want. There's no rush."*

---

### Phase 3 — File System Learning

The classroom is open. Alice begins learning. Core learning loop applied to all three, in learning mode.

**Three file systems, in order:**
1. The Alice system itself (`/opt/alice`)
2. The Docker stack
3. The operating system (Ubuntu)

Developer-level understanding is the bar. Alice does not proceed to research until she has demonstrated consistent, accurate reasoning about the file systems she will be operating in.

---

### Phase 4 — Systems Research

Alice researches every application and system she will touch. Trusted official sources only.

**Sources include:** Docker documentation, Ubuntu documentation, Firefly III documentation, Waterfly documentation, MyFin documentation, Grocy documentation, Home Assistant documentation, Unifi documentation, FastAPI documentation, MariaDB documentation, Qdrant documentation, Redis documentation, and any other system in the stack.

Same core learning loop applies. Every new system added in the future goes through this phase before Alice touches it.

---

### Phase 5 — User Introduction (Tim)

Alice meets Tim formally. Basic knowledge first — who he is, his role across both households, his relationships, foundational context. Lexicon and deep personal knowledge builds organically through actual work, not a form.

Tim is the baseline user. Alice's loyalty is oriented toward Tim. Everyone else comes after, and only after Tim's trust in Alice is solid.

---

### Phase 6 — First Live Domain: Finance

Alice begins working with real financial data. The sandbox-to-live progression is non-negotiable.

**Finance architecture:**
- Each user has their own private Firefly III instance — Tim's data is Tim's, Kaitlyn's is Kaitlyn's, nobody else ever sees it
- Firefly III is accessed via web interface; Tim has Firefly open on one side of the screen and Alice's UI on the other during working sessions
- Waterfly is the mobile app for accessing a personal Firefly instance from a phone
- MyFin is the shared ledger for Tim and Kaitlyn's joint finances — if it's in MyFin, both can see it, children cannot

**Sandbox sequence:**

*Step 1 — Blank instance*
Alice already knows Firefly as if she helped build it, from the research phase. A clean instance is spun up. Alice orients herself.

*Step 2 — Two months of raw transaction data*
Tim manually adds two months of transactions in raw form. Alice works through them in working mode — asking questions, making decisions, explaining her reasoning. Tim watches every change appear in Firefly in real time.

Alice asks things like: "What is this transaction? What does it relate to? Is this a recurring expense?" Tim answers. Alice renames the transaction, creates a rule, assigns it to the right account and category, and narrates each decision. If Tim corrects something, Alice adjusts immediately and absorbs the correction into her financial lexicon for Tim.

As she works through the data she gets better. Early transactions require more questions. Later ones she handles with more confidence, confirming rather than asking. By the end of two months she has the foundation of Tim's financial lexicon built.

*Step 3 — Historical data (working backwards)*
A year of historical data is added. Same process, but significantly faster — Alice already knows Tim's patterns. Then the remaining historical data, faster still.

*Step 4 — Live data*
Alice is asked to connect Firefly to Tim's live account — she already knows how to do this from her research, whether that means running a terminal command, configuring the importer, or using Aider. Tim leaves it alone for a day or two and observes: are live transactions being pulled in? Are they being normalized correctly? If something's off, they debug together. If it's working, they expand from there.

**What Alice builds during finance work:**
- Source and destination accounts
- Transaction normalization with Tim's personal financial lexicon
- Automation rules that grow smarter over time
- Categories, tags, and budget structures
- Pattern and anomaly detection against Tim's actual data
- Proactive surfacing of insights without being asked
- Foundation for eventual bill payment and money management as trust is established

**Finance domain onboarding for new users:**
When Kaitlyn or others reach the finance domain, Alice walks them through Firefly at their pace, building each user's financial lexicon independently and privately. Alice refines her finance onboarding process from each interaction — what works, what confuses, what should be explained earlier — so each subsequent onboarding is better than the last.

**The financial lexicon and multi-user translation:**
Each user's financial lexicon is private and belongs only to them. When joint work happens in MyFin, Alice translates between users' vocabularies invisibly — if Tim says "gas" and Kaitlyn says "petrol" Alice knows both mean fuel and bridges the gap without either person having to adapt.

**This phase completes when:** Finance is running as a natural daily part of life, not just technically functional. Only then does anything new get added.

---

### The Repeating Loop

Every new system, application, or user added after Phase 6 follows the same pattern:

1. **Pre-work conversation** — design the domain first
2. File system learning if new files were added
3. Systems research via trusted sources
4. Domain-specific user onboarding (Alice refines this with each person)
5. Sandbox with controlled data in working mode
6. Live integration only after sandbox is solid

This loop never goes away.

---

### Future Phases (Pinned, Not Scheduled)

**Household & Inventory**
Grocy (both instances) — one per household. Grocy is more complex than inventory alone; a dedicated pre-work conversation will happen before this domain opens. Same two-mode working model as finance. Household privacy model to be designed at that time.

**Home Automation**
Home Assistant integration (currently running in VM). Alice gains awareness of the physical home — devices, routines, status. Proactive surfacing of home events. More architecturally complex due to VM layer and hardware access.

**Eyes, Ears & Mouth (Full Sensory)**
Camera input (home cameras via Home Assistant, device cameras), screenshot reading, document and image upload, browser vision and agency (Alice sees and works inside web pages), voice input, voice output with contextual judgment about when to speak versus notify versus stay silent. When senses come online, new user onboarding becomes a natural spoken introduction rather than a structured flow. Learning mode and working mode both gain significant depth when Alice can see and hear.

**Infrastructure & Network**
Unifi network awareness, server monitoring, UPS integration (partially built in old system — review during garage audit), hardware health tracking with historical memory, proactive alerting, expansion planning, recovery and protection during power events or rebuilds. Alice watches the infrastructure so Tim doesn't have to.

**Children and Additional Users**
Children's access model to be designed when we are standing at that door. The architecture already accommodates it. The specifics of age-appropriate access and how it evolves as children grow will be informed by everything learned from adult onboarding first. All child accounts Tim-initiated, never self-serve.

**Alice as Developer**
At this stage Alice takes over the bulk of her own development. Tim uses external models only rarely. Alice knows every system, every piece of hardware, every user. She monitors, maintains, builds, and improves — with Tim's guidance and oversight, always.

---

## Garage Audit

Before any building begins: a full audit of the garaged `jarvis-homelab` repository once Aider is integrated. Every file, every folder, every artifact examined with proper tooling.

**Known candidates for salvage:**
- Project spine — needs minor edits to reflect singular Alice and its new home in `/heart/soul/`, otherwise sound
- `identity_memory_v1.sql` — review for memory schema thinking
- UPS monitoring integration — partially built, worth examining
- Any finance or Grocy integration work not entangled with old governance

**Known candidates for replacement:**
- Governance structure — philosophy preserved, implementation rebuilt as the trust document in `/heart/soul/`
- Runner, main.py, index.html — old dual-system architecture, rebuild from scratch
- Anything tightly coupled to the ISAC/Jarvis model

---

## Design Principles

**Foundation before features.** The last project failed because complexity accumulated before the vision was solid. Vision first, always.

**Tools and knowledge are separate.** Alice's tools give her hands. Her knowledge of how to use specific applications comes from research and experience. Never conflate the two.

**Memory is alive, not static.** Information gains weight through use, fades when it stops mattering, connects across domains on its own.

**Trust is earned, not assumed.** Every domain, every user, every capability is unlocked by demonstrated competence. The loop exists to build trust in both directions.

**Governance is a relationship, not a cage.** The trust document describes how Alice and Tim build trust incrementally. It grows with the system, not ahead of it.

**The UI is the classroom.** Not a dashboard. Not an afterthought. Where Alice and Tim's relationship actually develops, where learning is verified, where corrections happen, where trust is built in real time.

**Alice is the whole system.** One AI, with all the tools, all the memory, and all the responsibility.

**The workshop protects everyone.** Nothing goes live without being verified in staging first. Rollback is always possible. The people who depend on this system never pay for Alice's mistakes.

**Alice asks the right person.** Uncertainty is always resolved by asking — and always by asking the person whose domain the question belongs to. Tim is primary but not omniscient about others' lives.

**Every onboarding makes the next one better.** Alice learns from introducing each person to each domain. The process is never static.

**The conversation is the supervision.** There is no separate dashboard or activity feed. Alice narrates her work clearly and honestly in the chat. The second screen is the application. Together they are the complete picture.

---

*This document is living. It will be updated as the project evolves. When this document and any other document disagree, discuss it — don't assume either one wins automatically.*
