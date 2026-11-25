# Requirements: the checkout of the made-up shop

**Made up.** The shop, its products, its prices, its discount code and its tax rule are invented. No rule here is any
real company's. The shop is the small demo checkout in `participant/tests/playwright/demo-app/`, which runs on this
computer only.

These say what the checkout is to do. They are not a description of what the demo does today: the demo has one fixed
basket and one fixed code, and does some of this and not the rest. The last column says which.

## Importance

| Word | Meaning |
|---|---|
| must | The shop cannot open without it. If it is broken, the release is stopped |
| should | Expected by customers. If it is broken, the release may go out with a date for the repair |
| could | Wanted. If it is broken, it waits its turn |

## The requirements

| ID | Importance | Requirement | In the demo today |
|---|---|---|---|
| REQ-01 | must | The subtotal is the sum, over the lines of the basket, of the price of one item times its quantity | yes |
| REQ-02 | must | A valid discount code takes its percentage off the subtotal | yes, for one code |
| REQ-03 | must | Tax is 20% of what the customer pays for the goods, which is the subtotal after the discount | yes |
| REQ-04 | must | The total is the goods after the discount, plus the tax. The amount charged is the total shown | yes |
| REQ-05 | must | Every amount is rounded to whole pence once, at the end, with a half rounding up. No amount is rounded and then used in a further sum | no: the one basket has no part pence |
| REQ-06 | must | Placing the order shows a confirmation with an order reference and the total charged | yes |
| REQ-07 | should | A code that is unknown or past its end date is refused with a message, and no amount changes | no |
| REQ-08 | must | Placing the same order twice, by a second press or a resent request, makes one order and one charge | no |
| REQ-09 | should | The checkout can be completed with a keyboard alone and with a screen reader: the button has a name, and each amount has a label that is read with it | partly: not checked |
| REQ-10 | should | Each amount is shown with the currency sign and two decimal places. A discount is shown as a negative amount | yes |
| REQ-11 | could | The checkout page is shown within 2 seconds on the shop's reference connection | not measured |
| REQ-12 | could | The checkout can be read and used on a screen 320 pixels wide without scrolling sideways | not checked |

## Who decides

The participant acts as the product owner of this made-up shop. The owner decides what a rule means when it is in
doubt, and is the one who can accept a risk that is left untested.

Who can accept a risk: the participant, as product owner of the demo shop.

The tax rule, REQ-03, was ruled on once already. A redesign of the demo worked the tax out on the subtotal before the
discount, and the owner ruled that a bug. That is recorded at the top of
`participant/tests/playwright/demo-app/checkout-server.corrected.mjs`.
