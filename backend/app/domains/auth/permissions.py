import enum


class ScopeEnum(enum.StrEnum):
    SCHOOL = "SCHOOL"
    CLASS = "CLASS"
    SUBJECT = "SUBJECT"
    OWN = "OWN"
    CHILDREN = "CHILDREN"
    ASSIGNED_CLASSES = "ASSIGNED_CLASSES"
    ASSIGNED_SUBJECTS = "ASSIGNED_SUBJECTS"


class PermissionEnum(enum.StrEnum):
    # Dashboard
    dashboard_read = "dashboard.read"

    # Students
    students_read = "students.read"
    students_create = "students.create"
    students_update = "students.update"
    students_delete = "students.delete"
    students_export = "students.export"
    students_assign_class = "students.assign_class"
    students_transfer = "students.transfer"
    students_promote = "students.promote"

    # Teachers
    teachers_read = "teachers.read"
    teachers_create = "teachers.create"
    teachers_update = "teachers.update"
    teachers_delete = "teachers.delete"
    teachers_assign_class = "teachers.assign_class"
    teachers_assign_subject = "teachers.assign_subject"
    teachers_export = "teachers.export"
    teachers_view_workload = "teachers.view_workload"
    #: Set the school's full week (`staffworkloadrule`) and assign duties
    #: (`staffduty`). Narrower than reading the matrix: reshaping the week
    #: everybody is measured against is the office's decision, not a department's.
    teachers_manage_workload = "teachers.manage_workload"
    #: Full Aadhaar / PAN / bank numbers. The profile read masks them for
    #: everybody; this right plus `?reveal=true` is what shows them, and that
    #: reveal is written to `staffauditlog`.
    teachers_view_kyc = "teachers.view_kyc"
    #: The staff audit feed ("who changed what"). Narrower than `teachers.read`:
    #: the feed names every edited profile in the school.
    teachers_audit_read = "teachers.audit_read"
    #: The daily staff register (`staffattendancerecord`). Reading it is seeing every
    #: colleague's presence, so it is its own right and not part of `teachers.read`.
    staff_attendance_read = "staff_attendance.read"
    #: Marking today's roll. A department head holds `read` only.
    staff_attendance_mark = "staff_attendance.mark"
    #: Amending a day already marked. Separate from `mark` so the right to record a
    #: day and the right to rewrite one can be given apart.
    staff_attendance_update = "staff_attendance.update"

    # Classes
    classes_read = "classes.read"
    classes_create = "classes.create"
    classes_update = "classes.update"
    classes_delete = "classes.delete"
    classes_assign_teacher = "classes.assign_teacher"
    classes_assign_student = "classes.assign_student"
    classes_export = "classes.export"

    # Attendance
    attendance_read = "attendance.read"
    attendance_mark = "attendance.mark"
    attendance_update = "attendance.update"
    attendance_override = "attendance.override"
    attendance_approve = "attendance.approve"
    attendance_export = "attendance.export"

    # Timetable
    timetable_read = "timetable.read"
    timetable_create = "timetable.create"
    timetable_update = "timetable.update"
    timetable_delete = "timetable.delete"
    timetable_publish = "timetable.publish"
    timetable_manage_rooms = "timetable.manage_rooms"

    # Homework
    homework_read = "homework.read"
    homework_create = "homework.create"
    homework_update = "homework.update"
    homework_delete = "homework.delete"
    homework_publish = "homework.publish"
    homework_review = "homework.review"
    homework_monitor = "homework.monitor"
    homework_submit = "homework.submit"

    # Diary
    diary_read = "diary.read"
    diary_create = "diary.create"
    diary_update = "diary.update"
    diary_delete = "diary.delete"

    # Exams
    exams_read = "exams.read"
    exams_create = "exams.create"
    exams_update = "exams.update"
    exams_delete = "exams.delete"
    exams_publish = "exams.publish"

    # Marks
    marks_read = "marks.read"
    marks_create = "marks.create"
    marks_update = "marks.update"
    marks_approve = "marks.approve"
    marks_publish = "marks.publish"
    marks_export = "marks.export"

    # Report Cards
    report_cards_read = "report_cards.read"
    report_cards_create = "report_cards.create"
    report_cards_update = "report_cards.update"
    report_cards_approve = "report_cards.approve"
    report_cards_publish = "report_cards.publish"
    report_cards_export = "report_cards.export"

    # Fees
    fees_read = "fees.read"
    fees_create = "fees.create"
    fees_update = "fees.update"
    fees_refund = "fees.refund"
    fees_export = "fees.export"
    fees_manage_structure = "fees.manage_structure"
    fees_view_receipt = "fees.view_receipt"
    fees_pay = "fees.pay"

    # Admissions (Operations > Admission)
    admissions_read = "admissions.read"
    admissions_manage = "admissions.manage"

    # Staff hiring (Operations > Staff Hiring)
    hiring_read = "hiring.read"
    hiring_manage = "hiring.manage"
    #: The "Hired" decision itself - admin / principal / above only.
    hiring_hire = "hiring.hire"

    # Staff salary (Operations > Staff Salary) reuses the payroll.* codenames.

    # Payroll
    payroll_read = "payroll.read"
    payroll_manage = "payroll.manage"
    payroll_export = "payroll.export"
    payroll_view_payslip = "payroll.view_payslip"

    # Library
    library_read = "library.read"
    library_manage = "library.manage"
    library_issue = "library.issue"
    library_return = "library.return"
    library_view_history = "library.view_history"

    # Transport
    transport_read = "transport.read"
    transport_manage = "transport.manage"
    transport_assign = "transport.assign"
    transport_export = "transport.export"

    # Leave
    leave_read = "leave.read"
    leave_create = "leave.create"
    leave_update = "leave.update"
    leave_approve = "leave.approve"
    leave_reject = "leave.reject"
    leave_export = "leave.export"
    #: The school's leave types and their annual grants (`leavepolicy`), and one
    #: person's override (`leavebalance`). Narrower than `leave.approve`: granting
    #: days is a decision about every contract in the school, not about one Tuesday.
    leave_manage_policy = "leave.manage_policy"

    # Substitution
    substitutions_read = "substitutions.read"
    substitutions_assign = "substitutions.assign"
    substitutions_approve = "substitutions.approve"

    # Appraisal
    appraisals_read = "appraisals.read"
    #: Filling in **your own** appraisal (the service checks it is yours).
    appraisals_self = "appraisals.self"
    #: Rating somebody else's - an HOD inside their department, the office everywhere.
    appraisals_review = "appraisals.review"
    #: Opening/closing a season and finalising an appraisal.
    appraisals_manage = "appraisals.manage"
    #: Recording what somebody attended.
    training_manage = "training.manage"

    # PTM
    ptm_read = "ptm.read"
    ptm_create = "ptm.create"
    ptm_update = "ptm.update"
    ptm_manage = "ptm.manage"
    ptm_book = "ptm.book"
    ptm_cancel = "ptm.cancel"

    # Messages
    messages_read = "messages.read"
    messages_send = "messages.send"
    messages_broadcast = "messages.broadcast"
    messages_delete = "messages.delete"

    # Announcements
    announcements_read = "announcements.read"
    announcements_create = "announcements.create"
    announcements_update = "announcements.update"
    announcements_publish = "announcements.publish"
    announcements_delete = "announcements.delete"

    # Reports
    reports_read = "reports.read"
    reports_create = "reports.create"
    reports_export = "reports.export"

    # Analytics
    analytics_read = "analytics.read"
    analytics_export = "analytics.export"

    # AI Copilot
    ai_copilot_use = "ai_copilot.use"

    # Settings
    settings_read = "settings.read"
    settings_update = "settings.update"
    users_manage = "users.manage"
    roles_manage = "roles.manage"
    #: Super-admin only: switch this session to another account ("view as").
    #: Granted to the platform-admin role alone - never to a school role.
    users_impersonate = "users.impersonate"
    permissions_manage = "permissions.manage"
    school_configure = "school.configure"
    academic_year_manage = "academic_year.manage"
    classes_configure = "classes.configure"
    subjects_configure = "subjects.configure"

    # Profile
    profile_read = "profile.read"
    profile_update = "profile.update"
    profile_change_password = "profile.change_password"
    profile_change_avatar = "profile.change_avatar"

    # Class Teacher effective permissions
    class_students_read = "class.students.read"
    class_attendance_read = "class.attendance.read"
    class_attendance_mark = "class.attendance.mark"
    class_attendance_update = "class.attendance.update"
    class_homework_monitor = "class.homework.monitor"
    class_diary_manage = "class.diary.manage"
    class_leave_read = "class.leave.read"
    class_ptm_read = "class.ptm.read"
    class_communication_send = "class.communication.send"
    class_analytics_read = "class.analytics.read"
    class_announcements_create = "class.announcements.create"


DIRECTOR_PERMISSIONS = [
    "dashboard.read",
    "admissions.read",
    "admissions.manage",
    "hiring.read",
    "hiring.manage",
    "students.read",
    "students.export",
    "teachers.read",
    "teachers.view_workload",
    "classes.read",
    "classes.export",
    "attendance.read",
    "attendance.approve",
    "attendance.export",
    "timetable.read",
    "homework.read",
    "homework.monitor",
    "diary.read",
    "exams.read",
    "exams.create",
    "exams.update",
    "exams.delete",
    "exams.publish",
    "marks.read",
    "marks.update",
    "marks.approve",
    "marks.publish",
    "marks.export",
    "report_cards.read",
    "report_cards.update",
    "report_cards.approve",
    "report_cards.publish",
    "report_cards.export",
    "fees.read",
    "fees.create",
    "fees.update",
    "fees.refund",
    "fees.export",
    "fees.manage_structure",
    "fees.view_receipt",
    "payroll.read",
    "payroll.view_payslip",
    "payroll.export",
    "library.read",
    "library.manage",
    "library.view_history",
    "transport.read",
    "transport.export",
    "leave.read",
    # The director keeps the register like the office does, and files their own leave
    # like anybody else; they also write the school's policy - they are the role that
    # signs off entitlements with the principal.
    "staff_attendance.read",
    "staff_attendance.mark",
    "staff_attendance.update",
    "leave.create",
    "leave.approve",
    "leave.reject",
    "leave.export",
    "leave.manage_policy",
    "substitutions.read",
    "substitutions.assign",
    "substitutions.approve",
    # Appraisal: the office writes the season and signs the numbers off.
    "appraisals.read",
    "appraisals.self",
    "appraisals.review",
    "appraisals.manage",
    "training.manage",
    "ptm.read",
    "ptm.manage",
    "messages.read",
    "messages.send",
    "messages.broadcast",
    "announcements.read",
    "announcements.create",
    "announcements.update",
    "announcements.publish",
    "announcements.delete",
    "reports.read",
    "reports.create",
    "reports.export",
    "analytics.read",
    "analytics.export",
    "ai_copilot.use",
    "settings.read",
    "school.configure",
    "academic_year.manage",
    "classes.configure",
    "subjects.configure",
    "profile.read",
    "profile.update",
    "profile.change_password",
    "profile.change_avatar",
]

ADMIN_PERMISSIONS = [
    "dashboard.read",
    "admissions.read",
    "admissions.manage",
    "hiring.read",
    "hiring.manage",
    "students.read",
    "students.create",
    "students.update",
    "students.delete",
    "students.export",
    "students.assign_class",
    "students.transfer",
    "students.promote",
    "teachers.read",
    "teachers.create",
    "teachers.update",
    "teachers.delete",
    "teachers.assign_class",
    "teachers.assign_subject",
    "teachers.export",
    "teachers.view_workload",
    "classes.read",
    "classes.create",
    "classes.update",
    "classes.delete",
    "classes.assign_teacher",
    "classes.assign_student",
    "classes.export",
    "attendance.read",
    "attendance.mark",
    "attendance.update",
    "attendance.override",
    "attendance.approve",
    "attendance.export",
    "timetable.read",
    "timetable.create",
    "timetable.update",
    "timetable.delete",
    "timetable.publish",
    "timetable.manage_rooms",
    "homework.read",
    "homework.create",
    "homework.update",
    "homework.delete",
    "homework.publish",
    "homework.review",
    "homework.monitor",
    "diary.read",
    "diary.create",
    "diary.update",
    "diary.delete",
    "exams.read",
    "exams.create",
    "exams.update",
    "exams.delete",
    "exams.publish",
    "marks.read",
    "marks.create",
    "marks.update",
    "marks.approve",
    "marks.publish",
    "marks.export",
    "report_cards.read",
    "report_cards.create",
    "report_cards.update",
    "report_cards.approve",
    "report_cards.publish",
    "report_cards.export",
    "fees.read",
    "fees.create",
    "fees.update",
    "fees.refund",
    "fees.export",
    "fees.manage_structure",
    "fees.view_receipt",
    "payroll.read",
    "payroll.manage",
    "payroll.export",
    "payroll.view_payslip",
    "library.read",
    "library.manage",
    "library.issue",
    "library.return",
    "library.view_history",
    "transport.read",
    "transport.manage",
    "transport.assign",
    "transport.export",
    # The office keeps the staff register - reading it, marking the day, correcting a
    # marked day. Phase 9's matrix test caught that it could do none of the three.
    "staff_attendance.read",
    "staff_attendance.mark",
    "staff_attendance.update",
    "leave.read",
    "leave.create",
    "leave.update",
    "leave.approve",
    "leave.reject",
    "leave.export",
    "leave.manage_policy",
    "substitutions.read",
    "substitutions.assign",
    "substitutions.approve",
    "appraisals.read",
    "appraisals.self",
    "appraisals.review",
    "appraisals.manage",
    "training.manage",
    "ptm.read",
    "ptm.create",
    "ptm.update",
    "ptm.manage",
    "ptm.cancel",
    "messages.read",
    "messages.send",
    "messages.broadcast",
    "messages.delete",
    "announcements.read",
    "announcements.create",
    "announcements.update",
    "announcements.publish",
    "announcements.delete",
    "reports.read",
    "reports.create",
    "reports.export",
    "analytics.read",
    "analytics.export",
    "ai_copilot.use",
    "settings.read",
    "settings.update",
    "users.manage",
    "roles.manage",
    "permissions.manage",
    "school.configure",
    "academic_year.manage",
    "classes.configure",
    "subjects.configure",
    "profile.read",
    "profile.update",
    "profile.change_password",
    "profile.change_avatar",
]

PRINCIPAL_PERMISSIONS = [
    "dashboard.read",
    "admissions.read",
    "admissions.manage",
    "hiring.read",
    "hiring.manage",
    "hiring.hire",
    # The principal publishes the class-wise fee card and runs the monthly
    # salary register, so both Operations writes are granted here.
    "fees.manage_structure",
    "payroll.manage",
    "students.read",
    "students.update",
    "students.export",
    "students.assign_class",
    "students.transfer",
    "students.promote",
    "teachers.read",
    "teachers.update",
    "teachers.assign_class",
    "teachers.assign_subject",
    "teachers.view_workload",
    # The principal (and, by inheritance, the vice-principal) sets the school's
    # full week and hands out duties. The HOD holds `view_workload` only.
    "teachers.manage_workload",
    # The principal holds the school's confidential file: unmasked KYC and the
    # audit feed. The vice-principal inherits everything except `hiring.hire`, so
    # both rights are stripped again in VICE_PRINCIPAL_PERMISSIONS.
    "teachers.view_kyc",
    "teachers.audit_read",
    # The register: the principal marks the school's day, and amends a day that was
    # recorded wrongly. The HOD holds `read` only (below).
    "staff_attendance.read",
    "staff_attendance.mark",
    "staff_attendance.update",
    "classes.read",
    "classes.create",
    "classes.update",
    "classes.assign_teacher",
    "classes.assign_student",
    "classes.export",
    "attendance.read",
    "attendance.mark",
    "attendance.update",
    "attendance.override",
    "attendance.approve",
    "attendance.export",
    "timetable.read",
    "timetable.create",
    "timetable.update",
    "timetable.delete",
    "timetable.publish",
    "timetable.manage_rooms",
    "homework.read",
    "homework.create",
    "homework.update",
    "homework.delete",
    "homework.publish",
    "homework.review",
    "homework.monitor",
    "diary.read",
    "diary.create",
    "diary.update",
    "exams.read",
    "exams.create",
    "exams.update",
    "exams.delete",
    "exams.publish",
    "marks.read",
    "marks.create",
    "marks.update",
    "marks.approve",
    "marks.publish",
    "marks.export",
    "report_cards.read",
    "report_cards.create",
    "report_cards.update",
    "report_cards.approve",
    "report_cards.publish",
    "report_cards.export",
    "fees.read",
    "fees.create",
    "fees.update",
    "fees.export",
    "fees.view_receipt",
    "payroll.read",
    "library.read",
    "library.manage",
    "transport.read",
    "transport.manage",
    "leave.read",
    # The principal takes leave too - and this is the role the policy screen says
    # must exist for the school to have entitlements at all.
    "leave.create",
    "leave.approve",
    "leave.reject",
    "leave.export",
    "leave.manage_policy",
    "substitutions.read",
    "substitutions.assign",
    "substitutions.approve",
    "appraisals.read",
    "appraisals.self",
    "appraisals.review",
    "appraisals.manage",
    "training.manage",
    "ptm.read",
    "ptm.manage",
    "messages.read",
    "messages.send",
    "messages.broadcast",
    "announcements.read",
    "announcements.create",
    "announcements.update",
    "announcements.publish",
    "reports.read",
    "reports.create",
    "reports.export",
    "analytics.read",
    "analytics.export",
    "ai_copilot.use",
    "settings.read",
    "academic_year.manage",
    "classes.configure",
    "subjects.configure",
    "profile.read",
    "profile.update",
    "profile.change_password",
    "profile.change_avatar",
]

TEACHER_PERMISSIONS = [
    "dashboard.read",
    "students.read",
    "teachers.read",
    "teachers.update",
    "classes.read",
    "attendance.read",
    "attendance.mark",
    "attendance.update",
    "timetable.read",
    "homework.read",
    "homework.create",
    "homework.update",
    "homework.delete",
    "homework.publish",
    "homework.review",
    "homework.monitor",
    "diary.read",
    "diary.create",
    "diary.update",
    "exams.read",
    "exams.create",
    "exams.update",
    "marks.read",
    "marks.create",
    "marks.update",
    "marks.approve",
    "marks.export",
    "report_cards.read",
    "report_cards.create",
    "report_cards.update",
    "library.read",
    "library.issue",
    "library.return",
    "library.view_history",
    "transport.read",
    "leave.read",
    "leave.create",
    "leave.update",
    # A teacher reads the cover board (who is away, who is standing in) - their own
    # day is on it. Arranging and approving it are not theirs.
    "substitutions.read",
    "ptm.read",
    "ptm.create",
    "ptm.update",
    "ptm.manage",
    "ptm.cancel",
    "messages.read",
    # A teacher fills in their own appraisal and reads the season; rating is somebody
    # else's, and so is opening or finalising one.
    "appraisals.read",
    "appraisals.self",
    "messages.send",
    "announcements.read",
    "announcements.create",
    "announcements.update",
    "announcements.publish",
    "reports.read",
    "reports.export",
    "analytics.read",
    "ai_copilot.use",
    "settings.read",
    "profile.read",
    "profile.update",
    "profile.change_password",
    "profile.change_avatar",
    "payroll.view_payslip",
]

STUDENT_PERMISSIONS = [
    "dashboard.read",
    "students.read",
    "classes.read",
    "attendance.read",
    "timetable.read",
    "homework.read",
    "homework.submit",
    "diary.read",
    "exams.read",
    "marks.read",
    "report_cards.read",
    "fees.read",
    "fees.pay",
    "fees.view_receipt",
    "library.read",
    "library.return",
    "library.view_history",
    "transport.read",
    "leave.read",
    "leave.create",
    "leave.update",
    "ptm.read",
    "messages.read",
    "messages.send",
    "announcements.read",
    "reports.read",
    "analytics.read",
    "ai_copilot.use",
    "settings.read",
    "profile.read",
    "profile.update",
    "profile.change_password",
    "profile.change_avatar",
]

PARENT_PERMISSIONS = [
    "dashboard.read",
    "students.read",
    "classes.read",
    "attendance.read",
    "timetable.read",
    "homework.read",
    "diary.read",
    "exams.read",
    "marks.read",
    "report_cards.read",
    "fees.read",
    "fees.pay",
    "fees.view_receipt",
    "library.read",
    "library.view_history",
    "transport.read",
    "leave.read",
    "leave.create",
    "leave.update",
    "ptm.read",
    "ptm.book",
    "ptm.cancel",
    "messages.read",
    "messages.send",
    "announcements.read",
    "reports.read",
    "analytics.read",
    "ai_copilot.use",
    "settings.read",
    "profile.read",
    "profile.update",
    "profile.change_password",
    "profile.change_avatar",
]

HOD_PERMISSIONS = [
    "dashboard.read",
    "admissions.read",
    "admissions.manage",
    "hiring.read",
    "hiring.manage",
    "students.read",
    "students.export",
    "teachers.read",
    "teachers.update",
    "teachers.assign_class",
    "teachers.assign_subject",
    "teachers.view_workload",
    # A department head reads their department's register; marking the school's
    # day is the office's (`staff_attendance.mark` is not in this list).
    "staff_attendance.read",
    "classes.read",
    "classes.create",
    "classes.update",
    "classes.assign_teacher",
    "classes.assign_student",
    "classes.export",
    "attendance.read",
    "attendance.mark",
    "attendance.update",
    "attendance.override",
    "attendance.approve",
    "attendance.export",
    "timetable.read",
    "timetable.create",
    "timetable.update",
    "timetable.publish",
    "timetable.manage_rooms",
    "homework.read",
    "homework.create",
    "homework.update",
    "homework.delete",
    "homework.publish",
    "homework.review",
    "homework.monitor",
    "diary.read",
    "diary.create",
    "diary.update",
    "exams.read",
    "exams.create",
    "exams.update",
    "exams.publish",
    "marks.read",
    "marks.create",
    "marks.update",
    "marks.approve",
    "marks.publish",
    "marks.export",
    "report_cards.read",
    "report_cards.create",
    "report_cards.update",
    "report_cards.approve",
    "report_cards.publish",
    "report_cards.export",
    "fees.read",
    "fees.view_receipt",
    "library.read",
    "library.view_history",
    "transport.read",
    "leave.read",
    # A head of department is a teacher: they file their own leave, and decide their
    # department's. They do **not** write the school's policy - that is the office's.
    "leave.create",
    "leave.approve",
    "leave.reject",
    "leave.export",
    # A head of department arranges cover inside their own department and does not
    # sign it off - approval is the office's (see `substitution/service.py`).
    "substitutions.read",
    "substitutions.assign",
    "ptm.read",
    "ptm.manage",
    "messages.read",
    "messages.send",
    "messages.broadcast",
    "announcements.read",
    "announcements.create",
    "announcements.update",
    # An HOD reviews their own department (`403` outside it) but never finalises.
    "appraisals.read",
    "appraisals.self",
    "appraisals.review",
    "training.manage",
    "announcements.publish",
    "reports.read",
    "reports.create",
    "reports.export",
    "analytics.read",
    "analytics.export",
    "ai_copilot.use",
    "settings.read",
    "profile.read",
    "profile.update",
    "profile.change_password",
    "profile.change_avatar",
    "payroll.view_payslip",
]

ACCOUNTANT_PERMISSIONS = [
    "dashboard.read",
    "students.read",
    "teachers.read",
    "fees.read",
    "fees.create",
    "fees.update",
    "fees.refund",
    "fees.export",
    "fees.manage_structure",
    "fees.view_receipt",
    "payroll.read",
    "payroll.manage",
    "payroll.export",
    "payroll.view_payslip",
    "reports.read",
    "reports.create",
    "reports.export",
    "analytics.read",
    "ai_copilot.use",
    "settings.read",
    "messages.read",
    "messages.send",
    "announcements.read",
    "leave.read",
    "profile.read",
    "profile.update",
    "profile.change_password",
    "profile.change_avatar",
]

LIBRARIAN_PERMISSIONS = [
    "dashboard.read",
    "students.read",
    "teachers.read",
    "library.read",
    "library.manage",
    "library.issue",
    "library.return",
    "library.view_history",
    "reports.read",
    "ai_copilot.use",
    "settings.read",
    "messages.read",
    "messages.send",
    "announcements.read",
    "profile.read",
    "profile.update",
    "profile.change_password",
    "profile.change_avatar",
]

TRANSPORT_PERMISSIONS = [
    "dashboard.read",
    "students.read",
    "transport.read",
    "transport.manage",
    "transport.assign",
    "transport.export",
    "reports.read",
    "ai_copilot.use",
    "settings.read",
    "messages.read",
    "messages.send",
    "announcements.read",
    "profile.read",
    "profile.update",
    "profile.change_password",
    "profile.change_avatar",
]

STAFF_PERMISSIONS = [
    "dashboard.read",
    # Front-desk staff take admission applications; they do not get
    # `students.create` (that would let them create student records directly).
    "admissions.read",
    "admissions.manage",
    "students.read",
    "classes.read",
    "attendance.read",
    "timetable.read",
    "messages.read",
    "messages.send",
    "announcements.read",
    "ai_copilot.use",
    "settings.read",
    "profile.read",
    "profile.update",
    "profile.change_password",
    "profile.change_avatar",
]

# Note: This mapping is seeded into the DB on startup
# (see permissions_repository.seed_permissions). Editing this map + restarting
# the server re-seeds any new entries idempotently.
#
# Keys are role *codenames* (`role.codename`). The union of the lists is what a
# person actually gets: holding two roles grants the union of both
# (see AuthorizationService.has_permission).

#: Everything the platform can do.
ALL_PERMISSIONS = [permission.value for permission in PermissionEnum]

SYSTEM_ADMIN_PERMISSIONS = ALL_PERMISSIONS[:]

#: A school admin runs one registered school: everything **inside** that school,
#: nothing platform-wide. Impersonation stays with the platform admin (one named
#: holder, so the audit trail has a single actor class); the school boundary is
#: enforced by `user.school_id`, not by dropping permissions.
SCHOOL_ADMIN_PERMISSIONS = [
    permission
    for permission in ALL_PERMISSIONS
    if permission != PermissionEnum.users_impersonate.value
]

VICE_PRINCIPAL_PERMISSIONS = list(
    dict.fromkeys(
        [
            # The deputy runs the pipeline but does not take the Hired decision alone
            # (that stays with the principal and above).
            *(
                permission
                for permission in PRINCIPAL_PERMISSIONS
                if permission
                not in {
                    "hiring.hire",
                    "teachers.view_kyc",
                    "teachers.audit_read",
                    # The deputy runs the day and decides leave; writing every
                    # contract's entitlement in the school is the principal's
                    # signature, not theirs.
                    "leave.manage_policy",
                }
            ),
            # The day-to-day extras. Several of these are already the principal's, and
            # `dict.fromkeys` above is what keeps the list honest: Phase 9's matrix
            # test caught the list repeating five entries, which made the "extras" look
            # like a difference from the principal that it never was.
            "timetable.publish",
            "attendance.override",
            "attendance.approve",
            "leave.approve",
            "homework.monitor",
        ]
    )
)

ROLE_PERMISSIONS_MAP = {
    "system_admin": SYSTEM_ADMIN_PERMISSIONS,
    "school_admin": SCHOOL_ADMIN_PERMISSIONS,
    "vice_principal": VICE_PRINCIPAL_PERMISSIONS,
    "principal": PRINCIPAL_PERMISSIONS,
    "hod": HOD_PERMISSIONS,
    "teacher": TEACHER_PERMISSIONS,
    "student": STUDENT_PERMISSIONS,
    "guardian": PARENT_PERMISSIONS,
    "accountant": ACCOUNTANT_PERMISSIONS,
    "librarian": LIBRARIAN_PERMISSIONS,
    "transport": TRANSPORT_PERMISSIONS,
    "staff": STAFF_PERMISSIONS,
}
