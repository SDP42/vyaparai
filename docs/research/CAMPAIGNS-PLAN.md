# Campaigns and retention automation: plan

Status: proposed (2026-11-08). Builds on Phase 3 segments and product margins.

## Goal

Turn a segment into an action a shop owner can approve in a minute: who to contact, what to say,
what offer is safe to give, and how to measure whether it worked.

## What the research added (2026-11-09)

Mostly vendor blogs, so directional only. Sources: [win-back timing and offers](https://www.pecan.ai/blog/how-to-win-back-customers/),
[win-back campaigns](https://www.talon.one/blog/win-back-campaign),
[WhatsApp and DPDP consent](https://www.scconline.com/blog/post/2026/07/29/whatsapp-chatbot-opt-in-consent-dpdp-act-compliance/),
[WhatsApp opt-in in India](https://blog.campaignhq.co/whatsapp-opt-in-management-india-2026/).

- **Do not open with a deep discount**; escalate across steps (value message, small offer, best offer). Built as the step-by-step ladder.
- **Time by each customer's own rhythm**, not a fixed 90 days: we show how many times their usual gap has passed.
- **Judge by a holdout**, not attributed revenue; some of the discount goes to people who would have returned anyway. Built as a stable holdout group.
- **Consent is per channel, purpose-specific, recorded and revocable**, under both Meta's rules and the DPDP Act; no small-business exemption was found. C1 states it and marks every row "not recorded"; C2 stores it.
- No independent study compares discount depths, so the default ceilings are starting points to test with the holdout.

## Principles

1. **Draft and approve, never auto-send at first.** The owner reviews every campaign. Automation
   means "prepare the audience, message and offer", then "send on approval" or on a schedule the owner set.
2. **Margin-guarded offers.** A discount is only suggested if the products it covers keep a margin
   above a floor the owner sets (we already compute margin per product). The UI shows the expected cost.
3. **Consent first.** Only customers with recorded consent for the channel are contactable. Opt-out is
   honoured at once and logged. India's DPDP Act and the WhatsApp/SMS rules (opt-in, DLT-registered
   templates for SMS) apply; this must be confirmed with counsel before real sending.
4. **Honest measurement.** Every campaign keeps a holdout group (default 10 %) so uplift is measured
   against customers who were not contacted, not against last month.
5. **No dark patterns.** No fake urgency, no per-customer price discrimination beyond a published offer
   tier; offers are by segment, explained in plain words.

## Segment playbook (defaults the owner can edit)

| Segment | Goal | Default idea | Offer guard |
|---|---|---|---|
| Champions | Keep and reward | Early access, thank-you, referral ask | No discount by default |
| Loyal | Raise frequency | Bundle suggestion from basket pairs | Small, margin-checked |
| Promising / New | Second order | Welcome-back within 30 days | One-time, capped |
| Needs attention | Re-engage | Reminder of usual products | Optional small offer |
| Can't lose / At risk | Win back | Personal message, stronger offer | Largest allowed, still above floor |
| Hibernating | Reactivate or let go | One win-back, then suppress | Capped, then stop |

## Data additions

- `customers`: phone (hashed for display), email, `consent_whatsapp`, `consent_sms`, `consent_email`, `opted_out_at`, consent source and date.
- `campaigns`, `campaign_audience` (frozen snapshot of who was selected and why), `campaign_messages`, `offers`, `redemptions` (links a later order to an offer).
- Audit log entries for create, approve, send, opt-out.

## Delivery slices

| Slice | What | Effort |
|---|---|---|
| C1 ✅ | Audience builder from segments/filters, suggested offer with margin check and cost estimate, message templates (English and Hinglish), CSV export for manual sending, no consent-sensitive sending | 2 d |
| C2 | Consent fields and import, suppression and opt-out, campaign records, approval step, holdout | 2 d |
| C3 | Sending through one provider (WhatsApp Business API or email first), delivery status, rate limits, DLT/template approval handling | 3 d |
| C4 | Measurement: redemptions, uplift versus holdout, revenue and margin impact; automations ("when a Loyal customer turns Cooling, draft a nudge") that still need approval | 2–3 d |

## Open decisions

- Which channel first (WhatsApp Business, SMS, email)? Needs provider choice and cost.
- Do we store customer phone/email (the sample data has only a customer ID)? Needs the data model change and a privacy notice.
- Default holdout size and margin floor.
- Legal review of consent wording before C3.
