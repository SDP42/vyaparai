# Udhaar (credit) intelligence

Many small shops sell on credit and keep the khata in a notebook or a ledger app. This phase shows who owes what, for how long, who to chase first, and drafts a polite message in the customer's language. Nothing is sent by the product.

## Rules

- **Balance** per person = credit given minus payments received.
- **FIFO ageing**: a payment settles the oldest credit first, so what is still owed has an honest age. A payment larger than the dues is shown as an advance, never as a negative debt.
- **Buckets**: 0-30, 31-60, 61-90 and 90+ days. "Overdue" means older than 30 days.
- **Behaviour**: paying (a payment in the last 30 days), slow, not paying (oldest dues over 60 days and no payment for 60), settled.
- **Who to chase first**: rupees owed multiplied by age in months (capped at 4), so a small old debt does not outrank a large fresh one by accident, and a big stale one rises to the top.
- **Reminders**: drafted in Hinglish, English or Hindi, gentle up to 30 days, firmer to 60, then a final notice that further credit stops. Dues under 7 days old are left alone. A WhatsApp link (`wa.me`) pre-fills the text when a phone number is saved; the person presses send.
- **Alert**: more than ₹5,000 older than 30 days raises "udhaar is more than 30 days old" (medium from ₹20,000 or 3 people not paying).
- **Assistant**: "who owes me money", "udhaar kitna baaki hai", "उधार कितना बाकी है".

## Import

A CSV with Date, Name and either Amount plus a Type (credit, given, udhaar, sale or payment, received, jama) or separate Credit and Payment columns; Phone and Note are optional. Negative amounts are read as repayments. Re-importing the same file adds nothing (each entry has a fingerprint). Rows that cannot be read are counted and the first 30 are listed.

## Privacy

Only a name, an optional phone number and the amounts are stored. The phone number is used to open WhatsApp and is not sent anywhere by us. Viewers can see balances; only analysts and above can add entries or draft reminders. Customers are not required to match the sales data.

## Limits

- Names are matched after lower-casing and removing punctuation; "Ramesh S." and "Ramesh Sharma" are different people until the file uses one spelling.
- No promised-pay dates or partial payment plans yet.
- The ageing is only as good as the ledger: unrecorded payments make people look worse than they are.
- The tone of a reminder is a default; the owner should read it before sending, especially for a long-standing customer.
- Demo data (`data/sample/vyapar_demo_udhaar.csv`) is synthetic and was written for this project.

## API

`POST /workspaces/{id}/udhaar/import` · `POST .../udhaar/entries` · `GET .../udhaar/summary` · `GET .../udhaar/parties` · `GET .../udhaar/parties/{key}` · `GET .../udhaar/reminders?lang=` · `GET .../udhaar/template.csv`
