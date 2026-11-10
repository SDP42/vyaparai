# Connectors and scheduled imports (Phase 15)

_2026-11-10. Search results were thin on billing-app export layouts, so this records what was and was not confirmed._

## Why

Every forecast, alert and digest is only as fresh as the last import. Owners who must re-upload a file by hand stop doing it,
and the product goes stale. Phase 15 removes the chore.

## What was found

- **Billing-app exports.** Searches for the exact column names of Vyapar, Tally Prime, Busy and myBillBook sales exports found nothing
  reliable (one Vyapar help page confirms CSV and Excel export exist but lists no columns). **No app-specific presets were built.**
  Guessing headers would silently mis-map real files.
- **Google Sheets.** A sheet can be published to the web as CSV (File, Share, Publish to web), giving a live link; or shared as
  "Anyone with the link" and read through its export address. A published link is readable by anyone who has it, so customer
  names and phone numbers must stay out of it ([Searchspring guide](https://help.searchspring.net/hc/en-us/articles/34198395489179-How-to-convert-your-Google-Sheets-into-a-CSV-URL), [9to5Google](https://9to5google.com/guides/publish-to-the-web/)).
- **Safe fetching.** [OWASP SSRF Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html):
  prefer an allow-list; resolve once, validate the address and connect to exactly that address (a name check alone does not stop DNS
  rebinding); disable redirects or check every hop; deny-lists are bypass-prone. See also the [Webhook Security cheat sheet](https://cheatsheetseries.owasp.org/cheatsheets/Webhook_Security_Cheat_Sheet.html).

## Design

1. **Remembered mappings, not app presets.** When an owner confirms a column mapping, it is saved against the file's header
   fingerprint (order, case and punctuation ignored). The next file with the same layout is recognised and pre-filled, for uploads and for
   connected links, whichever billing app produced it. A saved mapping is ignored if a column it names has disappeared.
2. **Connected links.** An owner adds a published Google Sheet, Drive or Dropbox link (Google edit links are converted to CSV export links).
   Each link has a schedule (hourly, daily or by hand). Up to five per workspace.
3. **Import only what is new.** A file whose hash is unchanged is skipped; a changed file goes through the normal pipeline and orders are
   idempotent by bill number, so a full export every day adds only the new bills and never duplicates.
4. **Honest failures.** A link that cannot be fetched, is a web page instead of a file, is private, or cannot be matched shows a plain message
   and a next step ("upload this file once by hand and confirm the columns; we will remember them"). After five failures in a row the link
   pauses and an alert is raised.
5. **Scheduling.** `python -m app.import_runner` from cron every 15 minutes; each link follows its own schedule.

## Safety rules for the fetch (all tested)

https only, standard port, no credentials in the link; host must be on the allow-list (Google Sheets and Drive, Dropbox, GitHub raw;
an administrator can open it to any public host); the name is resolved once and every address must be an ordinary public address (loopback,
private, link-local and metadata, multicast, reserved, unspecified and IPv4-in-IPv6 are refused); the connection goes to the validated
address with the original name for TLS; redirects are followed by hand, at most three, each re-checked; 20-second timeout; size cap; a web
page is refused; error messages never reveal internal addresses. A test run against live DNS refused `localhost`, a cloud metadata name
and an unlisted host, and a real HTTPS download from an allowed host succeeded.

## Limits

- Only public or "anyone with the link" files; no sign-in (OAuth) to Google or billing apps yet.
- The file must be CSV or Excel in a layout we can map; if the first file cannot be matched, one manual upload teaches the mapping.
- No email-in, watch-folder or direct database connectors yet; no real-time push, only scheduled pulls.
- The runner is a command that something must schedule.
- Anyone with a published link can read it; the app warns the owner.
