# R3 · The total is the subtotal, less the discount, plus the tax

- Result: HELD, for the one basket this test uses
- Asserted: the total line of the order summary has exactly the text `£43.20`
- Read from the page at that moment: `£43.20`
- Given, the subtotal: `£40.00`
- Given, the discount: `-£4.00`
- Given, the tax: `£7.20`
- Why that value: 40.00 less 4.00 plus 7.20 is 43.20
- What this does not show: that any of the three figures it adds is right. It shows that they add up to the total
- Asserted at: `meaningful-evidence.spec.ts, line 93`, in the test "R3 · the total is the subtotal, less the discount, plus the tax"
- Picture: `R3-total.png`, of that part of the page and no more. sha256 `983965ff0f1e2cb69878041186d454d13da939413c4e699e12986563ff850182`
- Text inside the picture: `Subtotal` `£40.00` `Discount (WELCOME10)` `-£4.00` `Tax` `£7.20` `Total` `£43.20`
- Taken at: 2026-11-24T23:07:17.846Z, from a made-up checkout running on this computer only
