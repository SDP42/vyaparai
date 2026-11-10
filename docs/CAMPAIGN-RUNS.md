# Campaigns: consent, sending and measuring

The planner (see [CAMPAIGNS-PLAN](research/CAMPAIGNS-PLAN.md)) suggests who to message and with what offer. This part makes it safe to act and tells you whether it worked.

## Consent and contacts

- Per customer: a phone number (digits with country code; shown only as `•••• 1234`), a consent state (agreed, said no, not asked), **how and when** they agreed, and an opt-out date.
- Import a CSV (Customer, Phone, Consent yes/no, Source) or record one customer at a time.
- A STOP is final until the customer agrees again, and re-adding them requires saying how they agreed. Opt-outs match by customer key or phone.
- Only customers who agreed, have a phone and have not opted out can be in a campaign. If nobody qualifies, launching is refused.
- Every consent change and opt-out is audited.

## Launch and send

- Launching freezes the audience: the segment's customers who are eligible, split into **treatment** and **holdout** by a stable hash drawn from the *eligible* group, so the holdout is comparable.
- **Nothing is sent by the product.** Each treatment message is a WhatsApp link (`wa.me`) a person opens and sends, then marks as sent. WhatsApp's business API needs approval and fees, and a personal message from the shop's own number is what small shops already do.
- Consent is re-checked each time the outbox is opened or messages are marked: someone who opts out after launch disappears from the outbox.
- A daily cap (default 100) limits how many can be marked sent per workspace.
- Sending is an owner or admin action; analysts record consent.

## Measuring

Measured from the day the first message goes out, over the window (default 14 days), on completed orders:

- **Purchase rate**: messaged versus held back, difference in percentage points with a 95% interval (Newcombe, built from Wilson intervals).
- **Spend and profit per customer**: difference with a 95% bootstrap interval (2,000 resamples, seeded so it is repeatable). Profit counts only lines with a recorded cost and is after discounts, so a discount that did not pay for itself shows as a loss.
- **Extra profit** = difference per customer x customers messaged, with its range.
- **Verdict**: *it worked* only if the whole interval is above zero, *it did worse* only if it is entirely below, otherwise *cannot tell yet*.
- Warnings: groups under 30, no holdout, and how many customers per group a 5-point lift would need.

## Limits

- Only messages marked as sent count as treatment. If the owner sends but forgets to mark, those customers are missing from the result.
- Orders must carry the same customer key used in consent. Walk-in sales without a customer cannot be attributed.
- The holdout shows the effect of the campaign for this audience in this window, not for other shops or seasons.
- Small shops will often get "cannot tell yet". That is the honest answer, not a failure.
