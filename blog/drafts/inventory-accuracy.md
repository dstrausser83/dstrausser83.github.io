---
title: "Inventory accuracy: the metric that decides if your ERP works (and why it's unsexy) — David Strausser"
slug: "inventory-accuracy-the-unsexy-metric-that-decides-whether-yo"
date: "2026-09-23"
tags: erp, inventory, odoo, business, metrics
summary: "Inventory accuracy is the quiet metric that decides whether your ERP works. If your system's stock numbers don't match the warehouse within a couple percent, every downstream number — costs, margins, availability — is fiction. Here's how to measure it, fix it, and keep it fixed."
excerpt: "Why inventory accuracy matters more than you think for Odoo users. The quiet metric that keeps your ERP from failing without flashy reports."
keywords: "inventory accuracy, erp inventory management, odoo inventory, cycle counting"
---

## Quick answer

Inventory accuracy isn't about flashy reports. It's the silent check that tells you if your ERP actually counts what it's supposed to. If your stock numbers don't match what's physically in the warehouse within 1-2%, your whole system is guessing — and every number downstream of inventory (costs, margins, available-to-promise) is wrong too. Fix it with cycle counting, disciplined receiving, and syncing every sales channel to the ERP in real time.

## Why nobody talks about it

You might think your ERP is fine because the interface looks clean and the reports come out on time. Then someone does a physical count and finds you have 400 units of a product the system says you have 900 of — or zero of something the system insists is in stock. That gap is inventory accuracy, and it is the foundation everything else stands on. Get it wrong and your purchasing buys what you already have, your sales team promises what you do not have, and your cost of goods sold is a work of fiction.

It is unsexy because there is no dashboard that fixes it. No AI feature, no add-on, no consultant's magic. It is process discipline: receiving done right, counts done regularly, and every movement recorded. Companies would rather buy software than build discipline, which is why this metric stays broken in so many places.

Here is the uncomfortable part: most companies do not know their accuracy number. They have never measured it. They feel like inventory is "mostly right" because nobody has checked lately. The first time you run a real wall-to-wall count against the system, the result is usually a shock. I have seen variances of thirty percent. The companies that fix it are the ones that decided to look.

## How to measure it

The formula is simple. Count a set of SKUs physically, compare to the system quantity, and divide the accurate lines by the total lines counted. A line is accurate if the physical count matches the system within your tolerance — most operations use zero tolerance for high-value items and a small tolerance for bulk goods.

Do not measure dollars. Measure lines. Dollar accuracy hides problems: being over on a cheap item and under on an expensive one can net to zero dollars while both lines are wrong. Line accuracy tells you the truth about your process.

Benchmarks: world-class operations run 95%+ line accuracy. Most small and midsize businesses I see are at 70-85% and do not know it. Below 90%, you cannot trust the system for purchasing or promising — you are running the warehouse on tribal knowledge and spot checks. The goal is 95% or better, and it is absolutely achievable without exotic technology. It takes process, not software.

Run the measurement monthly at first, then quarterly once you are above 95%. Track it as a KPI the same way you track revenue. When the owner asks about it in the monthly review, it stays fixed. When nobody asks, it drifts.

## The five leaks

Inaccuracy comes from the same five leaks in almost every company. Fix these and accuracy follows.

**1. Receiving without discipline.** Product arrives, someone signs the BOL, and the boxes go straight to the shelf without being counted against the PO. Or they get counted but the receipt never gets posted in the system. Every unrecorded receipt is inventory the system does not know about — which becomes a variance at count time and a phantom shortage in the meantime. The fix: nothing goes to a bin without a posted receipt. No exceptions, no "I'll enter it later." Later does not happen.

**2. Unrecorded movements.** Someone moves stock from bulk storage to the pick face and does not record the transfer. Someone pulls a unit for a warranty replacement and forgets the adjustment. Someone "borrows" from one job to finish another. Each one is small. Together they are death by a thousand cuts. The fix is cultural more than technical: every movement gets recorded, and the system has to make recording fast enough that people actually do it. If your transfer process takes six clicks, people will skip it. Get it to two.

**3. Damaged, expired, and scrapped goods still on the books.** The pallet of water-damaged product sitting in the corner is still in the system at full quantity. The expired lot nobody quarantined is still available-to-promise. These are not counting errors — the count was right when it was received. They are status errors, and they accumulate quietly. The fix: a quarantine location in the system and a weekly habit of moving dead stock into it. What gets measured gets managed; what sits in the corner gets forgotten.

**4. Sales channels out of sync.** Your POS, your web store, your Amazon channel — if any of them does not update the ERP in real time, stock numbers drift between syncs. This is the leak that causes overselling: the web store shows twelve units because the last sync was an hour ago, but the warehouse shipped ten of them twenty minutes ago. The fix: real-time integration for every channel, and if a channel cannot do real-time, buffer its available quantity so you never promise what might already be gone.

**5. No cycle counting.** The annual physical count is an autopsy — it tells you what died, not how to keep things alive. Without regular cycle counts, small errors compound for eleven months and the annual count becomes a multi-day shutdown that everyone dreads. The fix below replaces it.

## Cycle counting: the actual fix

Cycle counting means counting a small slice of inventory on a regular rotation instead of everything once a year. ABC classification drives the schedule: A items (high value or high velocity) get counted monthly or weekly, B items quarterly, C items twice a year. A team of one or two people can cycle-count a midsize warehouse without stopping operations.

The discipline that makes it work: when a count is off, you do not just adjust the number — you find out why. Was it a receiving error? An unrecorded transfer? A BOM that consumes the wrong quantity? Every variance is a process defect, and fixing the defect prevents the next hundred variances. Companies that just adjust and move on stay at 85% forever. Companies that investigate each variance climb past 95% within two or three quarters.

In Odoo, cycle counting is built in: define your locations, set up inventory adjustments as a routine operation, and use the built-in reports to track adjustments over time. The tooling is the easy part. The habit — count, investigate, fix the process — is the whole game.

## Setup mistakes that doom accuracy from day one

For Odoo users especially, accuracy starts with configuration. Set up your locations and product categories correctly from the start — warehouse zones, quarantine locations, staging areas. If everything lives in one big "stock" location, you cannot count by zone and you cannot isolate problems. Skip this step and accuracy suffers from day one.

Product setup matters too: units of measure must be right (buying in cases, selling in eaches, stocking in pallets — get the conversions locked), and every product needs a consistent tracking method. Decide upfront which items are tracked by lot or serial number; adding traceability later to a live warehouse is painful.

## Frequently asked questions

### How do I know if my inventory accuracy is low?

If your stock counts don't match physical counts within 1-2% of lines over a month, you're under. Check your adjustment history in the ERP — if you're posting large adjustments every count, the process is leaking. And if you've never measured it, assume it's worse than you think.

### Can Odoo handle complex inventory rules?

Yes, but it's about setup. For most small businesses, Odoo's default rules work — locations, routes, and reordering rules cover the common cases. If you need custom logic, it's doable but requires careful configuration. Avoid overcomplicating it: every custom rule is a rule someone has to understand during a count.

### Why does this metric matter more than others?

Because it's the foundation. If inventory is wrong, all downstream data — sales, costs, pricing, purchasing — becomes unreliable. Revenue gets the attention, but inventory accuracy decides whether the numbers behind the revenue are real.

### What's a realistic accuracy target for a small business?

95% line accuracy. That means 95 out of 100 counted lines match the system. It's enough to trust the system for purchasing and promising without constant firefighting. Getting from 80% to 95% typically takes two to three quarters of disciplined cycle counting — not new software.

