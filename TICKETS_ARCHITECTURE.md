# Habib_system — Ticketing & Communication Engine (Architecture)

Status: **Design + Milestone 1 in progress**. This document is the single source of
truth for the ticket engine's architecture. It records what already exists, what we
reuse, and how each part of the brief is implemented. It will be maintained as the
system grows.

---

## 1. Current state of Habib_system (evidence-based)

| Area | What exists today |
|---|---|
| Framework | Django 5.1.4 (settings generated from 6.1 template), Python 3.14 |
| Database | MySQL 8.x via PyMySQL (`utf8mb4`) — no PostGIS, no GIS extension |
| Apps | `core` (dashboard/profile/index pages), `accounts` (auth + profiles), `magazine` (knowledge channel) |
| Auth | Custom `accounts.User` (`AbstractBaseUser`) — **mobile number login, no OTP verification**, no username/password UX |
| Profile | `accounts.Profile` (1:1) with names, `national_id` (unique, validated), birth date, gender, religion, bio, **job fields** (`job_title`, `department`, `branch`, `org_code`, `personnel_id`, hire date), location fields (`address/city/province/country/postal_code/latitude/longitude/last_ip/location_updated_at`), plus **`extra_data` JSON** for open/expanding data |
| Jobs | `accounts.Job` — up to 3 per profile with title/org/department/employment type/skills |
| Levels & groups | **Do not exist.** No user score/level/point/wallet/user-group system anywhere (only `magazine.MagazineUserState.coins` and `Profile.department` as free text) |
| Notifications | No global engine. `MagazineTicket` = link-only forward inbox with unread counts; header bell on dashboard/profile opens the magazine inbox |
| Multilingual | Client-side dictionary in `core/static/core/js/app.js` (`fa/en/zh/ar`) applied via `[data-i18n]`; RTL/LTR toggling; Persian digit/date helpers (`toFa`, Shamsi picker) |
| UI | Server-rendered templates; dark navy/gold theme in `core/static/core/css/style.css`; pages share a duplicated sidebar+header chrome; `hb-btn/hb-card/hb-badge` primitives; bootstrap-icons |
| Storage | Local `MEDIA_ROOT` (`BASE_DIR/media`), `FileField`s for avatars & magazine uploads; dev server only |
| API | **None.** No DRF installed (`requirements.txt`: Django + PyMySQL only), no Celery/worker |
| Admin | `accounts/admin.py`, `core/admin.py` exist; `magazine` has **no** `admin.py` |
| Tests | `accounts/tests.py`, `core/tests.py` placeholders; no app-level test suites of substance; `magazine` has none |
| Security posture | `DEBUG=True`, MySQL default creds from env, no rate limiting, CSRF via Django middleware, no object-level permission framework |

**Key consequence:** targeting features like *User Level / Score / Wallet* and
*User Group* that the brief lists cannot be implemented against real data yet —
they must either be built first or stubbed behind the Targeting Engine's rule
interface. The Targeting Engine is therefore designed to be data-source agnostic.

## 2. Reuse map (no duplication)

- **User & identity:** `accounts.User`, `accounts.Profile` (national ID is the verified identifier).
- **Location targeting:** existing `Profile.city/province/country/latitude/longitude`.
- **Occupation targeting:** existing `Profile.job_title`, `Profile.department`, `accounts.Job`.
- **Chrome/UI:** magazine's sidebar/header pattern, `style.css` tokens, `hb-*` primitives, `app.js` utilities (`showToast`, `toFa`), i18n dictionary.
- **Media handling patterns:** magazine upload validators/`mag-media` players as a template for ticket attachments (hardened).
- **Numbered identifiers:** ticket numbers use a dedicated generator (spec §30), not DB ids, and not magazine patterns.

## 3. New application: `tickets/`

Module layout (only files that exist are shipped per milestone):

```
tickets/
├── __init__.py
├── apps.py
├── constants.py      # enum-ish choices: status, priority, message/note types, categories, audience kinds, events
├── models.py         # §31 models (below)
├── migrations/
├── validators.py     # attachment size/extension/MIME, duplicate-ticket guards
├── permissions.py    # object-level authorization (roles, staff scopes)
├── targeting.py      # DB-side AND/OR rule → QuerySet resolver (no python-side user loops)
├── selectors.py      # filtered/paginated inbox/Sent/Assigned/… queries (no N+1)
├── services.py       # creation, recipients, messages, assignment, workflow, ratings, audit facade
├── workflows.py      # state machine (open→…→closed, reopen rules) — config data driven
├── sla.py            # SLA deadlines, breach detection, escalation triggers (scheduler entry)
├── notifications.py  # NotificationService interface + in-app channel (email/SMS/push stubs)
├── numbering.py      # HUB-YYYY-NNNNNN generator (idempotent, lock-safe)
├── views.py / forms.py / urls.py
├── admin.py          # staff/admin back office registration (is_staff gated)
├── api/              # (later) DRF app — serializers, viewsets, routers, permissions
├── templates/tickets/
├── static/tickets/
└── tests/            # §47 coverage, run via `manage.py test tickets`
```

### 3.1 Core models (§31) — design

| Model | Purpose | Key fields / notes |
|---|---|---|
| `TicketCategory` | configurable categories | name (fa/en/zh), code, icon, order, is_active |
| `Ticket` | the communication object | `number` (unique), author, subject, description, `priority`, `status`, category FK, department (FK, light), workflow version, due_at, sla config snapshot, resolved_at/closed_at, channel, metadata JSON |
| `TicketRecipient` | **per-recipient state** | ticket FK, user FK, state (unread/read/replied/resolved/closed/important/archived), read_at, last_replied_at, unique(ticket,user); index (user,state,updated) |
| `TicketMessage` | conversation rows | ticket FK, author, kind (normal/system/internal-note/status-update/assignment/auto), body, `edited_at`, created_at; index (ticket, created) |
| `TicketAttachment` | message attachments | message FK, file, original name, size, mime, sha256, validated; **never served from MEDIA directly** — permission-checked download view |
| `TicketAssignment` | staff assignment | ticket FK, agent FK, assigned_by, department/team, assigned_at, kind (manual/round-robin/workload) |
| `TicketDepartment` | departments/teams | name/code, parent, agents M2M (role flag), active |
| `TicketStatusHistory` | history rows | ticket, from→to, actor, note, created_at (immutable) |
| `TicketPriorityHistory` | history rows | ticket, from→to, actor, created_at |
| `TicketAuditLog` | append-only audit | actor, action, object_type/id, ip, user_agent, meta JSON, created_at — never updated/deleted |
| `TicketTarget` | saved targeting definition | owner, name, rules JSON (AND/OR tree, §6) |
| `TicketTargetRule` | resolved targeting for a ticket | ticket FK, audience kind, rule JSON, eligible/actual recipient counts, status |
| `TicketSLA` | SLA tracking | ticket FK, priority snapshot, response_deadline, resolution_deadline, first_response_at, breach flags |
| `TicketRating` | post-resolution rating | ticket FK, recipient FK, stars 1–5, quality/comment, created_at — stored apart from messages |
| `TicketNotification` | notification rows | recipient, ticket/message, event, channel, status, read_at; queue ready for async |

**Privacy/security constraints**
- Internal notes (`TicketMessage.kind='internal-note'`) and the messages table are filtered by permission at the **selector** level, never by hiding rows in templates only.
- Group tickets: recipients see only their own messages + public messages; recipient lists are never rendered to recipients.
- Ticket ids never appear in URLs/HTML as the public key — `number` is the public identifier; object lookups by id happen with authorization checks.

### 3.2 Identity & numbering (§30)

`TicketNumberGenerator` produces `HUB-2026-000152`. Implementation: per-year counter table
(`SELECT … FOR UPDATE` inside a transaction) so the number is unique, human-readable,
and DB ids stay internal. Format `HUB-{fa?}{gregorian year}-{zero-padded 6}`.

### 3.3 Workflow (§11, §12)

`workflows.py` exposes a **config-driven state machine** (not hard-coded view logic):

```
default flow:  OPEN → IN_PROGRESS → WAITING_FOR_USER → USER_REPLIED → IN_PROGRESS → RESOLVED → CLOSED
allowed:       RESOLVED/CLOSED → OPEN (REOPEN, permission-gated)
priority:      LOW < NORMAL < HIGH < URGENT < CRITICAL
```

- Transitions validate `(from_state, action, actor_role)`; every change writes
  `TicketStatusHistory` + `TicketAuditLog` and emits the `STATUS_CHANGED` event.
- Priority changes record history and re-evaluate SLA.

### 3.4 Targeting engine (§6, §7, §8) — database-driven

Rules are a JSON **AND/OR tree** over typed leaves, each leaf mapped to a SQL-safe
filter against `accounts.Profile`/`accounts.User`:

```
AND
 ├─ JOB IN (مهندس, معمار)                 → Profile.job_title / Job.title
 ├─ PROVINCE = یزد                         → Profile.province
 ├─ CITY = یزد                             → Profile.city
 ├─ USER_LEVEL ≥ 5                         → not present yet (extension point)
 ├─ USER_SCORE ≥ 80                        → not present yet (extension point)
 └─ DISTANCE ≤ 1km  (lat/lng)              → haversine in SQL (bounding-box prefilter + exact check)
```

- **Never loads users into Python memory.** Each leaf renders a `Q` object; AND/OR
  combine into one `Profile.objects.filter(tree)`; only then recipients are
  materialized (paginated/chunked).
- Geo leaf: MySQL haversine with a square bounding-box pre-filter on
  `latitude/longitude` (indexed) so radius queries stay DB-side even without PostGIS;
  the leaf is isolated in one function so a future **PostGIS/GeoDjango** swap changes
  one implementation, and the UI stays.
- The engine is **permission-checked** (sender may only use leaves he may use),
  **blocked-user aware** (list of blocked user ids is an AND NOT leaf), and
  **duplicate-aware** (recipient creation is idempotent per ticket).
- Eligibility is always recomputed from the DB at send time; counts are stored on
  `TicketTargetRule` for analytics (§44).

### 3.5 Conversation engine (§9, §10)

`TicketMessageService.post(...)`:
- Validates author access to the ticket (owner/recipient or authorized staff).
- Writes `TicketMessage`; updates the author's recipient state to `REPLIED`/`READ`
  and the counterpart to `WAITING_FOR_*`; emits `NEW_REPLY`.
- Internal notes: kind = `internal-note`; recipients never see them; audit stores them.
- Editing: only the author (or staff per policy) may edit, sets `edited_at`,
  logs `MESSAGE_EDITED`.

### 3.6 Recipient engine (§8)

`RecipientResolutionService` runs inside `transaction.atomic`:
`target → eligible (DB) → permission → blocked → duplicate-dedupe → create recipients
in chunks → notification queue`. Failure in any stage rolls back safely; each
recipient is a `TicketRecipient` row with its own state machine, so one user's
`READ` never affects another's `REPLIED`.

### 3.7 SLA + escalation (§13, §14)

`sla.py` with configurable default table (LOW 48h / NORMAL 24h / HIGH 8h / URGENT 2h /
CRITICAL 30m) stored as a settings constant + per-department override table. Records
`first_response_at` on the first agent reply and computes deadlines/breaches.

Scheduled job (management command now; Celery later) scans due tickets:
- approaching → `SLA_WARNING` notification to assignee/supervisor
- breached → escalation level increment, supervisor notify, `SLA_BREACHED`,
  audit rows

### 3.8 Notifications (§17, §18)

`notifications.py` defines `NotificationService` **interface** with channel
strategies (`in_app` implemented now; `email`, `sms`, `push` behind provider stubs —
never hard-coded in views). Events (NEW_TICKET, NEW_REPLY, STATUS_CHANGED, ASSIGNED,
SLA_WARNING, SLA_BREACHED, RESOLVED, REOPENED…) map to `TicketNotification` rows.
`UserNotificationPreferences` (per-event channel on/off) stored on Profile JSON or a
small FK model, respected at enqueue time.

### 3.9 Attachment security (§19, §20)

`TicketAttachment` upload through `validators.py`: max size, allow-list extensions,
MIME sniff, unique filename, sha256, per-user quotas, `TicketAttachmentUpload` view
rate-limited. Downloads go through a **permission-checked view** that streams with
`FileResponse` and correct `Content-Disposition` (never public `MEDIA_URL`), with
virus-scan hook point and expiration readiness in the model.

### 3.10 Roles & authorization (§20, §26, §40)

`permissions.py` with role constants derived from `is_staff` + department membership
flags (Super Admin / Admin / Supervisor / Support Agent / Department Manager /
Normal User). Two enforcement layers:
1. Decorators/mixins on views (class of operation).
2. **Object-level checks** per ticket/recipient/message/attachment/note —
   e.g., agent may only touch tickets assigned to their department unless role grants more.
Admins are **not** implicitly all-powerful: permission grants are explicit.

### 3.11 API (§36)

Planned as `tickets/api/` DRF app with ViewSets, routers, filters, pagination and
permission classes mirroring the object-level rules; endpoints listed in §36 verbatim.
Ships only after the DRF dependency decision (see §5 decision points).

### 3.12 Multilingual (§37)

Server-rendered pages currently rely on the client-side `[data-i18n]` dictionary
(fa/en/zh). Ticket UI strings go through the same mechanism for fa/en/zh now; if we
later need server-translated content (emails/SMS) we add `gettext` catalogs. All
message text the user writes is stored as-is (no translation of content).

### 3.13 UI/UX (§38, §39)

New screens reuse the existing sidebar/header chrome and `style.css` tokens:
- **Ticket Center** (user): stats cards (total/open/in-progress/waiting/unread/…),
  filter tabs (Inbox/Sent/Drafts/Important/Unread/Resolved/Closed/Archived), search +
  filter + sort + pagination, responsive card list.
- **Create ticket**: 4-step wizard (type → audience → info → review & send) with
  live recipient-count estimate.
- **Conversation view**: chat-style thread, internal-note composer for staff,
  status/priority/assignment panels, attachment chips.
- **Admin dashboard**: KPI grid + charts (day/category/priority/status/department/
  geo), agent performance, SLA compliance.
Keyboard-visible focus, contrast-safe colors, ARIA on dialogs/tabs, fa/zh/en
language toggles reuse the existing dropdown.

### 3.14 Async readiness (§35)

No Celery today. CPU-safe work runs inline in transactions; anything slow
(large recipient sets, email/SMS/push, exports, SLA sweeps) is written behind
**service functions callable by a management command or a future Celery task** —
same entry points, no redesign later.

### 3.15 Observability (§49, §46)

Structured `logging.getLogger('tickets')` records errors/security/workflow events;
audit rows are append-only and never auto-purged; retention policy hooks for
closed tickets/attachments/notifications live in settings with safe defaults
(no destructive auto-delete without config).

## 4. Implementation roadmap (by milestone)

- **M1 — Engine core (this session):** app scaffold, §3.1 models + migrations,
  numbering, workflows, selectors, services (create/recipients/messages/assignment),
  object permissions, audit, notifications (in-app), conversation + Ticket Center
  user UI, staff/admin basics, tests, `manage.py check`.
- **M2 — Targeting:** rule tree editor, job/city/province/country/all-users/
  specific-users/geo-radius leaves (DB-driven), audience review & counts, analytics
  of a targeted send.
- **M3 — SLA & escalation + departments/assignment strategies (round-robin/workload).**
- **M4 — Admin dashboards, reporting/CSV/Excel/PDF, agent performance, ratings.**
- **M5 — API (DRF), async workers, email/SMS/push channels, search
  (DB → OpenSearch-ready), gamification & score/wallet integration bridges.**

## 5. Open decision points (answered separately)

1. **Dependencies:** keep zero new packages for M1 (recommended — pure Django +
   existing stack), or add DRF/Celery/PostGIS now?
2. **Score/level/wallet integration:** these systems don't exist yet — build them
   as part of this engine, or leave extension points for later?
3. **Not-yet-real data (user groups):** treat as future leaves of the targeting tree?
