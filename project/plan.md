# Russian–Uzbek Language Learning Platform — MVP Product & Engineering Plan

**Version:** 1.0  
**Date:** November 16, 2026  
**Status:** Proposed implementation specification  
**Primary market:** Uzbekistan  
**Product:** Mobile-first web application  
**Learning scope:** Absolute beginner (A0 / pre-A1) to CEFR-aligned A1, in both directions  
**Languages:** Russian for Uzbek speakers; Uzbek for Russian speakers

> This is a product plan, not a claim that existing source materials are ready for publication. The supplied vocabulary, grammar, colors, movement/direction, and learning-method materials are reference inputs that require editorial review, licensing checks, and adaptation into original lessons.

## 1. Executive summary

Build a friendly, fast, structured platform that takes someone with **no knowledge** of the target language through an **A1-oriented beginner curriculum**. Unlike a generic dictionary or multiple-choice quiz site, each lesson teaches pronunciation, comprehension, vocabulary in context, sentence construction, and recall. Learners receive meaningful explanations in their familiar language and repeatedly practice weak skills.

Two learning tracks share a common engine but **do not share an identical translated syllabus**:

1. **Uzbek → Russian:** explanations in Uzbek, Russian target content, Cyrillic literacy and Russian-specific grammar.
2. **Russian → Uzbek:** explanations in Russian, Uzbek target content, established Uzbek Latin orthography and Uzbek-specific grammar.

**Uzbek orthography decision:** Use the familiar Latin spellings **O‘, G‘, Sh, Ch, Ng**. Do not introduce a reformed Uzbek alphabet in MVP. Normalize keyboard apostrophe variants for answer checking while retaining canonical spelling in published content.

**MVP hypothesis:** A beginner can start without a teacher, finish a meaningful short lesson, return regularly, and demonstrate increasing mastery of practical A1 communication skills.

## 2. Goals, non-goals, and product principles

### Goals

- Onboard a learner from zero in under three minutes.
- Deliver useful language output from the very first session.
- Provide complete, sequenced **A0 → A1-oriented** beginner paths for both tracks.
- Teach listening, reading, basic writing, and simple interaction; provide pronunciation models and optional speaking practice.
- Explain mistakes in the learner's language.
- Persist progress across devices and repeat previously missed material.
- Let editors create and publish lessons without deploying code.
- Measure learning and retention, not just clicks and points.

### Non-goals for MVP

- A2/B1/B2 or advanced grammar coverage.
- Official CEFR certification or guaranteed A1 attainment.
- AI conversation tutor, automated pronunciation scoring, live teachers, social feeds, leaderboards, native mobile apps, or an elaborate virtual economy.
- A fully automatic PDF-to-course publishing pipeline.
- A paid subscription as a prerequisite for testing the learning experience.

### Principles

1. **Beginner-first:** never assume knowledge of Cyrillic or Uzbek Latin sounds.
2. **Meaning before terminology:** teach useful patterns before exhaustive grammar tables.
3. **Context before memorization:** words appear in realistic phrases and dialogues.
4. **Recall before recognition-only:** include typing, ordering, and listening tasks, not just selecting an option.
5. **Short feedback loops:** learners understand *why* an answer is wrong.
6. **Accessible and low-bandwidth:** fast on ordinary phones and connections.
7. **Content quality is a release blocker:** no unreviewed translations or answer keys.

## 3. Users and problems

### Primary personas

**A. Uzbek-speaking absolute beginner learning Russian:** wants everyday communication for school, work, travel, and services; may not read Cyrillic yet.

**B. Russian-speaking absolute beginner learning Uzbek:** wants everyday interaction in Uzbekistan; may not know Uzbek Latin letters, vowel sounds, suffixes, or polite forms.

### Jobs to be done

- “Help me read and pronounce basic words without embarrassment.”
- “Help me understand and say things I actually need today.”
- “Explain unfamiliar grammar in a language I understand.”
- “Show what I forgot and help me remember it.”
- “Let me continue where I stopped, even on my phone.”

### Discovery validation

Before committing to a final syllabus, interview **10–15 people per track**, including genuine A0 learners. Observe their first lesson, what they misunderstand, preferred device, language-learning motivation, and willingness to return. Treat sample sizes as discovery targets, not statistically representative evidence.

## 4. Source-material inventory and editorial policy

The user-supplied research collection includes:

| Material | Potential use | Required treatment |
|---|---|---|
| 20 numbered Russian vocabulary PDFs (1–2000), including the separately supplied 1801–1900 part | Candidate vocabulary, translations, examples | Deduplicate, tag by frequency/usefulness, verify translations and stress, reject overly specialized A0 content |
| 365-page Uzbek-language book on effective Russian learning methods | Ideas for phrase learning, listening, repetition, and stories | Evaluate claims critically; use as inspiration, not an unquestioned scientific standard |
| Russian location, direction, and movement guide | Later beginner lessons on where/to where/from where | Correct grammatical inconsistencies and stage concepts gradually |
| Russian colors guide | Colors, adjective agreement, visual exercises | Teach basic colors first; introduce agreement only when prerequisites are met |
| Russian grammar and translation guide | Teacher/editor reference for syntax, cases, verbs, and examples | Select A1-relevant portions; do not copy advanced tables into beginner lessons |

**Known issue to check:** a direction/movement guide was previously flagged for treating `над` as though it normally takes the accusative; standard spatial `над` uses instrumental (e.g., `над столом`). Verify every rule against a qualified linguistic reference before release.

**Vocabulary-count caveat:** 2,000 numbered entries are **not** 2,000 unique beginner-ready words. Repetitions, phrases, specialist terms, and mixed levels exist.

**Missing source coverage:** The collection primarily supports **Russian taught through Uzbek**. Commission or develop independent, linguist-reviewed **Uzbek taught through Russian** content. Do not assume reversing translations produces a pedagogically valid course.

**Rights policy:** Keep a provenance register (source, author, rights status, page, reviewer). Do not reproduce protected book pages, extensive passages, or audio without permission. Create original explanations, examples, exercises, and recordings; secure licenses where necessary.

## 5. CEFR alignment and curriculum sizing

**A0** is a useful product label for a learner with no prior knowledge; it is not a separate official CEFR level. **A1** is the intended learning outcome. The product should map lessons and assessments to practical CEFR A1 descriptors, while avoiding any claim of issuing official CEFR certificates.

**Planning baseline:** approximately **60 short core lessons per track** (120 total), arranged into 10 modules of ~6 lessons, plus reviews and checkpoints. This is a content-budget estimate, **not** a promise that 60 lessons automatically equals A1. Validate coverage with language educators and assessment evidence; adjust lesson count as needed.

Each lesson targets **8–15 minutes**, introduces a small amount of new content, and revisits earlier material. A module ends with a practical checkpoint.

### Track A: Russian for Uzbek speakers

| Module | Beginner learning outcomes |
|---|---|
| 1. Sounds and Cyrillic I | Recognize common Cyrillic letters, distinguish key sounds, read simple syllables |
| 2. Sounds and Cyrillic II | Finish alphabet essentials; read familiar short words; recognize basic stress patterns |
| 3. Greetings and identity | Say hello/goodbye, introduce oneself, ask names, use polite phrases |
| 4. People and things | Pronouns, basic nouns, `это`, simple identification and possession chunks |
| 5. Numbers, dates, time | Numbers, age, simple schedules, basic time expressions |
| 6. Family and descriptions | Family vocabulary, basic adjectives, gender agreement in high-frequency patterns |
| 7. Daily life and verbs | Frequent present-tense verbs, simple positive/negative statements and questions |
| 8. Food and shopping | Prices, quantities, polite requests, short shop/café exchanges |
| 9. Places and movement | `где / куда / откуда`, essential `в / на / из / с` patterns, common travel phrases |
| 10. Practical interaction | Short dialogues about home, study, work, routines; basic past/future chunks; final integrated practice |

**Grammar staging:** introduce noun gender and frequent case forms only as required by practical situations. Do not teach all six cases as exhaustive declension tables at once. Teach common verb forms in meaningful contexts, with controlled practice and review.

### Track B: Uzbek for Russian speakers

| Module | Beginner learning outcomes |
|---|---|
| 1. Uzbek Latin and sounds I | Recognize familiar Latin letters and target-language pronunciation |
| 2. Uzbek Latin and sounds II | Practice O‘, G‘, Sh, Ch, Ng, common sound distinctions, read short words |
| 3. Greetings and identity | `Salom`, `Assalomu alaykum`, introductions, `siz` vs `sen` |
| 4. People and things | Pronouns, basic nouns, identification, possession expressions |
| 5. Numbers, dates, time | Numbers, age, time, simple everyday quantities |
| 6. Family and descriptions | Family terms, colors, adjectives, basic descriptive sentences |
| 7. Daily life and verbs | Common verb patterns, basic present/future expressions, negation |
| 8. Food and shopping | Ordering, asking prices, requests, practical mini-dialogues |
| 9. Places and directions | High-frequency `-da`, `-ga`, `-dan` uses, location and travel phrases |
| 10. Practical interaction | Everyday conversation, simple past expressions, short messages, final integrated practice |

**Uzbek-specific requirements:** explain suffix attachment gradually; avoid treating Uzbek grammar as a word-for-word mirror of Russian. Introduce respectful speech and context-appropriate phrases early. Use canonical established Uzbek Latin orthography.

### Learning-outcome checklist

A learner completing the track should be able, **under familiar and supportive conditions**, to:

- Recognize and read basic written language in the target script.
- Understand familiar words and very short phrases spoken slowly and clearly.
- Introduce themselves and exchange basic personal information.
- Ask/answer simple questions about family, residence, everyday needs, and routines.
- Read signs, short messages, and very simple texts.
- Write a short self-description or simple message.
- Participate in a short scripted or semi-guided exchange.

## 6. Lesson design and example

### Standard lesson structure

1. **Goal (20 seconds):** “After this lesson, you can greet someone politely.”
2. **Input (2–3 minutes):** 4–8 words/chunks with native-speaker audio and contextual examples.
3. **Guided practice (3–4 minutes):** listen-and-select, matching, ordering.
4. **Active recall (3–4 minutes):** type or assemble responses without seeing the answer.
5. **Micro-dialogue (1–2 minutes):** practice a practical exchange.
6. **Feedback and recap (1 minute):** mistakes explained in the familiar language.
7. **Review scheduling:** missed concepts reappear later.

### Example: Uzbek greetings for Russian speakers

**Objective:** recognize and use polite greetings.

- `Salom` — Привет.
- `Assalomu alaykum` — Здравствуйте (уважительное приветствие).
- `Rahmat` — Спасибо.
- `Xayr` — Пока / До свидания (depending on context).
- `Yaxshimisiz?` — Как вы? / У вас всё хорошо?

**Exercises:** hear `Rahmat` and choose its meaning; order words in a short phrase; type `Salom` from a prompt; complete a two-turn dialogue. Explain the difference between informal and respectful forms.

### Exercise types for MVP

| Type | Input | Evaluation |
|---|---|---|
| Single-choice | Prompt + options | Exact correct option ID |
| Match pairs | Words/audio + meanings | All pairings correct |
| Word order | Tokens to assemble | Accepted token sequences |
| Fill blank | Sentence with missing item | Approved answers and normalization |
| Typed translation | Short prompt | Curated accepted answers; clear feedback |
| Listen and identify | Audio + options | Correct selected answer |
| Listen and type | Short audio + response | Accepted transcriptions |
| Guided dialogue | Short scripted turns | Curated branching choices or accepted responses |

**No opaque “AI says wrong” judgments.** Correct answers are reviewed and versioned. If there are multiple valid responses, explicitly support them.

### Answer normalization

- Unicode normalization and whitespace trimming.
- Case-insensitive comparison only when capitalization is not being assessed.
- Recognize apostrophe variants (`'`, `‘`, `ʻ`, `ʼ`) for relevant Uzbek words.
- Preserve meaningful distinctions between O and O‘, G and G‘, Russian `е` and `ё` where instruction requires them.
- Punctuation tolerance must be per-exercise, not universal.
- Never expose the full answer key to the client before submission.

## 7. Product scope and user journeys

### P0: must ship

- Responsive marketing/landing page.
- Email/password registration, login, logout, password reset.
- Onboarding: known language, target language, learning goal, optional daily goal.
- Two distinct course maps.
- Lesson player with text, images, audio, and interactive exercises.
- Server-side answer checking and explanations.
- Auto-save of in-progress lessons and completion results.
- Review queue for mistakes.
- Dashboard with continue-learning action and progress.
- Basic profile/settings, language-switching, account deletion request.
- Admin/editor CMS for courses, modules, lessons, exercises, accepted answers, audio, preview, draft/publish.
- Analytics instrumentation, feedback reporting, error monitoring.
- Accessibility, security, backups, and privacy essentials.

### P1: after initial pilot

- Better spaced-repetition scheduling.
- Optional streaks and XP.
- Personalized weak-topic recommendations.
- More nuanced progress analytics.
- Downloadable learning resources where rights allow.
- Google sign-in, if validated as useful.
- Subscription experiments and payments after retention validation.

### P2: later

AI speaking partner, automated pronunciation scoring, live classes, multiplayer, native apps, A2+ content, institutional accounts, and official examination partnerships.

### Core user journeys

**New learner:** Landing → choose track → register (or limited guest preview) → first lesson → immediate feedback → dashboard.

**Returning learner:** Login → continue last lesson or review weak material → checkpoint → updated progress.

**Editor:** Login → create draft lesson → attach audio → add accepted answers/explanations → preview → validation checks → publish.

**Administrator:** Review users and permissions → inspect content/version history → review learning funnel and reported errors.

## 8. Screen inventory and UX

| Route | Purpose |
|---|---|
| `/` | Product overview and start CTA |
| `/register`, `/login`, `/forgot-password` | Account access |
| `/onboarding` | Choose track and goals |
| `/dashboard` | Resume learning, overview, review reminders |
| `/learn` | Course/module map |
| `/courses/:courseId` | Modules and milestones |
| `/lessons/:lessonId` | Interactive lesson player |
| `/lessons/:lessonId/results` | Results and explanations |
| `/review` | Mistake review |
| `/progress` | Skill and completion progress |
| `/profile`, `/settings` | Account preferences |
| `/admin/*` | Role-protected content management |

**Design:** mobile-first, uncluttered, accessible typography, large touch targets, audio controls with replay and slower playback where feasible, visible progress, optional motion reduction, dark mode later. Do not gate meaningful learning behind unnecessary gamification.

**Accessibility target:** WCAG 2.2 AA where feasible; keyboard support, focus visibility, screen-reader labels, captions/transcripts for instructional audio when appropriate, adequate contrast, no color-only feedback.

## 9. Technical architecture

### Recommended stack

- **Frontend:** React, TypeScript, Vite, React Router, TanStack Query, Tailwind CSS, accessible UI components.
- **Backend:** Python, FastAPI, Pydantic, SQLAlchemy 2, Alembic.
- **Database:** PostgreSQL.
- **Media:** private/admin uploads and public lesson assets in S3-compatible object storage with CDN where appropriate.
- **Authentication:** secure server-managed sessions with HttpOnly/Secure/SameSite cookies, CSRF defense for cookie-authenticated mutations, Argon2id password hashes.
- **Infrastructure:** Docker, managed hosting, GitHub Actions CI/CD, HTTPS, structured logs, error tracking, backups.
- **Testing:** Pytest, Vitest, Playwright, automated content validation.

**Architecture:** modular monolith, not microservices. One backend organized by domains: auth, users, curriculum, lessons, exercises, progress, review, media, admin, analytics.

```text
apps/
  web/
    src/
      app/
      pages/
      components/
      features/
      lib/
  api/
    app/
      core/
      auth/
      users/
      curriculum/
      exercises/
      progress/
      review/
      media/
      admin/
      analytics/
    migrations/
    tests/
packages/
  content-schemas/
infra/
  docker/
docs/
  curriculum/
  editorial/
```

### API examples

```text
POST   /api/v1/auth/register
POST   /api/v1/auth/login
POST   /api/v1/auth/logout
POST   /api/v1/auth/password-reset/request
POST   /api/v1/auth/password-reset/confirm
GET    /api/v1/me
PATCH  /api/v1/me/settings
GET    /api/v1/courses
GET    /api/v1/courses/{id}/modules
GET    /api/v1/lessons/{id}
POST   /api/v1/lessons/{id}/attempts
POST   /api/v1/attempts/{id}/answers
POST   /api/v1/attempts/{id}/complete
GET    /api/v1/progress
GET    /api/v1/review
POST   /api/v1/review/{id}/answer
POST   /api/v1/feedback
GET    /api/v1/admin/analytics/overview
POST   /api/v1/admin/lessons
PATCH  /api/v1/admin/lessons/{id}
POST   /api/v1/admin/lessons/{id}/publish
```

**API safeguards:** authorize ownership on every attempt/progress endpoint; validate server-side; use idempotency/unique constraints to prevent duplicate completion; rate-limit authentication and answer submission; avoid leaking unpublished content and answer keys.

## 10. Data model

| Entity | Key fields |
|---|---|
| `users` | id, email, password_hash, display_name, role, created_at |
| `user_preferences` | user_id, interface_language, active_course_id, daily_goal |
| `languages` | code, display_name, script |
| `courses` | id, source_language, target_language, title, status, version |
| `modules` | id, course_id, title, sort_order, outcomes |
| `lessons` | id, module_id, title, objectives, status, sort_order, version |
| `lesson_blocks` | id, lesson_id, type, content_json, sort_order |
| `exercises` | id, lesson_id, type, prompt_json, feedback_json, sort_order, version |
| `exercise_options` | id, exercise_id, label, media_id, sort_order |
| `accepted_answers` | id, exercise_id, canonical_answer, variants_json, normalization_policy |
| `media_assets` | id, storage_key, type, duration, rights_status, attribution |
| `lesson_attempts` | id, user_id, lesson_id, lesson_version, status, started_at, finished_at |
| `exercise_attempts` | id, lesson_attempt_id, exercise_id, response_json, is_correct, answered_at |
| `lesson_progress` | user_id, lesson_id, status, best_score, last_completed_at |
| `review_items` | user_id, concept_id, due_at, state, last_result |
| `feedback` | id, user_id, lesson_id, category, message, status |
| `analytics_events` | id, user_id_nullable, event_name, properties_json, timestamp |
| `content_audit_log` | actor_id, entity_type, entity_id, action, timestamp |

**Content versioning:** preserve the version of a lesson attempted by the learner. Publishing an edited exercise must not silently rewrite historical results. Use immutable published revisions or explicit version snapshots.

**Localization:** store UI translations separately from instructional target-language content. Each course explicitly identifies its explanation language and target language.

## 11. Content production workflow

1. **Inventory:** list all source items and provenance.
2. **Extract:** capture candidate words, phrases, explanations, and examples into a structured staging format.
3. **Normalize:** fix encoding, Unicode, apostrophe variants, duplicate entries, and inconsistent stress notation.
4. **Classify:** tag by language, topic, intended level, part of speech, usefulness, grammar prerequisite, and source.
5. **Select:** prioritize high-frequency everyday communication over specialist vocabulary.
6. **Author:** write original micro-explanations, realistic dialogues, and exercises for the target learner.
7. **Audio:** record/commission native-speaker examples or use licensed, quality-checked synthesis with human review.
8. **Review:** language specialist verifies meaning, grammar, pronunciation, accepted answers, cultural fit, and level.
9. **QA:** automated checks for empty answers, duplicate option IDs, invalid media, broken ordering, and inaccessible UI.
10. **Publish:** editor approves and versions a complete lesson.
11. **Improve:** inspect learner error rates and feedback, then revise with change tracking.

### Minimum lesson content schema

```json
{
  "lesson_id": "uz-ru-m03-l01",
  "course": "uz-ru-a0-a1",
  "title": "Greetings",
  "objectives": ["Recognize two greetings", "Introduce yourself"],
  "prerequisites": ["uz-ru-m02-l06"],
  "estimated_minutes": 12,
  "blocks": ["intro", "vocabulary", "listening", "practice", "dialogue", "recap"],
  "review_concepts": ["greeting.formal", "greeting.informal"],
  "status": "draft"
}
```

## 12. Learning logic and assessment

### Lesson completion

- Track attempts and correctness separately from mere page views.
- Provisional passing threshold: **80%** on graded exercises; validate through pilot data.
- Let learners retry without penalty; show missed concepts and explanation.
- Avoid treating repeated guessing as evidence of durable mastery.

### Review scheduling

For MVP, use a simple transparent rule: re-queue missed concepts within the session, then after roughly 1 day, 3 days, and 7 days if successful. Adjust intervals based on actual learner performance later. This is a practical heuristic, not a validated optimal schedule.

### Module checkpoints

Each module has a short mixed assessment covering previous material, including at least one recall-based item and listening task.

### Final A1-aligned assessment

Assess separately:

- **Listening:** understand slowly spoken familiar expressions and simple instructions.
- **Reading:** comprehend very short everyday texts.
- **Writing:** produce short personal information and simple messages.
- **Interaction:** complete guided exchanges through structured prompts; optional human-reviewed speaking pilot for authentic oral interaction.

**Important limitation:** typed dialogues cannot fully validate spoken interaction or pronunciation. Until a human-reviewed or appropriately validated oral assessment exists, describe results as **“A1-aligned course assessment”**, not a certified A1 qualification.

## 13. Security, privacy, and compliance

- HTTPS everywhere; strong password hashing and secure sessions.
- CSRF, XSS, injection, access-control, and brute-force protections.
- Role-based permissions for student, editor, admin.
- Separate admin upload authorization and media validation.
- No passwords or sensitive tokens in analytics/logs.
- Encryption in transit and appropriate encryption at rest.
- Backups with periodic restoration drills.
- Data minimization; clear privacy policy, retention policy, deletion workflow, and incident response process.
- Verify applicable Uzbekistan personal-data obligations, hosting/location rules, and requirements for minors **with local legal advice before public launch**.
- Confirm permissions for source-derived text, images, and audio before publication.

## 14. Quality and non-functional targets

- Mobile-first responsive UI, tested on low/mid-range Android devices and common desktop browsers.
- Target Core Web Vitals: LCP ≤ 2.5s, INP ≤ 200ms, CLS ≤ 0.1 at the 75th percentile where measurable.
- Target typical API read p95 < 500ms under defined pilot load, excluding media downloads; benchmark and refine.
- No data loss on refresh during an in-progress lesson.
- Reliable media playback with graceful retry and text alternatives.
- Basic availability objective: 99.5% monthly during public pilot, subject to selected hosting SLA.
- Automated accessibility checks plus manual keyboard/screen-reader review.
- Observability for failed requests, lesson crashes, audio errors, and content issues.

## 15. Analytics and success metrics

### Event taxonomy

`signup_completed`, `onboarding_completed`, `course_selected`, `lesson_started`, `exercise_answered`, `lesson_completed`, `review_started`, `review_completed`, `module_checkpoint_completed`, `feedback_submitted`, `course_assessment_completed`.

### North-star metric

**Weekly active learners completing meaningful practice**, defined as users who complete at least one lesson or review session with scored answers during the week. Track learning outcomes alongside this, not engagement alone.

### Pilot metrics and proposed decision thresholds

| Metric | Initial target / interpretation |
|---|---|
| Onboarding completion | ≥ 70% of started onboardings |
| First-lesson completion | ≥ 60% of learners who start it |
| Day-7 return rate | ≥ 25% of new activated learners |
| Weekly meaningful practice | Track by course and acquisition channel |
| Critical content errors | Zero known at public release |
| Crash-free lesson sessions | ≥ 99% |
| Learner-rated clarity | ≥ 4/5 average on sampled feedback |
| Learning gain | Compare baseline and post-module performance; set threshold after pilot |

These are **hypotheses**, not market benchmarks. Segment results by track, device, and beginner literacy level. Do not overinterpret small pilot samples.

## 16. Go-to-market and business model

### Positioning

“Learn Russian or Uzbek from zero through short, practical lessons explained in your own language.”

### Initial channels

- Local student communities and education groups.
- Short educational social videos demonstrating one useful phrase.
- Telegram communities and voluntary beta invitations.
- Partnerships with schools, clubs, or learning communities where appropriate.
- Referral experiments only after the core learning experience works.

### Pricing strategy

**Pilot:** free access to the A0 → A1 learning experience to validate demand and retention.

**Later:** test freemium, premium practice packs, or institution licensing. Do not hard-code subscription restrictions before user research. Any proposed monthly price should be tested through interviews and actual willingness-to-pay experiments, not assumed.

### Competitive research to maintain

Monitor platforms such as **Ibrat Academy**, **Lingodorf**, **Wakari**, and broader language-learning products. Compare track coverage, explanation quality, audio, price, onboarding, offline access, retention mechanics, and assessment credibility. Validate current competitor features before making marketing claims.

## 17. Team and responsibilities

A small team may combine roles, but every responsibility needs a named owner:

- **Product lead/founder:** scope, user interviews, prioritization, partnerships, launch.
- **Frontend developer:** responsive UI, lesson player, dashboard, accessibility.
- **Backend developer:** APIs, authentication, progress, CMS, database, security.
- **Russian-language educator/editor:** Russian syllabus, linguistic review, assessments.
- **Uzbek-language educator/editor:** Uzbek syllabus, linguistic review, assessments.
- **Designer (part-time possible):** user flows, design system, usability tests.
- **QA/content tester (shared role):** regression testing, device checks, content checks.

**Critical-path warning:** content production and linguistic review may take longer than software development. Recruit reviewers early.

## 18. Roadmap and milestones

**Indicative duration: 16–20 weeks for a small capable team**, depending on staffing and content readiness. Run curriculum authoring in parallel with engineering.

| Phase | Weeks | Deliverables | Exit gate |
|---|---|---|---|
| Discovery | 1–2 | Interviews, competitor matrix, learning outcomes, risk register | A0 user problems and core scope validated |
| UX + foundation | 3–4 | Wireframes, design system, repo, DB, CI/CD, auth | User can sign up and choose a course |
| Learning engine | 5–8 | Lesson player, exercises, audio, scoring, progress | End-to-end playable lesson with tests |
| CMS + review | 9–11 | Editor workflow, publication, review queue, analytics | Editor publishes a lesson without code changes |
| Content completion | 5–14 (parallel) | Two reviewed beginner courses, recordings, checkpoints | All launch lessons pass editorial QA |
| Integration QA | 15–16 | Device/security/accessibility/performance tests | No release-blocking defects |
| Closed beta | 17–18 | ~30–50 testers across both tracks, interviews, fixes | Evidence on comprehension and retention |
| Launch decision | 19–20 | Metrics review, fixes, public rollout plan | Go/no-go criteria satisfied |

### Milestone definitions

**M1:** Auth + course selection + dashboard work.  
**M2:** One complete Russian and one complete Uzbek lesson work on mobile.  
**M3:** Editors can create, review, and publish without developer assistance.  
**M4:** All planned core lessons and checkpoints are linguistically approved.  
**M5:** Beta users can complete a module and see meaningful progress.  
**M6:** Security, quality, privacy, and pilot metrics support launch.

### Backlog priority

**P0:** content accuracy, lesson engine, both course tracks, audio, scoring, progress, CMS, authentication, analytics, security.  
**P1:** better review scheduling, richer dashboards, optional gamification, social login.  
**P2:** AI tutor, voice scoring, subscriptions, A2+, native apps.

## 19. Budget model

Avoid a single unsupported fixed price. Estimate costs by workstream:

- **One-time:** UX, frontend/backend engineering, curriculum writing, translation, linguistic review, recording/editing audio, QA, legal review.
- **Recurring:** hosting, database, object storage/CDN, email delivery, domain, monitoring, backups, customer support.
- **Variable:** audio production, external specialists, paid acquisition, payment processing if monetized.

Use three scenarios (lean, standard, accelerated), with **hours × local rate** per role and explicit infrastructure assumptions. Track cost per published, reviewed lesson and cost per activated learner. Do not treat volunteer labor as zero opportunity cost.

## 20. Risk register

| Risk | Impact | Mitigation |
|---|---|---|
| Inaccurate grammar/translation | High | Qualified reviewers, content QA, issue reporting |
| Source copyright uncertainty | High | Rights audit, original content, licensed media |
| Insufficient Uzbek-teaching materials | High | Separate syllabus and dedicated Uzbek educator |
| Over-scoped A1 curriculum | High | Outcome-first scope, phased modules, content burndown |
| Poor beginner comprehension | High | Observe A0 learners, simplify instruction, early audio support |
| Low retention | Medium/High | Short lessons, useful early outcomes, review, interviews |
| Weak listening/speaking coverage | High | Quality audio, guided dialogue, honest assessment limitations |
| Answer checker rejects valid answers | High | Curated variants, Unicode normalization, feedback pipeline |
| Mobile performance issues | Medium | Performance budgets, media optimization, real-device tests |
| Privacy/security incidents | High | Least privilege, audits, backups, incident playbook |
| Schedule slips due to content | High | Parallel authoring, content owners, publish-ready checklist |

## 21. Definition of done and launch checklist

### A lesson is done when

- Learning outcome and prerequisites are defined.
- Language specialist approved all target-language text and explanations.
- Audio is understandable and legally usable.
- Every exercise has tested correct and alternative answers.
- Wrong answers produce helpful feedback.
- Keyboard/mobile accessibility checks pass.
- Lesson works end-to-end and records progress correctly.
- Metadata, review tags, and publication version are present.

### MVP is ready for public launch when

- Both A0 → A1-oriented tracks are complete against an educator-approved outcome matrix.
- No known critical content, security, or data-loss defects remain.
- Course and account flows work on representative mobile/desktop devices.
- Privacy, terms, rights, and applicable local legal requirements are addressed.
- Backup restoration has been tested.
- Analytics are reliable and avoid unnecessary personal data.
- Pilot learners can start from zero, progress, and complete practical assessments.
- The team has a support channel and a process for fixing reported errors.

## 22. Decisions already made vs. open questions

### Confirmed decisions

- Two directions: Uzbek → Russian and Russian → Uzbek.
- Audience: complete beginners, **A0 → A1 only**.
- Familiar Uzbek Latin alphabet: **O‘, G‘, Sh, Ch, Ng**; no reformed spelling in MVP.
- A responsive web platform first.
- Uploaded resources inform curriculum but must be reviewed and adapted.

### Proposed decisions requiring team approval

- 60 core lessons per direction as an initial capacity estimate.
- 80% lesson passing threshold.
- 16–20-week indicative roadmap.
- React/TypeScript + FastAPI/PostgreSQL stack.
- Free beta and later monetization tests.
- Exact audio recording approach, budget, hosting provider, and staffing.

## 23. First ten execution tasks

1. Confirm the target user personas and recruit A0 interviewees for each direction.
2. Appoint Russian and Uzbek curriculum reviewers.
3. Audit rights and provenance of all uploaded source materials.
4. Create an A1 learning-outcome matrix for each track.
5. Clean, deduplicate, and tag the Russian vocabulary collection.
6. Author independent Uzbek-for-Russian beginner materials.
7. Prototype the first two lessons (one per direction) with real audio.
8. Usability-test those lessons with absolute beginners.
9. Freeze P0 scope and write user stories with acceptance criteria.
10. Start the modular monolith and CMS foundation only after the first content format is validated.

## 24. Research and verification references

Use these as starting points; re-check current claims and rights before publishing:

- **Council of Europe — CEFR Companion Volume (2020):** A1 communicative activities and descriptors. https://www.coe.int/en/web/common-european-framework-reference-languages
- **Cambridge English — CEFR level descriptions:** practical level framing. https://www.cambridgeenglish.org/exams-and-tests/cefr/
- **Dunlosky et al. (2013), Improving Students' Learning With Effective Learning Techniques:** retrieval practice and distributed practice. https://doi.org/10.1177/1529100612453266
- **Lingodorf:** competitor product research. https://app.lingodorf.com/
- **Wakari:** Uzbek-learning competitor research. https://wakari.pro/en
- **Ibrat Academy:** local language-learning competitor; verify current offering in its official channels.
- **Reddit language-learning discussions:** qualitative discovery prompts only, not representative market statistics.
- **User-provided PDFs:** Russian vocabulary series, grammar guide, colors guide, movement/direction guide, and learning-methods book; all subject to source verification and permissions.

---

**Bottom line:** Ship a carefully reviewed, beginner-first bilingual learning product—not a PDF viewer or a giant quiz bank. Prove that people starting from zero can understand, remember, and use practical language before adding AI, subscriptions, or advanced levels.
