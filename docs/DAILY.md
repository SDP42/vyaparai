# Daily routines

The parts of a shop day that happen every day, made quick. Research and ranking: [research/DAILY-USE-FEATURES.md](research/DAILY-USE-FEATURES.md).
Everything here is a record or a calculation for a person to check: nothing is sent, paid or ordered.

| Page | What it does | Who sees it |
|---|---|---|
| **Today** (`/app/today`) | The first screen of the day: the last day's sales against the same day last week, who to call for udhaar, what to order, what is expiring, whether yesterday's galla was closed, urgent alerts. A one-line entry box ("Ramesh ko 200 udhaar", "Sunita ne 500 diye", "chai 60 kharcha") reads the sentence back before saving it | Every job; each card follows the job's capabilities (counter staff see no credit or cash) |
| **Galla** (`/app/galla`) | Close the day: morning cash, cash/UPI/card sales, cash taken out, cash counted. It works out what should be in the drawer (morning cash + cash sales + udhaar paid back − cash expenses − taken out), shows short or extra, compares typed sales with the sales file, and a rough day profit (sales × the last 30 days' margin − the day's expenses). Expenses by category and how they were paid | Owner, operations manager, accountant (view only) |
| **Orders** (`/app/orders`) | What to order, grouped by the supplier who last billed each product, as a message in English, Hinglish or Hindi to copy or share through the phone's share sheet | Owner, operations manager, analyst, accountant |
| **Expiry** (`/app/expiry`) | A short list of items the shop worries about, sorted into expired, this week, this month and later, with one tap to mark each sold, discounted, returned or thrown away | Owner, operations manager, counter staff |

## Honest limits

- The galla tally assumes udhaar paid back that day came in cash; payment mode is not recorded on udhaar entries.
- The rough profit is an estimate from the last 30 days' gross margin; with no cost data it is not shown.
- The expiry list is a reminder list, not a pharmacy register; it does not read batches from bills.
- One-line entries understand a few common shapes in Hinglish and Hindi; anything else is refused with an example
  rather than guessed. Hindi product names and numbers use the same parsers as the assistant.
- Order lists group by the supplier on the last confirmed bill; products never billed group under "No supplier yet".

## API

`GET /workspaces/{id}/daily/today` · `GET|PUT .../daily/close` · `GET .../daily/close/history` ·
`GET|POST .../daily/expenses`, `DELETE .../daily/expenses/{id}`, `GET .../daily/expense-categories` ·
`GET|POST .../daily/expiry`, `POST .../daily/expiry/{id}/clear` · `GET .../daily/orders?lang=` ·
`POST .../daily/quick/parse`, `POST .../daily/quick/save`. Writes need the owner or admin role; reading the galla
needs the `cash` capability, the expiry list `stock`, order lists `supplier`.
