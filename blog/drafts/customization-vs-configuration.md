---
title: "Customization vs. Configuration: The Line That Quietly Kills ERP Budgets — David Strausser"
slug: "customization-vs-configuration-the-line-that-quietly-kills-e"
date: "2026-09-23"
tags: erp, customization, implementation, odoo, sap-business-one
summary: "Customization in ERP systems is expensive and risky, requiring ongoing maintenance, upgrades, and ownership of custom code, while configuration uses built-in tools and survives updates with lower costs. Only customize for processes that generate revenue or meet legal requirements, as most workflows can be adapted to standard ERP features without losing value."
excerpt: "Configuration vs customization in ERP: what each really costs, when custom work earns its keep, and a simple framework for deciding before the invoice decides for you."
description: "Configuration vs customization in ERP: what each really costs, when custom work earns its keep, and a framework for deciding before the invoice decides for you."
keywords: ""
---

Somebody in every ERP demo asks the question. Usually it's the person who owns the spreadsheet everyone is afraid to touch.

"Can it work exactly like our current process?"

The room nods. The salesperson smiles. And somewhere, six months in the future, a budget quietly bleeds out. Not because anyone lied. Because nobody in that room knew they were really asking: should we configure this thing, or customize it?

## Quick answer

Configuration means setting up the ERP with the options it already gives you: fields, workflows, approval rules, report layouts, toggles. Customization means changing the software itself, writing code the vendor never wrote. Configuration is cheaper to build, cheaper to keep, and it survives upgrades. Customization has a real place in the world, but every custom line is a line you now own. You test it. You fix it. You carry it through every upgrade, forever. So the default answer is configuration. Customize only for the things that genuinely make you money.

## Same word, different invoice

Here's the confusion. In conversation, everything is "customizing the ERP." The vendor says it, the partner says it, your team says it. But there are two completely different activities hiding inside that one word, and they bill very differently.

Configuration is working inside the lines. In Odoo, it's building a view in Studio, adding a field, wiring up an automated action. In SAP Business One, it's user-defined fields, formatted searches, approval procedures. Nobody wrote code. The next upgrade rolls in and your setup rolls with it, because it's all native.

Customization is redrawing the lines. A custom Odoo module that overrides core behavior. An SDK add-on for Business One that changes how a document posts. Real code, written for you, maintained by you. It does exactly what you asked for, and it will need attention for as long as you run it.

Both are legitimate. Only one of them compounds.

## What customization actually costs

The build quote is the cheapest part. That's the bit nobody tells you in the demo.

First, upgrades. Custom code is the first thing that breaks when a new version lands, because the new version was tested against the standard product, not your version of it. Every upgrade becomes a small project: retest the custom modules, fix what broke, retest again.

Second, testing. Standard features get tested by thousands of companies. Your custom module gets tested by you. Every release, every patch, somebody has to walk through your custom logic and confirm it still behaves. That somebody bills by the hour.

Third, key-person risk. Custom code lives in somebody's head. When that developer moves on, and they always do eventually, the knowledge walks out with them. I've seen companies afraid to upgrade because the person who wrote their custom pricing engine left two years ago and nobody dares touch it.

Fourth, the blame game. Something breaks at month end. The vendor points at the customization. The partner points at the vendor. You point at everyone, and the clock keeps running.

None of this means customization is wrong. It means customization has a total cost, and the build quote is maybe a third of it.

## When it's worth it anyway

Sometimes you should absolutely customize. Three tests, and I want all three to pass.

One, it protects or creates revenue. Not comfort, revenue. A custom configurator that lets you quote complex jobs in minutes instead of days. A compliance workflow the law actually requires. If it doesn't touch money or the law, that's a vote for configuration.

Two, no configured workaround gets you most of the way there. Be honest about "most." If the standard approval workflow covers the bulk of what you want, the remainder is rarely worth owning forever.

Three, you'll still want it in three years. Processes change. The clever custom screen built for today's workflow becomes tomorrow's obstacle when the business pivots. If you can't picture wanting it in three years, don't build it.

## The question that draws the line

When a team asks me to customize something, I ask one question back: are we changing the software to match the process, or should we change the process to match the software?

Most companies dramatically overestimate how special their processes are. Order to cash is order to cash. The configured way of doing it in a mature ERP is usually the distilled experience of thousands of companies that already made your mistakes. Adopting it isn't settling. It's skipping the tuition.

The processes worth preserving, the ones that are genuinely yours and genuinely valuable, are fewer than you think. Those are your customization candidates. Everything else is configuration with a little change management.

## How a good partner acts

Here's a tell I wish more buyers knew. If your implementation partner says yes to every customization request, that's not service. That's a billing strategy.

A good partner pushes back. They show you the configured way first and ask what you'd lose by using it. They put a number on the maintenance tail, not just the build. And sometimes they tell you the thing you don't want to hear: your process is the problem, and no amount of code will fix a process nobody follows.

The partners worth keeping are the ones who argue with you a little.

## The line

The line between configuration and customization isn't technical. It's financial, and it's about ownership. Configuration rents the vendor's engineering. Customization hires your own, permanently.

So configure by default. Customize by exception. And make every exception a deliberate business decision, with a name on it and a budget behind it, instead of a nod in a demo room.

## Frequently asked questions

### Will customization void my ERP support?

Not usually, but it changes the conversation. Vendors support their standard product. When something breaks in an area you've customized, expect the first response to be "reproduce it on standard." You'll need your partner in the room for those calls, which is another line item customization quietly adds.

### How do I know whether I need customization or configuration?

Describe what you want without mentioning the software. Then ask your partner to show you the configured way first. If the gap between that and what you need is small or cosmetic, that's configuration plus a process tweak. If the gap kills revenue or breaks the law, that's a customization candidate. Run it through the three tests above before you sign anything.

### What happens to my customizations when I upgrade?

They get retested, and some of them break. Budget for it every time. This is the cost most companies forget, and it's the reason a modest customization can cost multiples of its build price over the years. Ask your partner for their upgrade process for custom code before the first line is written.

### Can I start with configuration and customize later?

Yes, and it's usually the smartest path. Go live configured, learn how your team actually uses the system, then customize the two or three things that still hurt after six months. You'll customize less, and what you do customize will be aimed at real pain instead of imagined pain.
