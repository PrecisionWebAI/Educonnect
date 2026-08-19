# 📘 EduVerse — Master Project Blueprint (Frontend-First Technical Document)

> **Version:** 1.0  •  **Component:** Frontend (React Web + React Native Mobile-ready)
> **Goal:** 80-Crore-student School Automation Platform — Portal for Director, Principal, Teacher, Student, Parent.
> **Format:** Every **Page** → every **Tab** → every **Feature + Action** (each described in max 2 lines).
> **Legend:** 🤖 = AI-powered feature • 🔔 = notification trigger • 📱 = mobile-first design

----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------



Press `Ctrl+Shift+V`  to see in (Preview mode) if it is not




## ANNEXURE — FULL FEATURE INDEX

### A1. PAGE INDEX — 21 Pages

| # | Page | Route | Roles | Tabs | Features |
|---|------|-------|-------|------|----------|
| 1 | PAGE 01 — AUTH (Login / Register / Sessions) | /auth | All (public) | 3 | 13 |
| 2 | PAGE 02 — DASHBOARD (Role-Mastered Home) | / | All (content switches by role) | 8 | 39 |
| 3 | PAGE 03 — STUDENTS (Master Data) | /students | ADMIN, DRC, PRINCIPAL, CT, SUBJ (own class), STUFF, GUARDIAN (own child) | 4 | 17 |
| 4 | PAGE 04 — ATTENDANCE | /attendance | ADMIN, DRC, PRINCIPAL, CT, SUBJ (own class), HOD, STUFF (data-entry), STU (self), GUARDIAN (child) | 4 | 16 |
| 5 | PAGE 05 — ACADEMICS / MARKS (Gradebook & Report Cards) | /academics | ADMIN, DRC (read), PRINCIPAL, HOD, CT, SUBJ (own subject), STU (self), GUARDIAN (child) | 4 | 16 |
| 6 | PAGE 06 — EXAMS & AI PAPERS (AI-first) | /exams | ADMIN, DRC (read), PRINCIPAL (approve), HOD (approve), SUBJ (own subject), CT (schedule), STU (view), GUARDIAN (view) | 5 | 27 |
| 7 | PAGE 07 — HOMEWORK & CLASS DIARY | /homework | SUBJ (assign), CT (diary), STU, GUARDIAN, HOD (monitor), ADMIN | 4 | 15 |
| 8 | PAGE 08 — TIMETABLE | /timetable | All (view per role), ADMIN/PRINCIPAL (publish), HOD (edit subject blocks) | 2 | 8 |
| 9 | PAGE 09 — TEACHERS & STAFF | /teachers | ADMIN, DRC (read), PRINCIPAL, HOD (subject view), ACCT (payroll view) | 4 | 14 |
| 10 | PAGE 10 — PAYROLL / PAYSLIP 🟩 | /payroll | ACCT (prepare), DRC (approve), PRINCIPAL (approve), TEACHER (own payslip only), ADMIN | 3 | 10 |
| 11 | PAGE 11 — FINANCE (Fees, Receipts, Budgets) 🟩 | /finance | ACCT, DRC (report), ADMIN, GUARDIAN (child fees & pay), STUFF (receive) | 4 | 16 |
| 12 | PAGE 12 — LIBRARY | /library | LIB, ADMIN, PRINCIPAL(monitor), STU (self), GUARDIAN (child) | 3 | 10 |
| 13 | PAGE 13 — TRANSPORT | /transport | TRANSP, ADMIN, DRC (monitor), PRINCIPAL, GUARDIAN (child route), STUDENT (own route) | 3 | 10 |
| 14 | PAGE 14 — TICKETS & SUPPORT (Escalation Chain) 🟥 | /tickets | All. Escalation chain: Ticket → (CT / SUBJ) → Principal → Director (auto-raise). | 4 | 16 |
| 15 | PAGE 15 — MEETINGS (Parent–Teacher Scheduling) 🟫 | /meetings | SUBJ, CT, PRINCIPAL, GUARDIAN, STUDENT (view) | 4 | 13 |
| 16 | PAGE 16 — NOTIFICATIONS CENTER 🔔 | /notifications | All (What-you-get depends on role & settings) | 4 | 15 |
| 17 | PAGE 17 — CHAT & COMMUNICATION 🟦 | /chat | All (context-limited by relationship rules) | 3 | 12 |
| 18 | PAGE 18 — LEAVE & APPLICATIONS (Students/Parents) 🟦 | /leave | STU, GUARDIAN, CT (approve), PRINCIPAL (approve staff, long), ADMIN | 4 | 16 |
| 19 | PAGE 19 — REPORTS & ANALYTICS 📊 | /reports | DRC, PRINCIPAL, HOD, ACCT, ADMIN (view), teachers (their scope) | 4 | 14 |
| 20 | PAGE 20 — AI COPILOT (Global Assistant) | /ai-copilot (also reachable from every screen via ⌘K / search bar) | All (scope-aware) | 4 | 14 |
| 21 | PAGE 21 — SETTINGS & CONFIGURATION | /settings | OWNER, ADMIN (full); PRINCIPAL (partial); individual preferences for all | 4 | 15 |

### A2. TAB INDEX — 82 Tabs

| # | Page | Tab |
|---|------|-----|
| 1 | PAGE 01 — AUTH (Login / Register / Sessions) | Tab 1.1 — Sign In |
| 2 | PAGE 01 — AUTH (Login / Register / Sessions) | Tab 1.2 — Register / Invite |
| 3 | PAGE 01 — AUTH (Login / Register / Sessions) | Tab 1.3 — Session & Security |
| 4 | PAGE 02 — DASHBOARD (Role-Mastered Home) | Tab D.1 — Director Dashboard 🟣 (every card = KPI + chart + drill-down) |
| 5 | PAGE 02 — DASHBOARD (Role-Mastered Home) | Tab D.2 — Principal Dashboard 🟣 |
| 6 | PAGE 02 — DASHBOARD (Role-Mastered Home) | Tab D.3 — HOD Academic Dashboard 🟪 |
| 7 | PAGE 02 — DASHBOARD (Role-Mastered Home) | Tab D.4 — Class Teacher Dashboard 🟦 |
| 8 | PAGE 02 — DASHBOARD (Role-Mastered Home) | Tab D.5 — Subject Teacher Dashboard 🟪 |
| 9 | PAGE 02 — DASHBOARD (Role-Mastered Home) | Tab D.6 — Student Dashboard |
| 10 | PAGE 02 — DASHBOARD (Role-Mastered Home) | Tab D.7 — Parent Dashboard (per child; switcher for multiple children) |
| 11 | PAGE 02 — DASHBOARD (Role-Mastered Home) | Tab D.8 — Accountant Dashboard 🟩 |
| 12 | PAGE 03 — STUDENTS (Master Data) | Tab 3.1 — Student List |
| 13 | PAGE 03 — STUDENTS (Master Data) | Tab 3.2 — Add / Edit Student |
| 14 | PAGE 03 — STUDENTS (Master Data) | Tab 3.3 — Student Profile (all roles see granted fields only) |
| 15 | PAGE 03 — STUDENTS (Master Data) | Tab 3.4 — Class Matrix (teacher-loved view) |
| 16 | PAGE 04 — ATTENDANCE | Tab 4.1 — Mark Attendance |
| 17 | PAGE 04 — ATTENDANCE | Tab 4.2 — Attendance History |
| 18 | PAGE 04 — ATTENDANCE | Tab 4.3 — Irregularity & Insights |
| 19 | PAGE 04 — ATTENDANCE | Tab 4.4 — Attendance ≥ Leave Sync |
| 20 | PAGE 05 — ACADEMICS / MARKS (Gradebook & Report Cards) | Tab 5.1 — Marks Entry (spreadsheet-grade) |
| 21 | PAGE 05 — ACADEMICS / MARKS (Gradebook & Report Cards) | Tab 5.2 — Gradebook / Report Card |
| 22 | PAGE 05 — ACADEMICS / MARKS (Gradebook & Report Cards) | Tab 5.3 — Results & Analytics 🟪 |
| 23 | PAGE 05 — ACADEMICS / MARKS (Gradebook & Report Cards) | Tab 5.4 — Marks Dispute (student can challenge) |
| 24 | PAGE 06 — EXAMS & AI PAPERS (AI-first) | Tab 6.1 — 🤖 AI Paper Generator |
| 25 | PAGE 06 — EXAMS & AI PAPERS (AI-first) | Tab 6.2 — Question Bank |
| 26 | PAGE 06 — EXAMS & AI PAPERS (AI-first) | Tab 6.3 — My Papers / Review Workflow |
| 27 | PAGE 06 — EXAMS & AI PAPERS (AI-first) | Tab 6.4 — Conduct & Marking |
| 28 | PAGE 06 — EXAMS & AI PAPERS (AI-first) | Tab 6.5 — Schedule & Seating |
| 29 | PAGE 07 — HOMEWORK & CLASS DIARY | Tab 7.1 — Assign Homework 🟪 |
| 30 | PAGE 07 — HOMEWORK & CLASS DIARY | Tab 7.2 — Submissions & Review |
| 31 | PAGE 07 — HOMEWORK & CLASS DIARY | Tab 7.3 — Class Diary (per student, per day) |
| 32 | PAGE 07 — HOMEWORK & CLASS DIARY | Tab 7.4 — Parent & Student View |
| 33 | PAGE 08 — TIMETABLE | Tab 8.1 — Weekly Table |
| 34 | PAGE 08 — TIMETABLE | Tab 8.2 — Editor (admin/principal) |
| 35 | PAGE 09 — TEACHERS & STAFF | Tab 9.1 — Staff List |
| 36 | PAGE 09 — TEACHERS & STAFF | Tab 9.2 — Workload & Course Matrix 🟣 (director's matrix) |
| 37 | PAGE 09 — TEACHERS & STAFF | Tab 9.3 — Leave & Substitute |
| 38 | PAGE 09 — TEACHERS & STAFF | Tab 9.4 — Performance & Review |
| 39 | PAGE 10 — PAYROLL / PAYSLIP 🟩 | Tab 10.1 — Salary Structure |
| 40 | PAGE 10 — PAYROLL / PAYSLIP 🟩 | Tab 10.2 — Month Processing |
| 41 | PAGE 10 — PAYROLL / PAYSLIP 🟩 | Tab 10.3 — Payslips |
| 42 | PAGE 11 — FINANCE (Fees, Receipts, Budgets) 🟩 | Tab 11.1 — Fee Collection |
| 43 | PAGE 11 — FINANCE (Fees, Receipts, Budgets) 🟩 | Tab 11.2 — Dues & Recovery |
| 44 | PAGE 11 — FINANCE (Fees, Receipts, Budgets) 🟩 | Tab 11.3 — Expenses & Budget |
| 45 | PAGE 11 — FINANCE (Fees, Receipts, Budgets) 🟩 | Tab 11.4 — Reports (director's revenue page) |
| 46 | PAGE 12 — LIBRARY | Tab 12.1 — Catalogue & Search |
| 47 | PAGE 12 — LIBRARY | Tab 12.2 — Issue / Return |
| 48 | PAGE 12 — LIBRARY | Tab 12.3 — Overdues & Notices |
| 49 | PAGE 13 — TRANSPORT | Tab 13.1 — Routes & Stops |
| 50 | PAGE 13 — TRANSPORT | Tab 13.2 — Buses & GPS |
| 51 | PAGE 13 — TRANSPORT | Tab 13.3 — Transport Fees & Enforcement |
| 52 | PAGE 14 — TICKETS & SUPPORT (Escalation Chain) 🟥 | Tab 14.1 — Raise a Ticket |
| 53 | PAGE 14 — TICKETS & SUPPORT (Escalation Chain) 🟥 | Tab 14.2 — My Tickets (role-appropriate state) |
| 54 | PAGE 14 — TICKETS & SUPPORT (Escalation Chain) 🟥 | Tab 14.3 — Support Inbox (teachers/principal/director) |
| 55 | PAGE 14 — TICKETS & SUPPORT (Escalation Chain) 🟥 | Tab 14.4 — Director / Principal Oversight |
| 56 | PAGE 15 — MEETINGS (Parent–Teacher Scheduling) 🟫 | Tab 15.1 — Teacher Slot Manager |
| 57 | PAGE 15 — MEETINGS (Parent–Teacher Scheduling) 🟫 | Tab 15.2 — Parent Booking |
| 58 | PAGE 15 — MEETINGS (Parent–Teacher Scheduling) 🟫 | Tab 15.3 — Meeting Room & Reminders |
| 59 | PAGE 15 — MEETINGS (Parent–Teacher Scheduling) 🟫 | Tab 15.4 — Meeting History & Analytics |
| 60 | PAGE 16 — NOTIFICATIONS CENTER 🔔 | Tab 16.1 — Live Feed |
| 61 | PAGE 16 — NOTIFICATIONS CENTER 🔔 | Tab 16.2 — Targeted & Important Alerts |
| 62 | PAGE 16 — NOTIFICATIONS CENTER 🔔 | Tab 16.3 — Broadcasts & Announcements |
| 63 | PAGE 16 — NOTIFICATIONS CENTER 🔔 | Tab 16.4 — Notifications for Absent/Parent |
| 64 | PAGE 17 — CHAT & COMMUNICATION 🟦 | Tab 17.1 — Conversations |
| 65 | PAGE 17 — CHAT & COMMUNICATION 🟦 | Tab 17.2 — Messaging Features |
| 66 | PAGE 17 — CHAT & COMMUNICATION 🟦 | Tab 17.3 — In-Context Chats |
| 67 | PAGE 18 — LEAVE & APPLICATIONS (Students/Parents) 🟦 | Tab 18.1 — 🤖 AI Application Generator |
| 68 | PAGE 18 — LEAVE & APPLICATIONS (Students/Parents) 🟦 | Tab 18.2 — Apply & Track |
| 69 | PAGE 18 — LEAVE & APPLICATIONS (Students/Parents) 🟦 | Tab 18.3 — Approver Side (class teacher / principal) |
| 70 | PAGE 18 — LEAVE & APPLICATIONS (Students/Parents) 🟦 | Tab 18.4 — Staff Leave (teacher) |
| 71 | PAGE 19 — REPORTS & ANALYTICS 📊 | Tab 19.1 — Report Builder |
| 72 | PAGE 19 — REPORTS & ANALYTICS 📊 | Tab 19.2 — Director Command Center |
| 73 | PAGE 19 — REPORTS & ANALYTICS 📊 | Tab 19.3 — Education-Specific |
| 74 | PAGE 19 — REPORTS & ANALYTICS 📊 | Tab 19.4 — Data Quality & Exports |
| 75 | PAGE 20 — AI COPILOT (Global Assistant) | Tab 20.1 — Command Palette (⌘K / Ctrl-K) |
| 76 | PAGE 20 — AI COPILOT (Global Assistant) | Tab 20.2 — 🤖 Ask EduVerse AI |
| 77 | PAGE 20 — AI COPILOT (Global Assistant) | Tab 20.3 — Genius Assistant (contextual) |
| 78 | PAGE 20 — AI COPILOT (Global Assistant) | Tab 20.4 — Automation Recipes |
| 79 | PAGE 21 — SETTINGS & CONFIGURATION | Tab 21.1 — Users & Roles |
| 80 | PAGE 21 — SETTINGS & CONFIGURATION | Tab 21.2 — School Profile |
| 81 | PAGE 21 — SETTINGS & CONFIGURATION | Tab 21.3 — Audit & Security |
| 82 | PAGE 21 — SETTINGS & CONFIGURATION | Tab 21.4 — Integrations & Preferences |

### A3. FEATURE & ACTION INDEX — 326 Features

| # | Page | Tab | Feature | What it does |
|---|------|-----|---------|--------------|
| 1 | PAGE 01 — AUTH (Login / Register / Sessions) | Tab 1.1 — Sign In | Email/username + password | Validated login with per-field errors; show-password toggle; caps-lock warning. |
| 2 | PAGE 01 — AUTH (Login / Register / Sessions) | Tab 1.1 — Sign In | Remember me | Persistent session for staff desktops vs soft-session for kiosk; expiry enforced by token age. |
| 3 | PAGE 01 — AUTH (Login / Register / Sessions) | Tab 1.1 — Sign In | Forgot password | Email OTP → reset link with expiry; token audit; confirmation mail on reset. 🔔 |
| 4 | PAGE 01 — AUTH (Login / Register / Sessions) | Tab 1.1 — Sign In | 2-Factor OTP (optional) | TOTP / email / SMS OTP on first login from a new device; backup codes printable. |
| 5 | PAGE 01 — AUTH (Login / Register / Sessions) | Tab 1.1 — Sign In | Role-aware redirect | Post-login route by role: owner→settings, director→dash, teacher→my-class, parent→child. |
| 6 | PAGE 01 — AUTH (Login / Register / Sessions) | Tab 1.2 — Register / Invite | Role-based registration | Students/parents self-register via school code + guardian-link; teachers invite-only. |
| 7 | PAGE 01 — AUTH (Login / Register / Sessions) | Tab 1.2 — Register / Invite | Invite-token flow | Admin issues invite links (role + class prefix inside token); expiry + revoke anytime. 🔔 |
| 8 | PAGE 01 — AUTH (Login / Register / Sessions) | Tab 1.2 — Register / Invite | School-code validation | Multi-tenant check before account creation; clear + friendly failure copy. |
| 9 | PAGE 01 — AUTH (Login / Register / Sessions) | Tab 1.2 — Register / Invite | OTP activation | Phone/email OTP activates the account; 60s resend timer; rate-limit feedback. |
| 10 | PAGE 01 — AUTH (Login / Register / Sessions) | Tab 1.3 — Session & Security | Active sessions list | View every logged-in device; revoke any session; "sign out all" on compromise. 🔔 |
| 11 | PAGE 01 — AUTH (Login / Register / Sessions) | Tab 1.3 — Session & Security | Idle auto-logout | Countdown toast + still-active modal; safe for labs/kiosks; audit trail entry. |
| 12 | PAGE 01 — AUTH (Login / Register / Sessions) | Tab 1.3 — Session & Security | Kiosk lock screen | Lab/library PCs lock on idle; quick-PIN resume; resumes without data exposure. |
| 13 | PAGE 01 — AUTH (Login / Register / Sessions) | Tab 1.3 — Session & Security | Password policy | Min length + strength meter; no reuse of last 5; staff expiry cycle; self-service change. |
| 14 | PAGE 02 — DASHBOARD (Role-Mastered Home) | Tab D.1 — Director Dashboard 🟣 (every card = KPI + chart + drill-down) | Students & Classes live | Admission total, active, vacancy; intake trend chart; drill to class rosters. |
| 15 | PAGE 02 — DASHBOARD (Role-Mastered Home) | Tab D.1 — Director Dashboard 🟣 (every card = KPI + chart + drill-down) | Revenue vs Plan | 🟩 collected vs target %, 6-month projection, top fee-raising classes; drill to receipts. |
| 16 | PAGE 02 — DASHBOARD (Role-Mastered Home) | Tab D.1 — Director Dashboard 🟣 (every card = KPI + chart + drill-down) | School-wide Attendance % | 🟦 all-class matrix today; click class → student detail; weekly loss chart. |
| 17 | PAGE 02 — DASHBOARD (Role-Mastered Home) | Tab D.1 — Director Dashboard 🟣 (every card = KPI + chart + drill-down) | Course-Completion Matrix | 🟣 per teacher: % chapters done vs plan; overdue in red; syllabus-gap alerts. |
| 18 | PAGE 02 — DASHBOARD (Role-Mastered Home) | Tab D.1 — Director Dashboard 🟣 (every card = KPI + chart + drill-down) | Exam Result Trends | class averages, pass %, topper list per term; subject-wise comparison lines. |
| 19 | PAGE 02 — DASHBOARD (Role-Mastered Home) | Tab D.1 — Director Dashboard 🟣 (every card = KPI + chart + drill-down) | Urgent Alerts Panel | 🟥 unresolved tickets >48h, absent teachers, pending approvals, fee-due spikes. 🔔 |
| 20 | PAGE 02 — DASHBOARD (Role-Mastered Home) | Tab D.1 — Director Dashboard 🟣 (every card = KPI + chart + drill-down) | 🤖 AI Weekly Insight | LLM writes one-paragraph briefing with numbers + clickable action suggestions. |
| 21 | PAGE 02 — DASHBOARD (Role-Mastered Home) | Tab D.1 — Director Dashboard 🟣 (every card = KPI + chart + drill-down) | 🤖 Anomaly Spotlight | LLM flags unusual signals (3-day teacher absence, sudden marks jump) for review. |
| 22 | PAGE 02 — DASHBOARD (Role-Mastered Home) | Tab D.2 — Principal Dashboard 🟣 | Today's Operations Board | running classes, present teachers, substitutes assigned, upcoming events. |
| 23 | PAGE 02 — DASHBOARD (Role-Mastered Home) | Tab D.2 — Principal Dashboard 🟣 | Approval Queue | leaves, fee waivers, mark disputes, paper approvals — approve/reject inline. 🔔 |
| 24 | PAGE 02 — DASHBOARD (Role-Mastered Home) | Tab D.2 — Principal Dashboard 🟣 | Class Attendance & Discipline | 🟦 charts per class → drill to student; early-dropout red flags. |
| 25 | PAGE 02 — DASHBOARD (Role-Mastered Home) | Tab D.2 — Principal Dashboard 🟣 | Escalated Tickets | 🟥 teacher/parent tickets reaching principal; SLA clock visible on each row. |
| 26 | PAGE 02 — DASHBOARD (Role-Mastered Home) | Tab D.2 — Principal Dashboard 🟣 | Staff Leave & Substitution | who is absent + auto-suggested substitute from free teachers. 🤖 |
| 27 | PAGE 02 — DASHBOARD (Role-Mastered Home) | Tab D.2 — Principal Dashboard 🟣 | Exam Monitor | live exam sessions, papers pending review, upload counts per class. |
| 28 | PAGE 02 — DASHBOARD (Role-Mastered Home) | Tab D.3 — HOD Academic Dashboard 🟪 | Subject Performance Matrix | class average, toppers, weak-topic detector from marks analytics. 🤖 |
| 29 | PAGE 02 — DASHBOARD (Role-Mastered Home) | Tab D.3 — HOD Academic Dashboard 🟪 | Question-Bank Health | 🤖 counts per subject/chapter/tags + gap suggestions ("ch.9 only 12 MCQ"). |
| 30 | PAGE 02 — DASHBOARD (Role-Mastered Home) | Tab D.3 — HOD Academic Dashboard 🟪 | Paper Review Queue | AI papers awaiting HOD approval; comment / approve / reject loop. 🔔 |
| 31 | PAGE 02 — DASHBOARD (Role-Mastered Home) | Tab D.3 — HOD Academic Dashboard 🟪 | Teacher Engagement | homework & exam assignment activity; syllabus % per teacher; zero-activity flags. |
| 32 | PAGE 02 — DASHBOARD (Role-Mastered Home) | Tab D.4 — Class Teacher Dashboard 🟦 | My Class Today | attendance grid summary; absent list with auto-parent-notification status visible. 🔔 |
| 33 | PAGE 02 — DASHBOARD (Role-Mastered Home) | Tab D.4 — Class Teacher Dashboard 🟦 | Diary & Homework Status | outstanding submissions; students not yet shown today's diary; quick nudge. 🔔 |
| 34 | PAGE 02 — DASHBOARD (Role-Mastered Home) | Tab D.4 — Class Teacher Dashboard 🟦 | Parent Meeting Reminders | upcoming booked slots; one-tap "book more" opens schedule page. |
| 35 | PAGE 02 — DASHBOARD (Role-Mastered Home) | Tab D.4 — Class Teacher Dashboard 🟦 | Leave Apps of MY Students | approve/reject inline; approval auto-marks attendance + notifies parent. 🔔 |
| 36 | PAGE 02 — DASHBOARD (Role-Mastered Home) | Tab D.5 — Subject Teacher Dashboard 🟪 | My Classes Today | timetable cards; one-tap "Start Attendance" on any live class. |
| 37 | PAGE 02 — DASHBOARD (Role-Mastered Home) | Tab D.5 — Subject Teacher Dashboard 🟪 | Marks Entry Shortcuts | pending class-tests list; last-entry time; jump straight to gradebook page. |
| 38 | PAGE 02 — DASHBOARD (Role-Mastered Home) | Tab D.5 — Subject Teacher Dashboard 🟪 | HW/Assignment Status | assigned vs submitted per class; overdue students with nudge button. 🔔 |
| 39 | PAGE 02 — DASHBOARD (Role-Mastered Home) | Tab D.5 — Subject Teacher Dashboard 🟪 | My AI Paper Drafts | drafts pending edit/regenerate/download; question-bank stats of my subjects. |
| 40 | PAGE 02 — DASHBOARD (Role-Mastered Home) | Tab D.6 — Student Dashboard | My Performance Cards | marks average, attendance %, pending homework, class rank (school setting allows). |
| 41 | PAGE 02 — DASHBOARD (Role-Mastered Home) | Tab D.6 — Student Dashboard | Today's Homework & Diary | assignments with due countdown; mark-as-done; parent gets read-confirmation. 🔔 |
| 42 | PAGE 02 — DASHBOARD (Role-Mastered Home) | Tab D.6 — Student Dashboard | Recent Grades | latest test scores with per-subject trend chart; "share with parents" one-tap link. |
| 43 | PAGE 02 — DASHBOARD (Role-Mastered Home) | Tab D.6 — Student Dashboard | My Leaves & Tickets | status chips pending/approved/rejected; resume-edit draft; reopen ticket. 🔔 |
| 44 | PAGE 02 — DASHBOARD (Role-Mastered Home) | Tab D.6 — Student Dashboard | 🤖 Study Assistant | chat "how do I improve maths?" → AI answers from my marks weak-topic analysis. |
| 45 | PAGE 02 — DASHBOARD (Role-Mastered Home) | Tab D.7 — Parent Dashboard (per child; switcher for multiple children) | Child Snapshot | marks, attendance %, behaviour notes, fee balance in four glance cards (🟪🟦🟥🟩). |
| 46 | PAGE 02 — DASHBOARD (Role-Mastered Home) | Tab D.7 — Parent Dashboard (per child; switcher for multiple children) | Today's Feed | real-time: child absent/leave, homework assigned, exam schedule, meeting booked. 🔔 live. |
| 47 | PAGE 02 — DASHBOARD (Role-Mastered Home) | Tab D.7 — Parent Dashboard (per child; switcher for multiple children) | Fee Status & Pay | 🟩 paid/pending chips, instant pay via gateway, receipt PDF download. |
| 48 | PAGE 02 — DASHBOARD (Role-Mastered Home) | Tab D.7 — Parent Dashboard (per child; switcher for multiple children) | Quick Actions | apply leave, raise ticket, book teacher meeting, open report card, message class teacher. |
| 49 | PAGE 02 — DASHBOARD (Role-Mastered Home) | Tab D.8 — Accountant Dashboard 🟩 | Today's Collection | cash/UPI/card/draft totals live; vs yesterday; vs monthly target bar. |
| 50 | PAGE 02 — DASHBOARD (Role-Mastered Home) | Tab D.8 — Accountant Dashboard 🟩 | Pending Dues Radar | top defaulters with "send reminder" bulk email/WhatsApp button. 🔔 |
| 51 | PAGE 02 — DASHBOARD (Role-Mastered Home) | Tab D.8 — Accountant Dashboard 🟩 | Expense Approvals | vouchers/invoices awaiting Director/Principal approval; attach & submit. 🔔 |
| 52 | PAGE 02 — DASHBOARD (Role-Mastered Home) | Tab D.8 — Accountant Dashboard 🟩 | Payroll Month Progress | staff count, gross payroll, TDS total, disburse-ready state check. |
| 53 | PAGE 03 — STUDENTS (Master Data) | Tab 3.1 — Student List | Search + filters | name/roll/class/section/status/fee-blocked; saved-filter presets; column toggle. |
| 54 | PAGE 03 — STUDENTS (Master Data) | Tab 3.1 — Student List | Row actions | profile, edit, mark-absent jump, fee view, send mail, message parent. |
| 55 | PAGE 03 — STUDENTS (Master Data) | Tab 3.1 — Student List | Bulk select & export | select many → CSV/Excel/PDF export; bulk edit section or alumni status. |
| 56 | PAGE 03 — STUDENTS (Master Data) | Tab 3.1 — Student List | Import (CSV/Excel) | multi-row add with field mapping preview; duplicate detection by email/roll. 🤖 warn rows |
| 57 | PAGE 03 — STUDENTS (Master Data) | Tab 3.1 — Student List | Student lifecycle filters | Active / Inactive / Alumni / Transferred; move to alumni with confirmation. |
| 58 | PAGE 03 — STUDENTS (Master Data) | Tab 3.2 — Add / Edit Student | Multi-step wizard | Admission no., personal, guardian, contact, documents, emergency — saved as draft each step. |
| 59 | PAGE 03 — STUDENTS (Master Data) | Tab 3.2 — Add / Edit Student | Photo & documents | drag-drop upload with size/type rules; preview; storage quota indicator. |
| 60 | PAGE 03 — STUDENTS (Master Data) | Tab 3.2 — Add / Edit Student | Guardian linking | attach existing parent account or create new; guardian↔sibling link for family discounts. |
| 61 | PAGE 03 — STUDENTS (Master Data) | Tab 3.2 — Add / Edit Student | 🤖 Auto-gating | warns duplicate admission number / AADHAAR mismatch; suggests class based on age. |
| 62 | PAGE 03 — STUDENTS (Master Data) | Tab 3.3 — Student Profile (all roles see granted fields only) | Overview | photo, roll, class, section, contact, guardian circle, admission date; print ID card button. |
| 63 | PAGE 03 — STUDENTS (Master Data) | Tab 3.3 — Student Profile (all roles see granted fields only) | Academic track | marks history per term, rank trend, teacher notes; export portfolio. 🟪 |
| 64 | PAGE 03 — STUDENTS (Master Data) | Tab 3.3 — Student Profile (all roles see granted fields only) | Attendance track | calendar heatmap, % per month, present/absent/leave split. 🟦 |
| 65 | PAGE 03 — STUDENTS (Master Data) | Tab 3.3 — Student Profile (all roles see granted fields only) | Fees tab | 🟩 heads, paid/pending timeline, receipts; reminders; family-discount applied marks. |
| 66 | PAGE 03 — STUDENTS (Master Data) | Tab 3.3 — Student Profile (all roles see granted fields only) | Behaviour & Diary tab | diary entries, compliments & complaints, improvement plan; parent-visible summary. |
| 67 | PAGE 03 — STUDENTS (Master Data) | Tab 3.3 — Student Profile (all roles see granted fields only) | Documents | admission docs, TC/LC, previous report cards; upload/withdraw; expiry alerts. |
| 68 | PAGE 03 — STUDENTS (Master Data) | Tab 3.4 — Class Matrix (teacher-loved view) | My Class Grid | roll-wise table with chips: attendance today, pending HW, fee due, last marks. |
| 69 | PAGE 03 — STUDENTS (Master Data) | Tab 3.4 — Class Matrix (teacher-loved view) | Quick Actions | mark absent today, send message, generate report card from the same row. |
| 70 | PAGE 04 — ATTENDANCE | Tab 4.1 — Mark Attendance | Class & period picker | select class/section/subject/date; loads student roster with default Present. |
| 71 | PAGE 04 — ATTENDANCE | Tab 4.1 — Mark Attendance | Quick-mark grid | tap/toggle each row: Present, Absent, Leave, Late, Half-day; keyboard shortcuts (1-5). |
| 72 | PAGE 04 — ATTENDANCE | Tab 4.1 — Mark Attendance | Bulk actions | "mark all present", "everyone except 3 absent", invert row (late→present); undo last action. |
| 73 | PAGE 04 — ATTENDANCE | Tab 4.1 — Mark Attendance | Remarks lane | per-student short remark (medical, OD, sport) shown to parent summary; reopen edit lock fee. |
| 74 | PAGE 04 — ATTENDANCE | Tab 4.1 — Mark Attendance | Photo attendance (optional) | AI face-mark tie-in: camera scans class → suggested marks are teacher-reviewed. 🤖 |
| 75 | PAGE 04 — ATTENDANCE | Tab 4.1 — Mark Attendance | Submit & notify | save once, all gadgets update; absent list auto-notifies parents via app+mail+WhatsApp. 🔔 |
| 76 | PAGE 04 — ATTENDANCE | Tab 4.2 — Attendance History | Calendar view | monthly grid of % per day; click cell → class/period breakdown; weekends greyed out. |
| 77 | PAGE 04 — ATTENDANCE | Tab 4.2 — Attendance History | Student-wise filter | top section: cumulative %, present/absent/leave counts, last 30 days heatmap. 🟦 |
| 78 | PAGE 04 — ATTENDANCE | Tab 4.2 — Attendance History | Class-wise filter | compare classes on same week; attendance % line chart; outliers highlighted. 🤖 |
| 79 | PAGE 04 — ATTENDANCE | Tab 4.2 — Attendance History | Export | monthly register PDF (print-quality), marker CSV for Excel, teacher-copy download. |
| 80 | PAGE 04 — ATTENDANCE | Tab 4.3 — Irregularity & Insights | 🤖 Irregular list | AI ranks students by attendance risk (school-policy thresholds respected); parent nudge. |
| 81 | PAGE 04 — ATTENDANCE | Tab 4.3 — Irregularity & Insights | 🤖 Trend alerts | a class dropping >10% in 2 weeks flags here for principal; auto-email to class teacher. 🔔 |
| 82 | PAGE 04 — ATTENDANCE | Tab 4.3 — Irregularity & Insights | Holiday / event calendar | upcoming holidays auto-excluded from targets; half-day rules configurable. |
| 83 | PAGE 04 — ATTENDANCE | Tab 4.3 — Irregularity & Insights | Monthly register | official attendance register sheet per class with signature columns (print view). |
| 84 | PAGE 04 — ATTENDANCE | Tab 4.4 — Attendance ≥ Leave Sync | Leave-linked attendance | approved leave auto-fills "Leave", not marks "Absent"; status chip visible. |
| 85 | PAGE 04 — ATTENDANCE | Tab 4.4 — Attendance ≥ Leave Sync | Late & early-out wave | office timer-screen entry for late arrivals; parent notified on repeated lateness. 🔔 |
| 86 | PAGE 05 — ACADEMICS / MARKS (Gradebook & Report Cards) | Tab 5.1 — Marks Entry (spreadsheet-grade) | Sheet-like grid | class × test columns; tab-navigation between cells; total/avg auto-calculated live. |
| 87 | PAGE 05 — ACADEMICS / MARKS (Gradebook & Report Cards) | Tab 5.1 — Marks Entry (spreadsheet-grade) | Bulk paste | paste rows from Excel (roll, marks) → validated & diff-previewed before save. |
| 88 | PAGE 05 — ACADEMICS / MARKS (Gradebook & Report Cards) | Tab 5.1 — Marks Entry (spreadsheet-grade) | Grading scheme | per-school rules: raw → grade (A+, A…), CGPA or percentage — all formats supported. |
| 89 | PAGE 05 — ACADEMICS / MARKS (Gradebook & Report Cards) | Tab 5.1 — Marks Entry (spreadsheet-grade) | Partial save & lock | save-as-draft vs finalize; final entries lock editing (unlock requires permission). |
| 90 | PAGE 05 — ACADEMICS / MARKS (Gradebook & Report Cards) | Tab 5.1 — Marks Entry (spreadsheet-grade) | Entry status | shows which class has full/partial/nil entry; deadline reminders for term end. 🔔 |
| 91 | PAGE 05 — ACADEMICS / MARKS (Gradebook & Report Cards) | Tab 5.2 — Gradebook / Report Card | Report card builder | 🇱 scheme selector: formative/summative, term/half-term; preview per student. |
| 92 | PAGE 05 — ACADEMICS / MARKS (Gradebook & Report Cards) | Tab 5.2 — Gradebook / Report Card | 🤖 Teacher remarks | AI drafts personalized remarks from marks + attendance (editable before print). |
| 93 | PAGE 05 — ACADEMICS / MARKS (Gradebook & Report Cards) | Tab 5.2 — Gradebook / Report Card | PDF report cards | batch generate whole class; print-quality; watermark draft/approved; sign fields. |
| 94 | PAGE 05 — ACADEMICS / MARKS (Gradebook & Report Cards) | Tab 5.2 — Gradebook / Report Card | Student portfolio export | one click: full academic history + certificates + attendance, zipped PDF. |
| 95 | PAGE 05 — ACADEMICS / MARKS (Gradebook & Report Cards) | Tab 5.3 — Results & Analytics 🟪 | Class result summary | avg/pass/toppers/fail list per subject & term; chart compare terms. |
| 96 | PAGE 05 — ACADEMICS / MARKS (Gradebook & Report Cards) | Tab 5.3 — Results & Analytics 🟪 | 🤖 Weak-topic detector | question-tagged marks → "ch.5 (Fractions) drags Class 7 down" insight card. |
| 97 | PAGE 05 — ACADEMICS / MARKS (Gradebook & Report Cards) | Tab 5.3 — Results & Analytics 🟪 | 🤖 Improvement/recession tracking | shows students improving fast vs slipping; suggested support list for HOD. |
| 98 | PAGE 05 — ACADEMICS / MARKS (Gradebook & Report Cards) | Tab 5.3 — Results & Analytics 🟪 | Ranking & percentile | class/section/subject ranks; optional visibility rule per school policy (admin toggle). |
| 99 | PAGE 05 — ACADEMICS / MARKS (Gradebook & Report Cards) | Tab 5.4 — Marks Dispute (student can challenge) | Raise dispute | student ticks an entry with reason; teacher sees in "Reassess Queue"; reply/update/close. 🔔 |
| 100 | PAGE 05 — ACADEMICS / MARKS (Gradebook & Report Cards) | Tab 5.4 — Marks Dispute (student can challenge) | Audit trail on change | every marks change logs old/new/who/when; principal can compare versions. |
| 101 | PAGE 05 — ACADEMICS / MARKS (Gradebook & Report Cards) | Tab 5.4 — Marks Dispute (student can challenge) | Grade normalization | scaling/percentile normalization supported for multi-section fairness. |
| 102 | PAGE 06 — EXAMS & AI PAPERS (AI-first) | Tab 6.1 — 🤖 AI Paper Generator | Parameter wizard | class, subject, board pattern, chapters, difficulty mix, marks weight, MCQ/short/long split. |
| 103 | PAGE 06 — EXAMS & AI PAPERS (AI-first) | Tab 6.1 — 🤖 AI Paper Generator | 🤖 Generate paper | LLM drafts full paper; question-by-question edit mode; regenerate single or all questions. |
| 104 | PAGE 06 — EXAMS & AI PAPERS (AI-first) | Tab 6.1 — 🤖 AI Paper Generator | 🤖 "Improve style" | select a question → AI rewrites it (tougher, simpler, clearer, board-pattern) with preview. |
| 105 | PAGE 06 — EXAMS & AI PAPERS (AI-first) | Tab 6.1 — 🤖 AI Paper Generator | Custom question add | drag in teacher's own questions mixed with AI ones; tag sources for future bank. |
| 106 | PAGE 06 — EXAMS & AI PAPERS (AI-first) | Tab 6.1 — 🤖 AI Paper Generator | Balanced difficulty gauge | AI auto-balances easy/medium/hard tally, shows count bars; one-click rebalance. 🤖 |
| 107 | PAGE 06 — EXAMS & AI PAPERS (AI-first) | Tab 6.1 — 🤖 AI Paper Generator | Syllabus binding | paper auto-maps to the course plan; chapters outside syllabus auto-warned. 🤖 |
| 108 | PAGE 06 — EXAMS & AI PAPERS (AI-first) | Tab 6.1 — 🤖 AI Paper Generator | Version history | every regenerate saved; compare V1 vs V2; restore any version; audit who changed what. |
| 109 | PAGE 06 — EXAMS & AI PAPERS (AI-first) | Tab 6.1 — 🤖 AI Paper Generator | Save as template | once approved, reuse as "Pattern B" for future terms; school-level shared templates. |
| 110 | PAGE 06 — EXAMS & AI PAPERS (AI-first) | Tab 6.2 — Question Bank | Bank explorer | subject/chapter/tag/difficulty filters; search; preview; copy-into-paper. |
| 111 | PAGE 06 — EXAMS & AI PAPERS (AI-first) | Tab 6.2 — Question Bank | Add/import questions | manual entry, bulk paste from Excel, upload Word/PDF bank (AI parses). 🤖 |
| 112 | PAGE 06 — EXAMS & AI PAPERS (AI-first) | Tab 6.2 — Question Bank | 🤖 Auto-tagging | AI suggests chapter/topic/difficulty/board-pattern tags on import; teacher fixes quickly. |
| 113 | PAGE 06 — EXAMS & AI PAPERS (AI-first) | Tab 6.2 — Question Bank | Health analytics | coers per chapter per complexity; gap suggestions; manual question version edits with audit. |
| 114 | PAGE 06 — EXAMS & AI PAPERS (AI-first) | Tab 6.3 — My Papers / Review Workflow | Draft list | status chips: new / in-review / approved / used-this-term; search by class or subject. |
| 115 | PAGE 06 — EXAMS & AI PAPERS (AI-first) | Tab 6.3 — My Papers / Review Workflow | Send for HOD/Principal review | attach message; reviewer comments inline on any question; approve/reject. 🔔 |
| 116 | PAGE 06 — EXAMS & AI PAPERS (AI-first) | Tab 6.3 — My Papers / Review Workflow | Diff-mode review | reviewer sees AI vs edited question side-by-side; one-tap approve-all pending. |
| 117 | PAGE 06 — EXAMS & AI PAPERS (AI-first) | Tab 6.3 — My Papers / Review Workflow | Schedule exam | pick date/time/duration; auto-announce to class + parents; insert into timetable. 🔔 |
| 118 | PAGE 06 — EXAMS & AI PAPERS (AI-first) | Tab 6.4 — Conduct & Marking | Live exam dashboard | which exams running today; students joined (online) / papers uploaded counts. |
| 119 | PAGE 06 — EXAMS & AI PAPERS (AI-first) | Tab 6.4 — Conduct & Marking | Student answer-sheet upload | students upload photos/scans per paper (mobile camera → PDF) with lock timer. |
| 120 | PAGE 06 — EXAMS & AI PAPERS (AI-first) | Tab 6.4 — Conduct & Marking | 🤖 AI auto-marking | AI marks MCQ instantly; subjective with rubric + model answer; confidence % shown. |
| 121 | PAGE 06 — EXAMS & AI PAPERS (AI-first) | Tab 6.4 — Conduct & Marking | Teacher review pass | review AI scores row-wise; tweak mark + remark; finalize (locked) with audit. 🔔 |
| 122 | PAGE 06 — EXAMS & AI PAPERS (AI-first) | Tab 6.4 — Conduct & Marking | Manual full marking | rubric builder (criteria + weight), slider per criterion, total auto-calc; per-class marking page. |
| 123 | PAGE 06 — EXAMS & AI PAPERS (AI-first) | Tab 6.4 — Conduct & Marking | Plagiarism-lite flag | 🤖 highlights near-identical answer pairs among class for human check. |
| 124 | PAGE 06 — EXAMS & AI PAPERS (AI-first) | Tab 6.4 — Conduct & Marking | Draft vs final results | release toggle: draft visible to teachers only; on publish → student/parent notified. 🔔 |
| 125 | PAGE 06 — EXAMS & AI PAPERS (AI-first) | Tab 6.4 — Conduct & Marking | Paper download formats | PDF (print-ready with header/watermark), Word editable, answer-key PDF, bubblesheet-ready. |
| 126 | PAGE 06 — EXAMS & AI PAPERS (AI-first) | Tab 6.5 — Schedule & Seating | Exam timetable grid | date × class × subject; conflict detection (teacher double-booked) with alert. 🤖 |
| 127 | PAGE 06 — EXAMS & AI PAPERS (AI-first) | Tab 6.5 — Schedule & Seating | Seating arrangement | room/roll mapping generator (roll numbers shuffled by pattern); printable seating slips. |
| 128 | PAGE 06 — EXAMS & AI PAPERS (AI-first) | Tab 6.5 — Schedule & Seating | Invigilation roster | auto-assign supervisors balancing load; swap requests with approval. 🤖 |
| 129 | PAGE 07 — HOMEWORK & CLASS DIARY | Tab 7.1 — Assign Homework 🟪 | 🤖 AI homework draft | teacher selects chapter → AI drafts title, questions, expected time, difficulty. |
| 130 | PAGE 07 — HOMEWORK & CLASS DIARY | Tab 7.1 — Assign Homework 🟪 | Assign to whole class or selected | class-wide, section-wide, or individual students (remedial/praises). |
| 131 | PAGE 07 — HOMEWORK & CLASS DIARY | Tab 7.1 — Assign Homework 🟪 | Multi-format attach | text, PDF, photo of board-work, link, embedded video; due date + reminder time. |
| 132 | PAGE 07 — HOMEWORK & CLASS DIARY | Tab 7.1 — Assign Homework 🟪 | Scheduling | post-now or schedule for afternoon; auto-posts to diary + notifies class & parents. 🔔 |
| 133 | PAGE 07 — HOMEWORK & CLASS DIARY | Tab 7.1 — Assign Homework 🟪 | Today's board | date-wise assignments of my classes; status: posted → viewed → done → graded. |
| 134 | PAGE 07 — HOMEWORK & CLASS DIARY | Tab 7.2 — Submissions & Review | Inbox per teacher | submitted files viewed inline; mark done / needs-rework / redo (one-tap feedback chips). |
| 135 | PAGE 07 — HOMEWORK & CLASS DIARY | Tab 7.2 — Submissions & Review | Reminders & escalations | auto nudge to pending students at X hours; escalate to parent on deadline miss. 🔔 |
| 136 | PAGE 07 — HOMEWORK & CLASS DIARY | Tab 7.2 — Submissions & Review | 🤖 AI short feedback | instant 1-line review summary per submission ("good reasoning, spelling needs care"). |
| 137 | PAGE 07 — HOMEWORK & CLASS DIARY | Tab 7.2 — Submissions & Review | Grades from HW | weight homework into report card as per school config; counter shown. |
| 138 | PAGE 07 — HOMEWORK & CLASS DIARY | Tab 7.3 — Class Diary (per student, per day) | Day Diary entry | CTJ writes one-liners (motivation, concern, health) shared privately with parent + admin. |
| 139 | PAGE 07 — HOMEWORK & CLASS DIARY | Tab 7.3 — Class Diary (per student, per day) | Student sees own diary | home tab lists "Today's diary for me" with read-confirm (parent notified on read). 🔔 |
| 140 | PAGE 07 — HOMEWORK & CLASS DIARY | Tab 7.3 — Class Diary (per student, per day) | 🤖 Diary assistant | drafts polite diary text from attendance/homework/marks cues; teacher edits freely. |
| 141 | PAGE 07 — HOMEWORK & CLASS DIARY | Tab 7.3 — Class Diary (per student, per day) | Monthly diary digest | PDF summary of terms' diary for parents' record; printable. |
| 142 | PAGE 07 — HOMEWORK & CLASS DIARY | Tab 7.4 — Parent & Student View | Child homework list | pending/done/due-soon cards; "Mark done" creates parent-visible confirmation. 🔔 |
| 143 | PAGE 07 — HOMEWORK & CLASS DIARY | Tab 7.4 — Parent & Student View | Digital copy on leave | if student on leave, homework bundle auto-emailed + app-shown; resume-able. 🔔 |
| 144 | PAGE 08 — TIMETABLE | Tab 8.1 — Weekly Table | Role-aware grid | teacher: My periods; student: My classes; parent: child's classes (no teacher names). |
| 145 | PAGE 08 — TIMETABLE | Tab 8.1 — Weekly Table | Day/class switch | jump day or class; legend for subject colors; print view per class. |
| 146 | PAGE 08 — TIMETABLE | Tab 8.1 — Weekly Table | Publish flow | draft → review → publish → all get notification; old version archived. 🔔 |
| 147 | PAGE 08 — TIMETABLE | Tab 8.2 — Editor (admin/principal) | Drag-drop builder | place subjects into class-period cells; live conflict warnings (teacher double-booked, room clashes). 🤖 |
| 148 | PAGE 08 — TIMETABLE | Tab 8.2 — Editor (admin/principal) | 🤖 Auto-suggest layout | AI proposes balanced timetable (contiguous free periods, workload fair split). |
| 149 | PAGE 08 — TIMETABLE | Tab 8.2 — Editor (admin/principal) | Substitute view | swap teacher for a day/hour; affected students/parents notified. 🔔 |
| 150 | PAGE 08 — TIMETABLE | Tab 8.2 — Editor (admin/principal) | Room management | labs/gyms/auditorium booking on the same grid; booking overlap check. 🤖 |
| 151 | PAGE 08 — TIMETABLE | Tab 8.2 — Editor (admin/principal) | Holiday/weekend overrides | mark special days (PTA meet, exam days) → timetable rows greyed with reason. |
| 152 | PAGE 09 — TEACHERS & STAFF | Tab 9.1 — Staff List | Staff directory | search by name/subject/class; filter by department, join year, leaving soon. |
| 153 | PAGE 09 — TEACHERS & STAFF | Tab 9.1 — Staff List | Profile card | qualification, subjects, classes, contact, joining, documents, total experience bar. |
| 154 | PAGE 09 — TEACHERS & STAFF | Tab 9.1 — Staff List | Row actions | edit profile, timetables, leaves, mark-assets (laptop/books), send message. |
| 155 | PAGE 09 — TEACHERS & STAFF | Tab 9.1 — Staff List | Import/export | bulk add staff via CSV; export directory card sheet. |
| 156 | PAGE 09 — TEACHERS & STAFF | Tab 9.2 — Workload & Course Matrix 🟣 (director's matrix) | Teacher Load Board | weekly periods, classes, subjects per teacher; overload/underload balance visual. |
| 157 | PAGE 09 — TEACHERS & STAFF | Tab 9.2 — Workload & Course Matrix 🟣 (director's matrix) | Course Completion Matrix | % of chapters taught vs plan per teacher per class; green=on-time, red=delayed. |
| 158 | PAGE 09 — TEACHERS & STAFF | Tab 9.2 — Workload & Course Matrix 🟣 (director's matrix) | 🤖 AI Efficiency insight | completion trends, substitution load, attendance pattern summary per teacher. |
| 159 | PAGE 09 — TEACHERS & STAFF | Tab 9.3 — Leave & Substitute | Apply leave (teacher) | date/type/substitute need; approval chain CT→Principal; substitute assignment. 🔔 |
| 160 | PAGE 09 — TEACHERS & STAFF | Tab 9.3 — Leave & Substitute | Approval board (principal) | approve/reject; auto-finds substitute from free slots list. 🤖 |
| 161 | PAGE 09 — TEACHERS & STAFF | Tab 9.3 — Leave & Substitute | Leave balance | CL/SL/PL per policy; used-remaining bars; year rollover rules applied. |
| 162 | PAGE 09 — TEACHERS & STAFF | Tab 9.3 — Leave & Substitute | Substitute notify | chosen teacher + affected class rolls notified immediately on approval. 🔔 |
| 163 | PAGE 09 — TEACHERS & STAFF | Tab 9.4 — Performance & Review | Review cycle | HOD/principal criteria forms (teaching quality, completion, attendance, parent feedback). |
| 164 | PAGE 09 — TEACHERS & STAFF | Tab 9.4 — Performance & Review | Parent feedback | anonymous ratings (star 1-5) summarised; AI summarises comments into action points. 🤖 |
| 165 | PAGE 09 — TEACHERS & STAFF | Tab 9.4 — Performance & Review | Appreciation & warning log | principal posts entries visible in teacher profile only to admin/principal. |
| 166 | PAGE 10 — PAYROLL / PAYSLIP 🟩 | Tab 10.1 — Salary Structure | Structure builder | basic, HRA, DA, allowances, deductions (PF, PT, TDS, advance); gross/net computation live. |
| 167 | PAGE 10 — PAYROLL / PAYSLIP 🟩 | Tab 10.1 — Salary Structure | Add-ons | bonus, overtime, transport, exam-duty pay with date scope; prorated monthly. |
| 168 | PAGE 10 — PAYROLL / PAYSLIP 🟩 | Tab 10.1 — Salary Structure | Salary revisions | effective-date revisions with history; approval flow; teacher notified on applied. 🔔 |
| 169 | PAGE 10 — PAYROLL / PAYSLIP 🟩 | Tab 10.2 — Month Processing | Run month | one-click "process March": attendance-influenced days, leaves, arrears auto-computed. 🤖 sanity-check |
| 170 | PAGE 10 — PAYROLL / PAYSLIP 🟩 | Tab 10.2 — Month Processing | 🤖 AI mismatch check | flags absent-day vs full-salary conflicts, duplicate pay, TDS anomalies before lock. |
| 171 | PAGE 10 — PAYROLL / PAYSLIP 🟩 | Tab 10.2 — Month Processing | Pay run rollback | un-posted runs can be re-opened; all changes logged; posting locks pages. |
| 172 | PAGE 10 — PAYROLL / PAYSLIP 🟩 | Tab 10.3 — Payslips | Payslip view | elegant print PDF: earnings/deductions/net, arrears, YTD table; watermark "draft/paid". |
| 173 | PAGE 10 — PAYROLL / PAYSLIP 🟩 | Tab 10.3 — Payslips | Teacher self-service | My Payslips list, download, PDF viewer, "claim missing month" ticket auto-created. |
| 174 | PAGE 10 — PAYROLL / PAYSLIP 🟩 | Tab 10.3 — Payslips | Register export | PDF/Excel per class of staff; bank-file export (INR format columns) for uploads. |
| 175 | PAGE 10 — PAYROLL / PAYSLIP 🟩 | Tab 10.3 — Payslips | Advance/loan tracker | sanction advance, EMI deduction chips, balance in payslip column. |
| 176 | PAGE 11 — FINANCE (Fees, Receipts, Budgets) 🟩 | Tab 11.1 — Fee Collection | Fee structure builder | heads (tuition, transport, hostel, id-card, uniform); one-time vs recurring; slab by class. |
| 177 | PAGE 11 — FINANCE (Fees, Receipts, Budgets) 🟩 | Tab 11.1 — Fee Collection | Collect fee (counter or portal) | select student → dues as on date → cash/card/UPI/cheque → instant receipt. |
| 178 | PAGE 11 — FINANCE (Fees, Receipts, Budgets) 🟩 | Tab 11.1 — Fee Collection | Receipt viewer | receipt no/date/mode/tax breakdown; PDF download; reprint allowed (audited); mail + WhatsApp. 🔔 |
| 179 | PAGE 11 — FINANCE (Fees, Receipts, Budgets) 🟩 | Tab 11.1 — Fee Collection | Family & sibling discount | auto-apply per policy on linked children; seen before payment. 🤖 verify |
| 180 | PAGE 11 — FINANCE (Fees, Receipts, Budgets) 🟩 | Tab 11.1 — Fee Collection | Part-pay & overdue rules | record part-payment, late-fee auto-rule, waiver requests with approval chain. |
| 181 | PAGE 11 — FINANCE (Fees, Receipts, Budgets) 🟩 | Tab 11.2 — Dues & Recovery | Dues ledger | per class drill: who owes what; sort by age; export recovery letter batch. |
| 182 | PAGE 11 — FINANCE (Fees, Receipts, Budgets) 🟩 | Tab 11.2 — Dues & Recovery | 🤖 AI risk forecast | flags families likely to default (pattern-based) for early soft reminder. |
| 183 | PAGE 11 — FINANCE (Fees, Receipts, Budgets) 🟩 | Tab 11.2 — Dues & Recovery | Reminder campaign | send polite email/WhatsApp/SMS in waves (L1=L2=L3) with template control. 🔔 |
| 184 | PAGE 11 — FINANCE (Fees, Receipts, Budgets) 🟩 | Tab 11.2 — Dues & Recovery | Restricted access notes | fee-blocked tag on report card/transcripts; visible only to finance/admin. |
| 185 | PAGE 11 — FINANCE (Fees, Receipts, Budgets) 🟩 | Tab 11.3 — Expenses & Budget | Expense entry | vendor, head, amount, bill upload, approve chain (accountant → director). |
| 186 | PAGE 11 — FINANCE (Fees, Receipts, Budgets) 🟩 | Tab 11.3 — Expenses & Budget | Budget vs actual | month & head: forecast bars; variance flagged. |
| 187 | PAGE 11 — FINANCE (Fees, Receipts, Budgets) 🟩 | Tab 11.3 — Expenses & Budget | Voucher & reconciliation | receipt-vs-bank statement check; pending match list. |
| 188 | PAGE 11 — FINANCE (Fees, Receipts, Budgets) 🟩 | Tab 11.4 — Reports (director's revenue page) | Collection reports | daily/term/year; per head/per class; cash vs digital split chart. |
| 189 | PAGE 11 — FINANCE (Fees, Receipts, Budgets) 🟩 | Tab 11.4 — Reports (director's revenue page) | 🤖 Revenue forecast | LLM/numeric: projection of next 3 months with assumptions; scenario slider. |
| 190 | PAGE 11 — FINANCE (Fees, Receipts, Budgets) 🟩 | Tab 11.4 — Reports (director's revenue page) | P&L summary | income minus expense per term; simple chart; export board Excel & PDF. |
| 191 | PAGE 11 — FINANCE (Fees, Receipts, Budgets) 🟩 | Tab 11.4 — Reports (director's revenue page) | Parent pay page | guardian opens Fees → sees balance → pays online → receipt auto-stored; both sides notified. 🔔 |
| 192 | PAGE 12 — LIBRARY | Tab 12.1 — Catalogue & Search | Book catalog | grid/list with cover, author, isbn, rack, copies; advanced filters + fuzzy search (debounced). |
| 193 | PAGE 12 — LIBRARY | Tab 12.1 — Catalogue & Search | 🤖 AI recommendation | "books for a Class-5 sci-fi lover" → suggestions from catalog + reading level match. |
| 194 | PAGE 12 — LIBRARY | Tab 12.1 — Catalogue & Search | Book create/import | single add, CSV import, aisle/rack codes; duplicate ISBN check. |
| 195 | PAGE 12 — LIBRARY | Tab 12.2 — Issue / Return | Issue desk | scan/type student + ISBN → issue; due date auto (policy days); copy availability live. |
| 196 | PAGE 12 — LIBRARY | Tab 12.2 — Issue / Return | Return desk | scan return, auto fine calc (late-fee rule), condition note icons (new/good/worn). |
| 197 | PAGE 12 — LIBRARY | Tab 12.2 — Issue / Return | Member cards | temporary cards for guests/teachers; card status; overdue block rules. |
| 198 | PAGE 12 — LIBRARY | Tab 12.2 — Issue / Return | Reserve & hold | student reserves a hot book; liber prims pickup queue + notify when ready. 🔔 |
| 199 | PAGE 12 — LIBRARY | Tab 12.3 — Overdues & Notices | Overdue list | auto list + email/WhatsApp reminder waves; parent gets child's overdue summary. 🔔 |
| 200 | PAGE 12 — LIBRARY | Tab 12.3 — Overdues & Notices | Damaged/lost | mark lost with price deduction flow (attached to finance), replace order flag. |
| 201 | PAGE 12 — LIBRARY | Tab 12.3 — Overdues & Notices | Book usage stats | top books, low-usage sections; purchase suggestions generated. 🤖 |
| 202 | PAGE 13 — TRANSPORT | Tab 13.1 — Routes & Stops | Route builder | stops, sequence, distance, bus id, capacity; route fee auto-linked to child bills. 🟩 |
| 203 | PAGE 13 — TRANSPORT | Tab 13.1 — Routes & Stops | Stop management | geo-tagging stops (map picker), time table per stop, headcount per stop. |
| 204 | PAGE 13 — TRANSPORT | Tab 13.1 — Routes & Stops | 🤖 AI route optimization | suggests stop-order tweaks to cut km & time; save time auto-applied with approval. |
| 205 | PAGE 13 — TRANSPORT | Tab 13.1 — Routes & Stops | Print route slips | authority slip per student for conductor/driver records. |
| 206 | PAGE 13 — TRANSPORT | Tab 13.2 — Buses & GPS | Bus registry | number, capacity, driver, attendant, route, fitness-validity alerts. 🔔 |
| 207 | PAGE 13 — TRANSPORT | Tab 13.2 — Buses & GPS | Live tracking | GPS pins per bus on map; ETA cards; parent sees child's bus ETA. (mobile-first) |
| 208 | PAGE 13 — TRANSPORT | Tab 13.2 — Buses & GPS | Trip journal | morning/evening pickup logs per student; missed-stop handled with advice; parent notified if not boarded. 🔔 |
| 209 | PAGE 13 — TRANSPORT | Tab 13.2 — Buses & GPS | Emergency | SOS button logs + mass-notifies parents/driver/principal on route incident. |
| 210 | PAGE 13 — TRANSPORT | Tab 13.3 — Transport Fees & Enforcement | Fee integration | transport add-on appears on child's fee bill; non-payment → service hold workflow. 🟩 |
| 211 | PAGE 13 — TRANSPORT | Tab 13.3 — Transport Fees & Enforcement | Boarding rules | strip photo, route-switch requests, temporary halt (by leave) with approval from transport office. |
| 212 | PAGE 14 — TICKETS & SUPPORT (Escalation Chain) 🟥 | Tab 14.1 — Raise a Ticket | One-click raise | issue type list (fee, marks, behaviour, homework, transport, library, technical, "other"). |
| 213 | PAGE 14 — TICKETS & SUPPORT (Escalation Chain) 🟥 | Tab 14.1 — Raise a Ticket | Who can I raise to? | pick target: subject teacher, class teacher, principal, director (chain rules enforced). |
| 214 | PAGE 14 — TICKETS & SUPPORT (Escalation Chain) 🟥 | Tab 14.1 — Raise a Ticket | AI helper | 🤖 pre-filled description suggestions + auto-category from keywords; attach image/PDF/proof. |
| 215 | PAGE 14 — TICKETS & SUPPORT (Escalation Chain) 🟥 | Tab 14.1 — Raise a Ticket | Priority selection | normal / urgent / critical (critical auto-pings principal + director). 🔔 |
| 216 | PAGE 14 — TICKETS & SUPPORT (Escalation Chain) 🟥 | Tab 14.1 — Raise a Ticket | Request+track duplicate | AI matches similar open tickets and suggests linking to reduce repeats. 🤖 |
| 217 | PAGE 14 — TICKETS & SUPPORT (Escalation Chain) 🟥 | Tab 14.2 — My Tickets (role-appropriate state) | Tracker view | status chips: opened → assigned → in-progress → awaiting-answer → resolved → closed. |
| 218 | PAGE 14 — TICKETS & SUPPORT (Escalation Chain) 🟥 | Tab 14.2 — My Tickets (role-appropriate state) | Threaded replies | conversation per ticket with attachments, previous action history, SLA clock per row. |
| 219 | PAGE 14 — TICKETS & SUPPORT (Escalation Chain) 🟥 | Tab 14.2 — My Tickets (role-appropriate state) | Reopen / feedback | mark resolved→ rate resolution; reopen auto-escalates one level up. 🔔 |
| 220 | PAGE 14 — TICKETS & SUPPORT (Escalation Chain) 🟥 | Tab 14.2 — My Tickets (role-appropriate state) | Related-entity link | ticket auto-links to student/marks/attendance record for instant context jump. |
| 221 | PAGE 14 — TICKETS & SUPPORT (Escalation Chain) 🟥 | Tab 14.3 — Support Inbox (teachers/principal/director) | Queue view | filters: mine, team, unassigned, owe-one, urgent; bulk actions (assign, close, snooze). |
| 222 | PAGE 14 — TICKETS & SUPPORT (Escalation Chain) 🟥 | Tab 14.3 — Support Inbox (teachers/principal/director) | Assignment | auto/smart assign by subject-match to teacher; manual override with audit. 🤖 |
| 223 | PAGE 14 — TICKETS & SUPPORT (Escalation Chain) 🟥 | Tab 14.3 — Support Inbox (teachers/principal/director) | Escalation rules | no reply in 24h → principal CC; 48h → director; auto-notify both on critical. 🔔 |
| 224 | PAGE 14 — TICKETS & SUPPORT (Escalation Chain) 🟥 | Tab 14.3 — Support Inbox (teachers/principal/director) | Resolution notes | teach leave visible to raiser; parent gets notification on resolution. 🔔 |
| 225 | PAGE 14 — TICKETS & SUPPORT (Escalation Chain) 🟥 | Tab 14.3 — Support Inbox (teachers/principal/director) | SLA dashboard | P95 response times, backlogs, most-complained categories (top3 for director). 🤖 |
| 226 | PAGE 14 — TICKETS & SUPPORT (Escalation Chain) 🟥 | Tab 14.4 — Director / Principal Oversight | Escalated view | every ticket at their level with parent/student context, history, aging bar. |
| 227 | PAGE 14 — TICKETS & SUPPORT (Escalation Chain) 🟥 | Tab 14.4 — Director / Principal Oversight | Decide & delegate | comment, send-back, assign-investigation, "resolved" with final note; all audited. |
| 228 | PAGE 15 — MEETINGS (Parent–Teacher Scheduling) 🟫 | Tab 15.1 — Teacher Slot Manager | Availability grid | teacher publishes open slots (day/time/duration, in-person or video). |
| 229 | PAGE 15 — MEETINGS (Parent–Teacher Scheduling) 🟫 | Tab 15.1 — Teacher Slot Manager | Slot types | open-parent, requested-only, urgent-parent; auto-block exam/weekend rules. |
| 230 | PAGE 15 — MEETINGS (Parent–Teacher Scheduling) 🟫 | Tab 15.1 — Teacher Slot Manager | 🤖 AI conflict check | overlapping own-class duties flagged; "smart slots" suggestions on low fill rates. |
| 231 | PAGE 15 — MEETINGS (Parent–Teacher Scheduling) 🟫 | Tab 15.2 — Parent Booking | Pick teacher + slot | calendar picker shows free times; watch conflicts with your other child's meetings. |
| 232 | PAGE 15 — MEETINGS (Parent–Teacher Scheduling) 🟫 | Tab 15.2 — Parent Booking | Instant confirmation | booking creates meeting card + calendar (.ics) + join link; both notified. 🔔 |
| 233 | PAGE 15 — MEETINGS (Parent–Teacher Scheduling) 🟫 | Tab 15.2 — Parent Booking | Reschedule handling | cancel/rebook with notice; teacher change emits new link; parent notified again. 🔔 |
| 234 | PAGE 15 — MEETINGS (Parent–Teacher Scheduling) 🟫 | Tab 15.2 — Parent Booking | 🤖 AI suggested agenda | booking notes suggest topics from child data (attendance dip, marks, fee) for brevity. |
| 235 | PAGE 15 — MEETINGS (Parent–Teacher Scheduling) 🟫 | Tab 15.3 — Meeting Room & Reminders | Pre-meeting sheet | teacher side: student snapshot card (marks, attendance, diary, previous meeting notes). |
| 236 | PAGE 15 — MEETINGS (Parent–Teacher Scheduling) 🟫 | Tab 15.3 — Meeting Room & Reminders | Video button / join link | one-tap join (WebRTC/Meet); duration guard alerts; session notes saved to student. |
| 237 | PAGE 15 — MEETINGS (Parent–Teacher Scheduling) 🟫 | Tab 15.3 — Meeting Room & Reminders | Reminder cascade | 🔔 24h and 15-min auto reminders; missed-meeting follow-up link re-book. |
| 238 | PAGE 15 — MEETINGS (Parent–Teacher Scheduling) 🟫 | Tab 15.3 — Meeting Room & Reminders | Post-meeting action | teacher adds follow-ups (test targets, parent to-do) visible to parent; parent can ack. |
| 239 | PAGE 15 — MEETINGS (Parent–Teacher Scheduling) 🟫 | Tab 15.4 — Meeting History & Analytics | Parent history | past meetings with summary + agreed actions; "meeting with all teachers" parent-day flow. |
| 240 | PAGE 15 — MEETINGS (Parent–Teacher Scheduling) 🟫 | Tab 15.4 — Meeting History & Analytics | 🤖 Insights for principal | participation rates, absence-attennance, teacher slot utilization, feedback ratings. |
| 241 | PAGE 16 — NOTIFICATIONS CENTER 🔔 | Tab 16.1 — Live Feed | Unified inbox | every module pushes here: attendance, homework, fees, tickets, meetings, exams, leave. |
| 242 | PAGE 16 — NOTIFICATIONS CENTER 🔔 | Tab 16.1 — Live Feed | Real-time stream | WebSocket push for new items (no refresh); sound + desktop toast for priority ones. |
| 243 | PAGE 16 — NOTIFICATIONS CENTER 🔔 | Tab 16.1 — Live Feed | Filter chips | All / Unread / Mentions / System / Alerts; per-module toggle (mute homework, keep fees). |
| 244 | PAGE 16 — NOTIFICATIONS CENTER 🔔 | Tab 16.1 — Live Feed | Read state | unread badge with count on bell; "mark all read"; per-item read/unread; read-receipt on critical. |
| 245 | PAGE 16 — NOTIFICATIONS CENTER 🔔 | Tab 16.2 — Targeted & Important Alerts | Role-driven highlights | teacher sees absent-substitute, HOD sees paper-review, parent sees child-absence. |
| 246 | PAGE 16 — NOTIFICATIONS CENTER 🔔 | Tab 16.2 — Targeted & Important Alerts | Priority banner | critical (incident, unresolved escalation) pinned top in red with accept button. 🟥 |
| 247 | PAGE 16 — NOTIFICATIONS CENTER 🔔 | Tab 16.2 — Targeted & Important Alerts | Snooze & schedule | reminders snooze to lunch / tomorrow; import into calendar (.ics). |
| 248 | PAGE 16 — NOTIFICATIONS CENTER 🔔 | Tab 16.2 — Targeted & Important Alerts | Notification rules | user controls channels per event: in-app / email / WhatsApp / SMS / push-device. |
| 249 | PAGE 16 — NOTIFICATIONS CENTER 🔔 | Tab 16.3 — Broadcasts & Announcements | School broadcast | principal/admin posts to role/class/whole-school; mandatory-read tracking for urgent ones. 🔔 |
| 250 | PAGE 16 — NOTIFICATIONS CENTER 🔔 | Tab 16.3 — Broadcasts & Announcements | Draft & schedule | compose rich notice (image/PDF link), schedule future send, target audience picker. |
| 251 | PAGE 16 — NOTIFICATIONS CENTER 🔔 | Tab 16.3 — Broadcasts & Announcements | Delivery report | see delivered/read stats; reminder pulse to non-readers (policy-safe times only). |
| 252 | PAGE 16 — NOTIFICATIONS CENTER 🔔 | Tab 16.3 — Broadcasts & Announcements | 🤖 AI rewrite assist | turns bullet points into a warm, clear notice; parent-friendly language option. |
| 253 | PAGE 16 — NOTIFICATIONS CENTER 🔔 | Tab 16.4 — Notifications for Absent/Parent | Absence instant-alert | day: class-teacher mark = absence → parent gets "Your child is absent today" in <1 min. |
| 254 | PAGE 16 — NOTIFICATIONS CENTER 🔔 | Tab 16.4 — Notifications for Absent/Parent | Leave auto-ack | approved/rejected leave also pushes; no double-ping when leave already pre-approved. 🔔 |
| 255 | PAGE 16 — NOTIFICATIONS CENTER 🔔 | Tab 16.4 — Notifications for Absent/Parent | Parent digest | one-tap "Today summary for my child" (attendance, homework, events) generated daily. 🤖 |
| 256 | PAGE 17 — CHAT & COMMUNICATION 🟦 | Tab 17.1 — Conversations | Thread list | 1:1 & group threads ordered by last message; unread badges; search across messages. |
| 257 | PAGE 17 — CHAT & COMMUNICATION 🟦 | Tab 17.1 — Conversations | Trusted-links only | parent ⇄ class teacher, parent ⇄ subject teacher, student ⇄ own class group, staff groups. |
| 258 | PAGE 17 — CHAT & COMMUNICATION 🟦 | Tab 17.1 — Conversations | Group spaces | per class, per staff dept, per subject team; who-can-post rules per space. |
| 259 | PAGE 17 — CHAT & COMMUNICATION 🟦 | Tab 17.1 — Conversations | Read receipts | single/double ticks; "delivered vs read"; mute per thread; pinned messages. |
| 260 | PAGE 17 — CHAT & COMMUNICATION 🟦 | Tab 17.2 — Messaging Features | Attachments | images, PDFs, voice notes (mobile), whiteboard link; 25MB limit with preview. |
| 261 | PAGE 17 — CHAT & COMMUNICATION 🟦 | Tab 17.2 — Messaging Features | Rich compose | emoji, quick replies chips ("Okay", "Noted"), scheduled send (staff only). |
| 262 | PAGE 17 — CHAT & COMMUNICATION 🟦 | Tab 17.2 — Messaging Features | Official badge | official announcements marked (can't alter); PIN code verify for sensitive info (fee details). |
| 263 | PAGE 17 — CHAT & COMMUNICATION 🟦 | Tab 17.2 — Messaging Features | Code / link safety | auto-warn links & attachments via safe-link checker before opening. 🤖 |
| 264 | PAGE 17 — CHAT & COMMUNICATION 🟦 | Tab 17.2 — Messaging Features | Moderation lite | offensive-word filter with soft-censor; report message → auto-ticket to principal. 🤖 🔔 |
| 265 | PAGE 17 — CHAT & COMMUNICATION 🟦 | Tab 17.3 — In-Context Chats | Row-to-chat jump | every entity (student, class, ticket, paper) has "Open chat" with its related people. |
| 266 | PAGE 17 — CHAT & COMMUNICATION 🟦 | Tab 17.3 — In-Context Chats | Ticket thread vs chat | tickets stay structured; chat is informal — auto-suggest "Convert to ticket" on issue words. 🤖 |
| 267 | PAGE 17 — CHAT & COMMUNICATION 🟦 | Tab 17.3 — In-Context Chats | Class-wide notes | teacher pins "No class tomorrow — Assembly" as chat-wide notice + notification. |
| 268 | PAGE 18 — LEAVE & APPLICATIONS (Students/Parents) 🟦 | Tab 18.1 — 🤖 AI Application Generator | Smart form | pick child, date-range, reason-type (medical, family, event, travel) → AI drafts full application. 🤖 |
| 269 | PAGE 18 — LEAVE & APPLICATIONS (Students/Parents) 🟦 | Tab 18.1 — 🤖 AI Application Generator | 🤖 Auto-parameters | suggested dates fit school calendar (exams/holidays auto-warned), duration auto-calculated. |
| 270 | PAGE 18 — LEAVE & APPLICATIONS (Students/Parents) 🟦 | Tab 18.1 — 🤖 AI Application Generator | Customize freely | edit AI text, add formal-family language, insert attachments (doctor note), save as template. |
| 271 | PAGE 18 — LEAVE & APPLICATIONS (Students/Parents) 🟦 | Tab 18.1 — 🤖 AI Application Generator | Free text mode | write completely your own application; AI only checks clarity + missing dates. 🤖 |
| 272 | PAGE 18 — LEAVE & APPLICATIONS (Students/Parents) 🟦 | Tab 18.1 — 🤖 AI Application Generator | Format picker | formal letter / simple note / medical-style variants for principal or class teacher. |
| 273 | PAGE 18 — LEAVE & APPLICATIONS (Students/Parents) 🟦 | Tab 18.2 — Apply & Track | Submit | choose approver (CT for short, Principal for >3 days); one-tap submit; instant ack. 🔔 |
| 274 | PAGE 18 — LEAVE & APPLICATIONS (Students/Parents) 🟦 | Tab 18.2 — Apply & Track | Status timeline | chips: submitted → approved / rejected / needs-more-info; comment history. |
| 275 | PAGE 18 — LEAVE & APPLICATIONS (Students/Parents) 🟦 | Tab 18.2 — Apply & Track | Withdraw / amend | pending ones editable; approved ones need unapprove request (class teacher). |
| 276 | PAGE 18 — LEAVE & APPLICATIONS (Students/Parents) 🟦 | Tab 18.2 — Apply & Track | Attendance tie-in | approved leave auto-fills attendance as "Leave" and never "Absent"; parent dashboard shows both. 🔔 |
| 277 | PAGE 18 — LEAVE & APPLICATIONS (Students/Parents) 🟦 | Tab 18.3 — Approver Side (class teacher / principal) | Approval queue | student + staff leave side by side; see attendance % before deciding; one-click resolve. |
| 278 | PAGE 18 — LEAVE & APPLICATIONS (Students/Parents) 🟦 | Tab 18.3 — Approver Side (class teacher / principal) | Bulk approve | same-day routine leaves in batch (configurable); comment field optional but recommended. |
| 279 | PAGE 18 — LEAVE & APPLICATIONS (Students/Parents) 🟦 | Tab 18.3 — Approver Side (class teacher / principal) | Policy engine | auto-enforce max-continuous-days rules, exam-period blackout, min-notice; bypass needs approval. 🤖 |
| 280 | PAGE 18 — LEAVE & APPLICATIONS (Students/Parents) 🟦 | Tab 18.3 — Approver Side (class teacher / principal) | Substitute/coverage hint | for teacher leave: suggested substitute from free periods shown. 🤖 |
| 281 | PAGE 18 — LEAVE & APPLICATIONS (Students/Parents) 🟦 | Tab 18.4 — Staff Leave (teacher) | Balance card | CL/SL/PL/OD used+remaining with year rules; carry-over summary. |
| 282 | PAGE 18 — LEAVE & APPLICATIONS (Students/Parents) 🟦 | Tab 18.4 — Staff Leave (teacher) | Apply & chain | leave requests route per policy (class-coverage aware); approved ones auto-broadcast. 🔔 |
| 283 | PAGE 18 — LEAVE & APPLICATIONS (Students/Parents) 🟦 | Tab 18.4 — Staff Leave (teacher) | OD duty slips | official-duty/OD application for events, workshops; PDF slip generated for records. |
| 284 | PAGE 19 — REPORTS & ANALYTICS 📊 | Tab 19.1 — Report Builder | Pick template | report card, attendance register, fee statement, teacher matrix, class summary, custom. |
| 285 | PAGE 19 — REPORTS & ANALYTICS 📊 | Tab 19.1 — Report Builder | Parameters | scope (class/term/student), columns, format; preview live before export. |
| 286 | PAGE 19 — REPORTS & ANALYTICS 📊 | Tab 19.1 — Report Builder | Export engine | PDF (print-ready), Excel, CSV, zipped batch; schedule recurring email share. 🔔 |
| 287 | PAGE 19 — REPORTS & ANALYTICS 📊 | Tab 19.1 — Report Builder | 🤖 Narrative report | AI writes executive summary with numbers + recommendations (editable before send). |
| 288 | PAGE 19 — REPORTS & ANALYTICS 📊 | Tab 19.2 — Director Command Center | School KPIs page | enrollment trends, revenue health, attendance %, results, teacher matrix — all one screen. |
| 289 | PAGE 19 — REPORTS & ANALYTICS 📊 | Tab 19.2 — Director Command Center | Compare & drill | period over period, class vs class, term vs term; table-to-chart toggle. |
| 290 | PAGE 19 — REPORTS & ANALYTICS 📊 | Tab 19.2 — Director Command Center | 🤖 Forecast widgets | next-term enrolment, fee collection, exam-pass trend; scenario toggles. |
| 291 | PAGE 19 — REPORTS & ANALYTICS 📊 | Tab 19.2 — Director Command Center | Auto weekly PDF | scheduled digest to director/principal mailbox every Friday. 🔔 |
| 292 | PAGE 19 — REPORTS & ANALYTICS 📊 | Tab 19.3 — Education-Specific | Board performance | subject-public averages across classes; weakest topics per subject. 🤖 |
| 293 | PAGE 19 — REPORTS & ANALYTICS 📊 | Tab 19.3 — Education-Specific | Teacher workload matrix | periods, classes, completion rate, substitution count per teacher. |
| 294 | PAGE 19 — REPORTS & ANALYTICS 📊 | Tab 19.3 — Education-Specific | Student cohort analysis | same-cohort progress from Grade 1→8; dropoff flags; growth charts. |
| 295 | PAGE 19 — REPORTS & ANALYTICS 📊 | Tab 19.3 — Education-Specific | Library & transport usage | borrowed books, bus occupancy %, route delays summary. |
| 296 | PAGE 19 — REPORTS & ANALYTICS 📊 | Tab 19.4 — Data Quality & Exports | Missing-data radar | students without photo, pending marks entries, unassigned teachers — one screen. 🤖 |
| 297 | PAGE 19 — REPORTS & ANALYTICS 📊 | Tab 19.4 — Data Quality & Exports | Full backup export | JSON dump export to admin (PII flagged); GDPR-style deletion request queue. |
| 298 | PAGE 20 — AI COPILOT (Global Assistant) | Tab 20.1 — Command Palette (⌘K / Ctrl-K) | Universal search | students, teachers, books, tickets, classes, pages; fuzzy + instant results. |
| 299 | PAGE 20 — AI COPILOT (Global Assistant) | Tab 20.1 — Command Palette (⌘K / Ctrl-K) | Action shortcuts | "Mark attendance 7A", "Generate maths paper", "Open fee page Rahul" → direct jumps. |
| 300 | PAGE 20 — AI COPILOT (Global Assistant) | Tab 20.1 — Command Palette (⌘K / Ctrl-K) | Recent & starred | remembers frequent searches/pages; favourite actions pinned to top. |
| 301 | PAGE 20 — AI COPILOT (Global Assistant) | Tab 20.2 — 🤖 Ask EduVerse AI | Scope-aware chat | parent asks "my child's progress", teacher asks "my class attendance this week" — answers from their data only. |
| 302 | PAGE 20 — AI COPILOT (Global Assistant) | Tab 20.2 — 🤖 Ask EduVerse AI | 🤖 Actionable replies | offer buttons: "Create report", "Send parent nudge", "Book meeting" — generated right from the answer. |
| 303 | PAGE 20 — AI COPILOT (Global Assistant) | Tab 20.2 — 🤖 Ask EduVerse AI | Data-grounded | every answer shows source links (which report/record it used); no guessing. |
| 304 | PAGE 20 — AI COPILOT (Global Assistant) | Tab 20.2 — 🤖 Ask EduVerse AI | Role policy guard | restricts subjects AI may speak about per role; PII never revealed cross-role. |
| 305 | PAGE 20 — AI COPILOT (Global Assistant) | Tab 20.3 — Genius Assistant (contextual) | Inline help | any page has "Explain this screen" → AI walks through the features in that tab. 🤖 |
| 306 | PAGE 20 — AI COPILOT (Global Assistant) | Tab 20.3 — Genius Assistant (contextual) | 🤖 Auto-cleanups | sees pagination garbage? offers "Merge duplicate students" with preview before run. |
| 307 | PAGE 20 — AI COPILOT (Global Assistant) | Tab 20.3 — Genius Assistant (contextual) | Form helper | AI pre-fills long forms from natural text: "Rahul, 7A, father Ramesh, phone 98…". |
| 308 | PAGE 20 — AI COPILOT (Global Assistant) | Tab 20.3 — Genius Assistant (contextual) | Language | answers in Eng / Hindi / regional language selected in settings (RTL ready). |
| 309 | PAGE 20 — AI COPILOT (Global Assistant) | Tab 20.4 — Automation Recipes | Recipe templates | "Daily: remind pending homework", "Friday: parent digest", "Exam-day: paper reminders". |
| 310 | PAGE 20 — AI COPILOT (Global Assistant) | Tab 20.4 — Automation Recipes | 🤖 Suggest recipes | AI watches patterns and suggests new automations (e.g., "Notify when 3 absences hit"). |
| 311 | PAGE 20 — AI COPILOT (Global Assistant) | Tab 20.4 — Automation Recipes | Run logs | every automation's runs & outcomes listed; pause/edit/delete with approval log. |
| 312 | PAGE 21 — SETTINGS & CONFIGURATION | Tab 21.1 — Users & Roles | User management | create/edit users, reset passwords (OTP), deactivate, assign roles + classes. |
| 313 | PAGE 21 — SETTINGS & CONFIGURATION | Tab 21.1 — Users & Roles | Role composer | build/limit role chips from permission catalogue (backend permission codes). |
| 314 | PAGE 21 — SETTINGS & CONFIGURATION | Tab 21.1 — Users & Roles | Permission matrix | page × role grid with checkboxes; duplicates of backend `role_permissions` visible. |
| 315 | PAGE 21 — SETTINGS & CONFIGURATION | Tab 21.1 — Users & Roles | Invite management | issue/revoke invite tokens; resend; expiry list. |
| 316 | PAGE 21 — SETTINGS & CONFIGURATION | Tab 21.2 — School Profile | School info | name, logo, address, contact, term structure (April/March), working days, holidays sync. |
| 317 | PAGE 21 — SETTINGS & CONFIGURATION | Tab 21.2 — School Profile | Fee structure | heads & amounts per class; discount rules; late-fee & waiver policies. |
| 318 | PAGE 21 — SETTINGS & CONFIGURATION | Tab 21.2 — School Profile | Academic config | classes/sections/subjects mapping, grading scheme, report-card layout picker. |
| 319 | PAGE 21 — SETTINGS & CONFIGURATION | Tab 21.2 — School Profile | Notification defaults | channel per category (in-app/email/WhatsApp/SMS), quiet hours, language. |
| 320 | PAGE 21 — SETTINGS & CONFIGURATION | Tab 21.3 — Audit & Security | Audit log viewer | search by user, entity, action, date range; export CSV; auto-archive triggers. |
| 321 | PAGE 21 — SETTINGS & CONFIGURATION | Tab 21.3 — Audit & Security | 2FA state | who has 2FA on/off; force-enable for admins; recovery-code reset. |
| 322 | PAGE 21 — SETTINGS & CONFIGURATION | Tab 21.3 — Audit & Security | Rate-limit & session policy | login attempts, session lengths, kiosk rules per device group. |
| 323 | PAGE 21 — SETTINGS & CONFIGURATION | Tab 21.3 — Audit & Security | Data retention | retention windows per record type; PII masking preview; deletion requests queue. |
| 324 | PAGE 21 — SETTINGS & CONFIGURATION | Tab 21.4 — Integrations & Preferences | WhatsApp / SMS / Email | gateway status, templates, test-send button, daily send quotas. |
| 325 | PAGE 21 — SETTINGS & CONFIGURATION | Tab 21.4 — Integrations & Preferences | Payment gateway | enabled modes, fee split %, invoice prefix, refund policy triggers. |
| 326 | PAGE 21 — SETTINGS & CONFIGURATION | Tab 21.4 — Integrations & Preferences | My preferences (everyone) | language, theme (light/dark/system), notification channels, density. |

### A4. AI-POWERED FEATURES — 67

| # | Page | Feature |
|---|------|---------|
| 1 | PAGE 02 — DASHBOARD (Role-Mastered Home) | 🤖 AI Weekly Insight |
| 2 | PAGE 02 — DASHBOARD (Role-Mastered Home) | 🤖 Anomaly Spotlight |
| 3 | PAGE 02 — DASHBOARD (Role-Mastered Home) | Staff Leave & Substitution |
| 4 | PAGE 02 — DASHBOARD (Role-Mastered Home) | Subject Performance Matrix |
| 5 | PAGE 02 — DASHBOARD (Role-Mastered Home) | Question-Bank Health |
| 6 | PAGE 02 — DASHBOARD (Role-Mastered Home) | 🤖 Study Assistant |
| 7 | PAGE 03 — STUDENTS (Master Data) | Import (CSV/Excel) |
| 8 | PAGE 03 — STUDENTS (Master Data) | 🤖 Auto-gating |
| 9 | PAGE 04 — ATTENDANCE | Photo attendance (optional) |
| 10 | PAGE 04 — ATTENDANCE | Class-wise filter |
| 11 | PAGE 04 — ATTENDANCE | 🤖 Irregular list |
| 12 | PAGE 04 — ATTENDANCE | 🤖 Trend alerts |
| 13 | PAGE 05 — ACADEMICS / MARKS (Gradebook & Report Cards) | 🤖 Teacher remarks |
| 14 | PAGE 05 — ACADEMICS / MARKS (Gradebook & Report Cards) | 🤖 Weak-topic detector |
| 15 | PAGE 05 — ACADEMICS / MARKS (Gradebook & Report Cards) | 🤖 Improvement/recession tracking |
| 16 | PAGE 06 — EXAMS & AI PAPERS (AI-first) | 🤖 Generate paper |
| 17 | PAGE 06 — EXAMS & AI PAPERS (AI-first) | 🤖 "Improve style" |
| 18 | PAGE 06 — EXAMS & AI PAPERS (AI-first) | Balanced difficulty gauge |
| 19 | PAGE 06 — EXAMS & AI PAPERS (AI-first) | Syllabus binding |
| 20 | PAGE 06 — EXAMS & AI PAPERS (AI-first) | Add/import questions |
| 21 | PAGE 06 — EXAMS & AI PAPERS (AI-first) | 🤖 Auto-tagging |
| 22 | PAGE 06 — EXAMS & AI PAPERS (AI-first) | 🤖 AI auto-marking |
| 23 | PAGE 06 — EXAMS & AI PAPERS (AI-first) | Plagiarism-lite flag |
| 24 | PAGE 06 — EXAMS & AI PAPERS (AI-first) | Exam timetable grid |
| 25 | PAGE 06 — EXAMS & AI PAPERS (AI-first) | Invigilation roster |
| 26 | PAGE 07 — HOMEWORK & CLASS DIARY | 🤖 AI homework draft |
| 27 | PAGE 07 — HOMEWORK & CLASS DIARY | 🤖 AI short feedback |
| 28 | PAGE 07 — HOMEWORK & CLASS DIARY | 🤖 Diary assistant |
| 29 | PAGE 08 — TIMETABLE | Drag-drop builder |
| 30 | PAGE 08 — TIMETABLE | 🤖 Auto-suggest layout |
| 31 | PAGE 08 — TIMETABLE | Room management |
| 32 | PAGE 09 — TEACHERS & STAFF | 🤖 AI Efficiency insight |
| 33 | PAGE 09 — TEACHERS & STAFF | Approval board (principal) |
| 34 | PAGE 09 — TEACHERS & STAFF | Parent feedback |
| 35 | PAGE 10 — PAYROLL / PAYSLIP 🟩 | Run month |
| 36 | PAGE 10 — PAYROLL / PAYSLIP 🟩 | 🤖 AI mismatch check |
| 37 | PAGE 11 — FINANCE (Fees, Receipts, Budgets) 🟩 | Family & sibling discount |
| 38 | PAGE 11 — FINANCE (Fees, Receipts, Budgets) 🟩 | 🤖 AI risk forecast |
| 39 | PAGE 11 — FINANCE (Fees, Receipts, Budgets) 🟩 | 🤖 Revenue forecast |
| 40 | PAGE 12 — LIBRARY | 🤖 AI recommendation |
| 41 | PAGE 12 — LIBRARY | Book usage stats |
| 42 | PAGE 13 — TRANSPORT | 🤖 AI route optimization |
| 43 | PAGE 14 — TICKETS & SUPPORT (Escalation Chain) 🟥 | AI helper |
| 44 | PAGE 14 — TICKETS & SUPPORT (Escalation Chain) 🟥 | Request+track duplicate |
| 45 | PAGE 14 — TICKETS & SUPPORT (Escalation Chain) 🟥 | Assignment |
| 46 | PAGE 14 — TICKETS & SUPPORT (Escalation Chain) 🟥 | SLA dashboard |
| 47 | PAGE 15 — MEETINGS (Parent–Teacher Scheduling) 🟫 | 🤖 AI conflict check |
| 48 | PAGE 15 — MEETINGS (Parent–Teacher Scheduling) 🟫 | 🤖 AI suggested agenda |
| 49 | PAGE 15 — MEETINGS (Parent–Teacher Scheduling) 🟫 | 🤖 Insights for principal |
| 50 | PAGE 16 — NOTIFICATIONS CENTER 🔔 | 🤖 AI rewrite assist |
| 51 | PAGE 16 — NOTIFICATIONS CENTER 🔔 | Parent digest |
| 52 | PAGE 17 — CHAT & COMMUNICATION 🟦 | Code / link safety |
| 53 | PAGE 17 — CHAT & COMMUNICATION 🟦 | Moderation lite |
| 54 | PAGE 17 — CHAT & COMMUNICATION 🟦 | Ticket thread vs chat |
| 55 | PAGE 18 — LEAVE & APPLICATIONS (Students/Parents) 🟦 | Smart form |
| 56 | PAGE 18 — LEAVE & APPLICATIONS (Students/Parents) 🟦 | 🤖 Auto-parameters |
| 57 | PAGE 18 — LEAVE & APPLICATIONS (Students/Parents) 🟦 | Free text mode |
| 58 | PAGE 18 — LEAVE & APPLICATIONS (Students/Parents) 🟦 | Policy engine |
| 59 | PAGE 18 — LEAVE & APPLICATIONS (Students/Parents) 🟦 | Substitute/coverage hint |
| 60 | PAGE 19 — REPORTS & ANALYTICS 📊 | 🤖 Narrative report |
| 61 | PAGE 19 — REPORTS & ANALYTICS 📊 | 🤖 Forecast widgets |
| 62 | PAGE 19 — REPORTS & ANALYTICS 📊 | Board performance |
| 63 | PAGE 19 — REPORTS & ANALYTICS 📊 | Missing-data radar |
| 64 | PAGE 20 — AI COPILOT (Global Assistant) | 🤖 Actionable replies |
| 65 | PAGE 20 — AI COPILOT (Global Assistant) | Inline help |
| 66 | PAGE 20 — AI COPILOT (Global Assistant) | 🤖 Auto-cleanups |
| 67 | PAGE 20 — AI COPILOT (Global Assistant) | 🤖 Suggest recipes |

### A5. NOTIFICATION TRIGGERS — 56

| # | Page | Feature |
|---|------|---------|
| 1 | PAGE 01 — AUTH (Login / Register / Sessions) | Forgot password |
| 2 | PAGE 01 — AUTH (Login / Register / Sessions) | Invite-token flow |
| 3 | PAGE 01 — AUTH (Login / Register / Sessions) | Active sessions list |
| 4 | PAGE 02 — DASHBOARD (Role-Mastered Home) | Urgent Alerts Panel |
| 5 | PAGE 02 — DASHBOARD (Role-Mastered Home) | Approval Queue |
| 6 | PAGE 02 — DASHBOARD (Role-Mastered Home) | Paper Review Queue |
| 7 | PAGE 02 — DASHBOARD (Role-Mastered Home) | My Class Today |
| 8 | PAGE 02 — DASHBOARD (Role-Mastered Home) | Diary & Homework Status |
| 9 | PAGE 02 — DASHBOARD (Role-Mastered Home) | Leave Apps of MY Students |
| 10 | PAGE 02 — DASHBOARD (Role-Mastered Home) | HW/Assignment Status |
| 11 | PAGE 02 — DASHBOARD (Role-Mastered Home) | Today's Homework & Diary |
| 12 | PAGE 02 — DASHBOARD (Role-Mastered Home) | My Leaves & Tickets |
| 13 | PAGE 02 — DASHBOARD (Role-Mastered Home) | Today's Feed |
| 14 | PAGE 02 — DASHBOARD (Role-Mastered Home) | Pending Dues Radar |
| 15 | PAGE 02 — DASHBOARD (Role-Mastered Home) | Expense Approvals |
| 16 | PAGE 04 — ATTENDANCE | Submit & notify |
| 17 | PAGE 04 — ATTENDANCE | 🤖 Trend alerts |
| 18 | PAGE 04 — ATTENDANCE | Late & early-out wave |
| 19 | PAGE 05 — ACADEMICS / MARKS (Gradebook & Report Cards) | Entry status |
| 20 | PAGE 05 — ACADEMICS / MARKS (Gradebook & Report Cards) | Raise dispute |
| 21 | PAGE 06 — EXAMS & AI PAPERS (AI-first) | Send for HOD/Principal review |
| 22 | PAGE 06 — EXAMS & AI PAPERS (AI-first) | Schedule exam |
| 23 | PAGE 06 — EXAMS & AI PAPERS (AI-first) | Teacher review pass |
| 24 | PAGE 06 — EXAMS & AI PAPERS (AI-first) | Draft vs final results |
| 25 | PAGE 07 — HOMEWORK & CLASS DIARY | Scheduling |
| 26 | PAGE 07 — HOMEWORK & CLASS DIARY | Reminders & escalations |
| 27 | PAGE 07 — HOMEWORK & CLASS DIARY | Student sees own diary |
| 28 | PAGE 07 — HOMEWORK & CLASS DIARY | Child homework list |
| 29 | PAGE 07 — HOMEWORK & CLASS DIARY | Digital copy on leave |
| 30 | PAGE 08 — TIMETABLE | Publish flow |
| 31 | PAGE 08 — TIMETABLE | Substitute view |
| 32 | PAGE 09 — TEACHERS & STAFF | Apply leave (teacher) |
| 33 | PAGE 09 — TEACHERS & STAFF | Substitute notify |
| 34 | PAGE 10 — PAYROLL / PAYSLIP 🟩 | Salary revisions |
| 35 | PAGE 11 — FINANCE (Fees, Receipts, Budgets) 🟩 | Receipt viewer |
| 36 | PAGE 11 — FINANCE (Fees, Receipts, Budgets) 🟩 | Reminder campaign |
| 37 | PAGE 11 — FINANCE (Fees, Receipts, Budgets) 🟩 | Parent pay page |
| 38 | PAGE 12 — LIBRARY | Reserve & hold |
| 39 | PAGE 12 — LIBRARY | Overdue list |
| 40 | PAGE 13 — TRANSPORT | Bus registry |
| 41 | PAGE 13 — TRANSPORT | Trip journal |
| 42 | PAGE 14 — TICKETS & SUPPORT (Escalation Chain) 🟥 | Priority selection |
| 43 | PAGE 14 — TICKETS & SUPPORT (Escalation Chain) 🟥 | Reopen / feedback |
| 44 | PAGE 14 — TICKETS & SUPPORT (Escalation Chain) 🟥 | Escalation rules |
| 45 | PAGE 14 — TICKETS & SUPPORT (Escalation Chain) 🟥 | Resolution notes |
| 46 | PAGE 15 — MEETINGS (Parent–Teacher Scheduling) 🟫 | Instant confirmation |
| 47 | PAGE 15 — MEETINGS (Parent–Teacher Scheduling) 🟫 | Reschedule handling |
| 48 | PAGE 15 — MEETINGS (Parent–Teacher Scheduling) 🟫 | Reminder cascade |
| 49 | PAGE 16 — NOTIFICATIONS CENTER 🔔 | School broadcast |
| 50 | PAGE 16 — NOTIFICATIONS CENTER 🔔 | Leave auto-ack |
| 51 | PAGE 17 — CHAT & COMMUNICATION 🟦 | Moderation lite |
| 52 | PAGE 18 — LEAVE & APPLICATIONS (Students/Parents) 🟦 | Submit |
| 53 | PAGE 18 — LEAVE & APPLICATIONS (Students/Parents) 🟦 | Attendance tie-in |
| 54 | PAGE 18 — LEAVE & APPLICATIONS (Students/Parents) 🟦 | Apply & chain |
| 55 | PAGE 19 — REPORTS & ANALYTICS 📊 | Export engine |
| 56 | PAGE 19 — REPORTS & ANALYTICS 📊 | Auto weekly PDF |




------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------




## 0. How This Document Works

| Level | Meaning | Example |
|-------|---------|---------|
| **PAGE** | Top-level route | `PAGE 05 — Attendance` → Route `/attendance` |
| **TAB** | Secondary navigation inside the page | `Tab 5.2 — Mark Attendance` |
| **FEATURE** | A distinct action/widget inside the tab | `Mark day-wise` → click = save attendance grid |

Roles column shows **who can open that page** (`●` = full access, `◐` = view-partial, `○` = view-line, `-` = no access).

---

## 2. User Roles & Access Model

> Backend seeds `ADMIN / TEACHER / STUDENT`. The blueprint **extends** this into the
> full school hierarchy below — every extended role maps to a permission bundle on the backend `ADMIN` bucket.

| Code | Role | Frontend Home Page | Seat of Power |
|------|------|--------------------|---------------|
| OWNER | Super Admin | Settings → Control Center | System-wide config, Billing of the platform |
| DRC | Director | Director Dashboard | Revenue, whole-school matrix, final escalations |
| PRINCIPAL | Principal / Vice-Principal | Dashboard | Operations, approvals, escalations |
| HOD | Head of Department | Academic Dashboard | Subject performance, question-bank, paper review |
| CT | Class Teacher | My Class Dashboard | Class attendance, diary, homework, leave |
| SUBJ | Subject Teacher | My Subjects | Marks, attendance, homework, exam papers |
| STU | Student | My Dashboard | Marks, attendance, homework, leave |
| GUARDIAN | Parent / Guardian | Child Dashboard | Child performance, fees, meetings, tickets |
| ACCT | Accountant | Finance Page | Fees, receipts, pay slips, budget |
| ADMIN | System Admin | Settings + All Pages | Users, roles, permissions, security |
| LIB | Librarian | Library page | Books, issue/return |
| TRANSP | Transport Officer | Transport page | Routes, buses, tracking |
| STUFF | Office Staff (Reception) | Students, leave, attendance | Data entry, letters |

**Global permission map (matches backend permission codes):**
`user:*`, `finance:*`, `academic:*`, `audit:*` → ADMIN = everything; TEACHER = academic read+create + user read; STUDENT = academic read. Director/Principal are granted `audit:read` + read on everything + report-only finance.

---

## 3. Frontend Architecture (World — 2 main parts)

```
EduVerse/
├── backend/            FastAPI + PostgreSQL + LangChain/LLM (API only — not in this doc)
└── frontend/           React + TypeScript + Vite (web) → React Native (mobile)
    ├── src/app/        Providers, Router, RootLayout, ThemeContext
    ├── src/shared/     ⭐ REUSED 1:1 in React Native
    │    ├── hooks/     useAuth, useDebounce, usePermissions, useOnlineStatus, usePagination
    │    ├── api/       axios instance + typed endpoint client + interceptors (token refresh)
    │    ├── types/     zod schemas + TS interfaces mirroring backend Pydantic
    │    ├── ui/        Design system: Button, Card, Table, Modal, Form …
    │    └── utils/     date, csv/export, pdf, currency, validators, formatters
    ├── features/       ONE core folder per domain (same names as backend modules)
    │    ├── auth/  students/  attendance/  academics/  exams/  homework/  timetable/
    │    ├── teachers/  payroll/  finance/  library/  transport/  tickets/
    │    ├── meetings/  notifications/  chat/  leave/  reports/  ai-copilot/  settings/
    └── pages/          route components only (thin — logic lives in features)
```

**Why this structure →** `frontend/shared/*` is the **60% that moves to React Native unchanged** (hooks,
types, API client, validation). Only `app/` layout + `pages/` navigation get re-skinned for mobile.

---

## 4. Global Conventions (apply to every page/tab/feature below)

1. **Design language** — Black & white base (95% of UI). Module accent "column colors":
   Finance=🟩 emerald • Alerts/tickets=🟥 red • Attendance=🟦 blue • Academic/Marks=🟪 violet • Meetings=🟫 teal.
2. **Responsive** — Desktop sidebar → mobile bottom-tabs; tables collapse to cards under 768px.
3. **Every create/edit form** has save + reset + cancel; every submit has optimistic state + rollback.
4. **Every list** = pagination or infinite scroll, global search bar, filter drawer, column toggle, CSV/Excel export.
5. **Every destructive action** = confirmation modal; dangerous ones (pay, delete, mark fail) require extra confirmation word.
6. **Empty states** = illustration + CTA. **Error states** = friendly message + retry button.
7. **Data protection** — all PII visible only to granted roles; student names redacted from receptionist screens by default.
8. **Audit** — every mutation logs who/when/what to the backend audit trail (visible to Director/Principal/Admin).
9. **Notifications** — any state change for the user (homework assigned, ticket replied, child absent) fires 1 action + notification.

---
## PAGE 01 — AUTH (Login / Register / Sessions)

**Route:** `/auth` • **Roles:** All (public)

### Tab 1.1 — Sign In
- **Email/username + password** — Validated login with per-field errors; show-password toggle; caps-lock warning.
- **Remember me** — Persistent session for staff desktops vs soft-session for kiosk; expiry enforced by token age.
- **Forgot password** — Email OTP → reset link with expiry; token audit; confirmation mail on reset. 🔔
- **2-Factor OTP (optional)** — TOTP / email / SMS OTP on first login from a new device; backup codes printable.
- **Role-aware redirect** — Post-login route by role: owner→settings, director→dash, teacher→my-class, parent→child.

### Tab 1.2 — Register / Invite
- **Role-based registration** — Students/parents self-register via school code + guardian-link; teachers invite-only.
- **Invite-token flow** — Admin issues invite links (role + class prefix inside token); expiry + revoke anytime. 🔔
- **School-code validation** — Multi-tenant check before account creation; clear + friendly failure copy.
- **OTP activation** — Phone/email OTP activates the account; 60s resend timer; rate-limit feedback.

### Tab 1.3 — Session & Security
- **Active sessions list** — View every logged-in device; revoke any session; "sign out all" on compromise. 🔔
- **Idle auto-logout** — Countdown toast + still-active modal; safe for labs/kiosks; audit trail entry.
- **Kiosk lock screen** — Lab/library PCs lock on idle; quick-PIN resume; resumes without data exposure.
- **Password policy** — Min length + strength meter; no reuse of last 5; staff expiry cycle; self-service change.

---

## PAGE 02 — DASHBOARD (Role-Mastered Home)

**Route:** `/` • **Roles:** All (content switches by role)

### Tab D.1 — Director Dashboard 🟣 (every card = KPI + chart + drill-down)
- **Students & Classes live** — Admission total, active, vacancy; intake trend chart; drill to class rosters.
- **Revenue vs Plan** — 🟩 collected vs target %, 6-month projection, top fee-raising classes; drill to receipts.
- **School-wide Attendance %** — 🟦 all-class matrix today; click class → student detail; weekly loss chart.
- **Course-Completion Matrix** — 🟣 per teacher: % chapters done vs plan; overdue in red; syllabus-gap alerts.
- **Exam Result Trends** — class averages, pass %, topper list per term; subject-wise comparison lines.
- **Urgent Alerts Panel** — 🟥 unresolved tickets >48h, absent teachers, pending approvals, fee-due spikes. 🔔
- **🤖 AI Weekly Insight** — LLM writes one-paragraph briefing with numbers + clickable action suggestions.
- **🤖 Anomaly Spotlight** — LLM flags unusual signals (3-day teacher absence, sudden marks jump) for review.

### Tab D.2 — Principal Dashboard 🟣
- **Today's Operations Board** — running classes, present teachers, substitutes assigned, upcoming events.
- **Approval Queue** — leaves, fee waivers, mark disputes, paper approvals — approve/reject inline. 🔔
- **Class Attendance & Discipline** — 🟦 charts per class → drill to student; early-dropout red flags.
- **Escalated Tickets** — 🟥 teacher/parent tickets reaching principal; SLA clock visible on each row.
- **Staff Leave & Substitution** — who is absent + auto-suggested substitute from free teachers. 🤖
- **Exam Monitor** — live exam sessions, papers pending review, upload counts per class.

### Tab D.3 — HOD Academic Dashboard 🟪
- **Subject Performance Matrix** — class average, toppers, weak-topic detector from marks analytics. 🤖
- **Question-Bank Health** — 🤖 counts per subject/chapter/tags + gap suggestions ("ch.9 only 12 MCQ").
- **Paper Review Queue** — AI papers awaiting HOD approval; comment / approve / reject loop. 🔔
- **Teacher Engagement** — homework & exam assignment activity; syllabus % per teacher; zero-activity flags.

### Tab D.4 — Class Teacher Dashboard 🟦
- **My Class Today** — attendance grid summary; absent list with auto-parent-notification status visible. 🔔
- **Diary & Homework Status** — outstanding submissions; students not yet shown today's diary; quick nudge. 🔔
- **Parent Meeting Reminders** — upcoming booked slots; one-tap "book more" opens schedule page.
- **Leave Apps of MY Students** — approve/reject inline; approval auto-marks attendance + notifies parent. 🔔

### Tab D.5 — Subject Teacher Dashboard 🟪
- **My Classes Today** — timetable cards; one-tap "Start Attendance" on any live class.
- **Marks Entry Shortcuts** — pending class-tests list; last-entry time; jump straight to gradebook page.
- **HW/Assignment Status** — assigned vs submitted per class; overdue students with nudge button. 🔔
- **My AI Paper Drafts** — drafts pending edit/regenerate/download; question-bank stats of my subjects.

### Tab D.6 — Student Dashboard
- **My Performance Cards** — marks average, attendance %, pending homework, class rank (school setting allows).
- **Today's Homework & Diary** — assignments with due countdown; mark-as-done; parent gets read-confirmation. 🔔
- **Recent Grades** — latest test scores with per-subject trend chart; "share with parents" one-tap link.
- **My Leaves & Tickets** — status chips pending/approved/rejected; resume-edit draft; reopen ticket. 🔔
- **🤖 Study Assistant** — chat "how do I improve maths?" → AI answers from my marks weak-topic analysis.

### Tab D.7 — Parent Dashboard (per child; switcher for multiple children)
- **Child Snapshot** — marks, attendance %, behaviour notes, fee balance in four glance cards (🟪🟦🟥🟩).
- **Today's Feed** — real-time: child absent/leave, homework assigned, exam schedule, meeting booked. 🔔 live.
- **Fee Status & Pay** — 🟩 paid/pending chips, instant pay via gateway, receipt PDF download.
- **Quick Actions** — apply leave, raise ticket, book teacher meeting, open report card, message class teacher.

### Tab D.8 — Accountant Dashboard 🟩
- **Today's Collection** — cash/UPI/card/draft totals live; vs yesterday; vs monthly target bar.
- **Pending Dues Radar** — top defaulters with "send reminder" bulk email/WhatsApp button. 🔔
- **Expense Approvals** — vouchers/invoices awaiting Director/Principal approval; attach & submit. 🔔
- **Payroll Month Progress** — staff count, gross payroll, TDS total, disburse-ready state check.

---

## PAGE 03 — STUDENTS (Master Data)

**Route:** `/students` • **Roles:** ADMIN, DRC, PRINCIPAL, CT, SUBJ (own class), STUFF, GUARDIAN (own child)

### Tab 3.1 — Student List
- **Search + filters** — name/roll/class/section/status/fee-blocked; saved-filter presets; column toggle.
- **Row actions** — profile, edit, mark-absent jump, fee view, send mail, message parent.
- **Bulk select & export** — select many → CSV/Excel/PDF export; bulk edit section or alumni status.
- **Import (CSV/Excel)** — multi-row add with field mapping preview; duplicate detection by email/roll. 🤖 warn rows
- **Student lifecycle filters** — Active / Inactive / Alumni / Transferred; move to alumni with confirmation.

### Tab 3.2 — Add / Edit Student
- **Multi-step wizard** — Admission no., personal, guardian, contact, documents, emergency — saved as draft each step.
- **Photo & documents** — drag-drop upload with size/type rules; preview; storage quota indicator.
- **Guardian linking** — attach existing parent account or create new; guardian↔sibling link for family discounts.
- **🤖 Auto-gating** — warns duplicate admission number / AADHAAR mismatch; suggests class based on age.

### Tab 3.3 — Student Profile (all roles see granted fields only)
- **Overview** — photo, roll, class, section, contact, guardian circle, admission date; print ID card button.
- **Academic track** — marks history per term, rank trend, teacher notes; export portfolio. 🟪
- **Attendance track** — calendar heatmap, % per month, present/absent/leave split. 🟦
- **Fees tab** — 🟩 heads, paid/pending timeline, receipts; reminders; family-discount applied marks.
- **Behaviour & Diary tab** — diary entries, compliments & complaints, improvement plan; parent-visible summary.
- **Documents** — admission docs, TC/LC, previous report cards; upload/withdraw; expiry alerts.

### Tab 3.4 — Class Matrix (teacher-loved view)
- **My Class Grid** — roll-wise table with chips: attendance today, pending HW, fee due, last marks.
- **Quick Actions** — mark absent today, send message, generate report card from the same row.

---

## PAGE 04 — ATTENDANCE

**Route:** `/attendance` • **Roles:** ADMIN, DRC, PRINCIPAL, CT, SUBJ (own class), HOD, STUFF (data-entry), STU (self), GUARDIAN (child)

### Tab 4.1 — Mark Attendance
- **Class & period picker** — select class/section/subject/date; loads student roster with default Present.
- **Quick-mark grid** — tap/toggle each row: Present, Absent, Leave, Late, Half-day; keyboard shortcuts (1-5).
- **Bulk actions** — "mark all present", "everyone except 3 absent", invert row (late→present); undo last action.
- **Remarks lane** — per-student short remark (medical, OD, sport) shown to parent summary; reopen edit lock fee.
- **Photo attendance (optional)** — AI face-mark tie-in: camera scans class → suggested marks are teacher-reviewed. 🤖
- **Submit & notify** — save once, all gadgets update; absent list auto-notifies parents via app+mail+WhatsApp. 🔔

### Tab 4.2 — Attendance History
- **Calendar view** — monthly grid of % per day; click cell → class/period breakdown; weekends greyed out.
- **Student-wise filter** — top section: cumulative %, present/absent/leave counts, last 30 days heatmap. 🟦
- **Class-wise filter** — compare classes on same week; attendance % line chart; outliers highlighted. 🤖
- **Export** — monthly register PDF (print-quality), marker CSV for Excel, teacher-copy download.

### Tab 4.3 — Irregularity & Insights
- **🤖 Irregular list** — AI ranks students by attendance risk (school-policy thresholds respected); parent nudge.
- **🤖 Trend alerts** — a class dropping >10% in 2 weeks flags here for principal; auto-email to class teacher. 🔔
- **Holiday / event calendar** — upcoming holidays auto-excluded from targets; half-day rules configurable.
- **Monthly register** — official attendance register sheet per class with signature columns (print view).

### Tab 4.4 — Attendance ≥ Leave Sync
- **Leave-linked attendance** — approved leave auto-fills "Leave", not marks "Absent"; status chip visible.
- **Late & early-out wave** — office timer-screen entry for late arrivals; parent notified on repeated lateness. 🔔

---

## PAGE 05 — ACADEMICS / MARKS (Gradebook & Report Cards)

**Route:** `/academics` • **Roles:** ADMIN, DRC (read), PRINCIPAL, HOD, CT, SUBJ (own subject), STU (self), GUARDIAN (child)

### Tab 5.1 — Marks Entry (spreadsheet-grade)
- **Sheet-like grid** — class × test columns; tab-navigation between cells; total/avg auto-calculated live.
- **Bulk paste** — paste rows from Excel (roll, marks) → validated & diff-previewed before save.
- **Grading scheme** — per-school rules: raw → grade (A+, A…), CGPA or percentage — all formats supported.
- **Partial save & lock** — save-as-draft vs finalize; final entries lock editing (unlock requires permission).
- **Entry status** — shows which class has full/partial/nil entry; deadline reminders for term end. 🔔

### Tab 5.2 — Gradebook / Report Card
- **Report card builder** — 🇱 scheme selector: formative/summative, term/half-term; preview per student.
- **🤖 Teacher remarks** — AI drafts personalized remarks from marks + attendance (editable before print).
- **PDF report cards** — batch generate whole class; print-quality; watermark draft/approved; sign fields.
- **Student portfolio export** — one click: full academic history + certificates + attendance, zipped PDF.

### Tab 5.3 — Results & Analytics 🟪
- **Class result summary** — avg/pass/toppers/fail list per subject & term; chart compare terms.
- **🤖 Weak-topic detector** — question-tagged marks → "ch.5 (Fractions) drags Class 7 down" insight card.
- **🤖 Improvement/recession tracking** — shows students improving fast vs slipping; suggested support list for HOD.
- **Ranking & percentile** — class/section/subject ranks; optional visibility rule per school policy (admin toggle).

### Tab 5.4 — Marks Dispute (student can challenge)
- **Raise dispute** — student ticks an entry with reason; teacher sees in "Reassess Queue"; reply/update/close. 🔔
- **Audit trail on change** — every marks change logs old/new/who/when; principal can compare versions.
- **Grade normalization** — scaling/percentile normalization supported for multi-section fairness.

---

## PAGE 06 — EXAMS & AI PAPERS (AI-first)

**Route:** `/exams` • **Roles:** ADMIN, DRC (read), PRINCIPAL (approve), HOD (approve), SUBJ (own subject), CT (schedule), STU (view), GUARDIAN (view)

### Tab 6.1 — 🤖 AI Paper Generator
- **Parameter wizard** — class, subject, board pattern, chapters, difficulty mix, marks weight, MCQ/short/long split.
- **🤖 Generate paper** — LLM drafts full paper; question-by-question edit mode; regenerate single or all questions.
- **🤖 "Improve style"** — select a question → AI rewrites it (tougher, simpler, clearer, board-pattern) with preview.
- **Custom question add** — drag in teacher's own questions mixed with AI ones; tag sources for future bank.
- **Balanced difficulty gauge** — AI auto-balances easy/medium/hard tally, shows count bars; one-click rebalance. 🤖
- **Syllabus binding** — paper auto-maps to the course plan; chapters outside syllabus auto-warned. 🤖
- **Version history** — every regenerate saved; compare V1 vs V2; restore any version; audit who changed what.
- **Save as template** — once approved, reuse as "Pattern B" for future terms; school-level shared templates.

### Tab 6.2 — Question Bank
- **Bank explorer** — subject/chapter/tag/difficulty filters; search; preview; copy-into-paper.
- **Add/import questions** — manual entry, bulk paste from Excel, upload Word/PDF bank (AI parses). 🤖
- **🤖 Auto-tagging** — AI suggests chapter/topic/difficulty/board-pattern tags on import; teacher fixes quickly.
- **Health analytics** — coers per chapter per complexity; gap suggestions; manual question version edits with audit.

### Tab 6.3 — My Papers / Review Workflow
- **Draft list** — status chips: new / in-review / approved / used-this-term; search by class or subject.
- **Send for HOD/Principal review** — attach message; reviewer comments inline on any question; approve/reject. 🔔
- **Diff-mode review** — reviewer sees AI vs edited question side-by-side; one-tap approve-all pending.
- **Schedule exam** — pick date/time/duration; auto-announce to class + parents; insert into timetable. 🔔

### Tab 6.4 — Conduct & Marking
- **Live exam dashboard** — which exams running today; students joined (online) / papers uploaded counts.
- **Student answer-sheet upload** — students upload photos/scans per paper (mobile camera → PDF) with lock timer.
- **🤖 AI auto-marking** — AI marks MCQ instantly; subjective with rubric + model answer; confidence % shown.
- **Teacher review pass** — review AI scores row-wise; tweak mark + remark; finalize (locked) with audit. 🔔
- **Manual full marking** — rubric builder (criteria + weight), slider per criterion, total auto-calc; per-class marking page.
- **Plagiarism-lite flag** — 🤖 highlights near-identical answer pairs among class for human check.
- **Draft vs final results** — release toggle: draft visible to teachers only; on publish → student/parent notified. 🔔
- **Paper download formats** — PDF (print-ready with header/watermark), Word editable, answer-key PDF, bubblesheet-ready.

### Tab 6.5 — Schedule & Seating
- **Exam timetable grid** — date × class × subject; conflict detection (teacher double-booked) with alert. 🤖
- **Seating arrangement** — room/roll mapping generator (roll numbers shuffled by pattern); printable seating slips.
- **Invigilation roster** — auto-assign supervisors balancing load; swap requests with approval. 🤖

---

## PAGE 07 — HOMEWORK & CLASS DIARY

**Route:** `/homework` • **Roles:** SUBJ (assign), CT (diary), STU, GUARDIAN, HOD (monitor), ADMIN

### Tab 7.1 — Assign Homework 🟪
- **🤖 AI homework draft** — teacher selects chapter → AI drafts title, questions, expected time, difficulty.
- **Assign to whole class or selected** — class-wide, section-wide, or individual students (remedial/praises).
- **Multi-format attach** — text, PDF, photo of board-work, link, embedded video; due date + reminder time.
- **Scheduling** — post-now or schedule for afternoon; auto-posts to diary + notifies class & parents. 🔔
- **Today's board** — date-wise assignments of my classes; status: posted → viewed → done → graded.

### Tab 7.2 — Submissions & Review
- **Inbox per teacher** — submitted files viewed inline; mark done / needs-rework / redo (one-tap feedback chips).
- **Reminders & escalations** — auto nudge to pending students at X hours; escalate to parent on deadline miss. 🔔
- **🤖 AI short feedback** — instant 1-line review summary per submission ("good reasoning, spelling needs care").
- **Grades from HW** — weight homework into report card as per school config; counter shown.

### Tab 7.3 — Class Diary (per student, per day)
- **Day Diary entry** — CTJ writes one-liners (motivation, concern, health) shared privately with parent + admin.
- **Student sees own diary** — home tab lists "Today's diary for me" with read-confirm (parent notified on read). 🔔
- **🤖 Diary assistant** — drafts polite diary text from attendance/homework/marks cues; teacher edits freely.
- **Monthly diary digest** — PDF summary of terms' diary for parents' record; printable.

### Tab 7.4 — Parent & Student View
- **Child homework list** — pending/done/due-soon cards; "Mark done" creates parent-visible confirmation. 🔔
- **Digital copy on leave** — if student on leave, homework bundle auto-emailed + app-shown; resume-able. 🔔

---

## PAGE 08 — TIMETABLE

**Route:** `/timetable` • **Roles:** All (view per role), ADMIN/PRINCIPAL (publish), HOD (edit subject blocks)

### Tab 8.1 — Weekly Table
- **Role-aware grid** — teacher: My periods; student: My classes; parent: child's classes (no teacher names).
- **Day/class switch** — jump day or class; legend for subject colors; print view per class.
- **Publish flow** — draft → review → publish → all get notification; old version archived. 🔔

### Tab 8.2 — Editor (admin/principal)
- **Drag-drop builder** — place subjects into class-period cells; live conflict warnings (teacher double-booked, room clashes). 🤖
- **🤖 Auto-suggest layout** — AI proposes balanced timetable (contiguous free periods, workload fair split).
- **Substitute view** — swap teacher for a day/hour; affected students/parents notified. 🔔
- **Room management** — labs/gyms/auditorium booking on the same grid; booking overlap check. 🤖
- **Holiday/weekend overrides** — mark special days (PTA meet, exam days) → timetable rows greyed with reason.

---

## PAGE 09 — TEACHERS & STAFF

**Route:** `/teachers` • **Roles:** ADMIN, DRC (read), PRINCIPAL, HOD (subject view), ACCT (payroll view)

### Tab 9.1 — Staff List
- **Staff directory** — search by name/subject/class; filter by department, join year, leaving soon.
- **Profile card** — qualification, subjects, classes, contact, joining, documents, total experience bar.
- **Row actions** — edit profile, timetables, leaves, mark-assets (laptop/books), send message.
- **Import/export** — bulk add staff via CSV; export directory card sheet.

### Tab 9.2 — Workload & Course Matrix 🟣 (director's matrix)
- **Teacher Load Board** — weekly periods, classes, subjects per teacher; overload/underload balance visual.
- **Course Completion Matrix** — % of chapters taught vs plan per teacher per class; green=on-time, red=delayed.
- **🤖 AI Efficiency insight** — completion trends, substitution load, attendance pattern summary per teacher.

### Tab 9.3 — Leave & Substitute
- **Apply leave (teacher)** — date/type/substitute need; approval chain CT→Principal; substitute assignment. 🔔
- **Approval board (principal)** — approve/reject; auto-finds substitute from free slots list. 🤖
- **Leave balance** — CL/SL/PL per policy; used-remaining bars; year rollover rules applied.
- **Substitute notify** — chosen teacher + affected class rolls notified immediately on approval. 🔔

### Tab 9.4 — Performance & Review
- **Review cycle** — HOD/principal criteria forms (teaching quality, completion, attendance, parent feedback).
- **Parent feedback** — anonymous ratings (star 1-5) summarised; AI summarises comments into action points. 🤖
- **Appreciation & warning log** — principal posts entries visible in teacher profile only to admin/principal.

---

## PAGE 10 — PAYROLL / PAYSLIP 🟩

**Route:** `/payroll` • **Roles:** ACCT (prepare), DRC (approve), PRINCIPAL (approve), TEACHER (own payslip only), ADMIN

### Tab 10.1 — Salary Structure
- **Structure builder** — basic, HRA, DA, allowances, deductions (PF, PT, TDS, advance); gross/net computation live.
- **Add-ons** — bonus, overtime, transport, exam-duty pay with date scope; prorated monthly.
- **Salary revisions** — effective-date revisions with history; approval flow; teacher notified on applied. 🔔

### Tab 10.2 — Month Processing
- **Run month** — one-click "process March": attendance-influenced days, leaves, arrears auto-computed. 🤖 sanity-check
- **🤖 AI mismatch check** — flags absent-day vs full-salary conflicts, duplicate pay, TDS anomalies before lock.
- **Pay run rollback** — un-posted runs can be re-opened; all changes logged; posting locks pages.

### Tab 10.3 — Payslips
- **Payslip view** — elegant print PDF: earnings/deductions/net, arrears, YTD table; watermark "draft/paid".
- **Teacher self-service** — My Payslips list, download, PDF viewer, "claim missing month" ticket auto-created.
- **Register export** — PDF/Excel per class of staff; bank-file export (INR format columns) for uploads.
- **Advance/loan tracker** — sanction advance, EMI deduction chips, balance in payslip column.

---

## PAGE 11 — FINANCE (Fees, Receipts, Budgets) 🟩

**Route:** `/finance` • **Roles:** ACCT, DRC (report), ADMIN, GUARDIAN (child fees & pay), STUFF (receive)

### Tab 11.1 — Fee Collection
- **Fee structure builder** — heads (tuition, transport, hostel, id-card, uniform); one-time vs recurring; slab by class.
- **Collect fee (counter or portal)** — select student → dues as on date → cash/card/UPI/cheque → instant receipt.
- **Receipt viewer** — receipt no/date/mode/tax breakdown; PDF download; reprint allowed (audited); mail + WhatsApp. 🔔
- **Family & sibling discount** — auto-apply per policy on linked children; seen before payment. 🤖 verify
- **Part-pay & overdue rules** — record part-payment, late-fee auto-rule, waiver requests with approval chain.

### Tab 11.2 — Dues & Recovery
- **Dues ledger** — per class drill: who owes what; sort by age; export recovery letter batch.
- **🤖 AI risk forecast** — flags families likely to default (pattern-based) for early soft reminder.
- **Reminder campaign** — send polite email/WhatsApp/SMS in waves (L1=L2=L3) with template control. 🔔
- **Restricted access notes** — fee-blocked tag on report card/transcripts; visible only to finance/admin.

### Tab 11.3 — Expenses & Budget
- **Expense entry** — vendor, head, amount, bill upload, approve chain (accountant → director).
- **Budget vs actual** — month & head: forecast bars; variance flagged.
- **Voucher & reconciliation** — receipt-vs-bank statement check; pending match list.

### Tab 11.4 — Reports (director's revenue page)
- **Collection reports** — daily/term/year; per head/per class; cash vs digital split chart.
- **🤖 Revenue forecast** — LLM/numeric: projection of next 3 months with assumptions; scenario slider.
- **P&L summary** — income minus expense per term; simple chart; export board Excel & PDF.
- **Parent pay page** — guardian opens Fees → sees balance → pays online → receipt auto-stored; both sides notified. 🔔

---

## PAGE 12 — LIBRARY

**Route:** `/library` • **Roles:** LIB, ADMIN, PRINCIPAL(monitor), STU (self), GUARDIAN (child)

### Tab 12.1 — Catalogue & Search
- **Book catalog** — grid/list with cover, author, isbn, rack, copies; advanced filters + fuzzy search (debounced).
- **🤖 AI recommendation** — "books for a Class-5 sci-fi lover" → suggestions from catalog + reading level match.
- **Book create/import** — single add, CSV import, aisle/rack codes; duplicate ISBN check.

### Tab 12.2 — Issue / Return
- **Issue desk** — scan/type student + ISBN → issue; due date auto (policy days); copy availability live.
- **Return desk** — scan return, auto fine calc (late-fee rule), condition note icons (new/good/worn).
- **Member cards** — temporary cards for guests/teachers; card status; overdue block rules.
- **Reserve & hold** — student reserves a hot book; liber prims pickup queue + notify when ready. 🔔

### Tab 12.3 — Overdues & Notices
- **Overdue list** — auto list + email/WhatsApp reminder waves; parent gets child's overdue summary. 🔔
- **Damaged/lost** — mark lost with price deduction flow (attached to finance), replace order flag.
- **Book usage stats** — top books, low-usage sections; purchase suggestions generated. 🤖

---

## PAGE 13 — TRANSPORT

**Route:** `/transport` • **Roles:** TRANSP, ADMIN, DRC (monitor), PRINCIPAL, GUARDIAN (child route), STUDENT (own route)

### Tab 13.1 — Routes & Stops
- **Route builder** — stops, sequence, distance, bus id, capacity; route fee auto-linked to child bills. 🟩
- **Stop management** — geo-tagging stops (map picker), time table per stop, headcount per stop.
- **🤖 AI route optimization** — suggests stop-order tweaks to cut km & time; save time auto-applied with approval.
- **Print route slips** — authority slip per student for conductor/driver records.

### Tab 13.2 — Buses & GPS
- **Bus registry** — number, capacity, driver, attendant, route, fitness-validity alerts. 🔔
- **Live tracking** — GPS pins per bus on map; ETA cards; parent sees child's bus ETA. (mobile-first)
- **Trip journal** — morning/evening pickup logs per student; missed-stop handled with advice; parent notified if not boarded. 🔔
- **Emergency** — SOS button logs + mass-notifies parents/driver/principal on route incident.

### Tab 13.3 — Transport Fees & Enforcement
- **Fee integration** — transport add-on appears on child's fee bill; non-payment → service hold workflow. 🟩
- **Boarding rules** — strip photo, route-switch requests, temporary halt (by leave) with approval from transport office.

---

## PAGE 14 — TICKETS & SUPPORT (Escalation Chain) 🟥

**Route:** `/tickets` • **Roles:** All. Escalation chain: Ticket → (CT / SUBJ) → Principal → Director (auto-raise).

### Tab 14.1 — Raise a Ticket
- **One-click raise** — issue type list (fee, marks, behaviour, homework, transport, library, technical, "other").
- **Who can I raise to?** — pick target: subject teacher, class teacher, principal, director (chain rules enforced).
- **AI helper** — 🤖 pre-filled description suggestions + auto-category from keywords; attach image/PDF/proof.
- **Priority selection** — normal / urgent / critical (critical auto-pings principal + director). 🔔
- **Request+track duplicate** — AI matches similar open tickets and suggests linking to reduce repeats. 🤖

### Tab 14.2 — My Tickets (role-appropriate state)
- **Tracker view** — status chips: opened → assigned → in-progress → awaiting-answer → resolved → closed.
- **Threaded replies** — conversation per ticket with attachments, previous action history, SLA clock per row.
- **Reopen / feedback** — mark resolved→ rate resolution; reopen auto-escalates one level up. 🔔
- **Related-entity link** — ticket auto-links to student/marks/attendance record for instant context jump.

### Tab 14.3 — Support Inbox (teachers/principal/director)
- **Queue view** — filters: mine, team, unassigned, owe-one, urgent; bulk actions (assign, close, snooze).
- **Assignment** — auto/smart assign by subject-match to teacher; manual override with audit. 🤖
- **Escalation rules** — no reply in 24h → principal CC; 48h → director; auto-notify both on critical. 🔔
- **Resolution notes** — teach leave visible to raiser; parent gets notification on resolution. 🔔
- **SLA dashboard** — P95 response times, backlogs, most-complained categories (top3 for director). 🤖

### Tab 14.4 — Director / Principal Oversight
- **Escalated view** — every ticket at their level with parent/student context, history, aging bar.
- **Decide & delegate** — comment, send-back, assign-investigation, "resolved" with final note; all audited.

---

## PAGE 15 — MEETINGS (Parent–Teacher Scheduling) 🟫

**Route:** `/meetings` • **Roles:** SUBJ, CT, PRINCIPAL, GUARDIAN, STUDENT (view)

### Tab 15.1 — Teacher Slot Manager
- **Availability grid** — teacher publishes open slots (day/time/duration, in-person or video).
- **Slot types** — open-parent, requested-only, urgent-parent; auto-block exam/weekend rules.
- **🤖 AI conflict check** — overlapping own-class duties flagged; "smart slots" suggestions on low fill rates.

### Tab 15.2 — Parent Booking
- **Pick teacher + slot** — calendar picker shows free times; watch conflicts with your other child's meetings.
- **Instant confirmation** — booking creates meeting card + calendar (.ics) + join link; both notified. 🔔
- **Reschedule handling** — cancel/rebook with notice; teacher change emits new link; parent notified again. 🔔
- **🤖 AI suggested agenda** — booking notes suggest topics from child data (attendance dip, marks, fee) for brevity.

### Tab 15.3 — Meeting Room & Reminders
- **Pre-meeting sheet** — teacher side: student snapshot card (marks, attendance, diary, previous meeting notes).
- **Video button / join link** — one-tap join (WebRTC/Meet); duration guard alerts; session notes saved to student.
- **Reminder cascade** — 🔔 24h and 15-min auto reminders; missed-meeting follow-up link re-book.
- **Post-meeting action** — teacher adds follow-ups (test targets, parent to-do) visible to parent; parent can ack.

### Tab 15.4 — Meeting History & Analytics
- **Parent history** — past meetings with summary + agreed actions; "meeting with all teachers" parent-day flow.
- **🤖 Insights for principal** — participation rates, absence-attennance, teacher slot utilization, feedback ratings.

---

## PAGE 16 — NOTIFICATIONS CENTER 🔔

**Route:** `/notifications` • **Roles:** All (What-you-get depends on role & settings)

### Tab 16.1 — Live Feed
- **Unified inbox** — every module pushes here: attendance, homework, fees, tickets, meetings, exams, leave.
- **Real-time stream** — WebSocket push for new items (no refresh); sound + desktop toast for priority ones.
- **Filter chips** — All / Unread / Mentions / System / Alerts; per-module toggle (mute homework, keep fees).
- **Read state** — unread badge with count on bell; "mark all read"; per-item read/unread; read-receipt on critical.

### Tab 16.2 — Targeted & Important Alerts
- **Role-driven highlights** — teacher sees absent-substitute, HOD sees paper-review, parent sees child-absence.
- **Priority banner** — critical (incident, unresolved escalation) pinned top in red with accept button. 🟥
- **Snooze & schedule** — reminders snooze to lunch / tomorrow; import into calendar (.ics).
- **Notification rules** — user controls channels per event: in-app / email / WhatsApp / SMS / push-device.

### Tab 16.3 — Broadcasts & Announcements
- **School broadcast** — principal/admin posts to role/class/whole-school; mandatory-read tracking for urgent ones. 🔔
- **Draft & schedule** — compose rich notice (image/PDF link), schedule future send, target audience picker.
- **Delivery report** — see delivered/read stats; reminder pulse to non-readers (policy-safe times only).
- **🤖 AI rewrite assist** — turns bullet points into a warm, clear notice; parent-friendly language option.

### Tab 16.4 — Notifications for Absent/Parent
- **Absence instant-alert** — day: class-teacher mark = absence → parent gets "Your child is absent today" in <1 min.
- **Leave auto-ack** — approved/rejected leave also pushes; no double-ping when leave already pre-approved. 🔔
- **Parent digest** — one-tap "Today summary for my child" (attendance, homework, events) generated daily. 🤖

---

## PAGE 17 — CHAT & COMMUNICATION 🟦

**Route:** `/chat` • **Roles:** All (context-limited by relationship rules)

### Tab 17.1 — Conversations
- **Thread list** — 1:1 & group threads ordered by last message; unread badges; search across messages.
- **Trusted-links only** — parent ⇄ class teacher, parent ⇄ subject teacher, student ⇄ own class group, staff groups.
- **Group spaces** — per class, per staff dept, per subject team; who-can-post rules per space.
- **Read receipts** — single/double ticks; "delivered vs read"; mute per thread; pinned messages.

### Tab 17.2 — Messaging Features
- **Attachments** — images, PDFs, voice notes (mobile), whiteboard link; 25MB limit with preview.
- **Rich compose** — emoji, quick replies chips ("Okay", "Noted"), scheduled send (staff only).
- **Official badge** — official announcements marked (can't alter); PIN code verify for sensitive info (fee details).
- **Code / link safety** — auto-warn links & attachments via safe-link checker before opening. 🤖
- **Moderation lite** — offensive-word filter with soft-censor; report message → auto-ticket to principal. 🤖 🔔

### Tab 17.3 — In-Context Chats
- **Row-to-chat jump** — every entity (student, class, ticket, paper) has "Open chat" with its related people.
- **Ticket thread vs chat** — tickets stay structured; chat is informal — auto-suggest "Convert to ticket" on issue words. 🤖
- **Class-wide notes** — teacher pins "No class tomorrow — Assembly" as chat-wide notice + notification.

---

## PAGE 18 — LEAVE & APPLICATIONS (Students/Parents) 🟦

**Route:** `/leave` • **Roles:** STU, GUARDIAN, CT (approve), PRINCIPAL (approve staff, long), ADMIN

### Tab 18.1 — 🤖 AI Application Generator
- **Smart form** — pick child, date-range, reason-type (medical, family, event, travel) → AI drafts full application. 🤖
- **🤖 Auto-parameters** — suggested dates fit school calendar (exams/holidays auto-warned), duration auto-calculated.
- **Customize freely** — edit AI text, add formal-family language, insert attachments (doctor note), save as template.
- **Free text mode** — write completely your own application; AI only checks clarity + missing dates. 🤖
- **Format picker** — formal letter / simple note / medical-style variants for principal or class teacher.

### Tab 18.2 — Apply & Track
- **Submit** — choose approver (CT for short, Principal for >3 days); one-tap submit; instant ack. 🔔
- **Status timeline** — chips: submitted → approved / rejected / needs-more-info; comment history.
- **Withdraw / amend** — pending ones editable; approved ones need unapprove request (class teacher).
- **Attendance tie-in** — approved leave auto-fills attendance as "Leave" and never "Absent"; parent dashboard shows both. 🔔

### Tab 18.3 — Approver Side (class teacher / principal)
- **Approval queue** — student + staff leave side by side; see attendance % before deciding; one-click resolve.
- **Bulk approve** — same-day routine leaves in batch (configurable); comment field optional but recommended.
- **Policy engine** — auto-enforce max-continuous-days rules, exam-period blackout, min-notice; bypass needs approval. 🤖
- **Substitute/coverage hint** — for teacher leave: suggested substitute from free periods shown. 🤖

### Tab 18.4 — Staff Leave (teacher)
- **Balance card** — CL/SL/PL/OD used+remaining with year rules; carry-over summary.
- **Apply & chain** — leave requests route per policy (class-coverage aware); approved ones auto-broadcast. 🔔
- **OD duty slips** — official-duty/OD application for events, workshops; PDF slip generated for records.

---

## PAGE 19 — REPORTS & ANALYTICS 📊

**Route:** `/reports` • **Roles:** DRC, PRINCIPAL, HOD, ACCT, ADMIN (view), teachers (their scope)

### Tab 19.1 — Report Builder
- **Pick template** — report card, attendance register, fee statement, teacher matrix, class summary, custom.
- **Parameters** — scope (class/term/student), columns, format; preview live before export.
- **Export engine** — PDF (print-ready), Excel, CSV, zipped batch; schedule recurring email share. 🔔
- **🤖 Narrative report** — AI writes executive summary with numbers + recommendations (editable before send).

### Tab 19.2 — Director Command Center
- **School KPIs page** — enrollment trends, revenue health, attendance %, results, teacher matrix — all one screen.
- **Compare & drill** — period over period, class vs class, term vs term; table-to-chart toggle.
- **🤖 Forecast widgets** — next-term enrolment, fee collection, exam-pass trend; scenario toggles.
- **Auto weekly PDF** — scheduled digest to director/principal mailbox every Friday. 🔔

### Tab 19.3 — Education-Specific
- **Board performance** — subject-public averages across classes; weakest topics per subject. 🤖
- **Teacher workload matrix** — periods, classes, completion rate, substitution count per teacher.
- **Student cohort analysis** — same-cohort progress from Grade 1→8; dropoff flags; growth charts.
- **Library & transport usage** — borrowed books, bus occupancy %, route delays summary.

### Tab 19.4 — Data Quality & Exports
- **Missing-data radar** — students without photo, pending marks entries, unassigned teachers — one screen. 🤖
- **Full backup export** — JSON dump export to admin (PII flagged); GDPR-style deletion request queue.

---

## PAGE 20 — AI COPILOT (Global Assistant)

**Route:** `/ai-copilot` (also reachable from every screen via ⌘K / search bar) • **Roles:** All (scope-aware)

### Tab 20.1 — Command Palette (⌘K / Ctrl-K)
- **Universal search** — students, teachers, books, tickets, classes, pages; fuzzy + instant results.
- **Action shortcuts** — "Mark attendance 7A", "Generate maths paper", "Open fee page Rahul" → direct jumps.
- **Recent & starred** — remembers frequent searches/pages; favourite actions pinned to top.

### Tab 20.2 — 🤖 Ask EduVerse AI
- **Scope-aware chat** — parent asks "my child's progress", teacher asks "my class attendance this week" — answers from their data only.
- **🤖 Actionable replies** — offer buttons: "Create report", "Send parent nudge", "Book meeting" — generated right from the answer.
- **Data-grounded** — every answer shows source links (which report/record it used); no guessing.
- **Role policy guard** — restricts subjects AI may speak about per role; PII never revealed cross-role.

### Tab 20.3 — Genius Assistant (contextual)
- **Inline help** — any page has "Explain this screen" → AI walks through the features in that tab. 🤖
- **🤖 Auto-cleanups** — sees pagination garbage? offers "Merge duplicate students" with preview before run.
- **Form helper** — AI pre-fills long forms from natural text: "Rahul, 7A, father Ramesh, phone 98…".
- **Language** — answers in Eng / Hindi / regional language selected in settings (RTL ready).

### Tab 20.4 — Automation Recipes
- **Recipe templates** — "Daily: remind pending homework", "Friday: parent digest", "Exam-day: paper reminders".
- **🤖 Suggest recipes** — AI watches patterns and suggests new automations (e.g., "Notify when 3 absences hit").
- **Run logs** — every automation's runs & outcomes listed; pause/edit/delete with approval log.

---

## PAGE 21 — SETTINGS & CONFIGURATION

**Route:** `/settings` • **Roles:** OWNER, ADMIN (full); PRINCIPAL (partial); individual preferences for all

### Tab 21.1 — Users & Roles
- **User management** — create/edit users, reset passwords (OTP), deactivate, assign roles + classes.
- **Role composer** — build/limit role chips from permission catalogue (backend permission codes).
- **Permission matrix** — page × role grid with checkboxes; duplicates of backend `role_permissions` visible.
- **Invite management** — issue/revoke invite tokens; resend; expiry list.

### Tab 21.2 — School Profile
- **School info** — name, logo, address, contact, term structure (April/March), working days, holidays sync.
- **Fee structure** — heads & amounts per class; discount rules; late-fee & waiver policies.
- **Academic config** — classes/sections/subjects mapping, grading scheme, report-card layout picker.
- **Notification defaults** — channel per category (in-app/email/WhatsApp/SMS), quiet hours, language.

### Tab 21.3 — Audit & Security
- **Audit log viewer** — search by user, entity, action, date range; export CSV; auto-archive triggers.
- **2FA state** — who has 2FA on/off; force-enable for admins; recovery-code reset.
- **Rate-limit & session policy** — login attempts, session lengths, kiosk rules per device group.
- **Data retention** — retention windows per record type; PII masking preview; deletion requests queue.

### Tab 21.4 — Integrations & Preferences
- **WhatsApp / SMS / Email** — gateway status, templates, test-send button, daily send quotas.
- **Payment gateway** — enabled modes, fee split %, invoice prefix, refund policy triggers.
- **My preferences (everyone)** — language, theme (light/dark/system), notification channels, density.

---

## SECTION S — CROSS-CUTTING SYSTEMS

### S.1 — 🤖 AI Automation Index (every AI touch-point in one table)

| # | Where | AI Does | Backend LLM call type |
|---|-------|---------|----------------------|
| 1 | Dashboard | Weekly 1-para briefing + anomaly flags | LLM summarize + rule-outliers |
| 2 | Students | Duplicate/roll/AADHAAR gating, age→class suggestion | LLM + validation rules |
| 3 | Attendance | Irregularity ranking, trend alerts | LLM classify + rules |
| 4 | Marks | Weak-topic detector, teacher remarks, improvement tracking | LLM analyze + template |
| 5 | Exam | Paper generation, improve style, rebalance, auto-tag bank | LLM generate/edit/classify |
| 6 | Exam marking | Auto-mark MCQ/subjective with rubric + confidence, copy-flag | LLM judge (rag w/ answer key) |
| 7 | Homework | HW draft, 1-line submission feedback | LLM generate/summarize |
| 8 | Diary | Polite diary draft from cues | LLM template+draft |
| 9 | Timetable | Conflict suggest auto-layout, sub suggestion | Solver (optimization) + LLM |
| 10 | Teachers | Efficiency insights, parent-feedback summary | LLM summarize |
| 11 | Payroll | Month sanity check (absent vs pay) | Rule-based + LLM check |
| 12 | Finance | Fee-dues risk forecast, revenue forecast | Time-series ML + LLM narrative |
| 13 | Library | Book recommendations | Embedding similarity |
| 14 | Transport | Route optimization, ETA/pickup advice | Solver + LLM |
| 15 | Tickets | Auto-category, duplicate link, draft reply | LLM classify/match/draft |
| 16 | Meetings | Conflict check, suggested agenda | Rules + LLM |
| 17 | Notifications | Parent digest, broadcast rewrite | LLM summarize/generate |
| 18 | Chat | Safe link check, offensive filter, convert-to-ticket | LLM + classifier |
| 19 | Leave | Application draft, dates validation, clarity check | LLM generate/validate |
| 20 | Reports | Narrative exec summary, forecasts | LLM + charts data |
| 21 | AI Copilot | Data-grounded Q&A + actionable buttons | RAG pipeline (LangChain) |

### S.2 — Real-Time (WebSocket/SSE) Matrix
| Channel | Pushes | Frontend Hook |
|---------|--------|---------------|
| Notifications | any new item to its owner/role | subscribe `/ws/notify` |
| Chat | new message/tick/typing | subscribe `/ws/chat/{thread}` |
| Attendance | class-marks → absent-parent alert | event → auto toast |
| Transport | GPS pins, ETA, board/missed events | push into map + feed |
| Meetings | booking/reschedule/reminder events | calendar refresh + toast |
| Exams | paper review status, results publish | revalidate queries on event |
| Broadcasts | mandatory notices | pinned banner on screen |
| Payroll | payslip published | badge + mail fallback |

> Fallback: WebSocket down → SSE fallback → 30s polling; offline queueing on mobile.

### S.3 — Security & Privacy (frontend must-haves)
1. Access/refresh JWT flow with refresh stored in httpOnly cookie; axios interceptor for silent refresh.
2. RBAC + permission check wrapper (`<Can do="academic:create">`) rendered at page → tab → button level.
3. PII rules: student contact & fee details visible only on a need-to-see basis; audit of every viewer.
4. XSS: all rich text sanitized (DOMPurify); file uploads validated type+size; chat links scanned.
5. CSRF: double-submit cookie + SameSite=Strict; logout on token invalidate.
6. Minors' data (children <18) handled with consent & minimal-collection defaults — UI shows consent banners.
7. Rate-limit UX: friendly "wait and retry" screens; captcha fallback on public registration.
8. Audit trail visible for director/principal/admin; never tamper-able from client.

### S.4 — Scalability & Performance (80-crore mindset)
1. Route-level code splitting + React.lazy; core bundle < 100KB gzip target.
2. TanStack Query cache + optimistic mutations; server-state never duplicated in client stores.
3. Virtualized tables for 10K+ students; debounced search (300ms); infinite scroll lists.
4. Lazy images with blur placeholder; CDN for static; icons as inline SVG (no icon-font flash).
5. PWA: service worker offline-first for parent/student mobile; sync queue for offline actions.
6. Multi-tenant isolated query keys + school-scoped data endpoints; no cross-school leaks.
7. RTL + 12 locales ready; component strings externalized from day 1.
8. A11y: WCAG 2.1 AA — contrast, focus rings, aria-labels, keyboard-only flows, reduced-motion support.

### S.5 — React Native Migration Map (60% reuse)
| Frontend Layer | In React Native | Shared? |
|----------------|-----------------|---------|
| `hooks/` (useAuth, useDebounce…) | works 1:1 (React) | ✅ shared |
| `types/` + zod schemas | works 1:1 | ✅ shared |
| `api/` axios client | works 1:1 (swap token storage) | ✅ shared |
| `utils/` (dates, pdf, csv) | selective (swap DOM APIs) | ~70% shared |
| `ui/` components | rebuild with RN primitives (design tokens shared) | tokens ✅ |
| `features/` logic/store | logic reused; JSX replaced | logic ✅ |
| `pages/` layout/nav | bottom-tab + stack navigator | rebuilt |

---

## SECTION B — BUILD ROADMAP (How We Train While Building)

> Each phase ends with a runnable demo + commit. Order chosen so concepts build on each other.

| Phase | Weeks | Focus | Deliverable |
|-------|-------|-------|-------------|
| P1 | 1-2 | Vite+TS+ESLint+structure+theme tokens | Skeleton app, B&W theme, Login page |
| P2 | 2-3 | Design system (Button→Table→Form) + Storybook | Reusable components library |
| P3 | 2-3 | Auth UX (login/register/session/RBAC guards) | Fully gated shell |
| P4 | 3-4 | Students CRUD + attendance + marks with Query | Feature 1-3 live against backend |
| P5 | 3-4 | Homework, diary, leave, notifications, tickets | Parent-teacher workflow demo |
| P6 | 3-4 | Exams/AI papers + report cards + exports | AI paper demo (backend hooks) |
| P7 | 3-4 | Meetings, chat, transport, library, finance-views | Role-specific dashboards |
| P8 | 2-3 | Reports, AI copilot, tests (Vitest/Playwright), perf | Production polish |
| P9 | 2-3 | Docker+CI/CD+nginx+PWA+Sentry | Shippable v1 |
| P10 | — | Extract `shared/` → npm workspace → React Native scaffold | Mobile POC |

---

## CONCLUSION

This blueprint covers **21 pages, 82 tabs, 326 features** across all five school roles,
wired for **real-time events, AI at 21 touch-points, black-&-white design with module accent
colors**, and a **60% React Native reuse path**. Build order: **P1 → P2 → … → P10**.
Every feature line here maps to a future `features/<name>/*` folder in the frontend.

**✔ Document complete — `project-blueprint.md` is READY.**



✅ **Sab verify ho gaya — Document COMPLETE!**

## 📊 Final Stats — `project-blueprint.md`

| Metric | Count |
|--------|-------|
| 📄 Pages | **21** |
| 📑 Tabs | **82** |
| ⚡ Features/Actions | **326** |
| 🤖 AI-powered features | **67** (features) — +5 ikons tab/section headings me |
| 🔔 Notification triggers | **56** (features) — +2 ikons text me |
| 📍 Location | `d:\My\self_dev\EduVerse\project-blueprint.md` (1418 lines) |

## ✅ Kya-Kya Cover Hua

**21 Pages:** Auth → Role-based Dashboards (Director/Principal/HOD/Class Teacher/Subject Teacher/Student/Parent/Accountant) → Students → Attendance → Marks → **🎓 Exams & AI Papers** (generate → improve style → review → AI marking → self/teacher marking → upload → download) → Homework & Diary → Timetable → Teachers (course-completion matrix) → Payroll/Payslip → Finance (🟩) → Library → Transport → **🎫 Tickets → Escalation (Teacher → Principal → Director)** → **📅 Parent-Teacher Meetings** (slot booking + notification) → **🔔 Notifications** (absent → parent instant alert) → Chat → **📝 AI Leave Application** (parameters → AI draft → customize → free-text) → Reports → AI Copilot → Settings.

**Cross-cutting:** AI Automation Index (21 AI use-cases) • WebSocket/SSE real-time matrix • Security (JWT flow, RBAC, PII, XSS/CSRF) • Scalability (80-crore mindset) • **React Native migration map (60% code reuse)** • 10-phase Build Roadmap (P1→P10).

## 🎨 Aapke Requirements — Bande Bande

- ✅ **Black & White theme** + column-wise colors (Finance=green, Alerts=tickets=red, Attendance=blue, Academic=violet, Meetings=teal)
- ✅ **Director revenue plan dashboard**, all-class attendance, teacher course-completion matrix, payslip
- ✅ **AI exam paper** generation/customize/download/mark + custom questions
- ✅ **Student/Parent performance dashboard**
- ✅ **Ticket system** with separate info-chat + escalation to Principal/Director
- ✅ **Absent → Parent notification** in <1 min
- ✅ **AI leave application** (parameters → draft → customize → full custom)

---
