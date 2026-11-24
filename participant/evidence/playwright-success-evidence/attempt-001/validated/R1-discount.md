# R1 · The discount is 10% of the subtotal

- Result: HELD, for the one basket this test uses
- Asserted: the discount line of the order summary has exactly the text `-£4.00`
- Read from the page at that moment: `-£4.00`
- Given, the subtotal: `£40.00`
- Given, the label of the discount line: `Discount (WELCOME10)`
- Why that value: 10% of 40.00 is 4.00, shown as an amount taken off
- What this does not show: that the discount is taken off what the customer pays. This line reads the same when the discount is printed and then ignored: R3 is where that is seen. Nor does it show the rate for any other subtotal. A flat 4.00 off would read the same
- Asserted at: `meaningful-evidence.spec.ts, line 46`, in the test "R1 · the discount is 10% of the subtotal"
- Picture: `R1-discount.png`, of that part of the page and no more. sha256 `695f75f5c5e3c0c0de8269b4b818e7b2e177ef5d7464c542fc33f65399e20859`
- Text inside the picture: `Subtotal` `£40.00` `Discount (WELCOME10)` `-£4.00`
- Taken at: 2026-11-24T23:07:17.628Z, from a made-up checkout running on this computer only
