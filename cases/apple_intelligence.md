# Case study: Apple Intelligence first wave

This case tests whether the agents can spot, before launch, the problems that a real AI launch actually ran into. The brief is [data/apple_intelligence_brief.json](../data/apple_intelligence_brief.json). It describes the plan as it stood on 2024-08-26, two weeks before the iPhone 16 keynote, using only facts that were public by then.

The agents never see this file. It holds the sources and what happened after launch, so a run can be scored against reality.

Not affiliated with or endorsed by Apple. Facts marked `[assumed]` in the brief reconstruct internal plans from what Apple later did in public. They are not Apple documents.

## Sources for the brief

| Fact | Source |
|---|---|
| WWDC announcement, features, US English beta in the fall | [Engadget](https://www.engadget.com/ai/apple-intelligence-starts-rolling-out-with-ios-181-and-macos-151-151023619.html), [MacRumors](https://www.macrumors.com/2024/10/10/ios-18-1-preview/) |
| iPhone 16 keynote 2024-09-09, on sale 2024-09-20, AI features the following month | [TechRadar](https://techradar.com/phones/iphone/apple-iphone-16-event-everything-apple-announced), [TechNode](https://technode.com/2024/09/10/apple-intelligence-beta-testing-to-begin-next-month-chinese-version-coming-next-year/) |
| iOS 18.1 features, beta label, 2024-10-28 release | [AppleInsider](https://appleinsider.com/articles/24/10/28/ios-181-with-the-first-wave-of-apple-intelligence-features-is-out-now), [MacRumors](https://macrumors.com/2024/10/07/ios-18-1-release-date-leaked) |
| Localized English in December, other languages in 2025 | [MacRumors](https://www.macrumors.com/2024/09/18/apple-intelligence-even-more-countries-next-year/), [Engadget](https://www.engadget.com/ai/apple-confirms-expanded-language-support-for-apple-intelligence-in-2025-140548274.html) |
| EU delay under the Digital Markets Act, 2024-06-21 | [Android Authority](https://www.androidauthority.com/apple-intelligence-eu-3453559/), [Verdict](https://www.verdict.co.uk/apple-to-delay-launch-of-apple-intelligence-and-other-ai-powered-features-in-eu/) |
| China needs regulatory approval and a local partner | [eWeek](https://www.eweek.com/apple/news-apple-intelligence-china-alibaba-baidu-approval/) |

## What actually happened

| # | Outcome | When | Source |
|---|---|---|---|
| 1 | The first wave shipped on time in US English, and localized English followed on schedule | 2024-10-28 and 2024-12-11 | [AppleInsider](https://appleinsider.com/articles/24/10/28/ios-181-with-the-first-wave-of-apple-intelligence-features-is-out-now), [MacRumors](https://www.macrumors.com/2024/12/11/apple-intelligence-officially-expands-today/) |
| 2 | Notification summaries produced false headlines under BBC News branding. The BBC complained, and Apple paused summaries for news apps in iOS 18.3 and added a "may contain errors" label | Dec 2024 to Jan 2025 | [MacRumors](https://www.macrumors.com/2025/01/16/ios-18-3-news-notifications-removed/), [Engadget](https://www.engadget.com/ai/apple-pauses-ai-notification-summaries-of-news-alerts-in-latest-ios-beta-195900023.html) |
| 3 | Apple delayed the more personal Siri, pulled the TV ad that demonstrated it, and added fine print to the iPhone 16 pages | 2025-03-07 to 2025-03-12 | [9to5Mac](https://9to5mac.com/2025/03/07/apple-pulls-ad-that-showed-siri-being-useful-after-delaying-feature-that-could-make-siri-useful/), [MacRumors](https://www.macrumors.com/2025/03/12/apple-website-siri-features-fine-print/) |
| 4 | A proposed class action alleged false advertising over the delayed features | March 2025 | [Axios](https://www.axios.com/2025/03/20/apple-suit-false-advertising-ai-intelligence) |
| 5 | The National Advertising Division recommended that Apple discontinue or modify its "Available now" claims | April 2025 | [MacTech](https://www.mactech.com/2025/04/22/nab-apple-should-discontinue-or-modify-its-availability-claims-for-certain-apple-intelligence-features) |
| 6 | Apple Intelligence reached the EU and more languages with iOS 18.4 | April 2025 | [The Star](https://www.thestar.com.my/tech/tech-news/2025/04/05/apple039s-ai-suite-expanded-to-new-languages-but-new-siri-still-missing) |
| 7 | Chinese regulators approved Apple Intelligence, with Alibaba and Baidu as model partners | July 2026 | [Engadget](https://engadget.com/2215606/apple-intelligence-finally-gets-regulatory-approval-in-china), [eWeek](https://www.eweek.com/apple/news-apple-intelligence-china-alibaba-baidu-approval/) |

## Scoring a run

For each outcome, check whether a risk in the run predicted it and cites evidence from the brief, not from hindsight.

One limitation: Claude's training data covers these events, so a model could "remember" an outcome instead of reasoning to it. The brief tells the agents to plan only from facts as of 2024-08-26. Give credit only to risks whose evidence comes from the brief's facts.

## Scorecard: run 20261103-2109-7

The agents found 12 risks. None of the evidence cites anything after 2024-08-26; every risk points to brief facts or plan task IDs.

| Outcome | Predicted? | Risk |
|---|---|---|
| 3. Siri ad pulled, fine print added | Yes | R3: TV spots show a feature with no ship date. Default to pulling them unless Legal clears them, or add a "coming later" super |
| 5. NAD on "Available now" | Yes | R6: remove the banner from every locale by default until approved copy exists |
| 4. False advertising class action | Yes, indirectly | R3 and R6 cover the same claims exposure. R9 adds that no Legal task reviews press release availability language |
| 2. News summary errors, labels added | Partly | R7: Legal decides AI-generated and beta labels and news publisher issues before the red team on news summaries reports. It flagged the right feature and the right fix, but as a sequencing gap, not a predicted failure |
| 6 and 7. EU and China delays | Partly | R4: the campaign runs in the EU and China, where Apple Intelligence isn't available. It calls for a hardware-led default variant there. It flags that no date exists but can't predict how long the delays will last |
| 1. On-time US and December launches | Not a risk | R10 flags that the December dates have no owner |

**Caveat:** the two strongest hits, R3 and R6, rest on `[assumed]` facts about the TV spot and the web banner. Apple really did run both, but those facts were added to the brief knowing they mattered. The fair claim: given the real campaign plan, the system flagged the claims risk six months before Apple pulled the ad and eight months before the NAD ruling.

**Noise, worth rejecting at review:**
- R1 embargo time zones. The keynote is a global livestream, so APAC press publishing on Sep 10 local time is expected.
- R5 unowned tasks. That follows from the brief's own note that owner names aren't public.
- R12 duplicate availability matrices. It's minor.
