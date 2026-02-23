# Alice — Trusted Sources Whitelist

**Path:** `/opt/jarvis/governance/operational_knowledge/trusted_sources.md`
**Status:** Active
**Authority:** Admin (Tim)
**Purpose:** Canonical list of official documentation sites Alice is permitted to treat as authoritative when learning, verifying facts, or answering questions about the systems in this stack. Alice should prefer these sources over third-party blogs, forums, or aggregators unless no official source exists.

---

## How to Use This Document

- When Alice performs a `web.search` or `web.open`, results from these domains should be weighted as **high-trust**.
- Results from domains NOT on this list should be treated as **unverified** and labeled as such.
- This list is not exhaustive — if a new system is added to the stack, this document must be updated by Admin before Alice treats that system's docs as trusted.
- Alice must never silently expand this list. Any proposed addition must be surfaced to Admin for approval.

---

## Trusted Sources by System

### Docker

| Domain | Description |
|---|---|
| `docs.docker.com` | Official Docker documentation (Engine, CLI, Compose, Desktop) |
| `hub.docker.com` | Official Docker Hub — image registry and official image documentation |

**Seed URLs:**
- https://docs.docker.com/
- https://docs.docker.com/engine/
- https://docs.docker.com/compose/
- https://hub.docker.com/

---

### Docker Compose

| Domain | Description |
|---|---|
| `docs.docker.com` | Docker Compose v2 reference (same domain as Docker docs) |

**Seed URLs:**
- https://docs.docker.com/compose/
- https://docs.docker.com/compose/compose-file/
- https://docs.docker.com/compose/reference/

---

### Ubuntu / Debian (Host OS)

| Domain | Description |
|---|---|
| `ubuntu.com` | Official Ubuntu documentation and release notes |
| `help.ubuntu.com` | Ubuntu community help wiki |
| `manpages.ubuntu.com` | Ubuntu man pages |
| `debian.org` | Debian project documentation (upstream of Ubuntu) |
| `packages.ubuntu.com` | Ubuntu package search |

**Seed URLs:**
- https://ubuntu.com/server/docs
- https://help.ubuntu.com/
- https://manpages.ubuntu.com/
- https://www.debian.org/doc/

---

### DockStarter

| Domain | Description |
|---|---|
| `dockstarter.com` | Official DockStarter documentation |
| `github.com/GetchaDEAGLE/DockSTARTer` | DockStarter source and issue tracker |

**Seed URLs:**
- https://dockstarter.com/
- https://dockstarter.com/basics/
- https://github.com/GetchaDEAGLE/DockSTARTer

---

### Grocy

| Domain | Description |
|---|---|
| `grocy.info` | Official Grocy project site and documentation |
| `github.com/grocy/grocy` | Grocy source, API reference, and issue tracker |
| `github.com/grocy/grocy-api-client` | Official Grocy API client reference |
| `demo.grocy.info` | Grocy live demo (read-only reference for UI/API behavior) |

**Seed URLs:**
- https://grocy.info/
- https://github.com/grocy/grocy
- https://github.com/grocy/grocy/wiki
- https://demo.grocy.info/api

---

### Barcode Buddy

| Domain | Description |
|---|---|
| `github.com/Forceu/barcodebuddy` | Official Barcode Buddy source, documentation, and API reference |
| `barcodebuddy.net` | Official Barcode Buddy project site |

**Seed URLs:**
- https://github.com/Forceu/barcodebuddy
- https://github.com/Forceu/barcodebuddy/wiki

---

### OpenFoodFacts

| Domain | Description |
|---|---|
| `world.openfoodfacts.org` | OpenFoodFacts main site and product database |
| `openfoodfacts.github.io` | OpenFoodFacts API documentation |
| `github.com/openfoodfacts` | OpenFoodFacts source and API specs |
| `wiki.openfoodfacts.org` | OpenFoodFacts wiki including API documentation |

**Seed URLs:**
- https://world.openfoodfacts.org/
- https://openfoodfacts.github.io/openfoodfacts-server/api/
- https://wiki.openfoodfacts.org/API

---

### Home Assistant

| Domain | Description |
|---|---|
| `home-assistant.io` | Official Home Assistant documentation |
| `developers.home-assistant.io` | Home Assistant developer and REST API documentation |
| `github.com/home-assistant` | Home Assistant source and integrations |

**Seed URLs:**
- https://www.home-assistant.io/docs/
- https://developers.home-assistant.io/docs/api/rest/
- https://www.home-assistant.io/integrations/

---

### Firefly III (Finance — System of Record)

| Domain | Description |
|---|---|
| `docs.firefly-iii.org` | Official Firefly III documentation |
| `api-docs.firefly-iii.org` | Official Firefly III REST API reference |
| `github.com/firefly-iii/firefly-iii` | Firefly III source and issue tracker |

**Seed URLs:**
- https://docs.firefly-iii.org/
- https://api-docs.firefly-iii.org/
- https://github.com/firefly-iii/firefly-iii

> **Note:** Finance execution is currently BLOCKED (FRTK LAP). These sources are trusted for reading and learning only. No writes to Firefly III are permitted without explicit Admin unblocking.

---

### Python (Runtime / Standard Library)

| Domain | Description |
|---|---|
| `docs.python.org` | Official Python documentation and standard library reference |
| `pypi.org` | Python Package Index — package metadata and documentation links |
| `peps.python.org` | Python Enhancement Proposals |

**Seed URLs:**
- https://docs.python.org/3/
- https://pypi.org/
- https://peps.python.org/

---

### FastAPI / Starlette (API Framework)

| Domain | Description |
|---|---|
| `fastapi.tiangolo.com` | Official FastAPI documentation |
| `starlette.io` | Official Starlette documentation |

**Seed URLs:**
- https://fastapi.tiangolo.com/
- https://www.starlette.io/

---

### SQLite (Embedded Database)

| Domain | Description |
|---|---|
| `sqlite.org` | Official SQLite documentation and SQL reference |

**Seed URLs:**
- https://www.sqlite.org/docs.html
- https://www.sqlite.org/lang.html

---

### httpx (HTTP Client)

| Domain | Description |
|---|---|
| `www.python-httpx.org` | Official httpx documentation |

**Seed URLs:**
- https://www.python-httpx.org/

---

### PyMuPDF / fitz (PDF Rendering)

| Domain | Description |
|---|---|
| `pymupdf.readthedocs.io` | Official PyMuPDF documentation |
| `github.com/pymupdf/PyMuPDF` | PyMuPDF source and issue tracker |

**Seed URLs:**
- https://pymupdf.readthedocs.io/en/latest/

---

## Domains Explicitly NOT Trusted by Default

The following categories of sources are **not** on the trusted list and must be treated as unverified:

- Third-party blogs (Medium, Dev.to, Hashnode, etc.)
- Stack Overflow / Reddit (useful for leads, not authoritative)
- YouTube / video content
- AI-generated documentation mirrors
- Any domain not listed above

Alice may still retrieve and use content from untrusted sources, but must label it as **unverified** and must not present it as authoritative.

---

## Change Control

- This document may only be modified by Admin (Tim).
- Alice must not silently add or remove entries.
- If Alice identifies a missing trusted source, she must surface it as a proposal and wait for explicit approval before treating it as trusted.
- Version changes require a comment noting what was added/removed and why.

---

*Last updated: 2026-02-01 | Owner: Admin (Tim)*
