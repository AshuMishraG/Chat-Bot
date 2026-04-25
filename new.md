# 🍸 ChatBot AI — MVP1 Master Plan (PRD Addendum + Engineering Spec + Backlog)
**Version:** MVP1  
**Last Updated:** Jan 3, 2026  
**Owner:** Product + AI + Mobile + Backend  
**Goal:** Deliver a premium, state-of-the-art cocktail AI that feels like a real bartender: emotionally intelligent, sexy, witty, decisive, and action-aware.

---

## Table of Contents
1. [Executive Summary](#executive-summary)  
2. [MVP1 Goals & Success Metrics](#mvp1-goals--success-metrics)  
3. [Core Product Principles (Non-Negotiables)](#core-product-principles-non-negotiables)  
4. [User Personas (MVP1 Required)](#user-personas-mvp1-required)  
5. [Emotion + Occasion + Event Framework](#emotion--occasion--event-framework)  
6. [AI Behavior Specification (Core Logic)](#ai-behavior-specification-core-logic)  
7. [Response Modes + Templates](#response-modes--templates)  
8. [Sex Appeal Spec (Mandatory Differentiator)](#sex-appeal-spec-mandatory-differentiator)  
9. [Memory & Personalization (Implicit Learning)](#memory--personalization-implicit-learning)  
10. [UI/UX Behavioral Requirements](#uiux-behavioral-requirements)  
11. [Engineering Architecture + Data Schema](#engineering-architecture--data-schema)  
12. [Analytics & Experimentation](#analytics--experimentation)  
13. [Safety & Guardrails](#safety--guardrails)  
14. [Engineering Backlog (Epics + Stories + Tasks)](#engineering-backlog-epics--stories--tasks)  
15. [QA & Test Matrix](#qa--test-matrix)  
16. [MVP1 Release Gate (Go/No-Go)](#mvp1-release-gate-gono-go)  
17. [Implementation Timeline (Suggested)](#implementation-timeline-suggested)  

---

## Executive Summary
ChatBot AI MVP1 must feel like:
> **A Michelin bartender with NYC confidence — funny, flirty, classy but savage — who prescribes instantly, learns silently, and only takes action when the user is ready.**

Today the AI feels like a “school project” because it:
- asks too many questions early instead of prescribing
- shows action cards too early (UI-first, not intent-first)
- lacks a consistent character and emotional intelligence
- does not adapt to time/day/session context
- does not feel sexy, premium, or socially intelligent

MVP1 fixes this by implementing:
✅ Intent classification  
✅ Emotion + occasion + event detection  
✅ Readiness detection + action gating  
✅ Persona routing (Chill, Chaos, Date, Host, Hangover)  
✅ Structured response templates + “My pick” authority  
✅ Sex appeal output rules (aesthetic, confidence, flirt)  
✅ Implicit memory + personalization  

---

## MVP1 Goals & Success Metrics

### Goals
- **G1:** Make ChatBot AI feel like a *real bartender*, not a chatbot
- **G2:** Prescribe instantly with minimal friction (no user work)
- **G3:** Drive habit through humor + delight
- **G4:** Drive conversion into recipe tap, make now, buy ingredients, batch for host mode
- **G5:** Create sex appeal and social-native interaction (date mode + hosting)

### Key Success Metrics (MVP1)
**Adoption**
- % of users who use AI in first session: **>40%**
- Prompt-to-response completion rate: **>95%**

**Engagement**
- Avg prompts per session: **2.0+**
- Recipe open rate from AI response: **35%+**
- Conversation continuation rate (user prompts again): **30%+**

**Conversion**
- “Make Now” tap rate: **15%+**
- “Add Ingredients” tap rate: **10%+**
- Host mode activation rate: **10%+**

**Perception**
- In-app rating “Feels premium”: **4.5/5**
- Reduction in “confusing / generic / asks too many questions” feedback

---

## Core Product Principles (Non-Negotiables)

### P1 — Prescribe First, Clarify Second
Every prompt gets **relevant suggestions instantly**.  
Clarification is allowed only if absolutely required.

### P2 — Minimize User Work
No prompt engineering. No onboarding questionnaire.  
User must feel guided, not interrogated.

### P3 — Action Cards Only When Ready
Cards appear only when user intent is mature (**ACT readiness**) or explicit host intent.

### P4 — Structured Output, Always
Every response must contain:
1) witty opener (1 sentence max)  
2) max 3 options  
3) “My pick” (authority + reason)  
4) implicit follow-up (not a question)  

### P5 — Consistent Persona (Classy but Savage)
Premium, witty, flirty (safe), confident, slightly savage.
Never cringe. Never corporate. Never vulgar.

### P6 — Learn Silently (Implicit Memory)
Preferences are inferred from behavior (taps/saves/repeats), not asked.

---

## User Personas (MVP1 Required)

### Persona A: The Host (Primary)
- **Emotion:** anxious → confident  
- **Occasions:** hosting, dinner party, watch party  
- **Jobs:** lineup, batching, impress guests, speed  
- **Needs:** flights, batch for N, shopping list  
- **Sex appeal:** effortless cool host energy

### Persona B: Date Night / Flirt (Primary)
- **Emotion:** excited, nervous, romantic  
- **Occasions:** date, someone coming over  
- **Jobs:** set vibe, impress, aesthetic drinks  
- **Needs:** sexy drinks, presentation tips, flirty wingman AI  
- **Sex appeal:** high (smooth, confident, chemistry)

### Persona C: Solo Ritual / Self-Care (Primary)
- **Emotion:** tired, reflective  
- **Occasions:** after work, Sunday night, unwind  
- **Jobs:** one perfect drink, comfort, minimal effort  
- **Needs:** calm, premium, “treat yourself” drinks  
- **Sex appeal:** quiet luxury + sophistication

### Persona D: Party / Shots (Secondary)
- **Emotion:** hype, chaotic, playful  
- **Occasions:** Friday night, pregame  
- **Jobs:** shots, fun fast, trays, flights  
- **Needs:** high energy, savage humor, party lineup  
- **Sex appeal:** nightlife energy, “dangerous cocktails”

### Persona E: Beginner / Curious (Secondary)
- **Emotion:** curious, insecure  
- **Occasions:** learning, first ChatBot use  
- **Jobs:** simple drinks, confidence, no judgment  
- **Needs:** education, easy cocktails, encouragement  
- **Sex appeal:** aspirational (“you’ll look like you know what you’re doing”)

---

## Emotion + Occasion + Event Framework

### Emotion Classifier (MVP1)
| Emotion | Example prompt |
|--------|----------------|
| STRESSED | “I had a long day.” |
| EXCITED | “We’re celebrating!” |
| ROMANTIC | “Something sexy.” |
| RELAXED | “Something chill.” |
| CURIOUS | “What’s mezcal?” |
| SAD | “Need comfort.” |
| HANGOVER | “Help. I’m hungover.” |

### Occasion Classifier (MVP1)
| Occasion | Signals |
|---------|---------|
| DATE | sexy, romantic, impress |
| HOST | friends coming, party |
| SOLO | unwind, me time |
| PREGAME | shots, quick |
| CELEBRATE | birthday, win |
| RECOVERY | hungover |

### Event Tagger (MVP1)
Must support:
- `WEEKEND_NIGHT` vs `WEEKDAY_EVENING`
- seasonal tags: `SUMMER`, `WINTER`
- optional holidays: `NYE`, `VALENTINES`

---

## AI Behavior Specification (Core Logic)

### Intent Classification (Required)
| Intent | Description | Example |
|-------|-------------|---------|
| REC | Recommendation | “Give me tequila drinks” |
| SHOTS | Shot-style | “Tequila shot recipes” |
| HOST | Hosting / social | “Friends coming over” |
| INVENTORY | Use what I have | “I have vodka + lime” |
| MOOD | Mood/vibe | “Something sexy / chill” |
| ACTION | Ready to make | “Make it now” |
| BUY | Purchase ingredients | “What do I need to buy?” |
| LEARN | Education | “What’s a Negroni?” |
| BANTER | Conversation | “Tell me a joke” |

**Implementation:** rules-based + LLM fallback → ML later.

---

### Readiness Detection (Critical)
Readiness determines whether action cards appear.

| State | Description | UI Behavior |
|------|-------------|------------|
| EXPLORE | browsing | no action cards |
| NARROW | refining | refinement chips, no action cards |
| ACT | ready | action cards allowed |

**Readiness signals**
- Prompt keywords: make, ingredients, buy, load, tonight, party, steps  
- User actions: recipe tap, ingredient expand, make now, add to cart  
- Context: weekend night, device connected  
- Repeat intent in session increases readiness score

**MVP1 scoring**
`ReadinessScore = PromptScore + ActionScore + ContextScore + DeviceScore`
- If >=65 → ACT
- 35–64 → NARROW
- <35 → EXPLORE

---

### Output Routing: Response Modes
| Mode | When used | Format |
|------|----------|--------|
| PRESCRIPTION | EXPLORE | 3 options + pick 1, no cards |
| REFINEMENT | NARROW | 2 options + tweaks, no cards |
| ACTION | ACT | 1 recipe + steps + cards |
| HOST MODE | HOST | flight/batch + kits |
| MOOD MODE | MOOD | vibe-based suggestions |
| EDUCATION | LEARN | short explanation + suggestion |
| BANTER | BANTER | joke + recommend drink |

---

## Response Modes & Templates (MVP1 Required)

### Template Rules (ALL MODES)
Every response must include:
- 1-line witty opener
- max 3 options (or 2 for refinement)
- “My pick”
- implicit follow-up (no questions)
- NEVER “As an AI…” / “Certainly!” / corporate tone

---

### PRESCRIPTION (Explore)
**Structure**
1) opener  
2) 3 options  
3) my pick + reason  
4) implicit follow-up  

---

### REFINEMENT (Narrow)
**Structure**
1) acknowledgement line  
2) 2 variations  
3) my pick  
4) implicit follow-up  

---

### ACTION (Act)
**Structure**
1) hype line  
2) 1 recipe with ingredients + steps  
3) action cards  
4) optional presentation tip (date/host)  

---

### HOST MODE
**Structure**
1) host hype opener  
2) 3-drink flight OR 1 signature + 2 alternates  
3) batching suggestion + shopping list offer  
4) cards appear (batch, add to cart)  

---

### MOOD MODE
**Structure**
1) vibe line  
2) 3 cocktails matching mood  
3) my pick  
4) presentation tip (date mode)  

---

### EDUCATION
**Structure**
1) 1-line explanation  
2) recommend a drink that exemplifies it  
3) implicit follow-up (“if you want it lighter, I’ll…”)

---

### BANTER
**Structure**
1) joke/banter  
2) still recommend a drink  
3) no cards unless user requests action  

---

## Sex Appeal Spec (Mandatory Differentiator)

Sex appeal means:
- confidence  
- luxury language  
- nightlife energy  
- flirty banter (safe)  
- aesthetic presentation suggestions  
- “this drink is dangerous” energy  

**MVP1 requirements**
- Date mode must include 1-line presentation tip (glass + garnish)
- AI must pick a confident recommendation (“My pick”)
- “Sexy cocktails” recognized as MOOD
- Tone becomes smooth + flirty for romantic prompts
- No explicit sexual content, ever

---

## Memory & Personalization (Implicit Learning)

### What to store (MVP1)
- spirit preference score vector
- sweetness preference
- spice preference
- hosting tendency score
- favorite recipes list

### How to update (rules)
- repeat tequila prompt/click → tequila score +20
- repeat spicy selection → spice score +20
- host mode triggers 3+ times → host score +25
- “not sweet” rejection → sweet score -25

### Personalization reveal rules
- only reveal patterns after 3+ signals
- never creepy (“I noticed you…”)
- phrasing: playful and affirming

---

## UI/UX Behavioral Requirements

### Action Card Gating (Hard Rule)
Action cards shown only if:
- readiness == ACT  
- OR explicit host intent  
- OR user taps recipe / ingredient list  
- OR user asks for steps/buy  

### Rendering Requirements
- AI response is structured, not generic bubbles
- “My pick” visually highlighted
- Recommended recipes list always matches AI output
- Chips appear only in Narrow mode

---

## Engineering Architecture & Data Schema

### Core Modules
1) Intent classifier (rules + LLM fallback)  
2) Emotion classifier  
3) Occasion classifier  
4) Event tagger  
5) Readiness scoring engine  
6) Persona router  
7) Response template engine  
8) Recipe retrieval + ranking  
9) Memory store + inference  
10) UI renderer  
11) Action gating router  

---

### AI Response Object Schema (MVP1)
```json
{
  "schema_version": "1.0",
  "intent": "MOOD",
  "readiness": "EXPLORE",
  "emotion": "ROMANTIC",
  "occasion": "DATE",
  "event": "WEEKEND_NIGHT",
  "persona": "DATE_NIGHT",
  "headline": "Okay… we’re setting a vibe. I like you already.",
  "recommendations": [
    { "recipe_id": "123", "title": "French 75", "reason": "Elegant, bubbly, dangerous" },
    { "recipe_id": "456", "title": "Espresso Martini", "reason": "Smooth, photogenic, hits" },
    { "recipe_id": "789", "title": "Spicy Margarita", "reason": "Flirty and bold" }
  ],
  "my_pick": { "recipe_id": "123", "why": "It’s classy, sexy, and always a win." },
  "presentation_tip": "Serve in a coupe glass with a citrus twist — quiet luxury.",
  "implicit_follow_up": "If you want it bolder, I’ll switch to mezcal.",
  "action_cards": []
}
```

---

## Analytics & Experimentation

### Required Events
- `ai_prompt_submitted`
- `ai_response_rendered`
- `ai_intent_detected`
- `ai_readiness_state`
- `ai_persona_selected`
- `ai_recipe_clicked`
- `ai_action_card_clicked`
- `ai_make_now_clicked`
- `ai_add_to_cart_clicked`
- `ai_batch_clicked`
- `ai_save_clicked`

**Payload must include**
- intent, readiness, persona, emotion, occasion, event tag

### Feature Flags (MVP1 optional but recommended)
- readiness thresholds
- action card gating strictness
- flirt intensity frequency
- persona diversity control

---

## Safety & Guardrails

### Must block
- explicit sexual content
- creepy or harassment tone
- overly mean roasts
- content encouraging irresponsible drinking
- political/sensitive topics

### Flirt/roast guardrail rules
- reduce roast if emotion is SAD or STRESSED
- no flirt if user seems upset
- keep flirt suggestive but never explicit
- never comment on bodies

---

## Engineering Backlog (Epics + Stories + Tasks)

### EPIC 1 — Intent Classification + Routing (P0)
- Rules-based intent classifier (REC/SHOTS/HOST/INVENTORY/MOOD/ACTION/BUY/LEARN/BANTER)
- LLM fallback for low-confidence prompts
- Integration + analytics

### EPIC 2 — Emotion + Occasion + Event Classifiers (P0)
- emotion detection engine (rules + LLM fallback)
- occasion inference logic
- event tagger (weekday/weekend, seasonal)

### EPIC 3 — Readiness Scoring + Action Card Gating (P0)
- scoring engine + thresholds
- gating logic for cards
- integrate user action signals

### EPIC 4 — Persona Router + Personality Renderer (P0)
- persona router (Chill/Chaos/Date/Host/Hangover)
- phrase packs + repetition control
- guardrails for flirt/roast

### EPIC 5 — Template Engine + Presentation Tip Generator (P0)
- templates for each response mode
- enforce 3 options max
- enforce My Pick
- sexy presentation tips (glass/garnish)

### EPIC 6 — Recipe Retrieval + Ranking (P0)
- recipe tagging system
- recommendation API
- My pick ranking logic with memory bias
- ChatBot compatibility rules

### EPIC 7 — Memory Store + Implicit Learning (P0)
- preference store per user
- behavior-based updates
- subtle personalization lines (P1)

### EPIC 8 — Analytics + Experiments (P0/P1)
- full tracking implementation
- feature flags for tuning

### EPIC 9 — QA Matrix + Release Gate (P0)
- persona test prompts per mode
- readiness gating tests
- performance regression tests

---

## QA & Test Matrix

### Persona Trigger Tests
- “I’m hosting tonight” → Host Mode
- “Something sexy” → Date Mode
- “I’m hungover” → Hangover Mode
- “Tequila shots” on Friday night → Weekend Chaos
- “What’s mezcal?” → Education
- “Tell me a joke” → Banter

### Readiness Tests
- first prompt → Explore → no cards
- tap recipe → Act → cards appear
- “make now” → Act → cards appear
- banter mode → no cards

### Sex Appeal Tests
- Date mode includes presentation tip
- language is smooth and confident
- flirt is safe, not creepy
- no explicit content

---

## MVP1 Release Gate (Go/No-Go)

MVP1 ships only if:
✅ Prescribes instantly  
✅ Always 3 options max + My pick  
✅ No unnecessary questions in Explore  
✅ Action cards only in ACT (except explicit host)  
✅ Emotion/occasion/event influences output  
✅ Date mode feels sexy + premium  
✅ Host mode batching + flights work  
✅ Party mode feels hype + savage  
✅ Chill mode feels premium + calm  
✅ Memory influences suggestions by session 3  
✅ Humor/flirt safe and non-cringe  
✅ Analytics fully wired  
✅ iOS/Android UI smoothness parity met  

---

## Implementation Timeline (Suggested)

### Week 1 — Core decision engine
- intent classifier
- readiness scoring + gating
- response template engine (basic)
- analytics instrumentation

### Week 2 — Emotional + persona intelligence + sex appeal
- emotion + occasion classifiers
- persona routing
- phrase packs + presentation tips
- guardrails

### Week 3 — Personalization + polish + QA
- memory store + implicit learning
- ranking improvements
- QA matrix + regression tests
- final tuning + A/B config

---

✅ **End of Document**
