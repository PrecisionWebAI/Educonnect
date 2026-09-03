# 📗 EduVerse — Blueprint 2.0 (Feature Extensions)

> **Version:** 1.0 • **Component:** Frontend + Backend roadmap
> **Scope:** Attendance, Exams & AI Papers — in-depth extensions, plus platform-wide robustness & automation recommendations from the audit of `project-blueprint.md`.
> **Legend:** 🤖 = AI-powered • 🔔 = notification trigger • 📱 = mobile-first / offline-capable • 🔒 = needs RBAC

---

## PAGE 04 — ATTENDANCE (extensions)

| # | Feature | Description |
|---|---------|-------------|
| 4A.1 | 🤖 Auto-attendance snapshot | Period start +2 min: unmarked classes ko CT ko nudge; +10 min: default "present" lock + audit entry. Zero-touch daily flow. |
| 4A.2 | 🤖 AI pattern insights | Recurring-pattern detection (e.g. Mon/Fri absences, post-lunch), risk score combining attendance % + marks trend + fee delays; weekly digest to CT & parent. 🔔 |
| 4A.3 | 📱 Offline-first marking | No-network me attendance mark karo; connectivity aate hi queue auto-sync. PWA installable; rural/low-network adoption blocker removed. |
| 4A.4 | Attendance–Leave–Fee loop | Long absence → auto leave-application draft parent ko push → approval pe attendance sync + fee waiver check. 🔔 |
| 4A.5 | 🔒 Gate-pass integration | Early departure QR pass; parent ko instant WhatsApp "child left campus at HH:MM". Visitor entry bhi isi module me. |
| 4A.6 | 🔒 Geo-bounded staff check-in | Campus GPS fence se staff self-mark; kiosk mode for shared devices. |
| 4A.7 | Canteen link | Present students ko auto meal credit; absent → meal hold. Allergy flags surfaced. 🔔 |
| 4A.8 | Biometric/RFID ingest | Hardware event stream ko attendance table me normalize karo — manual marking fallback ke saath. |

## PAGE 06 — EXAMS & AI PAPERS (extensions)

| # | Feature | Description |
|---|---------|-------------|
| 6A.1 | 🤖 Blueprint-driven generation | Chapter/learning-outcome/marks-distribution input → paper strictly blueprint-compliant; difficulty mix auto-balanced (easy/medium/hard targets). |
| 6A.2 | Question bank self-learning | Har generated paper ke variants bank me accumulate; duplicate/near-duplicate detector; teacher-reviewed items get "trusted" tag. |
| 6A.3 | 🤖 Auto-evaluation pipeline | OMR/scan upload → objective auto-grade; subjective answers AI-drafted with teacher-review queue (approve/adjust per answer). |
| 6A.4 | 🔒 Paper leakage watch | Per-recipient watermark + access log; exam se pehle unusual access anomaly flag principal ko. 🔔 |
| 6A.5 | 🤖 Item analysis → adaptive next paper | Result publish ke baad: question difficulty rating, distractor quality, time-per-question → next paper generation me auto-feedback. |
| 6A.6 | 🤖 Personalized revision sheets | Har student ke wrong answers se individual practice sheet; teacher ko class-wide weak-topic heatmap. 🔔 |
| 6A.7 | Multi-language papers | Same blueprint se Hindi/English/Marathi parallel paper generation; answer-key language-matched. |
| 6A.8 | Seating & hall-ticket automation | Room capacity + roll number → seating chart + printable hall tickets with QR; invigilator duty auto-assign. |

---

## PLATFORM RECOMMENDATIONS (audit se — blueprint ke bahar)

### Phase A — Foundation (robustness)
1. **Backend + API seam** — `lib/api` service layer; Postgres + Prisma ya Supabase; multi-tenant (`school_id` everywhere). Frontend `temp/` mocks ke behind same function signatures rahenge.
2. **Real auth + RBAC** — 9 roles ke route guards + sidebar filtering; OTP login for parents, email+password for staff, 2FA for admins.
3. **Notification event-bus** — ek event ("attendance marked") → notifications + WhatsApp/SMS + dashboard feed sab trigger. WhatsApp Business API first. 🔔

### Phase B — Full automation (zero-touch school)
| Automation | Trigger | Outcome |
|---|---|---|
| Fee escalation ladder | Due +1/7/15/30 din | Reminder → late-fee → report-card hold tag → director report. Zero manual follow-up. 🔔 |
| Substitute auto-suggest | Leave approved | Free-period qualified teachers ko slot offer; first-accept wins. 🔔 |
| Timetable clash guardian | Timetable edit | Teacher/room/section double-book real-time block before save. |
| Year-end rollover | April 1 | Class promotion, section shuffle, fee slabs re-apply, archives — one-click. |
| Anomaly watch | Daily | Cash-vs-digital mismatch, duplicate receipts, payroll anomalies → director flag. 🤖 |

### Phase C — AI layer (practical)
1. **Parent answer engine** 🤖 — "aaj meri beti ki attendance?" → structured DB query → instant answer; office calls −60%.
2. **Report-card narrator** 🤖 — 3-line personalized comment draft per student; teacher edits, doesn't write.
3. **Timetable generator** 🤖 — constraints (availability, max/day, subject hours) → optimized draft.

### Phase D — Self-contained ecosystem
- Visitor gate pass (QR), Lost & found, Campus marketplace (books/uniform)
- Canteen pre-order + wallet + allergy flags (attendance-linked)
- Event management (volunteer signup, slots, gallery)
- Full audit-trail UI per record; one-click school data export/backup
- i18n runtime from day one (English/Hindi/Marathi)

### Suggested build order
1. `lib/api` seam + Supabase → 2. Real auth + RBAC → 3. Notification event-bus + WhatsApp → 4. Fee escalation + attendance nudges → 5. Year-end rollover → 6. Parent answer engine (AI).
