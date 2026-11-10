# Multi-store

A store is its own workspace: its own data, team, roles, settings and audit trail. Nothing is merged between stores.

## What you get

- **Stores page**: every shop you belong to, side by side, on growth against the period before, margin, order value and discount rate (rates, not raw sales: a bigger shop is not a better-run one), plus total sales and the average margin.
- **Needs attention**, ranked first: sales down 10% or more, margin 3+ points under your stores' average, products that will run out before an order can arrive, ₹20,000 or more of udhaar over 30 days, and open high alerts.
- **Same period for all** to compare like with like; without it each store is read on its own latest 30 days, and a note says when stores' latest sale dates differ.
- **Add a shop** creates a workspace and opens its Data page. The switcher in the sidebar changes the current shop; the Open button does the same.
- **People**: each shop has its own owner, admins, analysts and viewers; an invited person sees only the shops they were invited to, with that role.

## Rules

- A person sees only workspaces they are a member of (tested: another owner's shop never appears).
- Each shop is read with the person's role in that shop; a viewer can see the comparison but nothing they could not already see there.
- At most 12 shops are compared at once.

## Not built

- **Staff-level targets and sales per cashier.** Sales files do not say who rang up a sale, so staff performance cannot be measured; shop-level targets are on the Goals page.
- Stock transfers between shops, shared product catalogues, and combined customer lists across shops.
- Consolidated reports across shops (each shop reports on its own).

## API

`GET /stores/overview?from=&to=`
