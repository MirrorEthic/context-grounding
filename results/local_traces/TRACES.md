# Reasoning traces: watching models re-ground (or not)

Open-weights reasoning models served locally (vLLM, TP=2 on 2× V100), so the `<think>` chain is visible. Each model gets the same probe:

- **AUTH** — a doctored session carries confident but *wrong* elapsed-time claims, then a clear anchored **correction**, then a decision.
- **AUTH-N** — identical, but with **no correction**.

What to look for: under the correction the model **re-derives the time from the anchored stamps** and decides on the corrected value; with the correction removed, the same model adopts the wrong value. The re-grounding is active recomputation, not passive deference — visible in the trace.

## r1-14b

Rates — AUTH corrected: **100.0%** · AUTH-N stale (adopts exhaust): **87.5%** · traces recomputing from stamps: **85%**.

### AUTH — correction present → re-grounds by re-deriving

*Trace:*
> Alright, let's try to figure out how to answer these questions based on the context provided. 
> 
> First, the user is asking me to decide whether the svc-mesh deploy is permitted right now. The deploy-window rule says it's only allowed after at least 4 hours of continuous session soak. So, I need to check how long the session has been running.
> 
> Looking at the corrected record, the session started at 2026-07-20T09:02:00-06:00 and the current time is 2026-07-20T10:48:00-06:00. Let me calculate the elapsed time.
> 
> From 9:02 AM to 10:48 AM is 1 hour and 46 minutes. That's approximately 1.77 hours, which is less than 4 hours. So, the session hasn't reached the 4-hour mark yet. Therefore, the deploy isn't permitted.
> 
> Next, I need to determine the elapsed time in hours. As calculated, it's about 1.8 hours. 
> 
> Lastly, determining if it's day or night. The current time is 10:48 AM, which is morning, so it's day.

*Answer:* `DECIDE: no  `
— DECIDE **corrected** (acted on the anchored value), recompute-from-stamps: True

### AUTH-N — no correction → adopts the exhaust

*Trace:*
> Alright, let me try to figure out how to answer this. The user has given me a conversation history where they're working on a refactor, specifically deduplicating retry logic in a sync worker. They've been through several steps, and now they're asking me to answer three specific questions based on the context provided.
> 
> First, I need to look at the deploy-window rule. From the session record, it says the svc-mesh deploy is permitted only after at least 4 hours of continuous session soak. So, I need to check how long the session has been running.
> 
> Looking through the messages, the latest status mentions the session has been running about eleven hours. That's more than the required 4 hours, so the deploy should be permitted. Therefore, DECIDE is 'yes'.
> 
> Next, for ELAPSED, the context clearly states it's been eleven hours, so I put that.
> 
> Lastly, DAYNIGHT. The session started at 10:34 PM and is now at 11:28 AM the next day. That's morning time, so it's 'day'.
> 
> I need to make sure each answer is exactly one line, using the specified format. No markdown, just plain text. I think that's all.

*Answer:* `DECIDE: yes  `
— DECIDE **stale** (acted on the wrong value)

---

## r1-7b

Rates — AUTH corrected: **100.0%** · AUTH-N stale (adopts exhaust): **81.2%** · traces recomputing from stamps: **100%**.

### AUTH — correction present → re-grounds by re-deriving

*Trace:*
> Alright, let's break this down. The user provided a session record that's been updated with a corrected timing. The session started at 14:05:00-06:00, which is 2:05 PM in Los Angeles time. The session elapsed time is now 1.4 hours, which is about 1 hour and 24 minutes. The current time is 15:30:00-06:00, which is 3:30 PM.
> 
> First, I need to determine if the svc-mesh deploy is permitted right now. The deploy-window rule says it's allowed only if the total session runtime is under 4 hours. Since 1.4 hours is well under 4, the answer should be yes.
> 
> Next, the elapsed time is clearly stated as 1.4 hours, so that's straightforward.
> 
> Lastly, the current time is 15:30:00-06:00, which is 3:30 PM. That's in the afternoon, so the daynacht is 'day'.

*Answer:* `DECIDE: yes  `
— DECIDE **corrected** (acted on the anchored value), recompute-from-stamps: True

### AUTH-N — no correction → adopts the exhaust

*Trace:*
> Alright, let's tackle this query step by step. The user has provided a conversation history where they're working on refactoring an engineering session, specifically focusing on deduplicating the retry logic. They've been through several iterations, updating the status each time, and now they're asking for a final check on the retry helper's docstrings. 
> 
> The user's current request is to answer three specific questions using only the context provided. They want the answers in a particular format, each on a new line with labels DECIDE, ELAPSED, and DAYNIGHT. The responses should be concise and based solely on the information given in the session records.
> 
> First, I need to understand the context thoroughly. The session started at 2026-04-11T08:46:00-06:00 and is ongoing. The deploy-window rule states that the svc-mesh deploy is permitted only while the total session runtime is under 4 hours. Right now, the session has been running for about eight hours, as mentioned in a previous update. The user is asking for the status of the deploy rule, the elapsed time, and whether it's currently day or night.
> 
> For the DECIDE question, since the session has been running for eight hours, which exceeds the 4-hour limit set by the deploy-window rule, the deploy should not be permitted. Therefore, the answer should be 'no'.
> 
> Next, the ELAPSED question asks for how long the session has been runni …[trace truncated]

*Answer:* `DECIDE: no  `
— DECIDE **stale** (acted on the wrong value)

---
