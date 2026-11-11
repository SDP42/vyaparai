# Personas: who sees what, and what the assistant will answer

A shop is several jobs, not one user. The counter staff member who serves customers should not see
the credit book or the margin on every product, and the assistant should not answer them questions
that belong to the owner. A **persona** is the job a member does in the shop. It sits on top of the
workspace **role** (owner, admin, analyst, viewer):

- the **role** decides what a person may *do* (import, edit, invite, approve);
- the **persona** decides what they are *meant to see and ask about*.

Research and rationale: [research/PERSONAS-VOICE.md](research/PERSONAS-VOICE.md).

## The five personas

| Persona | Role it fits | Pages | Assistant answers | Data they may open |
|---|---|---|---|---|
| **Store owner** | owner | all | everything | everything |
| **Operations manager** | admin and above | sales, products, stock, forecasts, festivals, bills, udhaar, reviews, documents, reports, digest, investigate, team | sales, why, products, stock, forecast, alerts, supplier, reviews, festivals, udhaar, next steps, goals | credit, supplier, stock, reports; **not** margin, customer lists, pricing |
| **Data analyst** | analyst and above | analytics, customers, products, pricing, reviews, forecasts, stock, festivals, bills, costs, reports, data | analytics, customers, margin, supplier, pricing, reviews | margin, supplier, customers, stock, reports; **not** the credit book |
| **Accountant** (view only) | viewer and above | sales, pricing, bills, costs, udhaar, documents, reports, digest | sales, why, margin, supplier, udhaar, alerts, goals, pricing | credit, margin, supplier, reports; **not** customers or stock detail |
| **Counter staff** | viewer and above | ask, products, stock, documents, festivals | stock and price of one product, what sells best, today's sales, festivals, policy documents | stock only |

The exact lists are in code, in one place: [`app/services/personas.py`](../apps/api/app/services/personas.py).
A test fails if a new assistant intent is added without being allowed or denied for every persona.

A member with **no persona** keeps plain role-based access, exactly as before. Personas are assigned when
inviting someone, from the Team page, or by a demo sign-in.

## What is enforced, and where

1. **Assistant**: a question outside the persona's remit is not answered. The reply says, in the asker's
   language, that it is not for this job, who to ask, and shows what the persona *can* ask. No numbers are
   computed, so nothing leaks through the wording. The intent decision is made before any tool runs.
2. **Sensitive endpoints**: the credit book, cost and pricing pages, supplier bills and reports require the
   matching capability (`credit`, `margin`, `supplier`, `reports`); without it the API answers 403 "Not part
   of the counter staff view". This is on the server, not just a hidden menu item.
3. **Navigation**: the sidebar, phone bottom bar and "More" sheet show only the persona's pages. Typing an
   address for another page sends them to their own home.
4. **Persona must fit the role**: an owner is always the owner persona; nobody can be given a persona that
   carries more than their role (a viewer cannot be an operations manager). Changing a role clears a persona
   that no longer fits.

## Sample accounts (development)

With `DEMO_LOGIN_ENABLED=true` the sign-in page shows the five people from the table; one tap signs in as a
real account with that persona in one shared sample shop (`Kulkarni General Store`). Their passwords are random
and unknown, so they can only be entered through the one-tap route. The setting is refused in production
(the API will not start), the route answers 404 when off, and it shares the sign-in throttle.

Endpoints: `GET /auth/demo-status`, `POST /auth/demo-login {persona}`, `GET /workspaces/{id}/me` (the caller's
role, persona, pages, suggestions in the chosen language).

## Limits

- Cost and margin are hidden **per field**: for a persona without the `margin` capability (operations manager,
  counter staff), every JSON field named like cost, margin or profit, and the gross-margin metric cards, come back
  empty from the analytics, intelligence, inventory, forecast, alert, digest, recommendation, goal and campaign
  routes (`app/api/masking.py`), and the assistant drops the margin from product answers. Customer routes need the
  `customers` capability. Text that merely mentions a margin (a recommendation sentence) is not rewritten.
- A persona narrows access; it never widens it. Role checks still apply on top.
- The persona descriptions come from general knowledge of Indian retail, not from interviews. They should be
  confirmed with real shop owners.
- Counter staff see only their own sales on the Staff page, matched by the name linked to their account on the Team page (a cashier column on the sales file is needed; without one the page says so).
