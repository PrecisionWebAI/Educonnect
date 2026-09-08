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
    "leave.approve",
    "leave.reject",
    "leave.export",
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
    "leave.read",
    "leave.create",
    "leave.update",
    "leave.approve",
    "leave.reject",
    "leave.export",
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
    "leave.approve",
    "leave.reject",
    "leave.export",
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
    "ptm.read",
    "ptm.create",
    "ptm.update",
    "ptm.manage",
    "ptm.cancel",
    "messages.read",
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

CLASS_TEACHER_EFFECTIVE_PERMISSIONS = [
    "class.students.read",
    "class.attendance.read",
    "class.attendance.mark",
    "class.attendance.update",
    "class.homework.monitor",
    "class.diary.manage",
    "class.leave.read",
    "class.ptm.read",
    "class.communication.send",
    "class.analytics.read",
    "class.announcements.create",
]

HOD_PERMISSIONS = [
    "dashboard.read",
    "students.read",
    "students.export",
    "teachers.read",
    "teachers.update",
    "teachers.assign_class",
    "teachers.assign_subject",
    "teachers.view_workload",
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
    "leave.approve",
    "leave.reject",
    "leave.export",
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
    "profile.read",
    "profile.update",
    "profile.change_password",
    "profile.change_avatar",
    "payroll.view_payslip",
]

CLASS_TEACHER_PERMISSIONS = [
    *TEACHER_PERMISSIONS,
    "class.students.read",
    "class.attendance.read",
    "class.attendance.mark",
    "class.attendance.update",
    "class.homework.monitor",
    "class.diary.manage",
    "class.leave.read",
    "class.ptm.read",
    "class.communication.send",
    "class.analytics.read",
    "class.announcements.create",
]

SUBJECT_TEACHER_PERMISSIONS = TEACHER_PERMISSIONS[:]

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

# Note: This mapping is now seeded into the DB on startup (see permissions_repository.seed_permissions).
# Editing this map + restarting the server will re-seed any new entries idempotently.
ROLE_PERMISSIONS_MAP = {
    "director": DIRECTOR_PERMISSIONS,
    "admin": ADMIN_PERMISSIONS,
    "principal": PRINCIPAL_PERMISSIONS,
    "hod": HOD_PERMISSIONS,
    "class_teacher": CLASS_TEACHER_PERMISSIONS,
    "subject_teacher": SUBJECT_TEACHER_PERMISSIONS,
    "teacher": TEACHER_PERMISSIONS,
    "student": STUDENT_PERMISSIONS,
    "guardian": PARENT_PERMISSIONS,
    "accountant": ACCOUNTANT_PERMISSIONS,
    "librarian": LIBRARIAN_PERMISSIONS,
    "transport": TRANSPORT_PERMISSIONS,
    "staff": STAFF_PERMISSIONS,
}
