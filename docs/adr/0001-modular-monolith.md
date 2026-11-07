# 0001 · Modular monolith with FastAPI

- **Date:** 2026-11-07 · **Status:** Accepted

**Context.** A single developer must deliver ingestion, analytics, ML, RAG and agents within ~16 weeks.
Microservices would add deployment, networking and consistency costs without a scaling need.

**Decision.** One FastAPI deployable, organised by layer (`api → services → repositories → models`)
and later by domain module. ML, RAG and agent code lives in `ml/`, `rag/`, `agents/` and is
called through service interfaces.

**Consequences.** Simple local setup and debugging, with one process to deploy. Module boundaries
must be enforced by convention and review. Extraction into a service later is possible because
callers depend on service interfaces.
