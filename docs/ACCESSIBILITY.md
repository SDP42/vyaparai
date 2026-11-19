# Accessibility

What is checked, what was found and fixed, and what has not been tested.

## How it is checked

[`scripts/a11y-audit.js`](../scripts/a11y-audit.js) is a small audit we wrote (no third-party engine) to run on any
page in the browser console. It checks: page language, one `h1`, heading order, a `main` landmark, images
without alt text, links and buttons without a name, form controls without a label, duplicate ids, positive
`tabindex`, touch targets under 24 px, and text contrast against WCAG 2.1 AA (4.5:1, or 3:1 for large text).

On 2026-11-11 it was run on the landing page, the sign-in page and all 23 app pages of that day. The Today, Galla,
Orders and Expiry pages and the new landing page came on 2026-11-12 and have not been through it yet.

## Found and fixed

| Finding | Fix |
|---|---|
| Brand red, muted grey, turmeric-brown and green used for small text were 4.0 to 4.5:1 | Darkened the four text colours in `globals.css` (now 4.8 to 5.9:1 on the cream backgrounds); chart axis grey the same |
| Small text buttons and links 16 to 20 px high | `main button` and small standalone links get a 24 px minimum height |
| Landing nav links 17 px high | Padding added |
| Heading jumps from h1 to h3 on Next steps and Pricing | Now h2 |
| Review stars read as a row of characters and had 1.5:1 contrast | One image with a label ("4 out of 5 stars"), glyphs hidden from screen readers, darker colour |
| Sign-in card link in a pale accent colour (2:1) | Dark text, accent only on the arrow |

## Built in earlier

Skip link, visible focus ring, `aria-live` regions for answers and the voice state, labelled form fields,
`aria-current` on navigation, reduced-motion paths for every animation (the opening is skipped entirely), a
keyboard route through the opening (the scissors are a focusable button: Enter cuts the ribbon, Esc skips).

## Not tested

- A real screen reader (VoiceOver, TalkBack, NVDA): the audit cannot judge reading order or wording.
- Keyboard-only use of every dialog and chart.
- Colour contrast of text over images or gradients is only estimated from the nearest solid background.
- Hindi and Hinglish pages for line-breaking and font fallback on real devices.
