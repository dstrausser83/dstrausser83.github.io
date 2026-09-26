---
title: "The go-live checklist nobody tells you: 5 tests to run before flipping the switch on a new ERP — David Strausser"
slug: "the-go-live-checklist-nobody-gives-you-what-to-test-before-f"
date: "2026-09-23"
tags: erp, sap, odoo, go-live, testing
summary: "ERP go-lives fail on the small stuff nobody tested: bad data syncs, wrong permissions, untested edge cases. Run these five tests with real data and real users before you flip the switch, and go-live day stays boring — which is exactly what you want."
excerpt: "A single dad's practical guide to ERP go-live testing. Five checks that catch costly mistakes before production. No fluff, just what works."
keywords: "erp go-live checklist, erp testing, odoo go-live, sap business one testing"
---

## Quick answer

Before any ERP go-live, test data sync, user permissions, and edge cases with real data and real users. The failures that hurt most are rarely the big features. They are the small checks nobody ran. Budget a focused few days for this, not a few hours, and go-live day will be boring — which is exactly the goal.

## Why go-lives go sideways

I have watched enough go-lives to know the pattern. The big demo went great. The training sessions went fine. Everybody signed off. Then Monday morning hits, the first real order comes in, and something small breaks — a tax code that did not carry over, a warehouse user who cannot post a receipt, a report the controller needs that nobody built. None of these are hard problems. Every one of them was catchable. They just never got tested because the testing plan covered the happy path and stopped there.

The happy path always works. It worked in the demo, it worked in training, and it will work on go-live day. Your business does not run on the happy path. It runs on the messy middle: the partial shipments, the credit memos, the rush orders, the user who does things in a slightly different order than the manual says. That is what you test.

## The 5 tests

**1. Data sync.** Confirm your old system's data lands correctly in the new one: customer records, invoice numbers, open balances, item masters. Run it with real data, not a tidy sample. Real data has the duplicates, typos, and odd characters that break imports, and you want to meet them now.

This is the test teams skip most often, because the migration already "worked" once during the build. But the build migration ran months ago on a snapshot. Since then, the business kept running on the old system — new customers, new items, new open orders. The delta is where the surprises live. Run a fresh full load into a test company a week before go-live and reconcile it: total open AR in the old system versus the new, total open AP, inventory valuation by warehouse. If the numbers do not tie to the penny, you do not go live. Full stop.

**2. User permissions.** Log in as each role and try to do the job. Sales should not see payroll. Warehouse should not edit pricing. Permission screens always look right until you test them as the actual user.

Do this literally: sit down, log in as the warehouse lead, and try to receive a purchase order, transfer stock, and print a pick list. Then try something they should not be able to do — void a posted invoice, change a price, run payroll. If the system lets them, your roles are wrong. I have seen warehouse staff with full admin rights because someone cloned the wrong template during setup and nobody checked. That is a segregation-of-duties problem that will embarrass you in an audit and cost you real money if someone makes an honest mistake with too much power.

Test every role that touches the system, including the ones people forget: the outside sales rep who only logs in twice a month, the temp in shipping, the controller's assistant. Roles rot over time — someone gets extra access "just for this week" and it never gets revoked. Go-live is your one clean starting point. Start clean.

**3. Edge cases.** Test the weird-but-real scenarios: a payment arriving after cutoff, a credit memo against a closed period, a customer with two ship-to addresses. Rare in testing, constant in production.

Here is how to find your edge cases: ask the most experienced person in each department what annoys them about the current system. Not what is broken — what is annoying. The annoying stuff is the edge cases. "Every month I have to manually fix the freight on drop-ship orders." "Returns from last quarter always post to the wrong account." Those are your test scripts. Write each one down as a scenario, run it in the test company, and confirm the result posts where it should.

**4. Real-time updates.** Confirm changes show up when they should. If there is a sync delay between modules, find it now. That is how double shipments and double billing happen: one screen says the inventory moved and the other has not caught up yet.

This matters most when you have integrations: the ERP talking to a web store, a warehouse management add-on, EDI with a big customer. Each of those has a sync rhythm — real-time, every fifteen minutes, nightly batch. Map every integration and its timing, then test the handoff under load. Create an order in the web store and time how long it takes to appear in the ERP. Receive inventory in the warehouse module and check when the available-to-promise number updates.

The failure mode here is always the same: two people acting on two different versions of the truth. Sales promises a ship date based on inventory the warehouse already allocated. Accounting bills based on a shipment that has not posted yet. These are not system bugs — the system is doing what it was configured to do. They are expectation bugs, and the fix is knowing the timing and training people around it before it costs you a customer.

**5. One real user's full day.** Sit with an actual user and watch them work start to finish. You will find the confusing screens, the five-click tasks that should take one, and the reports nobody can find. No manual covers this.

Pick the person who will live in the system the most — usually someone in order entry, purchasing, or the warehouse — and shadow them for a full day in the test environment running real scenarios. Do not guide them. Do not explain. Just watch and take notes every time they hesitate, click the wrong thing, or ask "where do I find...?" Every hesitation is a training gap or a design problem, and every one of them becomes a support ticket on day two if you do not fix it now.

This test also catches the missing-reports problem. Every implementation has a moment where someone asks for a report that was never in scope: the open-orders-by-sales-rep summary the owner looks at every morning, the margin-by-customer view the sales manager built in Excel for years. Find these before go-live, not after. Building a report in week one is a minor task. Discovering the business cannot operate without it on day two is a crisis.

## What to do when a test fails

A failed test before go-live is a gift. It is the system telling you exactly where it will break, on your schedule, with no customers watching. The wrong response is to argue the test was unrealistic. If a real user doing a real task hit it in testing, a real user will hit it in production.

And set the expectation with leadership now: the first week will surface things no test caught. That is normal. What is not normal is discovering them with no plan. Keep the partner on standby for the first two weeks, keep a daily fifteen-minute triage call on the calendar, and keep a single list where every issue goes. Most of them will be training. A few will be real. You will sort them out fast if you are looking.

## Frequently asked questions

### What is the biggest mistake teams make?

Testing with clean sample data instead of messy real data. Production data is where the surprises live. The second biggest mistake is letting the partner's sign-off substitute for your own testing — their checklist gets you live, yours keeps you healthy.

### How long should testing take?

Long enough to run every check above with real data and real users. For most small and midsize rollouts that means a focused few days, not weeks. Rushing it is how go-lives slip. If leadership is pushing the date, cut scope, not testing — go live with fewer modules done right rather than everything done halfway.

### Can a smaller rollout skip testing?

Smaller scope means a smaller checklist, not a zero checklist. Even a single-module go-live deserves the data sync and permissions checks at minimum. The tests scale down; they do not disappear.


### What if we find a blocker the week of go-live?

Delay. A one-week delay costs you a week. A broken go-live costs you a quarter — in cleanup, in credibility with your team, and in the fixes you will be paying the partner to make under pressure. Nobody ever got fired for delaying a go-live by a week to fix a data problem. Plenty of people have been fired for the mess that followed a go-live they knew was not ready.

Go-live day should be boring. Run these five tests and it will be.
