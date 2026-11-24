# R2 · Tax is 20% of what the customer pays for the goods, after the discount

- Result: HELD, for the one basket this test uses
- Asserted: the tax line of the order summary has exactly the text `£7.20`
- Read from the page at that moment: `£7.20`
- Given, the subtotal: `£40.00`
- Given, the discount: `-£4.00`
- Why that value: 40.00 less 4.00 is 36.00, and 20% of 36.00 is 7.20. On the 40.00 before the discount it would be 8.00
- What this does not show: the rate for any other basket. A rate of 20.01% gives this same figure here. It is the tax shown, and R3 is where it is seen to be in the total
- Asserted at: `meaningful-evidence.spec.ts, line 68`, in the test "R2 · tax is 20% of the goods after the discount"
- Picture: `R2-tax.png`, of that part of the page and no more. sha256 `bee7b7b84d9ce595f264f6b81e85e6eb2fd298d0efcc2eb98074bac4b2a225ef`
- Text inside the picture: `Subtotal` `£40.00` `Discount (WELCOME10)` `-£4.00` `Tax` `£7.20`
- Taken at: 2026-11-24T23:07:17.738Z, from a made-up checkout running on this computer only
