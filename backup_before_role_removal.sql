--
-- PostgreSQL database dump
--

\restrict ubesctVdeTpbCWMd6p7u4NcOGjux4fwc3AiNEzU7Iw0hAheDJjBOj89HLP9KTgS

-- Dumped from database version 16.15
-- Dumped by pg_dump version 16.15

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: attendancestatus; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.attendancestatus AS ENUM (
    'present',
    'absent',
    'leave',
    'late',
    'half_day'
);


ALTER TYPE public.attendancestatus OWNER TO postgres;

--
-- Name: coveragemode; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.coveragemode AS ENUM (
    'auto',
    'marks',
    'percent'
);


ALTER TYPE public.coveragemode OWNER TO postgres;

--
-- Name: dayofweek; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.dayofweek AS ENUM (
    'monday',
    'tuesday',
    'wednesday',
    'thursday',
    'friday',
    'saturday',
    'sunday'
);


ALTER TYPE public.dayofweek OWNER TO postgres;

--
-- Name: feefrequency; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.feefrequency AS ENUM (
    'monthly',
    'term',
    'yearly',
    'one_time'
);


ALTER TYPE public.feefrequency OWNER TO postgres;

--
-- Name: generationjobstatus; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.generationjobstatus AS ENUM (
    'queued',
    'running',
    'done',
    'failed',
    'canceled'
);


ALTER TYPE public.generationjobstatus OWNER TO postgres;

--
-- Name: paperstatus; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.paperstatus AS ENUM (
    'draft',
    'in_review',
    'approved'
);


ALTER TYPE public.paperstatus OWNER TO postgres;

--
-- Name: paymentmode; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.paymentmode AS ENUM (
    'cash',
    'upi',
    'card',
    'cheque',
    'bank_transfer'
);


ALTER TYPE public.paymentmode OWNER TO postgres;

--
-- Name: sourcetype; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.sourcetype AS ENUM (
    'pdf',
    'image',
    'url',
    'text',
    'bank'
);


ALTER TYPE public.sourcetype OWNER TO postgres;

--
-- Name: submissionstatus; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.submissionstatus AS ENUM (
    'pending',
    'submitted',
    'graded'
);


ALTER TYPE public.submissionstatus OWNER TO postgres;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


ALTER TABLE public.alembic_version OWNER TO postgres;

--
-- Name: attendanceauditlog; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.attendanceauditlog (
    id uuid NOT NULL,
    school_id uuid,
    attendance_record_id uuid NOT NULL,
    changed_by_id uuid NOT NULL,
    changed_at timestamp without time zone NOT NULL,
    previous_status public.attendancestatus,
    new_status public.attendancestatus NOT NULL,
    previous_remarks character varying,
    new_remarks character varying
);


ALTER TABLE public.attendanceauditlog OWNER TO postgres;

--
-- Name: attendancerecord; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.attendancerecord (
    id uuid NOT NULL,
    school_id uuid,
    student_id uuid NOT NULL,
    classroom_id uuid NOT NULL,
    section_id uuid NOT NULL,
    subject_id uuid,
    date date NOT NULL,
    status public.attendancestatus NOT NULL,
    remarks character varying,
    overridden_by_id uuid
);


ALTER TABLE public.attendancerecord OWNER TO postgres;

--
-- Name: bus; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.bus (
    id uuid NOT NULL,
    school_id uuid,
    name character varying NOT NULL,
    plate character varying NOT NULL,
    route character varying NOT NULL,
    capacity integer NOT NULL,
    occupied integer NOT NULL,
    status character varying NOT NULL
);


ALTER TABLE public.bus OWNER TO postgres;

--
-- Name: chatfile; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.chatfile (
    id uuid NOT NULL,
    school_id uuid,
    name character varying NOT NULL,
    shared_by character varying NOT NULL,
    size character varying NOT NULL,
    "when" character varying NOT NULL
);


ALTER TABLE public.chatfile OWNER TO postgres;

--
-- Name: chatmessage; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.chatmessage (
    id uuid NOT NULL,
    school_id uuid,
    thread_id uuid NOT NULL,
    sender_id uuid NOT NULL,
    content_text character varying NOT NULL,
    attachment_url character varying,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.chatmessage OWNER TO postgres;

--
-- Name: chatthread; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.chatthread (
    id uuid NOT NULL,
    school_id uuid,
    name character varying,
    is_group boolean NOT NULL
);


ALTER TABLE public.chatthread OWNER TO postgres;

--
-- Name: chatthreadparticipant; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.chatthreadparticipant (
    id uuid NOT NULL,
    school_id uuid,
    thread_id uuid NOT NULL,
    user_id uuid NOT NULL
);


ALTER TABLE public.chatthreadparticipant OWNER TO postgres;

--
-- Name: classdiary; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.classdiary (
    id uuid NOT NULL,
    school_id uuid,
    student_id uuid NOT NULL,
    teacher_id uuid NOT NULL,
    classroom_id uuid,
    section_id uuid,
    date date NOT NULL,
    note character varying NOT NULL
);


ALTER TABLE public.classdiary OWNER TO postgres;

--
-- Name: classroom; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.classroom (
    id uuid NOT NULL,
    school_id uuid,
    name character varying NOT NULL,
    level integer NOT NULL,
    stage character varying NOT NULL
);


ALTER TABLE public.classroom OWNER TO postgres;

--
-- Name: copilotautomation; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.copilotautomation (
    id uuid NOT NULL,
    school_id uuid,
    title character varying NOT NULL,
    schedule character varying NOT NULL,
    last_run character varying NOT NULL,
    active boolean NOT NULL
);


ALTER TABLE public.copilotautomation OWNER TO postgres;

--
-- Name: copilotsuggestion; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.copilotsuggestion (
    id uuid NOT NULL,
    school_id uuid,
    prompt character varying NOT NULL,
    tag character varying NOT NULL
);


ALTER TABLE public.copilotsuggestion OWNER TO postgres;

--
-- Name: dataquality; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.dataquality (
    id uuid NOT NULL,
    school_id uuid,
    area character varying NOT NULL,
    score integer NOT NULL,
    issue character varying NOT NULL,
    status character varying NOT NULL
);


ALTER TABLE public.dataquality OWNER TO postgres;

--
-- Name: educationreport; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.educationreport (
    id uuid NOT NULL,
    school_id uuid,
    metric character varying NOT NULL,
    class_name character varying NOT NULL,
    value character varying NOT NULL,
    trend character varying NOT NULL
);


ALTER TABLE public.educationreport OWNER TO postgres;

--
-- Name: employee; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.employee (
    id uuid NOT NULL,
    school_id uuid,
    user_id uuid NOT NULL,
    employee_code character varying NOT NULL,
    department character varying NOT NULL,
    qualification character varying,
    experience_years integer NOT NULL,
    joining_date date NOT NULL,
    email character varying,
    phone character varying,
    address character varying,
    emergency_contact character varying,
    aadhaar_no character varying,
    pan_no character varying,
    bank_name character varying,
    bank_account_no character varying,
    ifsc character varying,
    previous_employer_monthly_salary double precision,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.employee OWNER TO postgres;

--
-- Name: employeesalary; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.employeesalary (
    id uuid NOT NULL,
    school_id uuid,
    employee_id uuid NOT NULL,
    salary_monthly double precision NOT NULL,
    effective_from date NOT NULL,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.employeesalary OWNER TO postgres;

--
-- Name: exam; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.exam (
    id uuid NOT NULL,
    school_id uuid,
    name character varying NOT NULL,
    term character varying,
    start_date date,
    end_date date,
    status character varying NOT NULL,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.exam OWNER TO postgres;

--
-- Name: examsource; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.examsource (
    id uuid NOT NULL,
    school_id uuid,
    classroom_id uuid,
    subject_id uuid,
    created_by uuid,
    source_type public.sourcetype NOT NULL,
    title character varying NOT NULL,
    class_name character varying NOT NULL,
    subject character varying NOT NULL,
    board character varying NOT NULL,
    teacher_name character varying NOT NULL,
    kind character varying NOT NULL,
    strictness character varying NOT NULL,
    tags json NOT NULL,
    chapters json NOT NULL,
    storage_key character varying,
    metadata_json json NOT NULL,
    page_count integer,
    status character varying NOT NULL,
    chunk_count integer NOT NULL,
    error character varying,
    content_hash character varying,
    replaces_id uuid,
    version integer NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.examsource OWNER TO postgres;

--
-- Name: feestructure; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.feestructure (
    id uuid NOT NULL,
    school_id uuid,
    name character varying NOT NULL,
    amount double precision NOT NULL,
    classroom_id uuid NOT NULL,
    frequency public.feefrequency NOT NULL,
    due_day character varying,
    status character varying NOT NULL
);


ALTER TABLE public.feestructure OWNER TO postgres;

--
-- Name: feetransaction; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.feetransaction (
    id uuid NOT NULL,
    school_id uuid,
    student_id uuid NOT NULL,
    fee_structure_id uuid NOT NULL,
    amount_paid double precision NOT NULL,
    date date NOT NULL,
    payment_mode public.paymentmode NOT NULL,
    receipt_number character varying NOT NULL
);


ALTER TABLE public.feetransaction OWNER TO postgres;

--
-- Name: gatewaystatus; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.gatewaystatus (
    id uuid NOT NULL,
    school_id uuid,
    name character varying NOT NULL,
    type character varying NOT NULL,
    status character varying NOT NULL,
    quota character varying NOT NULL
);


ALTER TABLE public.gatewaystatus OWNER TO postgres;

--
-- Name: generationjob; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.generationjob (
    id uuid NOT NULL,
    school_id uuid,
    paper_id uuid,
    status public.generationjobstatus NOT NULL,
    graph_state json NOT NULL,
    stages json NOT NULL,
    blueprint_snapshot json NOT NULL,
    coverage_snapshot json NOT NULL,
    config_snapshot json NOT NULL,
    result_snapshot json NOT NULL,
    model_info json NOT NULL,
    error character varying,
    trace_id character varying,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.generationjob OWNER TO postgres;

--
-- Name: homeworkassignment; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.homeworkassignment (
    id uuid NOT NULL,
    school_id uuid,
    title character varying NOT NULL,
    description character varying NOT NULL,
    classroom_id uuid NOT NULL,
    section_id uuid,
    subject_id uuid NOT NULL,
    teacher_id uuid NOT NULL,
    due_date date NOT NULL
);


ALTER TABLE public.homeworkassignment OWNER TO postgres;

--
-- Name: homeworksubmission; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.homeworksubmission (
    id uuid NOT NULL,
    school_id uuid,
    homework_id uuid NOT NULL,
    student_id uuid NOT NULL,
    content_url character varying,
    status public.submissionstatus NOT NULL,
    teacher_feedback character varying
);


ALTER TABLE public.homeworksubmission OWNER TO postgres;

--
-- Name: impersonationlog; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.impersonationlog (
    id uuid NOT NULL,
    actor_user_id uuid NOT NULL,
    target_user_id uuid NOT NULL,
    started_at timestamp without time zone NOT NULL,
    ended_at timestamp without time zone,
    reason character varying
);


ALTER TABLE public.impersonationlog OWNER TO postgres;

--
-- Name: leaverequest; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.leaverequest (
    id uuid NOT NULL,
    school_id uuid,
    student_id uuid,
    requester_user_id uuid NOT NULL,
    leave_type character varying NOT NULL,
    from_date date NOT NULL,
    to_date date NOT NULL,
    days integer NOT NULL,
    reason character varying,
    status character varying NOT NULL,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.leaverequest OWNER TO postgres;

--
-- Name: librarybook; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.librarybook (
    id uuid NOT NULL,
    school_id uuid,
    isbn character varying NOT NULL,
    title character varying NOT NULL,
    author character varying NOT NULL,
    category character varying NOT NULL,
    copies integer NOT NULL,
    available integer NOT NULL
);


ALTER TABLE public.librarybook OWNER TO postgres;

--
-- Name: libraryissue; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.libraryissue (
    id uuid NOT NULL,
    school_id uuid,
    book_id uuid NOT NULL,
    student_id uuid NOT NULL,
    issued_date date NOT NULL,
    due_date date NOT NULL,
    status character varying NOT NULL
);


ALTER TABLE public.libraryissue OWNER TO postgres;

--
-- Name: marks; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.marks (
    id uuid NOT NULL,
    school_id uuid,
    exam_id uuid NOT NULL,
    student_id uuid NOT NULL,
    subject_id uuid NOT NULL,
    marks_obtained double precision NOT NULL,
    max_marks double precision NOT NULL,
    grade character varying,
    entered_by uuid,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.marks OWNER TO postgres;

--
-- Name: meeting; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.meeting (
    id uuid NOT NULL,
    school_id uuid,
    title character varying NOT NULL,
    with_whom character varying NOT NULL,
    meeting_date date NOT NULL,
    meeting_time character varying NOT NULL,
    room character varying,
    status character varying NOT NULL
);


ALTER TABLE public.meeting OWNER TO postgres;

--
-- Name: notification; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.notification (
    id uuid NOT NULL,
    school_id uuid,
    user_id uuid NOT NULL,
    title character varying NOT NULL,
    body character varying NOT NULL,
    kind character varying NOT NULL,
    read boolean NOT NULL,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.notification OWNER TO postgres;

--
-- Name: palettecommand; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.palettecommand (
    id uuid NOT NULL,
    school_id uuid,
    label character varying NOT NULL,
    shortcut character varying NOT NULL,
    category character varying NOT NULL
);


ALTER TABLE public.palettecommand OWNER TO postgres;

--
-- Name: paperdraft; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.paperdraft (
    id uuid NOT NULL,
    school_id uuid,
    title character varying NOT NULL,
    classroom_id uuid,
    subject_id uuid,
    created_by uuid,
    class_name character varying NOT NULL,
    subject character varying NOT NULL,
    board character varying NOT NULL,
    exam_type character varying NOT NULL,
    language character varying NOT NULL,
    chapters json NOT NULL,
    sources json NOT NULL,
    instructions json NOT NULL,
    scope json NOT NULL,
    constraints json NOT NULL,
    total_marks integer NOT NULL,
    duration_minutes integer NOT NULL,
    blueprint json NOT NULL,
    coverage_mode public.coveragemode NOT NULL,
    coverage_plan json NOT NULL,
    part_a json NOT NULL,
    part_b json NOT NULL,
    status public.paperstatus NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.paperdraft OWNER TO postgres;

--
-- Name: permission; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.permission (
    id uuid NOT NULL,
    codename character varying NOT NULL,
    category character varying NOT NULL,
    label character varying NOT NULL
);


ALTER TABLE public.permission OWNER TO postgres;

--
-- Name: pipeline_hiring_table; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.pipeline_hiring_table (
    id uuid NOT NULL,
    school_id uuid,
    candidate_no character varying,
    candidate_name character varying NOT NULL,
    role character varying NOT NULL,
    department character varying NOT NULL,
    qualification character varying,
    experience integer NOT NULL,
    applied_on date NOT NULL,
    interview_on date,
    emp_id character varying,
    status character varying NOT NULL,
    phone character varying,
    email character varying,
    applied_for character varying,
    subject_id uuid,
    subject_name character varying,
    resume_path character varying,
    interview_at timestamp without time zone,
    interview_note character varying,
    decided_by_user_id uuid,
    decided_at timestamp without time zone
);


ALTER TABLE public.pipeline_hiring_table OWNER TO postgres;

--
-- Name: questionusagelog; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.questionusagelog (
    id uuid NOT NULL,
    school_id uuid,
    fingerprint character varying NOT NULL,
    text character varying NOT NULL,
    paper_id uuid,
    class_name character varying NOT NULL,
    subject character varying NOT NULL,
    chapter character varying NOT NULL,
    topic character varying NOT NULL,
    qtype character varying NOT NULL,
    marks integer NOT NULL,
    created_by uuid,
    used_at timestamp without time zone NOT NULL
);


ALTER TABLE public.questionusagelog OWNER TO postgres;

--
-- Name: reportcard; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.reportcard (
    id uuid NOT NULL,
    school_id uuid,
    title character varying NOT NULL,
    metric character varying NOT NULL,
    value character varying NOT NULL,
    trend character varying NOT NULL,
    tone character varying NOT NULL
);


ALTER TABLE public.reportcard OWNER TO postgres;

--
-- Name: role; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.role (
    id uuid NOT NULL,
    codename character varying NOT NULL,
    label character varying NOT NULL,
    description character varying,
    is_system boolean NOT NULL
);


ALTER TABLE public.role OWNER TO postgres;

--
-- Name: rolepermission; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.rolepermission (
    id uuid NOT NULL,
    role_id uuid NOT NULL,
    permission_id uuid NOT NULL
);


ALTER TABLE public.rolepermission OWNER TO postgres;

--
-- Name: salarypayment; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.salarypayment (
    id uuid NOT NULL,
    school_id uuid,
    employee_id uuid NOT NULL,
    month character varying NOT NULL,
    gross double precision NOT NULL,
    deductions double precision NOT NULL,
    net double precision NOT NULL,
    status character varying NOT NULL,
    paid_on date
);


ALTER TABLE public.salarypayment OWNER TO postgres;

--
-- Name: school; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.school (
    id uuid NOT NULL,
    name character varying NOT NULL,
    code character varying NOT NULL,
    email character varying NOT NULL,
    phone character varying,
    address character varying,
    is_active boolean NOT NULL,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.school OWNER TO postgres;

--
-- Name: section; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.section (
    id uuid NOT NULL,
    school_id uuid,
    name character varying NOT NULL,
    classroom_id uuid NOT NULL,
    class_teacher_id uuid
);


ALTER TABLE public.section OWNER TO postgres;

--
-- Name: securitylog; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.securitylog (
    id uuid NOT NULL,
    school_id uuid,
    event character varying NOT NULL,
    "user" character varying NOT NULL,
    "when" character varying NOT NULL
);


ALTER TABLE public.securitylog OWNER TO postgres;

--
-- Name: student_admission_form; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.student_admission_form (
    id uuid NOT NULL,
    school_id uuid,
    application_no character varying NOT NULL,
    status character varying NOT NULL,
    created_on date NOT NULL,
    notes character varying,
    student_first_name character varying,
    student_middle_name character varying,
    student_last_name character varying,
    student_email character varying,
    date_of_birth date,
    gender character varying,
    blood_group character varying,
    religion character varying,
    category character varying,
    mother_tongue character varying,
    nationality character varying,
    aadhaar_id character varying,
    address character varying,
    permanent_address character varying,
    previous_school_name character varying,
    previous_class_passed character varying,
    previous_board character varying,
    transfer_certificate_no character varying,
    old_unique_id character varying,
    father_name character varying,
    father_occupation character varying,
    father_phone character varying,
    father_email character varying,
    father_annual_income character varying,
    mother_name character varying,
    mother_occupation character varying,
    mother_phone character varying,
    mother_email character varying,
    mother_annual_income character varying,
    guardian_name character varying,
    guardian_relation character varying,
    guardian_phone character varying,
    guardian_email character varying,
    guardian_occupation character varying,
    guardian_address character varying,
    applied_for_class_level character varying,
    current_class_or_last_class character varying,
    applied_section_preference character varying,
    needs_transport character varying,
    transport_route character varying,
    needs_hostel character varying,
    separation_dropped_class character varying,
    separation_reason character varying,
    separation_session character varying,
    separation_date date,
    student_id uuid,
    student_user_id uuid,
    guardian_user_id uuid,
    promoted_at timestamp without time zone
);


ALTER TABLE public.student_admission_form OWNER TO postgres;

--
-- Name: studentparentrelationship; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.studentparentrelationship (
    id uuid NOT NULL,
    school_id uuid,
    student_id uuid NOT NULL,
    parent_user_id uuid NOT NULL,
    relationship_type character varying NOT NULL
);


ALTER TABLE public.studentparentrelationship OWNER TO postgres;

--
-- Name: studentprofile; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.studentprofile (
    id uuid NOT NULL,
    school_id uuid,
    user_id uuid NOT NULL,
    admission_number character varying NOT NULL,
    date_of_birth date NOT NULL,
    guardian_name character varying NOT NULL,
    gender character varying,
    classroom_id uuid,
    section_id uuid
);


ALTER TABLE public.studentprofile OWNER TO postgres;

--
-- Name: subject; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.subject (
    id uuid NOT NULL,
    school_id uuid,
    name character varying NOT NULL,
    code character varying NOT NULL
);


ALTER TABLE public.subject OWNER TO postgres;

--
-- Name: subjectteacher; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.subjectteacher (
    id uuid NOT NULL,
    school_id uuid,
    section_id uuid NOT NULL,
    subject_id uuid NOT NULL,
    teacher_id uuid NOT NULL
);


ALTER TABLE public.subjectteacher OWNER TO postgres;

--
-- Name: supportticket; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.supportticket (
    id uuid NOT NULL,
    school_id uuid,
    subject character varying NOT NULL,
    category character varying NOT NULL,
    priority character varying NOT NULL,
    status character varying NOT NULL,
    reporter_user_id uuid NOT NULL,
    assignee character varying,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.supportticket OWNER TO postgres;

--
-- Name: syllabusprogress; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.syllabusprogress (
    id uuid NOT NULL,
    school_id uuid,
    section_id uuid NOT NULL,
    subject_id uuid NOT NULL,
    chapters_total integer NOT NULL,
    chapters_done integer NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.syllabusprogress OWNER TO postgres;

--
-- Name: teacherreview; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.teacherreview (
    id uuid NOT NULL,
    school_id uuid,
    teacher_id uuid NOT NULL,
    rating integer NOT NULL,
    reviewer_role character varying NOT NULL,
    comment character varying,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.teacherreview OWNER TO postgres;

--
-- Name: teachersubject; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.teachersubject (
    id uuid NOT NULL,
    school_id uuid,
    teacher_id uuid NOT NULL,
    subject_id uuid NOT NULL
);


ALTER TABLE public.teachersubject OWNER TO postgres;

--
-- Name: timetableperiod; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.timetableperiod (
    id uuid NOT NULL,
    school_id uuid,
    classroom_id uuid NOT NULL,
    section_id uuid,
    subject_id uuid NOT NULL,
    teacher_id uuid NOT NULL,
    day_of_week public.dayofweek NOT NULL,
    start_time time without time zone NOT NULL,
    end_time time without time zone NOT NULL,
    room character varying
);


ALTER TABLE public.timetableperiod OWNER TO postgres;

--
-- Name: transportroute; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.transportroute (
    id uuid NOT NULL,
    school_id uuid,
    name character varying NOT NULL,
    bus_id character varying NOT NULL,
    driver character varying NOT NULL,
    stops integer NOT NULL,
    students integer NOT NULL,
    status character varying NOT NULL
);


ALTER TABLE public.transportroute OWNER TO postgres;

--
-- Name: user; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public."user" (
    id uuid NOT NULL,
    school_id uuid,
    email character varying NOT NULL,
    full_name character varying NOT NULL,
    is_active boolean NOT NULL,
    hashed_password character varying NOT NULL,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public."user" OWNER TO postgres;

--
-- Name: user_role; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.user_role (
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    role_id uuid NOT NULL,
    is_primary boolean NOT NULL,
    assigned_at timestamp without time zone NOT NULL
);


ALTER TABLE public.user_role OWNER TO postgres;

--
-- Data for Name: alembic_version; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.alembic_version (version_num) FROM stdin;
f9e0f1a2b3c5
\.


--
-- Data for Name: attendanceauditlog; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.attendanceauditlog (id, school_id, attendance_record_id, changed_by_id, changed_at, previous_status, new_status, previous_remarks, new_remarks) FROM stdin;
\.


--
-- Data for Name: attendancerecord; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.attendancerecord (id, school_id, student_id, classroom_id, section_id, subject_id, date, status, remarks, overridden_by_id) FROM stdin;
\.


--
-- Data for Name: bus; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.bus (id, school_id, name, plate, route, capacity, occupied, status) FROM stdin;
\.


--
-- Data for Name: chatfile; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.chatfile (id, school_id, name, shared_by, size, "when") FROM stdin;
\.


--
-- Data for Name: chatmessage; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.chatmessage (id, school_id, thread_id, sender_id, content_text, attachment_url, created_at) FROM stdin;
\.


--
-- Data for Name: chatthread; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.chatthread (id, school_id, name, is_group) FROM stdin;
\.


--
-- Data for Name: chatthreadparticipant; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.chatthreadparticipant (id, school_id, thread_id, user_id) FROM stdin;
\.


--
-- Data for Name: classdiary; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.classdiary (id, school_id, student_id, teacher_id, classroom_id, section_id, date, note) FROM stdin;
\.


--
-- Data for Name: classroom; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.classroom (id, school_id, name, level, stage) FROM stdin;
8348a30b-c177-4d70-91b5-2e4b48f4eff1	26fc741e-7270-4f5a-98fd-63a548c315a3	Nursery	0	pre_primary
39eb951e-7827-4de4-9ae5-24cf9ae530f9	26fc741e-7270-4f5a-98fd-63a548c315a3	LKG	1	pre_primary
ebd99f35-32c7-407e-9468-3266f36d0da7	26fc741e-7270-4f5a-98fd-63a548c315a3	UKG	2	pre_primary
de0e7fe8-0234-48ef-9c27-68c22bfc2c0e	26fc741e-7270-4f5a-98fd-63a548c315a3	Class 1	3	primary
39ed03d2-eb15-40dd-8f62-7eba0495fc5b	26fc741e-7270-4f5a-98fd-63a548c315a3	Class 2	4	primary
5aacf61c-8088-4f62-a3e9-40f279163878	26fc741e-7270-4f5a-98fd-63a548c315a3	Class 3	5	primary
28b751e1-27c6-416e-bdba-7555dae76eea	26fc741e-7270-4f5a-98fd-63a548c315a3	Class 4	6	primary
2c600b56-0685-4a55-9d8d-1d3bac400924	26fc741e-7270-4f5a-98fd-63a548c315a3	Class 5	7	primary
f6f903cb-4ce2-4bba-b0aa-7c8d3bb8e8b1	26fc741e-7270-4f5a-98fd-63a548c315a3	Class 6	8	middle
fe8a2bd0-aa9e-408b-96bb-b5ae62b09143	26fc741e-7270-4f5a-98fd-63a548c315a3	Class 7	9	middle
565a7d90-d741-433d-a8f0-c283dcf322b4	26fc741e-7270-4f5a-98fd-63a548c315a3	Class 8	10	middle
7523d809-73e0-4bf8-ad41-37b3f3c894a5	26fc741e-7270-4f5a-98fd-63a548c315a3	Class 9	11	secondary
1f267193-8747-453c-a927-93a5b3be2394	26fc741e-7270-4f5a-98fd-63a548c315a3	Class 10	12	secondary
005350a3-5dae-4186-a621-7fcf575f0d87	26fc741e-7270-4f5a-98fd-63a548c315a3	Class 11	13	senior_secondary
83a115e0-81d4-4ac6-99cc-be57968fe628	26fc741e-7270-4f5a-98fd-63a548c315a3	Class 12	14	senior_secondary
cf3aaa3a-a212-4f56-828a-29ce291347b7	329eb5b7-10d1-42c9-b309-19477157eeb5	Nursery	0	pre_primary
ca8ca282-cbef-4812-9f7c-6f244814e979	329eb5b7-10d1-42c9-b309-19477157eeb5	LKG	1	pre_primary
a5ee9016-6e98-44eb-939e-2660e18d5924	329eb5b7-10d1-42c9-b309-19477157eeb5	UKG	2	pre_primary
c51c1348-ff2b-4fce-90a8-a59b44c4a9c3	329eb5b7-10d1-42c9-b309-19477157eeb5	Class 1	3	primary
6d68246e-df3d-40b3-8071-3c412f22e260	329eb5b7-10d1-42c9-b309-19477157eeb5	Class 2	4	primary
cd445379-afec-4e9d-8477-922da7540044	329eb5b7-10d1-42c9-b309-19477157eeb5	Class 3	5	primary
540f6289-8115-4da3-aa73-8d5343fefc16	329eb5b7-10d1-42c9-b309-19477157eeb5	Class 4	6	primary
b977bd8b-ebac-4d24-b264-e2f23bf52911	329eb5b7-10d1-42c9-b309-19477157eeb5	Class 5	7	primary
84362e32-cde0-4fbf-82a3-ad7f1781818c	329eb5b7-10d1-42c9-b309-19477157eeb5	Class 6	8	middle
43cc5754-c358-4f1c-b0cc-f5122280183c	329eb5b7-10d1-42c9-b309-19477157eeb5	Class 7	9	middle
b2400fea-d404-4af7-ac20-7a6e63c9da98	329eb5b7-10d1-42c9-b309-19477157eeb5	Class 8	10	middle
8c6f96e3-facf-4b40-b19c-db13ccac2d92	329eb5b7-10d1-42c9-b309-19477157eeb5	Class 9	11	secondary
5855d269-b8c2-4f20-8d30-5520bc195aed	329eb5b7-10d1-42c9-b309-19477157eeb5	Class 10	12	secondary
d0f1ad44-a1a1-477e-814c-2bd430b98959	329eb5b7-10d1-42c9-b309-19477157eeb5	Class 11	13	senior_secondary
6bf1c57c-2e52-47dc-bde7-058e72505c00	329eb5b7-10d1-42c9-b309-19477157eeb5	Class 12	14	senior_secondary
\.


--
-- Data for Name: copilotautomation; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.copilotautomation (id, school_id, title, schedule, last_run, active) FROM stdin;
\.


--
-- Data for Name: copilotsuggestion; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.copilotsuggestion (id, school_id, prompt, tag) FROM stdin;
\.


--
-- Data for Name: dataquality; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.dataquality (id, school_id, area, score, issue, status) FROM stdin;
\.


--
-- Data for Name: educationreport; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.educationreport (id, school_id, metric, class_name, value, trend) FROM stdin;
\.


--
-- Data for Name: employee; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.employee (id, school_id, user_id, employee_code, department, qualification, experience_years, joining_date, email, phone, address, emergency_contact, aadhaar_no, pan_no, bank_name, bank_account_no, ifsc, previous_employer_monthly_salary, created_at) FROM stdin;
2f03984b-388e-4701-9a4f-bd74ab6ff76d	26fc741e-7270-4f5a-98fd-63a548c315a3	908cf9dd-602f-4653-87ac-13b3e83958aa	EMP-0038	Sports	Bped	4	2026-11-02	tanyashrivastav123@gmail.com	85454984848	dnfsjkldjfa	48781214656	98413184561	7784552	Kotak mahindra	849844489646	dkdkc0001	24964	2026-11-02 11:37:46.96086
\.


--
-- Data for Name: employeesalary; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.employeesalary (id, school_id, employee_id, salary_monthly, effective_from, created_at) FROM stdin;
9223978a-40b2-432e-9b5c-2b6e13dcf27e	26fc741e-7270-4f5a-98fd-63a548c315a3	2f03984b-388e-4701-9a4f-bd74ab6ff76d	32000	2026-11-02	2026-11-02 11:37:46.978426
\.


--
-- Data for Name: exam; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.exam (id, school_id, name, term, start_date, end_date, status, created_at) FROM stdin;
\.


--
-- Data for Name: examsource; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.examsource (id, school_id, classroom_id, subject_id, created_by, source_type, title, class_name, subject, board, teacher_name, kind, strictness, tags, chapters, storage_key, metadata_json, page_count, status, chunk_count, error, content_hash, replaces_id, version, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: feestructure; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.feestructure (id, school_id, name, amount, classroom_id, frequency, due_day, status) FROM stdin;
47e713b7-a1c8-4629-9a8e-2283e99aae69	26fc741e-7270-4f5a-98fd-63a548c315a3	Tuestion fees	12000	1f267193-8747-453c-a927-93a5b3be2394	monthly	500	Draft
\.


--
-- Data for Name: feetransaction; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.feetransaction (id, school_id, student_id, fee_structure_id, amount_paid, date, payment_mode, receipt_number) FROM stdin;
\.


--
-- Data for Name: gatewaystatus; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.gatewaystatus (id, school_id, name, type, status, quota) FROM stdin;
\.


--
-- Data for Name: generationjob; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.generationjob (id, school_id, paper_id, status, graph_state, stages, blueprint_snapshot, coverage_snapshot, config_snapshot, result_snapshot, model_info, error, trace_id, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: homeworkassignment; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.homeworkassignment (id, school_id, title, description, classroom_id, section_id, subject_id, teacher_id, due_date) FROM stdin;
\.


--
-- Data for Name: homeworksubmission; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.homeworksubmission (id, school_id, homework_id, student_id, content_url, status, teacher_feedback) FROM stdin;
\.


--
-- Data for Name: impersonationlog; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.impersonationlog (id, actor_user_id, target_user_id, started_at, ended_at, reason) FROM stdin;
\.


--
-- Data for Name: leaverequest; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.leaverequest (id, school_id, student_id, requester_user_id, leave_type, from_date, to_date, days, reason, status, created_at) FROM stdin;
\.


--
-- Data for Name: librarybook; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.librarybook (id, school_id, isbn, title, author, category, copies, available) FROM stdin;
\.


--
-- Data for Name: libraryissue; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.libraryissue (id, school_id, book_id, student_id, issued_date, due_date, status) FROM stdin;
\.


--
-- Data for Name: marks; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.marks (id, school_id, exam_id, student_id, subject_id, marks_obtained, max_marks, grade, entered_by, created_at) FROM stdin;
\.


--
-- Data for Name: meeting; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.meeting (id, school_id, title, with_whom, meeting_date, meeting_time, room, status) FROM stdin;
\.


--
-- Data for Name: notification; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.notification (id, school_id, user_id, title, body, kind, read, created_at) FROM stdin;
\.


--
-- Data for Name: palettecommand; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.palettecommand (id, school_id, label, shortcut, category) FROM stdin;
\.


--
-- Data for Name: paperdraft; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.paperdraft (id, school_id, title, classroom_id, subject_id, created_by, class_name, subject, board, exam_type, language, chapters, sources, instructions, scope, constraints, total_marks, duration_minutes, blueprint, coverage_mode, coverage_plan, part_a, part_b, status, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: permission; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.permission (id, codename, category, label) FROM stdin;
4d386bdc-9a78-4215-a9c1-eb6d22b68b10	dashboard.read	Dashboard	Read
20e5c59f-7396-46dc-8297-142e40347332	students.read	Students	Read
f274f4fd-5b74-48dd-96d2-1a276cc8c239	students.create	Students	Create
90889445-d0ff-4cca-9bd4-a8da0b0fd45f	students.update	Students	Update
8aa3b220-a233-4ea0-be6b-7766c715f60f	students.delete	Students	Delete
a3a2d2b2-4901-46b8-bfaf-163beede39e9	students.export	Students	Export
fc6dd1d5-140a-44ba-b630-59f1a988dae6	students.assign_class	Students	Assign Class
8f0194fd-e080-4f98-b46f-71c75812e8c2	students.transfer	Students	Transfer
ef0ee95d-2607-4aa8-b8cf-267b94db76d1	students.promote	Students	Promote
5c4f1a53-b5be-49c3-8639-e0ef8b62826a	teachers.read	Teachers	Read
fd1ac7c2-f3cb-46a1-8de8-411a81bb0b9a	teachers.create	Teachers	Create
c88911a2-b1b8-496f-9c53-adea5384f7cf	teachers.update	Teachers	Update
0a8c77b2-31ab-4db3-86cc-36136cfcf63f	teachers.delete	Teachers	Delete
678de476-da63-428c-9a8c-8d0de781400b	teachers.assign_class	Teachers	Assign Class
9206f1af-e598-4228-a352-e8b71701f500	teachers.assign_subject	Teachers	Assign Subject
d7591f4b-217f-4d3b-a190-6fa9bde2e0db	teachers.export	Teachers	Export
52a2daaf-298d-41f8-b034-9b9352a00386	teachers.view_workload	Teachers	View Workload
933f5bd1-6cdc-4d92-85fe-a13dfaa6b71c	classes.read	Classes	Read
3a1b4156-55a1-446e-b188-df5e77dfd8b5	classes.create	Classes	Create
f7876ae0-847a-46d0-896d-26a337f9605b	classes.update	Classes	Update
67e8e39a-b946-4036-9071-6622ffcebcb0	classes.delete	Classes	Delete
f596816e-a0ac-4396-b526-c0cc7e4f1547	classes.assign_teacher	Classes	Assign Teacher
34efa491-5e0f-451b-9897-829b40376ae9	classes.assign_student	Classes	Assign Student
1d230fba-3517-4936-a3a3-65eb110b963d	classes.export	Classes	Export
6710a77c-e35a-4f4c-a1d8-bd2a480faf9b	attendance.read	Attendance	Read
879b5348-dc23-4238-9770-618fca34f404	attendance.mark	Attendance	Mark
f91b7933-b575-4783-bdeb-69883ff75b57	attendance.update	Attendance	Update
c5b7095e-b795-438b-9455-d4eabba5fbaa	attendance.override	Attendance	Override
f08197bb-10f5-4097-b737-96bdc77dd673	attendance.approve	Attendance	Approve
8c413273-dd5d-4e54-a23c-f516044e9961	attendance.export	Attendance	Export
b824f887-522b-42c3-bb6d-e9bf3fe2c68d	timetable.read	Timetable	Read
c795a61c-1525-4603-bc85-d04be7098f69	timetable.create	Timetable	Create
eb624a8e-2ddc-4f3a-9f15-571996b861fc	timetable.update	Timetable	Update
dc30661b-be68-476b-8fab-e75d843b454c	timetable.delete	Timetable	Delete
8494e31f-b5a4-4895-8600-5613daaf2e7b	timetable.publish	Timetable	Publish
2045a7fa-d8fe-4784-bda5-4bccf4d69809	timetable.manage_rooms	Timetable	Manage Rooms
27b4f7cc-d8d9-4b12-bb83-a47153e5d135	homework.read	Homework	Read
250dfee3-8da0-479e-aad8-2a74f24b9f9d	homework.create	Homework	Create
b2ba2fe1-84ba-4d59-ad57-f1872021589d	homework.update	Homework	Update
4202bfd2-c595-4d18-aa0f-80ae538e4fea	homework.delete	Homework	Delete
76d1637a-aaf4-451b-b1d0-7849957a42a8	homework.publish	Homework	Publish
e5395d8e-6cdc-4411-b2b5-835ad149e933	homework.review	Homework	Review
57d21fef-512f-43cb-9aa0-0bebae2f355e	homework.monitor	Homework	Monitor
a4be3422-b10b-4422-b513-fbdc9eeb864a	homework.submit	Homework	Submit
db812fd9-919e-47e1-aa9d-7b0de37b9863	diary.read	Diary	Read
050305b3-edec-407f-91e8-eb7f6e9fa1b3	diary.create	Diary	Create
bf762354-ead7-4be6-a836-f57bd7df1c1d	diary.update	Diary	Update
044f2158-b337-4877-b82c-11dc936b716f	diary.delete	Diary	Delete
2a5a1c0d-47b4-4e9f-9ab4-b9106ed67a9d	exams.read	Exams	Read
f75c6bcc-c9ae-4a04-a8e0-f56d351009af	exams.create	Exams	Create
8231e7d4-b4e8-495a-b881-3bfabbd85b67	exams.update	Exams	Update
5199b83d-34c6-4a7c-9bf9-d140a27f93c8	exams.delete	Exams	Delete
e59e5d27-8afb-4b5f-9d8d-dc5c6f19708e	exams.publish	Exams	Publish
1cdef3b1-d9ec-4f0d-9b7f-e6e927643e9a	marks.read	Marks	Read
6a0ca14f-762d-4171-974e-c5870aa4076f	marks.create	Marks	Create
bad99487-1598-4525-ad21-de5dce5a91dc	marks.update	Marks	Update
a590fd62-ff70-4e2f-aeb0-caf4b535c746	marks.approve	Marks	Approve
00ea86d7-62b3-4756-9abc-66dacc78c876	marks.publish	Marks	Publish
17665863-3735-46dc-96b5-2d9ebecff977	marks.export	Marks	Export
36876181-d912-41bd-b06a-60c741e04818	report_cards.read	Report Cards	Read
6c32aa54-5304-4b8d-a2f2-2d822f61be12	report_cards.create	Report Cards	Create
110560c2-7eb4-4890-b004-659f0203dd83	report_cards.update	Report Cards	Update
91afb109-c9f5-448c-a236-3d7f88c0f293	report_cards.approve	Report Cards	Approve
666022e6-ebb1-4567-b794-45b4c50c708f	report_cards.publish	Report Cards	Publish
bb7bfcf6-f92a-4d61-9111-9f9806601c2a	report_cards.export	Report Cards	Export
f2011e4a-07b4-4261-b2b5-f4539f8c416a	fees.read	Fees	Read
163342df-9367-4e54-ab5c-4a3b55a0eadf	fees.create	Fees	Create
0504f8e1-168a-4ff6-ab0f-dd568397795c	fees.update	Fees	Update
053efc51-5d68-493e-9463-4a1bf18f3e48	fees.refund	Fees	Refund
ebe02472-e9c4-4989-a790-844163a82925	fees.export	Fees	Export
f7626507-7853-4068-9040-38e777f25125	fees.manage_structure	Fees	Manage Structure
6484136b-fe57-404d-a347-b69e93c13522	fees.view_receipt	Fees	View Receipt
b2552d1f-ede7-4eae-8c25-6a76e5a21d3d	fees.pay	Fees	Pay
4a4915f6-f177-463e-b39e-4da042aa8161	admissions.read	Admissions	Read
56873e03-3c87-4d82-8269-9e6aa3db3032	admissions.manage	Admissions	Manage
748d0cb1-56ff-4702-acb8-56dcb71ca5e7	hiring.read	Hiring	Read
2dba0a89-468b-4549-87a8-235671b1359b	hiring.manage	Hiring	Manage
4d94fe84-d560-491b-991c-e7178471a947	payroll.read	Payroll	Read
94334195-e94b-4573-9741-bdb8b6136ff9	payroll.manage	Payroll	Manage
ed1f3bdb-ad27-4f05-822d-b2fdaf075597	payroll.export	Payroll	Export
19e05924-5d4f-4757-81e6-1c37d4916abc	payroll.view_payslip	Payroll	View Payslip
2cc0b75a-d873-405a-a0c0-16db2fbc6b0c	library.read	Library	Read
51efca30-9d3f-4e11-a348-1dad485a5697	library.manage	Library	Manage
d86c4f72-d7de-4941-85fe-6961f64b2ea2	library.issue	Library	Issue
6bd00f42-381f-4896-8623-b5544b4b0b22	library.return	Library	Return
2320bed8-da22-4c89-b9fb-ff4b418f4a8c	library.view_history	Library	View History
d4633090-107d-403d-97c2-2d0d55c27c6b	transport.read	Transport	Read
19a8509d-03ca-4da6-9df3-0b92df7ad979	transport.manage	Transport	Manage
58072bb2-4d54-4ae8-b0c5-dc9f6097919f	transport.assign	Transport	Assign
5053f6ca-436a-451a-93ee-c4ad12438907	transport.export	Transport	Export
108b4f24-756f-41e2-ac39-931accb6ea93	leave.read	Leave	Read
a39d27bb-6303-421a-b7ce-72f7d99f5440	leave.create	Leave	Create
8ce60f0c-ccc9-4184-8e2b-c206676cf5c9	leave.update	Leave	Update
3ffa1f68-2f02-4324-978a-4c3f21f448ea	leave.approve	Leave	Approve
ba6d6b2d-f61e-4386-a25c-9970024aaaef	leave.reject	Leave	Reject
2d74c01e-2810-43d6-a55c-1ceab0927969	leave.export	Leave	Export
dd907879-5cbc-47f2-babb-ff4b2defdc6c	ptm.read	Ptm	Read
c1f47380-0996-4290-b87e-077540b9b9d7	ptm.create	Ptm	Create
00d3653e-11f3-4810-a61a-a1a332dfa2b9	ptm.update	Ptm	Update
7a8ba668-b0af-4363-a8e4-f144a7505a1c	ptm.manage	Ptm	Manage
d95430d1-61e7-454b-a558-484d7ad0660f	ptm.book	Ptm	Book
d5860be8-90b5-49c2-806f-afe0dd274de2	ptm.cancel	Ptm	Cancel
75a0377a-5654-48b7-beb7-de38c5ef3989	messages.read	Messages	Read
25ba7451-8f52-498b-a711-63e0912d3d96	messages.send	Messages	Send
36ee221c-e9c7-4883-af27-f9fb34aea280	messages.broadcast	Messages	Broadcast
0c3a68f5-f8cb-4bbf-88cb-fb99113df3d9	messages.delete	Messages	Delete
a78b2610-91d9-45d7-995d-acd45cdb2467	announcements.read	Announcements	Read
9fb4b34d-e40e-49a4-8792-2ea2bafd09e4	announcements.create	Announcements	Create
ae8acfa4-7627-4be5-850c-08e578e5120d	announcements.update	Announcements	Update
4a0bb4f9-c62e-43be-8b7f-43c655b8ef87	announcements.publish	Announcements	Publish
70057449-f1cc-4aae-9909-93b4eb1e5551	announcements.delete	Announcements	Delete
32e6f002-686e-476d-927c-ce33afae643f	reports.read	Reports	Read
00cef543-6279-4001-98e9-658888d00d4a	reports.create	Reports	Create
f7a4888a-cfde-423f-a37c-58da8a4a816d	reports.export	Reports	Export
4b679c02-a189-48d9-bcf6-08f2e43b0e3c	analytics.read	Analytics	Read
fe33b744-a71a-48df-a745-d3727090a952	analytics.export	Analytics	Export
f951e8be-b16f-4c3d-8f09-e9876962c656	ai_copilot.use	Ai Copilot	Use
4476b209-eac9-4a2d-80b4-0ea8b554062b	settings.read	Settings	Read
5d5c4f18-3fdf-4ee2-b1fa-0e68f890e91f	settings.update	Settings	Update
6d5b9fc5-f65f-4f3b-ad98-79e71525bf0c	users.manage	Users	Manage
be0fe4c5-0c0d-4b09-8c31-1a9eaa76ff8b	roles.manage	Roles	Manage
f1d29e73-9e39-42b6-8358-8ccd36b8db3b	users.impersonate	Users	Impersonate
a0e3be5c-00cf-4e73-9b65-3075c9eea5bd	permissions.manage	Permissions	Manage
ab630454-1125-4eaf-8b4a-6e61dd864ecc	school.configure	School	Configure
7816f54c-240a-4e69-b5ba-613841909a80	academic_year.manage	Academic Year	Manage
91546a63-0f5f-4386-8cec-15f79688a2ab	classes.configure	Classes	Configure
77e68e9d-b065-45b3-806e-81a05f877331	subjects.configure	Subjects	Configure
a60d00c1-f5a6-418d-b33e-82262a17f27f	profile.read	Profile	Read
e618d856-394d-4dd2-a082-1c6ad0e1a536	profile.update	Profile	Update
157f216b-29fc-4e27-b1f9-0037bc198653	profile.change_password	Profile	Change Password
49327f7a-a0dd-49c2-9ebe-5f18b1678222	profile.change_avatar	Profile	Change Avatar
b269cf3b-410b-48b6-9b98-a767a359bfca	class.students.read	Class	Students Read
76e4c1f5-1cb3-4f6c-b1d1-c826260ff287	class.attendance.read	Class	Attendance Read
f56acff4-9d19-4438-a35a-57696e8c2e4b	class.attendance.mark	Class	Attendance Mark
b90df2f5-b568-46cd-bfd1-7e39893e634b	class.attendance.update	Class	Attendance Update
6bbf4a74-2e94-49e8-83bb-4110c19f0e13	class.homework.monitor	Class	Homework Monitor
529daa10-dfbb-4401-80e8-fc9a363f3807	class.diary.manage	Class	Diary Manage
f5e90c0e-8733-43ac-879f-55c5fc15425a	class.leave.read	Class	Leave Read
404c9ddd-8025-4581-8f27-decf8f551a16	class.ptm.read	Class	Ptm Read
cbe13e0e-4693-45a0-8878-30ff3fdd825a	class.communication.send	Class	Communication Send
4539e17a-67ab-44cc-85f3-5e2d300899b2	class.analytics.read	Class	Analytics Read
cd940f62-f215-4901-bfec-f38cf7713515	class.announcements.create	Class	Announcements Create
402faa4a-dee4-4bb4-917d-b51fe11342bf	hiring.hire	Hiring	Hire
\.


--
-- Data for Name: pipeline_hiring_table; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.pipeline_hiring_table (id, school_id, candidate_no, candidate_name, role, department, qualification, experience, applied_on, interview_on, emp_id, status, phone, email, applied_for, subject_id, subject_name, resume_path, interview_at, interview_note, decided_by_user_id, decided_at) FROM stdin;
6e9930ad-f04b-41b7-b14a-bfd42ec42a73	26fc741e-7270-4f5a-98fd-63a548c315a3	CAN-2026-0031	aditya jain	Teacher	Science	Msc.	4	2026-10-31	2026-10-31	EMP-0037	Hired	7845962321	sdjldkajfk@gmail.com	teacher	036283e0-8f3b-4c55-9901-00fd922607fd	Biology	\N	\N		8859c8d9-d761-4ec3-bd79-8f4adae8eb45	2026-10-31 11:07:50.788479
\.


--
-- Data for Name: questionusagelog; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.questionusagelog (id, school_id, fingerprint, text, paper_id, class_name, subject, chapter, topic, qtype, marks, created_by, used_at) FROM stdin;
\.


--
-- Data for Name: reportcard; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.reportcard (id, school_id, title, metric, value, trend, tone) FROM stdin;
\.


--
-- Data for Name: role; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.role (id, codename, label, description, is_system) FROM stdin;
ffedd356-f752-411c-a857-25cd9734fefb	system_admin	System Admin	Platform administrator: unrestricted access, manages roles and grants.	t
4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	principal	Principal	Heads academics; approves papers, fee cards and payroll.	t
396ebfa4-f377-4dfd-b839-c98a79be5a09	vice_principal	Vice Principal	Deputy to the principal: timetable, discipline, approvals.	t
01428281-67d6-45f7-812f-3bc6d3310e88	hod	Head of Department	Leads a department's teachers, syllabus and results.	t
686f9b85-9087-40c8-bed8-651369cb3abf	teacher	Teacher	Teaching staff: classroom, homework, marks, attendance.	t
6f220a6c-5ac7-476a-aa2a-88c4d6fd7f82	class_teacher	Class Teacher	Owns one section: attendance register, diary, report cards.	t
c5871d62-fd0a-47b7-88ea-17e6b18b148f	subject_teacher	Subject Teacher	Teaches one subject across several classes.	t
18f215ab-603c-4280-9ea0-69d54b285084	accountant	Accountant	Fees, receipts, payroll and collection reports.	t
9ed7fcec-d186-4c2f-b466-8d264b98887c	librarian	Librarian	Catalogue, issues and returns.	t
30c1b546-d6be-476d-a28b-f9b8fa4a74f3	transport	Transport Manager	Buses, routes and stop assignments.	t
d96e7e61-4fcf-478a-aa8e-3af2da78754c	staff	Staff	Support staff: front office, lab, maintenance.	t
c43d1a51-bd5e-4ad6-a5cc-be2cf6e37862	student	Student	Learner login: own timetable, homework and fees.	t
52d627c1-d317-462c-b6df-a4da19d22472	guardian	Parent / Guardian	Parent login: their children's records only.	t
8a213533-674c-4ab7-9511-f49ef20ce50c	school_admin	School Admin	Runs one registered school: every permission inside that school only.	t
\.


--
-- Data for Name: rolepermission; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.rolepermission (id, role_id, permission_id) FROM stdin;
f8152b2e-3f24-4869-aedd-530215d8442d	ffedd356-f752-411c-a857-25cd9734fefb	4d386bdc-9a78-4215-a9c1-eb6d22b68b10
67672b36-865f-44f4-a654-5a0a85514afc	ffedd356-f752-411c-a857-25cd9734fefb	20e5c59f-7396-46dc-8297-142e40347332
cea5c937-6dac-4b97-9999-656d43b038f3	ffedd356-f752-411c-a857-25cd9734fefb	f274f4fd-5b74-48dd-96d2-1a276cc8c239
2ea8f1c6-2103-4cc3-a0ab-6573667cb9b6	ffedd356-f752-411c-a857-25cd9734fefb	90889445-d0ff-4cca-9bd4-a8da0b0fd45f
07efebb7-e90e-4a4a-b281-72c4ea8b411a	ffedd356-f752-411c-a857-25cd9734fefb	8aa3b220-a233-4ea0-be6b-7766c715f60f
af2b5655-35c9-4e78-9be6-8fe7ca7388fa	ffedd356-f752-411c-a857-25cd9734fefb	a3a2d2b2-4901-46b8-bfaf-163beede39e9
e2f32901-a224-45ef-998a-6b220b15081d	ffedd356-f752-411c-a857-25cd9734fefb	fc6dd1d5-140a-44ba-b630-59f1a988dae6
3872eca5-2eac-462e-b19f-539b5bdee223	ffedd356-f752-411c-a857-25cd9734fefb	8f0194fd-e080-4f98-b46f-71c75812e8c2
2d1a3fe0-2237-4ed8-891b-a03a41d5b19b	ffedd356-f752-411c-a857-25cd9734fefb	ef0ee95d-2607-4aa8-b8cf-267b94db76d1
98cb0e5d-5fe1-467f-bbce-4e3974e309c3	ffedd356-f752-411c-a857-25cd9734fefb	5c4f1a53-b5be-49c3-8639-e0ef8b62826a
5fde25ed-4af9-4075-a8e6-d580e069221e	ffedd356-f752-411c-a857-25cd9734fefb	fd1ac7c2-f3cb-46a1-8de8-411a81bb0b9a
0ca9f97c-66f3-4334-b325-cc09fcd45bfa	ffedd356-f752-411c-a857-25cd9734fefb	c88911a2-b1b8-496f-9c53-adea5384f7cf
a7f1371a-1dfa-47af-bb06-9e699dc8cb35	ffedd356-f752-411c-a857-25cd9734fefb	0a8c77b2-31ab-4db3-86cc-36136cfcf63f
443655a4-9f93-4600-8627-b4ed727c47a7	ffedd356-f752-411c-a857-25cd9734fefb	678de476-da63-428c-9a8c-8d0de781400b
794f7bca-4f9f-4c87-9edf-71870fd34fa1	ffedd356-f752-411c-a857-25cd9734fefb	9206f1af-e598-4228-a352-e8b71701f500
9531fc78-afb9-45a9-ad86-4d223d679bed	ffedd356-f752-411c-a857-25cd9734fefb	d7591f4b-217f-4d3b-a190-6fa9bde2e0db
fc377b97-64fc-4a5e-9cbc-1f6f9bac357b	ffedd356-f752-411c-a857-25cd9734fefb	52a2daaf-298d-41f8-b034-9b9352a00386
1a739cb5-06c0-4aa9-b708-daa8ee452db8	ffedd356-f752-411c-a857-25cd9734fefb	933f5bd1-6cdc-4d92-85fe-a13dfaa6b71c
42125e6f-753b-44ee-ada9-aca4edebd948	ffedd356-f752-411c-a857-25cd9734fefb	3a1b4156-55a1-446e-b188-df5e77dfd8b5
2cbcd658-9880-4da2-9716-b2cc9431dd96	ffedd356-f752-411c-a857-25cd9734fefb	f7876ae0-847a-46d0-896d-26a337f9605b
45f6e73b-a0ab-419a-b5a7-a7ab967758e2	ffedd356-f752-411c-a857-25cd9734fefb	67e8e39a-b946-4036-9071-6622ffcebcb0
2359fe28-7a8a-47a0-a3b4-49e42c299f33	ffedd356-f752-411c-a857-25cd9734fefb	f596816e-a0ac-4396-b526-c0cc7e4f1547
a9e17cf7-b151-4208-bf27-0c85f67d70c7	ffedd356-f752-411c-a857-25cd9734fefb	34efa491-5e0f-451b-9897-829b40376ae9
bf75f122-6bad-491d-83bb-1bd608324361	ffedd356-f752-411c-a857-25cd9734fefb	1d230fba-3517-4936-a3a3-65eb110b963d
47b4f5db-5485-42d7-be97-7230ade7bc69	ffedd356-f752-411c-a857-25cd9734fefb	6710a77c-e35a-4f4c-a1d8-bd2a480faf9b
dcd513a9-3af9-4da9-8ca8-39a411700590	ffedd356-f752-411c-a857-25cd9734fefb	879b5348-dc23-4238-9770-618fca34f404
84064dcb-0ff4-467f-9c43-f0c53b7150ef	ffedd356-f752-411c-a857-25cd9734fefb	f91b7933-b575-4783-bdeb-69883ff75b57
160f3252-b23d-470e-b8d4-80a5879755d0	ffedd356-f752-411c-a857-25cd9734fefb	c5b7095e-b795-438b-9455-d4eabba5fbaa
1648a174-ee0f-4958-b317-bcd28fbefd5a	ffedd356-f752-411c-a857-25cd9734fefb	f08197bb-10f5-4097-b737-96bdc77dd673
c4fc89f2-f944-4aaf-9240-041342499a97	ffedd356-f752-411c-a857-25cd9734fefb	8c413273-dd5d-4e54-a23c-f516044e9961
5858de59-7910-4ff2-92f7-17a0e24eb96a	ffedd356-f752-411c-a857-25cd9734fefb	b824f887-522b-42c3-bb6d-e9bf3fe2c68d
7832436c-4551-4df2-88ef-82a5fb8cae2e	ffedd356-f752-411c-a857-25cd9734fefb	c795a61c-1525-4603-bc85-d04be7098f69
94594538-cc4c-4b8f-941c-ec7e2a7c7718	ffedd356-f752-411c-a857-25cd9734fefb	eb624a8e-2ddc-4f3a-9f15-571996b861fc
95a3dba0-84d0-4a46-b18c-5ed16aa6fd9f	ffedd356-f752-411c-a857-25cd9734fefb	dc30661b-be68-476b-8fab-e75d843b454c
62bb1887-dcd7-4ed4-b235-96d6eff04e97	ffedd356-f752-411c-a857-25cd9734fefb	8494e31f-b5a4-4895-8600-5613daaf2e7b
56781935-fd00-4cf9-b8d9-ec486d9c2d60	ffedd356-f752-411c-a857-25cd9734fefb	2045a7fa-d8fe-4784-bda5-4bccf4d69809
31e00e28-3961-42f4-b07e-aa17ac65cd7b	ffedd356-f752-411c-a857-25cd9734fefb	27b4f7cc-d8d9-4b12-bb83-a47153e5d135
3a28df19-4054-4884-9e18-a34efbe16839	ffedd356-f752-411c-a857-25cd9734fefb	250dfee3-8da0-479e-aad8-2a74f24b9f9d
718eaa54-93ea-47e7-b6d1-d2767687e5ed	ffedd356-f752-411c-a857-25cd9734fefb	b2ba2fe1-84ba-4d59-ad57-f1872021589d
2c92d1a4-5342-4b23-a7fe-6bad3425177f	ffedd356-f752-411c-a857-25cd9734fefb	4202bfd2-c595-4d18-aa0f-80ae538e4fea
edd90f37-444a-423c-9ab9-f5d3c22ff0ab	ffedd356-f752-411c-a857-25cd9734fefb	76d1637a-aaf4-451b-b1d0-7849957a42a8
fe637a6d-4876-40b2-98bd-b753766de56b	ffedd356-f752-411c-a857-25cd9734fefb	e5395d8e-6cdc-4411-b2b5-835ad149e933
143255ce-c724-4ea7-8d38-164c5c5891c9	ffedd356-f752-411c-a857-25cd9734fefb	57d21fef-512f-43cb-9aa0-0bebae2f355e
a8e5c292-0ee7-4892-90c4-72850881a27c	ffedd356-f752-411c-a857-25cd9734fefb	a4be3422-b10b-4422-b513-fbdc9eeb864a
987e12c8-3d49-49aa-b915-58aaa0e7e5f5	ffedd356-f752-411c-a857-25cd9734fefb	db812fd9-919e-47e1-aa9d-7b0de37b9863
a6200738-1c3b-4308-b106-8919b7e3300b	ffedd356-f752-411c-a857-25cd9734fefb	050305b3-edec-407f-91e8-eb7f6e9fa1b3
b3749b47-5f48-4f6d-94ef-7fa39231649b	ffedd356-f752-411c-a857-25cd9734fefb	bf762354-ead7-4be6-a836-f57bd7df1c1d
f304e229-7e98-4ed3-a8a6-6ba67dc49c4c	ffedd356-f752-411c-a857-25cd9734fefb	044f2158-b337-4877-b82c-11dc936b716f
31e044c5-4d36-429a-b4ed-d466bf3be630	ffedd356-f752-411c-a857-25cd9734fefb	2a5a1c0d-47b4-4e9f-9ab4-b9106ed67a9d
59d8fe8f-3cde-45bc-856d-ff952758a454	ffedd356-f752-411c-a857-25cd9734fefb	f75c6bcc-c9ae-4a04-a8e0-f56d351009af
c800c0d6-02bc-49ab-9212-f28f60f7114c	ffedd356-f752-411c-a857-25cd9734fefb	8231e7d4-b4e8-495a-b881-3bfabbd85b67
c2325327-3212-496a-83e9-88748bb9d2a6	ffedd356-f752-411c-a857-25cd9734fefb	5199b83d-34c6-4a7c-9bf9-d140a27f93c8
ef782d2d-5998-42da-8880-478c8a14213e	ffedd356-f752-411c-a857-25cd9734fefb	e59e5d27-8afb-4b5f-9d8d-dc5c6f19708e
3a136098-d56a-4f02-9b61-b7211641be74	ffedd356-f752-411c-a857-25cd9734fefb	1cdef3b1-d9ec-4f0d-9b7f-e6e927643e9a
d0ec8780-11ca-4fed-9088-bbe95d9e1864	ffedd356-f752-411c-a857-25cd9734fefb	6a0ca14f-762d-4171-974e-c5870aa4076f
e1c1e41e-8158-41ef-85bf-d1baffac5563	ffedd356-f752-411c-a857-25cd9734fefb	bad99487-1598-4525-ad21-de5dce5a91dc
95590042-2edf-472e-911c-8c704d5dc819	ffedd356-f752-411c-a857-25cd9734fefb	a590fd62-ff70-4e2f-aeb0-caf4b535c746
a8e724e2-3a5d-46a7-9dd4-5be13efc4e8c	ffedd356-f752-411c-a857-25cd9734fefb	00ea86d7-62b3-4756-9abc-66dacc78c876
b8c7f029-1bf1-4a81-8b80-d41ca572fd1a	ffedd356-f752-411c-a857-25cd9734fefb	17665863-3735-46dc-96b5-2d9ebecff977
b3e20393-29b9-4614-8b0f-04118ad79dec	ffedd356-f752-411c-a857-25cd9734fefb	36876181-d912-41bd-b06a-60c741e04818
75ce06ad-5aac-41b9-bb8d-ed60d33c495d	ffedd356-f752-411c-a857-25cd9734fefb	6c32aa54-5304-4b8d-a2f2-2d822f61be12
2c7cfaa5-d8ec-4587-b4fc-0247de9a7e2b	ffedd356-f752-411c-a857-25cd9734fefb	110560c2-7eb4-4890-b004-659f0203dd83
e4afc319-7eae-45ab-9461-c57549bf4a67	ffedd356-f752-411c-a857-25cd9734fefb	91afb109-c9f5-448c-a236-3d7f88c0f293
f43e8986-aabb-45f6-93e7-2c26ae17a263	ffedd356-f752-411c-a857-25cd9734fefb	666022e6-ebb1-4567-b794-45b4c50c708f
41a4de2e-d422-4140-a322-b9978f503621	ffedd356-f752-411c-a857-25cd9734fefb	bb7bfcf6-f92a-4d61-9111-9f9806601c2a
8d8bea44-8a40-4efe-ac78-1f78c779b7d6	ffedd356-f752-411c-a857-25cd9734fefb	f2011e4a-07b4-4261-b2b5-f4539f8c416a
fbbfbb11-f7a9-4d85-ad15-135f234f0c8f	ffedd356-f752-411c-a857-25cd9734fefb	163342df-9367-4e54-ab5c-4a3b55a0eadf
145bd2c2-6b0a-4728-9ef0-75c548859fbc	ffedd356-f752-411c-a857-25cd9734fefb	0504f8e1-168a-4ff6-ab0f-dd568397795c
35fd287f-8bfa-471a-980c-86a25dd1281a	ffedd356-f752-411c-a857-25cd9734fefb	053efc51-5d68-493e-9463-4a1bf18f3e48
9da315fe-a46b-4037-a788-d3c785bc6393	ffedd356-f752-411c-a857-25cd9734fefb	ebe02472-e9c4-4989-a790-844163a82925
7a072838-e79c-4f1b-aedc-6d8b6ae077f4	ffedd356-f752-411c-a857-25cd9734fefb	f7626507-7853-4068-9040-38e777f25125
0a463df4-7ff0-4165-9d10-684118c74a09	ffedd356-f752-411c-a857-25cd9734fefb	6484136b-fe57-404d-a347-b69e93c13522
23265b4b-4c91-45d0-bc3a-d230c4fc4d72	ffedd356-f752-411c-a857-25cd9734fefb	b2552d1f-ede7-4eae-8c25-6a76e5a21d3d
b9583294-85fb-4238-ab22-60e2cdb5ffcc	ffedd356-f752-411c-a857-25cd9734fefb	4a4915f6-f177-463e-b39e-4da042aa8161
0fb7167f-0fb0-492f-8dab-6cb05f8b0d4c	ffedd356-f752-411c-a857-25cd9734fefb	56873e03-3c87-4d82-8269-9e6aa3db3032
ab04dab4-ff63-42e6-b0e7-5d5c1c15df81	ffedd356-f752-411c-a857-25cd9734fefb	748d0cb1-56ff-4702-acb8-56dcb71ca5e7
9364913c-edc8-481a-abf5-cd809affa4a4	ffedd356-f752-411c-a857-25cd9734fefb	2dba0a89-468b-4549-87a8-235671b1359b
b08ccfc1-fedf-456e-8170-1091582cf16f	ffedd356-f752-411c-a857-25cd9734fefb	4d94fe84-d560-491b-991c-e7178471a947
91834624-0159-4de7-9e9e-9ed1756e7dc1	ffedd356-f752-411c-a857-25cd9734fefb	94334195-e94b-4573-9741-bdb8b6136ff9
ec26152a-94cb-42eb-909d-6417a5755325	ffedd356-f752-411c-a857-25cd9734fefb	ed1f3bdb-ad27-4f05-822d-b2fdaf075597
bbeff319-1121-4c8b-ab30-870d98e8bf36	ffedd356-f752-411c-a857-25cd9734fefb	19e05924-5d4f-4757-81e6-1c37d4916abc
1eeb71e6-cd90-4438-9ff9-117171418dc8	ffedd356-f752-411c-a857-25cd9734fefb	2cc0b75a-d873-405a-a0c0-16db2fbc6b0c
f6489be9-782c-40ce-85ee-002b91f565dd	ffedd356-f752-411c-a857-25cd9734fefb	51efca30-9d3f-4e11-a348-1dad485a5697
5be60291-f258-4c23-a15a-03d8c4f722b9	ffedd356-f752-411c-a857-25cd9734fefb	d86c4f72-d7de-4941-85fe-6961f64b2ea2
95835578-7b25-474b-8958-9b957e366eea	ffedd356-f752-411c-a857-25cd9734fefb	6bd00f42-381f-4896-8623-b5544b4b0b22
b43d6424-cafb-4722-bda6-04981c665de7	ffedd356-f752-411c-a857-25cd9734fefb	2320bed8-da22-4c89-b9fb-ff4b418f4a8c
ef40adcf-e17a-4198-9678-5bf3f0c2a07c	ffedd356-f752-411c-a857-25cd9734fefb	d4633090-107d-403d-97c2-2d0d55c27c6b
04a79048-35e1-4ecb-829c-7a35829ef69e	ffedd356-f752-411c-a857-25cd9734fefb	19a8509d-03ca-4da6-9df3-0b92df7ad979
e5c808d0-dab1-4616-9f7e-e342ab58989f	ffedd356-f752-411c-a857-25cd9734fefb	58072bb2-4d54-4ae8-b0c5-dc9f6097919f
ae577674-57d2-490b-8793-41347056d5a2	ffedd356-f752-411c-a857-25cd9734fefb	5053f6ca-436a-451a-93ee-c4ad12438907
d5993d0a-6c1d-4e08-ae0f-0e2451d1081f	ffedd356-f752-411c-a857-25cd9734fefb	108b4f24-756f-41e2-ac39-931accb6ea93
295dccfe-ae18-44c8-ba61-588535af08bd	ffedd356-f752-411c-a857-25cd9734fefb	a39d27bb-6303-421a-b7ce-72f7d99f5440
e81c4b6b-fe11-4c25-86cd-cacf2be6e571	ffedd356-f752-411c-a857-25cd9734fefb	8ce60f0c-ccc9-4184-8e2b-c206676cf5c9
5ab53f37-523e-4f87-b99f-cee744fe88be	ffedd356-f752-411c-a857-25cd9734fefb	3ffa1f68-2f02-4324-978a-4c3f21f448ea
bc549a75-b854-4c32-a0a0-7fc2238c03c2	ffedd356-f752-411c-a857-25cd9734fefb	ba6d6b2d-f61e-4386-a25c-9970024aaaef
7fdda891-7dcc-450d-9e0b-d2a23d2397fd	ffedd356-f752-411c-a857-25cd9734fefb	2d74c01e-2810-43d6-a55c-1ceab0927969
90cb01f5-199e-439d-86a9-3bd0a41d2083	ffedd356-f752-411c-a857-25cd9734fefb	dd907879-5cbc-47f2-babb-ff4b2defdc6c
e21df09a-5eb2-466f-8ebe-82d722537a2f	ffedd356-f752-411c-a857-25cd9734fefb	c1f47380-0996-4290-b87e-077540b9b9d7
347d8404-ac27-4e1e-b523-7b3f321eb579	ffedd356-f752-411c-a857-25cd9734fefb	00d3653e-11f3-4810-a61a-a1a332dfa2b9
f54132d2-8142-484d-9ce9-7c9bae3fa6c7	ffedd356-f752-411c-a857-25cd9734fefb	7a8ba668-b0af-4363-a8e4-f144a7505a1c
08d4bc3e-169e-4c9b-9433-b7992d847935	ffedd356-f752-411c-a857-25cd9734fefb	d95430d1-61e7-454b-a558-484d7ad0660f
df0e76fc-fe87-478b-bd46-498d6a3d0dbc	ffedd356-f752-411c-a857-25cd9734fefb	d5860be8-90b5-49c2-806f-afe0dd274de2
f98ec2c6-caa9-4c62-82f0-d61094ea8669	ffedd356-f752-411c-a857-25cd9734fefb	75a0377a-5654-48b7-beb7-de38c5ef3989
af209438-155e-40ce-8a99-69c022be19e1	ffedd356-f752-411c-a857-25cd9734fefb	25ba7451-8f52-498b-a711-63e0912d3d96
264a111a-0780-41bd-b56f-e364df7c36be	ffedd356-f752-411c-a857-25cd9734fefb	36ee221c-e9c7-4883-af27-f9fb34aea280
72dbf2f2-2b9a-4c33-b246-3ad10a76af19	ffedd356-f752-411c-a857-25cd9734fefb	0c3a68f5-f8cb-4bbf-88cb-fb99113df3d9
c89f225c-b1ed-4a9a-b394-1c6a918b8e93	ffedd356-f752-411c-a857-25cd9734fefb	a78b2610-91d9-45d7-995d-acd45cdb2467
908af915-1feb-456c-9ca7-dc75d353d8d8	ffedd356-f752-411c-a857-25cd9734fefb	9fb4b34d-e40e-49a4-8792-2ea2bafd09e4
18d81af7-95f0-4379-9615-1fff13d61742	ffedd356-f752-411c-a857-25cd9734fefb	ae8acfa4-7627-4be5-850c-08e578e5120d
8ff7264b-727c-4726-ba5a-dccf51e3f644	ffedd356-f752-411c-a857-25cd9734fefb	4a0bb4f9-c62e-43be-8b7f-43c655b8ef87
f885c265-ff52-43e7-a898-cf5372e355c2	ffedd356-f752-411c-a857-25cd9734fefb	70057449-f1cc-4aae-9909-93b4eb1e5551
20eb57c6-64a5-4fbd-a082-6ba82216b74b	ffedd356-f752-411c-a857-25cd9734fefb	32e6f002-686e-476d-927c-ce33afae643f
1c810625-91c1-4195-ab1c-9a0f3895495f	ffedd356-f752-411c-a857-25cd9734fefb	00cef543-6279-4001-98e9-658888d00d4a
4b5d4abb-fa34-4757-8f2e-07662b3057d6	ffedd356-f752-411c-a857-25cd9734fefb	f7a4888a-cfde-423f-a37c-58da8a4a816d
1fefbbc8-ed71-4c5a-b906-6027e3114e83	ffedd356-f752-411c-a857-25cd9734fefb	4b679c02-a189-48d9-bcf6-08f2e43b0e3c
797aaf3b-c0f1-4ba7-a9c1-18ff918ed0e9	ffedd356-f752-411c-a857-25cd9734fefb	fe33b744-a71a-48df-a745-d3727090a952
a437eea3-c8cd-4434-9c29-70239b68ce0a	ffedd356-f752-411c-a857-25cd9734fefb	f951e8be-b16f-4c3d-8f09-e9876962c656
35e87d02-9454-4c23-9eb3-02fc0625dbeb	ffedd356-f752-411c-a857-25cd9734fefb	4476b209-eac9-4a2d-80b4-0ea8b554062b
5cd5c216-4f2f-4176-b124-aa4e41aba3b3	ffedd356-f752-411c-a857-25cd9734fefb	5d5c4f18-3fdf-4ee2-b1fa-0e68f890e91f
efdd81c2-2b33-4c72-8d18-c0142a8ec529	ffedd356-f752-411c-a857-25cd9734fefb	6d5b9fc5-f65f-4f3b-ad98-79e71525bf0c
ddefecfa-6be2-415a-a562-dd5b37b6c14e	ffedd356-f752-411c-a857-25cd9734fefb	be0fe4c5-0c0d-4b09-8c31-1a9eaa76ff8b
1a266538-09a5-4ea0-baeb-888e46b63f2b	ffedd356-f752-411c-a857-25cd9734fefb	f1d29e73-9e39-42b6-8358-8ccd36b8db3b
34c8ede6-8a59-48c5-8543-75445892c81e	ffedd356-f752-411c-a857-25cd9734fefb	a0e3be5c-00cf-4e73-9b65-3075c9eea5bd
bea4af9b-6484-43e7-b145-f3b697675e66	ffedd356-f752-411c-a857-25cd9734fefb	ab630454-1125-4eaf-8b4a-6e61dd864ecc
0ec6c21d-dce6-4580-8d03-298484cf9e1d	ffedd356-f752-411c-a857-25cd9734fefb	7816f54c-240a-4e69-b5ba-613841909a80
95f9b4dd-bec1-496c-b2a6-9d372e0839a0	ffedd356-f752-411c-a857-25cd9734fefb	91546a63-0f5f-4386-8cec-15f79688a2ab
94718faa-0c72-458b-86cd-29de22150757	ffedd356-f752-411c-a857-25cd9734fefb	77e68e9d-b065-45b3-806e-81a05f877331
e0e96060-c0d3-485f-91d1-3c7f8700f0a7	ffedd356-f752-411c-a857-25cd9734fefb	a60d00c1-f5a6-418d-b33e-82262a17f27f
32045102-6f9a-40a6-8c16-da781cd577a8	ffedd356-f752-411c-a857-25cd9734fefb	e618d856-394d-4dd2-a082-1c6ad0e1a536
e1f77f84-f555-4e95-9823-6d66053e34d5	ffedd356-f752-411c-a857-25cd9734fefb	157f216b-29fc-4e27-b1f9-0037bc198653
7a9dfbb1-4ad1-4431-a643-a4a331d582d9	ffedd356-f752-411c-a857-25cd9734fefb	49327f7a-a0dd-49c2-9ebe-5f18b1678222
16f5bce6-d1eb-400d-831a-357609d09e64	ffedd356-f752-411c-a857-25cd9734fefb	b269cf3b-410b-48b6-9b98-a767a359bfca
15709437-b639-4d01-9e71-b9c0d4fd502f	ffedd356-f752-411c-a857-25cd9734fefb	76e4c1f5-1cb3-4f6c-b1d1-c826260ff287
adca8310-d6ba-4ba8-973c-eb77fd346f03	ffedd356-f752-411c-a857-25cd9734fefb	f56acff4-9d19-4438-a35a-57696e8c2e4b
a1cee068-9e89-452a-9b60-6c26dc173d09	ffedd356-f752-411c-a857-25cd9734fefb	b90df2f5-b568-46cd-bfd1-7e39893e634b
e80d052c-3113-48ad-a9cb-7d078b2aec03	ffedd356-f752-411c-a857-25cd9734fefb	6bbf4a74-2e94-49e8-83bb-4110c19f0e13
5b8c7a60-1969-4c6b-9cc3-8c5dc319518f	ffedd356-f752-411c-a857-25cd9734fefb	529daa10-dfbb-4401-80e8-fc9a363f3807
8c2097d5-940d-46a3-98fe-ba1a2925c477	ffedd356-f752-411c-a857-25cd9734fefb	f5e90c0e-8733-43ac-879f-55c5fc15425a
9e482179-f0c0-491a-b2e7-0b9335c6e228	ffedd356-f752-411c-a857-25cd9734fefb	404c9ddd-8025-4581-8f27-decf8f551a16
77747fb0-0001-4462-ac40-5c012126031d	ffedd356-f752-411c-a857-25cd9734fefb	cbe13e0e-4693-45a0-8878-30ff3fdd825a
c66b0816-d1af-4b42-8930-d6ba5e4048f3	ffedd356-f752-411c-a857-25cd9734fefb	4539e17a-67ab-44cc-85f3-5e2d300899b2
7c5da3ca-8fdd-4464-960f-d5c6bf9db96c	ffedd356-f752-411c-a857-25cd9734fefb	cd940f62-f215-4901-bfec-f38cf7713515
764f0874-9795-4d5c-a508-e20671a964e2	8a213533-674c-4ab7-9511-f49ef20ce50c	4d386bdc-9a78-4215-a9c1-eb6d22b68b10
3238704c-4db8-46b9-ae0a-adb4ccf8a5de	8a213533-674c-4ab7-9511-f49ef20ce50c	20e5c59f-7396-46dc-8297-142e40347332
bc0c8475-d32e-4656-be5c-b1330fc1e4dd	8a213533-674c-4ab7-9511-f49ef20ce50c	f274f4fd-5b74-48dd-96d2-1a276cc8c239
2489ca33-be70-4a4a-aa52-8d147ef41264	8a213533-674c-4ab7-9511-f49ef20ce50c	90889445-d0ff-4cca-9bd4-a8da0b0fd45f
14f3a8ec-553c-4584-bd12-13825e4d3cb5	8a213533-674c-4ab7-9511-f49ef20ce50c	8aa3b220-a233-4ea0-be6b-7766c715f60f
66ad1d7f-36ac-4a86-a66d-df77dc13b9a9	8a213533-674c-4ab7-9511-f49ef20ce50c	a3a2d2b2-4901-46b8-bfaf-163beede39e9
56288359-a80a-4e07-acbf-99724484c507	8a213533-674c-4ab7-9511-f49ef20ce50c	fc6dd1d5-140a-44ba-b630-59f1a988dae6
698fd357-7f91-45c0-b8c8-13f9959d4aa9	8a213533-674c-4ab7-9511-f49ef20ce50c	8f0194fd-e080-4f98-b46f-71c75812e8c2
e7da515e-f7b6-478e-9dd5-d83e6f0f0d87	8a213533-674c-4ab7-9511-f49ef20ce50c	ef0ee95d-2607-4aa8-b8cf-267b94db76d1
7ccf0d63-2912-4734-bed9-614c40fd2e88	8a213533-674c-4ab7-9511-f49ef20ce50c	5c4f1a53-b5be-49c3-8639-e0ef8b62826a
3cda415b-3a8c-41de-8056-a6ebe9ea3a75	8a213533-674c-4ab7-9511-f49ef20ce50c	fd1ac7c2-f3cb-46a1-8de8-411a81bb0b9a
442e8a95-f2ca-4aa5-b1d8-6a6928146d38	8a213533-674c-4ab7-9511-f49ef20ce50c	c88911a2-b1b8-496f-9c53-adea5384f7cf
3f7d1072-c1e7-48b2-a639-14e0bf8e78ab	8a213533-674c-4ab7-9511-f49ef20ce50c	0a8c77b2-31ab-4db3-86cc-36136cfcf63f
4c1738f8-826a-4bb4-a20a-393fb5b1a81f	8a213533-674c-4ab7-9511-f49ef20ce50c	678de476-da63-428c-9a8c-8d0de781400b
e6999d2c-6595-48b9-a08e-f58bf90c8bed	8a213533-674c-4ab7-9511-f49ef20ce50c	9206f1af-e598-4228-a352-e8b71701f500
86d8dc9a-a3fe-480c-a832-506dc79b9fb0	8a213533-674c-4ab7-9511-f49ef20ce50c	d7591f4b-217f-4d3b-a190-6fa9bde2e0db
fa97d171-d197-48b7-816a-dfa8bcae025e	8a213533-674c-4ab7-9511-f49ef20ce50c	52a2daaf-298d-41f8-b034-9b9352a00386
f1036eda-36d1-4c50-81fd-c2bedbc45a2d	8a213533-674c-4ab7-9511-f49ef20ce50c	933f5bd1-6cdc-4d92-85fe-a13dfaa6b71c
f5497873-9955-4a9c-bd03-4316eca61974	8a213533-674c-4ab7-9511-f49ef20ce50c	3a1b4156-55a1-446e-b188-df5e77dfd8b5
b89269d5-04db-4717-a091-f57147886df5	8a213533-674c-4ab7-9511-f49ef20ce50c	f7876ae0-847a-46d0-896d-26a337f9605b
60655dd3-5bad-4be3-8162-c5e4e80b6b55	8a213533-674c-4ab7-9511-f49ef20ce50c	67e8e39a-b946-4036-9071-6622ffcebcb0
47ec1df5-1d5a-4b94-84eb-4784bf9a3666	8a213533-674c-4ab7-9511-f49ef20ce50c	f596816e-a0ac-4396-b526-c0cc7e4f1547
d65a8758-1c1a-4f99-addc-d5bd7e1089e4	8a213533-674c-4ab7-9511-f49ef20ce50c	34efa491-5e0f-451b-9897-829b40376ae9
39a79b24-b704-4355-ac9b-ee9d2d8e9d09	8a213533-674c-4ab7-9511-f49ef20ce50c	1d230fba-3517-4936-a3a3-65eb110b963d
fd58bb4d-56ed-4fff-959a-82f735c3e0c6	8a213533-674c-4ab7-9511-f49ef20ce50c	6710a77c-e35a-4f4c-a1d8-bd2a480faf9b
689888d6-4f1f-462b-98b5-95f3c8ac844a	8a213533-674c-4ab7-9511-f49ef20ce50c	879b5348-dc23-4238-9770-618fca34f404
88357708-e806-4df9-a157-d664609f6a36	8a213533-674c-4ab7-9511-f49ef20ce50c	f91b7933-b575-4783-bdeb-69883ff75b57
4583357f-2377-41c4-87af-e65ae3c6bac8	8a213533-674c-4ab7-9511-f49ef20ce50c	c5b7095e-b795-438b-9455-d4eabba5fbaa
a1836b14-0c34-40e5-a1e3-ab7cd193b463	8a213533-674c-4ab7-9511-f49ef20ce50c	f08197bb-10f5-4097-b737-96bdc77dd673
3c874881-2149-4f43-a993-03ea6af9132c	8a213533-674c-4ab7-9511-f49ef20ce50c	8c413273-dd5d-4e54-a23c-f516044e9961
30a87f6c-0cf6-4ae8-8326-05c6e4813aae	8a213533-674c-4ab7-9511-f49ef20ce50c	b824f887-522b-42c3-bb6d-e9bf3fe2c68d
2aa5a0f2-5d81-4c66-af1b-384aaaa87dbf	8a213533-674c-4ab7-9511-f49ef20ce50c	c795a61c-1525-4603-bc85-d04be7098f69
0f4896de-4302-4cc3-b4e9-6e7903d5e819	8a213533-674c-4ab7-9511-f49ef20ce50c	eb624a8e-2ddc-4f3a-9f15-571996b861fc
058b885b-52ab-4ed8-a41d-32db58c9e5ac	8a213533-674c-4ab7-9511-f49ef20ce50c	dc30661b-be68-476b-8fab-e75d843b454c
7a1cd8bc-e786-4bf6-95b2-baf19bd8ce63	8a213533-674c-4ab7-9511-f49ef20ce50c	8494e31f-b5a4-4895-8600-5613daaf2e7b
d59b8ca2-05cc-452d-8105-727d7bb7803e	8a213533-674c-4ab7-9511-f49ef20ce50c	2045a7fa-d8fe-4784-bda5-4bccf4d69809
0e51f672-9f5f-415d-a578-6608f94a21d3	8a213533-674c-4ab7-9511-f49ef20ce50c	27b4f7cc-d8d9-4b12-bb83-a47153e5d135
74ff6fab-0923-4173-a841-a3d0a8a4e75b	8a213533-674c-4ab7-9511-f49ef20ce50c	250dfee3-8da0-479e-aad8-2a74f24b9f9d
7ec8da86-eb84-4346-a2f4-a4fea08c7376	8a213533-674c-4ab7-9511-f49ef20ce50c	b2ba2fe1-84ba-4d59-ad57-f1872021589d
9c1e0758-a097-4eda-bb7d-1b465d5110ba	8a213533-674c-4ab7-9511-f49ef20ce50c	4202bfd2-c595-4d18-aa0f-80ae538e4fea
b7da0626-44b1-46cf-abb9-d5341ae0335f	8a213533-674c-4ab7-9511-f49ef20ce50c	76d1637a-aaf4-451b-b1d0-7849957a42a8
34f918c8-63a3-47fe-bda2-3dae06549df3	8a213533-674c-4ab7-9511-f49ef20ce50c	e5395d8e-6cdc-4411-b2b5-835ad149e933
ca84470d-01c5-4164-8a7c-1e8943ffa61d	8a213533-674c-4ab7-9511-f49ef20ce50c	57d21fef-512f-43cb-9aa0-0bebae2f355e
f6e28850-0660-4f23-a482-ea1b5274aea8	8a213533-674c-4ab7-9511-f49ef20ce50c	a4be3422-b10b-4422-b513-fbdc9eeb864a
4cdb8592-1cc9-4c83-b0c7-2ae6daead9c0	8a213533-674c-4ab7-9511-f49ef20ce50c	db812fd9-919e-47e1-aa9d-7b0de37b9863
b8435773-d6a7-4d22-8c80-ff6010813277	8a213533-674c-4ab7-9511-f49ef20ce50c	050305b3-edec-407f-91e8-eb7f6e9fa1b3
4b077fd9-2d62-4f96-b565-1d19560e2fed	8a213533-674c-4ab7-9511-f49ef20ce50c	bf762354-ead7-4be6-a836-f57bd7df1c1d
45056986-b230-417d-b406-7ad8f59d225c	8a213533-674c-4ab7-9511-f49ef20ce50c	044f2158-b337-4877-b82c-11dc936b716f
d322471e-b23b-4263-8c8a-59f96806b26b	8a213533-674c-4ab7-9511-f49ef20ce50c	2a5a1c0d-47b4-4e9f-9ab4-b9106ed67a9d
2915795e-526f-4581-8b77-b01af9ec9a4d	8a213533-674c-4ab7-9511-f49ef20ce50c	f75c6bcc-c9ae-4a04-a8e0-f56d351009af
597f5f28-0a51-4e8d-85cf-51dbdb1baf3f	8a213533-674c-4ab7-9511-f49ef20ce50c	8231e7d4-b4e8-495a-b881-3bfabbd85b67
bd0d56f2-07f3-48ed-8ecc-0123af9059bb	8a213533-674c-4ab7-9511-f49ef20ce50c	5199b83d-34c6-4a7c-9bf9-d140a27f93c8
6ce4f45e-7ce8-4bb9-80d8-14219585ad2e	8a213533-674c-4ab7-9511-f49ef20ce50c	e59e5d27-8afb-4b5f-9d8d-dc5c6f19708e
b63fc086-576d-4128-9201-d46718c2f7f8	8a213533-674c-4ab7-9511-f49ef20ce50c	1cdef3b1-d9ec-4f0d-9b7f-e6e927643e9a
45a80bf0-e05d-4cbd-8d84-a48153e49585	8a213533-674c-4ab7-9511-f49ef20ce50c	6a0ca14f-762d-4171-974e-c5870aa4076f
28983da6-8613-4029-851d-053924d0ab26	8a213533-674c-4ab7-9511-f49ef20ce50c	bad99487-1598-4525-ad21-de5dce5a91dc
23f10e7a-29c0-42de-8e65-de7973cad4e8	8a213533-674c-4ab7-9511-f49ef20ce50c	a590fd62-ff70-4e2f-aeb0-caf4b535c746
42bc7d98-39b6-46ad-a8cd-ff774ba0eca4	8a213533-674c-4ab7-9511-f49ef20ce50c	00ea86d7-62b3-4756-9abc-66dacc78c876
9f618447-6e89-4fbe-9667-5b63c18e54da	8a213533-674c-4ab7-9511-f49ef20ce50c	17665863-3735-46dc-96b5-2d9ebecff977
2b80af2f-911e-4069-a9e0-855c881c44b8	8a213533-674c-4ab7-9511-f49ef20ce50c	36876181-d912-41bd-b06a-60c741e04818
9e3f2ce5-758d-490e-8ac2-110129a9e503	8a213533-674c-4ab7-9511-f49ef20ce50c	6c32aa54-5304-4b8d-a2f2-2d822f61be12
6ce76482-cc5f-4981-b819-778a3834527f	8a213533-674c-4ab7-9511-f49ef20ce50c	110560c2-7eb4-4890-b004-659f0203dd83
94e81ca1-7025-43c1-a786-ffde5cc9a302	8a213533-674c-4ab7-9511-f49ef20ce50c	91afb109-c9f5-448c-a236-3d7f88c0f293
cdbbff91-187c-45aa-a9ed-286f3c61c99c	8a213533-674c-4ab7-9511-f49ef20ce50c	666022e6-ebb1-4567-b794-45b4c50c708f
ed4b792e-cd37-47d0-874a-f8613795c5b6	8a213533-674c-4ab7-9511-f49ef20ce50c	bb7bfcf6-f92a-4d61-9111-9f9806601c2a
b239291a-a3e1-409d-97bc-e0caf9cf27e1	8a213533-674c-4ab7-9511-f49ef20ce50c	f2011e4a-07b4-4261-b2b5-f4539f8c416a
9eaa50d3-f846-4901-8582-b4e28b5834a6	8a213533-674c-4ab7-9511-f49ef20ce50c	163342df-9367-4e54-ab5c-4a3b55a0eadf
eb43de83-4311-4440-87ec-7c75f21a465d	8a213533-674c-4ab7-9511-f49ef20ce50c	0504f8e1-168a-4ff6-ab0f-dd568397795c
291bec8e-4d04-4d87-8678-e4bc198cf235	8a213533-674c-4ab7-9511-f49ef20ce50c	053efc51-5d68-493e-9463-4a1bf18f3e48
65b9b284-28d7-43e8-8b0c-f05c3d6c3132	8a213533-674c-4ab7-9511-f49ef20ce50c	ebe02472-e9c4-4989-a790-844163a82925
85dadb07-ecc9-42fb-862f-e229a3cd2a36	8a213533-674c-4ab7-9511-f49ef20ce50c	f7626507-7853-4068-9040-38e777f25125
96745fa5-e30b-4c3b-97b3-f7355954db1b	8a213533-674c-4ab7-9511-f49ef20ce50c	6484136b-fe57-404d-a347-b69e93c13522
da553fe2-86b4-48ca-9c03-fd7f7e659340	8a213533-674c-4ab7-9511-f49ef20ce50c	b2552d1f-ede7-4eae-8c25-6a76e5a21d3d
f346b7b5-ba30-44af-8a4e-c30fc1408e67	8a213533-674c-4ab7-9511-f49ef20ce50c	4a4915f6-f177-463e-b39e-4da042aa8161
1bf7dc9d-7e4f-496d-a1f3-ad08b77a0116	8a213533-674c-4ab7-9511-f49ef20ce50c	56873e03-3c87-4d82-8269-9e6aa3db3032
d1f0ad7f-dbc8-4836-b3bc-c73203022cb0	8a213533-674c-4ab7-9511-f49ef20ce50c	748d0cb1-56ff-4702-acb8-56dcb71ca5e7
076c66a2-6de3-4b48-a328-31d29149faa2	8a213533-674c-4ab7-9511-f49ef20ce50c	2dba0a89-468b-4549-87a8-235671b1359b
7ed254ce-f830-4a9a-8c68-d5d5e57c9009	8a213533-674c-4ab7-9511-f49ef20ce50c	4d94fe84-d560-491b-991c-e7178471a947
29783f50-48d8-4d0e-ad84-e2b9b02b5763	8a213533-674c-4ab7-9511-f49ef20ce50c	94334195-e94b-4573-9741-bdb8b6136ff9
b1e2f11e-adac-4e4e-9f3a-518dd4b0d57a	8a213533-674c-4ab7-9511-f49ef20ce50c	ed1f3bdb-ad27-4f05-822d-b2fdaf075597
742da222-30d5-47af-a371-8c6c3215e206	8a213533-674c-4ab7-9511-f49ef20ce50c	19e05924-5d4f-4757-81e6-1c37d4916abc
8beede68-7f19-4f93-85e8-0d0418888042	8a213533-674c-4ab7-9511-f49ef20ce50c	2cc0b75a-d873-405a-a0c0-16db2fbc6b0c
51b8282b-9c71-41e3-9542-f1119ebb7949	8a213533-674c-4ab7-9511-f49ef20ce50c	51efca30-9d3f-4e11-a348-1dad485a5697
90709c00-2682-4f1d-9841-0e7911547577	8a213533-674c-4ab7-9511-f49ef20ce50c	d86c4f72-d7de-4941-85fe-6961f64b2ea2
10bf8f65-820a-4483-a108-875f758e9b66	8a213533-674c-4ab7-9511-f49ef20ce50c	6bd00f42-381f-4896-8623-b5544b4b0b22
e1aad77d-f49b-46e6-a0f7-96d7595792d1	8a213533-674c-4ab7-9511-f49ef20ce50c	2320bed8-da22-4c89-b9fb-ff4b418f4a8c
7bc251c9-5b60-4b82-9f39-f64649dd839c	8a213533-674c-4ab7-9511-f49ef20ce50c	d4633090-107d-403d-97c2-2d0d55c27c6b
065e04e0-348b-4e15-b6b5-6fb5da18b3c9	8a213533-674c-4ab7-9511-f49ef20ce50c	19a8509d-03ca-4da6-9df3-0b92df7ad979
04c87645-abde-4e28-aa15-29918dd34d42	8a213533-674c-4ab7-9511-f49ef20ce50c	58072bb2-4d54-4ae8-b0c5-dc9f6097919f
273111dc-8e63-46c8-a354-c994aaf031fc	8a213533-674c-4ab7-9511-f49ef20ce50c	5053f6ca-436a-451a-93ee-c4ad12438907
9f805852-de8a-462e-82a8-85ca9e543c06	8a213533-674c-4ab7-9511-f49ef20ce50c	108b4f24-756f-41e2-ac39-931accb6ea93
e61d2611-37e5-4995-af60-a2275861eca5	8a213533-674c-4ab7-9511-f49ef20ce50c	a39d27bb-6303-421a-b7ce-72f7d99f5440
9689b2f3-b0d1-4e7f-bfd3-c680e67ab48b	8a213533-674c-4ab7-9511-f49ef20ce50c	8ce60f0c-ccc9-4184-8e2b-c206676cf5c9
827e7894-09ab-4183-807b-9c5f8606aacd	8a213533-674c-4ab7-9511-f49ef20ce50c	3ffa1f68-2f02-4324-978a-4c3f21f448ea
8572e718-7f3c-43f8-b629-9bb64cce0a16	8a213533-674c-4ab7-9511-f49ef20ce50c	ba6d6b2d-f61e-4386-a25c-9970024aaaef
af15044c-5b33-4d27-ae31-9a222bbba4b5	8a213533-674c-4ab7-9511-f49ef20ce50c	2d74c01e-2810-43d6-a55c-1ceab0927969
b1514551-56b3-48b3-b52a-dbdd2ec8973c	8a213533-674c-4ab7-9511-f49ef20ce50c	dd907879-5cbc-47f2-babb-ff4b2defdc6c
3a9d52fa-d909-4188-8c12-dc364aade4c3	8a213533-674c-4ab7-9511-f49ef20ce50c	c1f47380-0996-4290-b87e-077540b9b9d7
9ea03834-d6cf-4c31-afc8-f28d36d87092	8a213533-674c-4ab7-9511-f49ef20ce50c	00d3653e-11f3-4810-a61a-a1a332dfa2b9
bb249f0e-1cc8-4091-8368-496a9351fb0d	8a213533-674c-4ab7-9511-f49ef20ce50c	7a8ba668-b0af-4363-a8e4-f144a7505a1c
c02440f1-c124-4f1d-a202-0d7b3a414fa2	8a213533-674c-4ab7-9511-f49ef20ce50c	d95430d1-61e7-454b-a558-484d7ad0660f
ad5b08f6-0f57-4e12-b32e-76d5681d3778	8a213533-674c-4ab7-9511-f49ef20ce50c	d5860be8-90b5-49c2-806f-afe0dd274de2
0807a925-4654-4ee6-baa6-c177f1290859	8a213533-674c-4ab7-9511-f49ef20ce50c	75a0377a-5654-48b7-beb7-de38c5ef3989
e4ca35b2-fccf-497b-a0b0-16e778acd998	8a213533-674c-4ab7-9511-f49ef20ce50c	25ba7451-8f52-498b-a711-63e0912d3d96
ebecb899-268c-418d-a2f2-7a59e780df0b	8a213533-674c-4ab7-9511-f49ef20ce50c	36ee221c-e9c7-4883-af27-f9fb34aea280
19f50de5-1e61-4aab-a36a-4e5e16d21c97	8a213533-674c-4ab7-9511-f49ef20ce50c	0c3a68f5-f8cb-4bbf-88cb-fb99113df3d9
a4655c66-b059-4c30-8bc4-1469d48fcdf8	8a213533-674c-4ab7-9511-f49ef20ce50c	a78b2610-91d9-45d7-995d-acd45cdb2467
df9aa7e6-d858-4941-8a3f-3e55b6854ef4	8a213533-674c-4ab7-9511-f49ef20ce50c	9fb4b34d-e40e-49a4-8792-2ea2bafd09e4
2d495245-5b47-406e-aa79-0ee4967c1afe	8a213533-674c-4ab7-9511-f49ef20ce50c	ae8acfa4-7627-4be5-850c-08e578e5120d
9ee0ad4f-3e89-4144-93da-c4ea8f5bec3d	8a213533-674c-4ab7-9511-f49ef20ce50c	4a0bb4f9-c62e-43be-8b7f-43c655b8ef87
7866167e-456c-49cc-876a-939236ef41c3	8a213533-674c-4ab7-9511-f49ef20ce50c	70057449-f1cc-4aae-9909-93b4eb1e5551
5fd9eb3b-cc08-4c1c-9659-6c6aba73d124	8a213533-674c-4ab7-9511-f49ef20ce50c	32e6f002-686e-476d-927c-ce33afae643f
a0e01832-e638-4f5e-9998-fb0ccf80aa80	8a213533-674c-4ab7-9511-f49ef20ce50c	00cef543-6279-4001-98e9-658888d00d4a
56da3ae3-3255-4c17-b274-53de76ee80b0	8a213533-674c-4ab7-9511-f49ef20ce50c	f7a4888a-cfde-423f-a37c-58da8a4a816d
28da198b-fc20-45a3-99ad-d6c0f398ec4b	8a213533-674c-4ab7-9511-f49ef20ce50c	4b679c02-a189-48d9-bcf6-08f2e43b0e3c
014c7be1-1622-4cee-96c4-d9a86f670995	8a213533-674c-4ab7-9511-f49ef20ce50c	fe33b744-a71a-48df-a745-d3727090a952
b37548a1-ede6-4ba8-bfa1-47431f3c39c1	8a213533-674c-4ab7-9511-f49ef20ce50c	f951e8be-b16f-4c3d-8f09-e9876962c656
43f22f78-93ee-44c4-b625-27c87d742a92	8a213533-674c-4ab7-9511-f49ef20ce50c	4476b209-eac9-4a2d-80b4-0ea8b554062b
c8cd3362-c368-467a-bd83-6ff5e5c69043	8a213533-674c-4ab7-9511-f49ef20ce50c	5d5c4f18-3fdf-4ee2-b1fa-0e68f890e91f
bdda5d42-0738-4b90-9462-23ac94953682	8a213533-674c-4ab7-9511-f49ef20ce50c	6d5b9fc5-f65f-4f3b-ad98-79e71525bf0c
f7e96d4c-c605-4a56-b452-4a97b50a819a	8a213533-674c-4ab7-9511-f49ef20ce50c	be0fe4c5-0c0d-4b09-8c31-1a9eaa76ff8b
512d34fc-7e76-47ae-9700-83907eb5838f	8a213533-674c-4ab7-9511-f49ef20ce50c	a0e3be5c-00cf-4e73-9b65-3075c9eea5bd
c382a632-ad9b-48fc-a1eb-158a2072b64d	8a213533-674c-4ab7-9511-f49ef20ce50c	ab630454-1125-4eaf-8b4a-6e61dd864ecc
8cf624a9-2712-4362-9282-8c36583e702f	8a213533-674c-4ab7-9511-f49ef20ce50c	7816f54c-240a-4e69-b5ba-613841909a80
6e7c510a-8784-45c1-8873-e9e7f8cfb910	8a213533-674c-4ab7-9511-f49ef20ce50c	91546a63-0f5f-4386-8cec-15f79688a2ab
4eceee02-136d-4907-bb41-ed8c253fa27f	8a213533-674c-4ab7-9511-f49ef20ce50c	77e68e9d-b065-45b3-806e-81a05f877331
3ed608b0-5c0e-45d1-9700-d3d07dcfc31d	8a213533-674c-4ab7-9511-f49ef20ce50c	a60d00c1-f5a6-418d-b33e-82262a17f27f
c5306ed2-a6fc-4a28-9880-2dd6c3c9e08d	8a213533-674c-4ab7-9511-f49ef20ce50c	e618d856-394d-4dd2-a082-1c6ad0e1a536
5bf6d262-0418-458a-8b6b-72a9a2def346	8a213533-674c-4ab7-9511-f49ef20ce50c	157f216b-29fc-4e27-b1f9-0037bc198653
795ce4ed-6109-4618-bcb1-78b44c3d9899	8a213533-674c-4ab7-9511-f49ef20ce50c	49327f7a-a0dd-49c2-9ebe-5f18b1678222
ed786f0c-c10c-49eb-aa2c-0ae7ed63cc5b	8a213533-674c-4ab7-9511-f49ef20ce50c	b269cf3b-410b-48b6-9b98-a767a359bfca
e197493c-d782-4308-8893-588e818fd1b9	8a213533-674c-4ab7-9511-f49ef20ce50c	76e4c1f5-1cb3-4f6c-b1d1-c826260ff287
fde9d76b-f7a6-4e92-84ea-21a5483fe6c1	8a213533-674c-4ab7-9511-f49ef20ce50c	f56acff4-9d19-4438-a35a-57696e8c2e4b
233e1aef-b8ae-4a25-b030-f9dcc139d430	8a213533-674c-4ab7-9511-f49ef20ce50c	b90df2f5-b568-46cd-bfd1-7e39893e634b
0a90b5db-ca08-4f44-86ef-3405568c97f4	8a213533-674c-4ab7-9511-f49ef20ce50c	6bbf4a74-2e94-49e8-83bb-4110c19f0e13
66714ad4-42cb-4a8e-9e53-a84b4f05453c	8a213533-674c-4ab7-9511-f49ef20ce50c	529daa10-dfbb-4401-80e8-fc9a363f3807
6914476e-5d9d-41e2-9580-b15e17486778	8a213533-674c-4ab7-9511-f49ef20ce50c	f5e90c0e-8733-43ac-879f-55c5fc15425a
6beec1ae-184e-476c-abb0-676d85d157ec	8a213533-674c-4ab7-9511-f49ef20ce50c	404c9ddd-8025-4581-8f27-decf8f551a16
ea6e0ae2-8a26-466d-9643-d98ca61b54bb	8a213533-674c-4ab7-9511-f49ef20ce50c	cbe13e0e-4693-45a0-8878-30ff3fdd825a
ccc8091a-f336-4eb3-a6be-8824ba7b1e76	8a213533-674c-4ab7-9511-f49ef20ce50c	4539e17a-67ab-44cc-85f3-5e2d300899b2
a7e90be3-51b7-407e-9773-88cd84c200ab	8a213533-674c-4ab7-9511-f49ef20ce50c	cd940f62-f215-4901-bfec-f38cf7713515
8cf82b92-acc5-4081-9137-3b677a086139	396ebfa4-f377-4dfd-b839-c98a79be5a09	4d386bdc-9a78-4215-a9c1-eb6d22b68b10
9d0b47f3-a769-431e-8e0d-52beeed92f4d	396ebfa4-f377-4dfd-b839-c98a79be5a09	4a4915f6-f177-463e-b39e-4da042aa8161
5934e81f-526b-49bf-84ad-c7177bfa4b64	396ebfa4-f377-4dfd-b839-c98a79be5a09	56873e03-3c87-4d82-8269-9e6aa3db3032
8a629369-2983-449b-b1c7-aeb3f20ede4c	396ebfa4-f377-4dfd-b839-c98a79be5a09	748d0cb1-56ff-4702-acb8-56dcb71ca5e7
81b37339-716b-4ab0-b473-d912fe8cd5c8	396ebfa4-f377-4dfd-b839-c98a79be5a09	2dba0a89-468b-4549-87a8-235671b1359b
5a83acf0-2b48-4e74-a697-18aadec3adf0	396ebfa4-f377-4dfd-b839-c98a79be5a09	f7626507-7853-4068-9040-38e777f25125
a56adcee-8588-46bd-b2e2-f7f200c8e7bb	396ebfa4-f377-4dfd-b839-c98a79be5a09	94334195-e94b-4573-9741-bdb8b6136ff9
c756aa16-62ff-42ea-926c-2eb2dd287848	396ebfa4-f377-4dfd-b839-c98a79be5a09	20e5c59f-7396-46dc-8297-142e40347332
b61c6411-1fdf-438c-903a-145609c71c76	396ebfa4-f377-4dfd-b839-c98a79be5a09	90889445-d0ff-4cca-9bd4-a8da0b0fd45f
f406e52e-7623-4096-a000-a69e04c83be2	396ebfa4-f377-4dfd-b839-c98a79be5a09	a3a2d2b2-4901-46b8-bfaf-163beede39e9
4696ee32-0d4d-4948-ad6c-1578bbac75c7	396ebfa4-f377-4dfd-b839-c98a79be5a09	fc6dd1d5-140a-44ba-b630-59f1a988dae6
dfd1acfa-89e7-4705-b45f-86c72ed95b8f	396ebfa4-f377-4dfd-b839-c98a79be5a09	8f0194fd-e080-4f98-b46f-71c75812e8c2
6204bad4-fc25-4f2c-95e6-350455230460	396ebfa4-f377-4dfd-b839-c98a79be5a09	ef0ee95d-2607-4aa8-b8cf-267b94db76d1
793574ac-2171-4821-b351-ce518b9cd52a	396ebfa4-f377-4dfd-b839-c98a79be5a09	5c4f1a53-b5be-49c3-8639-e0ef8b62826a
0a3a8120-b212-42e3-8438-becf5f30bad9	396ebfa4-f377-4dfd-b839-c98a79be5a09	c88911a2-b1b8-496f-9c53-adea5384f7cf
d4acff35-0aa4-4adb-be6e-0dfeffa1b52c	396ebfa4-f377-4dfd-b839-c98a79be5a09	678de476-da63-428c-9a8c-8d0de781400b
1872245f-0f96-4730-853d-300078c7cf5d	396ebfa4-f377-4dfd-b839-c98a79be5a09	9206f1af-e598-4228-a352-e8b71701f500
07f84930-bf91-4538-86c0-bade7fc50789	396ebfa4-f377-4dfd-b839-c98a79be5a09	52a2daaf-298d-41f8-b034-9b9352a00386
91d4e1b9-e3c0-4337-a6dc-aca2d771e410	396ebfa4-f377-4dfd-b839-c98a79be5a09	933f5bd1-6cdc-4d92-85fe-a13dfaa6b71c
720d3da7-2cea-4e13-b400-934dfe09108a	396ebfa4-f377-4dfd-b839-c98a79be5a09	3a1b4156-55a1-446e-b188-df5e77dfd8b5
06052f8e-589c-409d-a782-57fa1205583e	396ebfa4-f377-4dfd-b839-c98a79be5a09	f7876ae0-847a-46d0-896d-26a337f9605b
96d989a1-5000-4def-8e2d-b47874ab2ef2	396ebfa4-f377-4dfd-b839-c98a79be5a09	f596816e-a0ac-4396-b526-c0cc7e4f1547
732909a4-3b59-4e3d-8eaf-f1101c415d40	396ebfa4-f377-4dfd-b839-c98a79be5a09	34efa491-5e0f-451b-9897-829b40376ae9
2226afda-1318-4e62-bda1-d0f56f288dd2	396ebfa4-f377-4dfd-b839-c98a79be5a09	1d230fba-3517-4936-a3a3-65eb110b963d
de2ee775-dcac-4b9c-b468-ea0c792facc0	396ebfa4-f377-4dfd-b839-c98a79be5a09	6710a77c-e35a-4f4c-a1d8-bd2a480faf9b
90af99e4-75f3-4aba-ac8f-16236bc8e094	396ebfa4-f377-4dfd-b839-c98a79be5a09	879b5348-dc23-4238-9770-618fca34f404
dc09eac8-38a0-4fe6-b3e8-7d00f691039e	396ebfa4-f377-4dfd-b839-c98a79be5a09	f91b7933-b575-4783-bdeb-69883ff75b57
c6855d6e-0489-45b0-b4e4-374f97cbf6ae	396ebfa4-f377-4dfd-b839-c98a79be5a09	c5b7095e-b795-438b-9455-d4eabba5fbaa
b208da67-3979-4eea-93c5-7899e98ea67f	396ebfa4-f377-4dfd-b839-c98a79be5a09	f08197bb-10f5-4097-b737-96bdc77dd673
621f8d17-ca03-4539-8e87-c714ee3040a0	396ebfa4-f377-4dfd-b839-c98a79be5a09	8c413273-dd5d-4e54-a23c-f516044e9961
9b6abb2c-c6fe-460c-905b-66b1c5191e84	396ebfa4-f377-4dfd-b839-c98a79be5a09	b824f887-522b-42c3-bb6d-e9bf3fe2c68d
e6f3a882-93ea-4ea4-a930-4a0b1f6fc452	396ebfa4-f377-4dfd-b839-c98a79be5a09	c795a61c-1525-4603-bc85-d04be7098f69
b8cd21a4-502d-4605-8c39-db181f49448a	396ebfa4-f377-4dfd-b839-c98a79be5a09	eb624a8e-2ddc-4f3a-9f15-571996b861fc
2ef88fb5-3dba-4808-97fc-825a13119498	396ebfa4-f377-4dfd-b839-c98a79be5a09	dc30661b-be68-476b-8fab-e75d843b454c
9a501a31-c6c8-4577-83dc-910bf9fd2f9c	396ebfa4-f377-4dfd-b839-c98a79be5a09	8494e31f-b5a4-4895-8600-5613daaf2e7b
d9a6fc91-fc94-4a13-8e03-a997a78917ff	396ebfa4-f377-4dfd-b839-c98a79be5a09	2045a7fa-d8fe-4784-bda5-4bccf4d69809
b69ab3f6-332a-41ef-8dd3-904ae55b354d	396ebfa4-f377-4dfd-b839-c98a79be5a09	27b4f7cc-d8d9-4b12-bb83-a47153e5d135
ef73cc4b-0881-4e68-a3e3-f9164bd13a95	396ebfa4-f377-4dfd-b839-c98a79be5a09	250dfee3-8da0-479e-aad8-2a74f24b9f9d
fe301c7e-b81f-4d57-a3b7-8c0331e42f8e	396ebfa4-f377-4dfd-b839-c98a79be5a09	b2ba2fe1-84ba-4d59-ad57-f1872021589d
d6a1ea8a-fc51-4754-a46b-f1efaf21c567	396ebfa4-f377-4dfd-b839-c98a79be5a09	4202bfd2-c595-4d18-aa0f-80ae538e4fea
6c79eff1-4077-4940-bf2c-f0c3285a9698	396ebfa4-f377-4dfd-b839-c98a79be5a09	76d1637a-aaf4-451b-b1d0-7849957a42a8
95b61670-d5bf-4f39-bc68-28a34098f2e6	396ebfa4-f377-4dfd-b839-c98a79be5a09	e5395d8e-6cdc-4411-b2b5-835ad149e933
f759e469-55ba-4a70-a69a-ce578060c44d	396ebfa4-f377-4dfd-b839-c98a79be5a09	57d21fef-512f-43cb-9aa0-0bebae2f355e
ffe36c51-4ff9-4094-85d9-5b0f92167d3e	396ebfa4-f377-4dfd-b839-c98a79be5a09	db812fd9-919e-47e1-aa9d-7b0de37b9863
51376705-ed19-404b-aa2b-0fd9fd2c8dd6	396ebfa4-f377-4dfd-b839-c98a79be5a09	050305b3-edec-407f-91e8-eb7f6e9fa1b3
9f87316e-0abe-435d-92d6-00432b7b5d4d	396ebfa4-f377-4dfd-b839-c98a79be5a09	bf762354-ead7-4be6-a836-f57bd7df1c1d
cbf39ba0-8916-40fc-9052-fdfe6ca0596b	396ebfa4-f377-4dfd-b839-c98a79be5a09	2a5a1c0d-47b4-4e9f-9ab4-b9106ed67a9d
b8a235e0-8df7-43e9-a465-973669a0b020	396ebfa4-f377-4dfd-b839-c98a79be5a09	f75c6bcc-c9ae-4a04-a8e0-f56d351009af
99e02905-8603-4415-a3d9-8a0ae0df2258	396ebfa4-f377-4dfd-b839-c98a79be5a09	8231e7d4-b4e8-495a-b881-3bfabbd85b67
089c7920-2692-46d5-98f8-2a5c1d35ba56	396ebfa4-f377-4dfd-b839-c98a79be5a09	5199b83d-34c6-4a7c-9bf9-d140a27f93c8
43a17597-46bc-4f68-849e-328e0c16f47b	396ebfa4-f377-4dfd-b839-c98a79be5a09	e59e5d27-8afb-4b5f-9d8d-dc5c6f19708e
30c7ba04-9d93-4993-a669-7ef0dd79cd0e	396ebfa4-f377-4dfd-b839-c98a79be5a09	1cdef3b1-d9ec-4f0d-9b7f-e6e927643e9a
99858c31-d5c1-4442-8690-9ff1fbacd4fa	396ebfa4-f377-4dfd-b839-c98a79be5a09	6a0ca14f-762d-4171-974e-c5870aa4076f
1663320d-1f6b-48da-ae21-fb4ac8f6ac64	396ebfa4-f377-4dfd-b839-c98a79be5a09	bad99487-1598-4525-ad21-de5dce5a91dc
8bff8795-3aa4-42f5-8cf8-c56d3591b6ac	396ebfa4-f377-4dfd-b839-c98a79be5a09	a590fd62-ff70-4e2f-aeb0-caf4b535c746
584f46e6-8b9a-41fd-92ee-f802943f7a19	396ebfa4-f377-4dfd-b839-c98a79be5a09	00ea86d7-62b3-4756-9abc-66dacc78c876
c6d4a836-611d-4763-88b0-ff7c02fd320d	396ebfa4-f377-4dfd-b839-c98a79be5a09	17665863-3735-46dc-96b5-2d9ebecff977
fdd0841e-dcc0-45aa-b6db-a22ea9ea3f9e	396ebfa4-f377-4dfd-b839-c98a79be5a09	36876181-d912-41bd-b06a-60c741e04818
122f8784-1f5b-4fef-a0d8-fd03631cae85	396ebfa4-f377-4dfd-b839-c98a79be5a09	6c32aa54-5304-4b8d-a2f2-2d822f61be12
d865c3d7-a2ca-462d-af5c-ba137bea67bb	396ebfa4-f377-4dfd-b839-c98a79be5a09	110560c2-7eb4-4890-b004-659f0203dd83
63ce7e67-b703-4ed5-a4f7-227ad1de9aa4	396ebfa4-f377-4dfd-b839-c98a79be5a09	91afb109-c9f5-448c-a236-3d7f88c0f293
d9a1443a-2c3f-407f-b5e4-189300ff45d2	396ebfa4-f377-4dfd-b839-c98a79be5a09	666022e6-ebb1-4567-b794-45b4c50c708f
55513b55-a660-480e-a0a2-b0c3e83a351b	396ebfa4-f377-4dfd-b839-c98a79be5a09	bb7bfcf6-f92a-4d61-9111-9f9806601c2a
e6212680-29b9-4f61-9a6c-19043741aea0	396ebfa4-f377-4dfd-b839-c98a79be5a09	f2011e4a-07b4-4261-b2b5-f4539f8c416a
861a95bb-5c9d-49f3-9a3e-ed491f59c49b	396ebfa4-f377-4dfd-b839-c98a79be5a09	163342df-9367-4e54-ab5c-4a3b55a0eadf
a333a8ac-372b-4dc1-92cd-594bca65c6ec	396ebfa4-f377-4dfd-b839-c98a79be5a09	0504f8e1-168a-4ff6-ab0f-dd568397795c
b5cdd7c5-dd10-4d9a-b68d-6cf70c8836b0	396ebfa4-f377-4dfd-b839-c98a79be5a09	ebe02472-e9c4-4989-a790-844163a82925
22ff6635-7803-42c1-9aec-8b87245ec1cd	396ebfa4-f377-4dfd-b839-c98a79be5a09	6484136b-fe57-404d-a347-b69e93c13522
abab1fc1-d2cf-42aa-90d4-11ed3dfa7e4a	396ebfa4-f377-4dfd-b839-c98a79be5a09	4d94fe84-d560-491b-991c-e7178471a947
e9ab8488-4bcf-4d27-afac-cae500c2410b	396ebfa4-f377-4dfd-b839-c98a79be5a09	2cc0b75a-d873-405a-a0c0-16db2fbc6b0c
b7b2c6b8-eb60-4bc5-8eba-1b8d75fe693e	396ebfa4-f377-4dfd-b839-c98a79be5a09	51efca30-9d3f-4e11-a348-1dad485a5697
115ed34c-aad2-4eb4-b66f-c3590fe13370	396ebfa4-f377-4dfd-b839-c98a79be5a09	d4633090-107d-403d-97c2-2d0d55c27c6b
a2b57108-7eb3-42be-9bea-795d0c90299e	396ebfa4-f377-4dfd-b839-c98a79be5a09	19a8509d-03ca-4da6-9df3-0b92df7ad979
94ad837d-4aeb-4a12-8b6c-85e349ecb5fd	396ebfa4-f377-4dfd-b839-c98a79be5a09	108b4f24-756f-41e2-ac39-931accb6ea93
08d1cf72-9be5-4d09-900f-7087e806b2c6	396ebfa4-f377-4dfd-b839-c98a79be5a09	3ffa1f68-2f02-4324-978a-4c3f21f448ea
79fddc63-06f5-4146-8c7e-db7bbeed5095	396ebfa4-f377-4dfd-b839-c98a79be5a09	ba6d6b2d-f61e-4386-a25c-9970024aaaef
b422ccbc-3d14-4e9a-af04-908ddd03f050	396ebfa4-f377-4dfd-b839-c98a79be5a09	2d74c01e-2810-43d6-a55c-1ceab0927969
dabf12d7-daab-47d8-9ceb-ba3ad1dfbfdc	396ebfa4-f377-4dfd-b839-c98a79be5a09	dd907879-5cbc-47f2-babb-ff4b2defdc6c
5f2fc593-84ee-4538-817c-93bf0bbe5281	396ebfa4-f377-4dfd-b839-c98a79be5a09	7a8ba668-b0af-4363-a8e4-f144a7505a1c
9f67e91f-aed9-47a7-bbb1-c106fe2bf8dd	396ebfa4-f377-4dfd-b839-c98a79be5a09	75a0377a-5654-48b7-beb7-de38c5ef3989
ed4693a1-a0fc-46e3-b675-2ce87f7e8604	396ebfa4-f377-4dfd-b839-c98a79be5a09	25ba7451-8f52-498b-a711-63e0912d3d96
b767d0a9-4015-4851-9001-ff42fceaa3aa	396ebfa4-f377-4dfd-b839-c98a79be5a09	36ee221c-e9c7-4883-af27-f9fb34aea280
7baa27e1-ad20-4e73-9b24-05f6008c2768	396ebfa4-f377-4dfd-b839-c98a79be5a09	a78b2610-91d9-45d7-995d-acd45cdb2467
4a582211-a630-4c2d-a984-a8b9fbaa58fc	396ebfa4-f377-4dfd-b839-c98a79be5a09	9fb4b34d-e40e-49a4-8792-2ea2bafd09e4
25ed9ce9-36ab-48c8-880c-af3aa440e654	396ebfa4-f377-4dfd-b839-c98a79be5a09	ae8acfa4-7627-4be5-850c-08e578e5120d
67c5bbdf-455c-4f3f-8b38-64ceb5c8f202	396ebfa4-f377-4dfd-b839-c98a79be5a09	4a0bb4f9-c62e-43be-8b7f-43c655b8ef87
578f2f00-95a9-49e1-98dd-e35a737f1ad4	396ebfa4-f377-4dfd-b839-c98a79be5a09	32e6f002-686e-476d-927c-ce33afae643f
bc71915c-64d3-4b45-9402-ff66311cc753	396ebfa4-f377-4dfd-b839-c98a79be5a09	00cef543-6279-4001-98e9-658888d00d4a
8eff4266-df75-4a5e-a45e-91224db713f1	396ebfa4-f377-4dfd-b839-c98a79be5a09	f7a4888a-cfde-423f-a37c-58da8a4a816d
2caf6428-d2c0-43c0-b6d8-3de8836ebcbb	396ebfa4-f377-4dfd-b839-c98a79be5a09	4b679c02-a189-48d9-bcf6-08f2e43b0e3c
c2336ab2-3ebb-426c-a023-36fbed2d1517	396ebfa4-f377-4dfd-b839-c98a79be5a09	fe33b744-a71a-48df-a745-d3727090a952
d8811810-3a92-4361-99c6-ad358b1f8fdd	396ebfa4-f377-4dfd-b839-c98a79be5a09	f951e8be-b16f-4c3d-8f09-e9876962c656
d66512e1-9261-497f-9a9c-2da128f683f5	396ebfa4-f377-4dfd-b839-c98a79be5a09	4476b209-eac9-4a2d-80b4-0ea8b554062b
4e487f5c-d2e6-44b5-88d5-6caa621c5572	396ebfa4-f377-4dfd-b839-c98a79be5a09	7816f54c-240a-4e69-b5ba-613841909a80
904e75b0-8dd6-44f1-8a55-0380009493fb	396ebfa4-f377-4dfd-b839-c98a79be5a09	91546a63-0f5f-4386-8cec-15f79688a2ab
7415e083-c5c9-48eb-90af-b31dc46a3069	396ebfa4-f377-4dfd-b839-c98a79be5a09	77e68e9d-b065-45b3-806e-81a05f877331
77f81685-ce6f-4cd9-96ef-da087f50a821	396ebfa4-f377-4dfd-b839-c98a79be5a09	a60d00c1-f5a6-418d-b33e-82262a17f27f
f82dc9cb-8504-4dee-b395-260e4c35301f	396ebfa4-f377-4dfd-b839-c98a79be5a09	e618d856-394d-4dd2-a082-1c6ad0e1a536
7d912294-6680-4f5d-8020-1343ee2f13f6	396ebfa4-f377-4dfd-b839-c98a79be5a09	157f216b-29fc-4e27-b1f9-0037bc198653
92f136e5-4c22-4dce-9073-81b83ca8be21	396ebfa4-f377-4dfd-b839-c98a79be5a09	49327f7a-a0dd-49c2-9ebe-5f18b1678222
af5381ce-6a5f-4f57-a38a-b13d0a11ced8	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	4d386bdc-9a78-4215-a9c1-eb6d22b68b10
0b79d10a-b6d3-4a64-ab29-35bfa88dbcda	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	4a4915f6-f177-463e-b39e-4da042aa8161
453b62e9-0265-4d5e-b9dc-d06ca35d751e	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	56873e03-3c87-4d82-8269-9e6aa3db3032
b29b5a8b-068a-4fb3-95e2-24fcbd0d1d25	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	748d0cb1-56ff-4702-acb8-56dcb71ca5e7
7648759d-14cc-4276-84f5-127baceaa243	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	2dba0a89-468b-4549-87a8-235671b1359b
82f78fb9-e7f9-4bbd-b40d-2aff2b308f3e	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	f7626507-7853-4068-9040-38e777f25125
0e8de059-6e8b-4129-a61c-0fb0341edf16	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	94334195-e94b-4573-9741-bdb8b6136ff9
23f94db2-8cbd-4f47-b0b7-e4a6f0b20ebc	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	20e5c59f-7396-46dc-8297-142e40347332
989bd0c1-3a38-4404-9e17-359832553fc8	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	90889445-d0ff-4cca-9bd4-a8da0b0fd45f
dcc553c2-e4e7-43c4-aabb-1b9fab22eac6	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	a3a2d2b2-4901-46b8-bfaf-163beede39e9
a10dca71-f5c6-4e29-88d5-e161747b3847	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	fc6dd1d5-140a-44ba-b630-59f1a988dae6
f045d56e-cead-4889-8cb4-54b2fcc253e4	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	8f0194fd-e080-4f98-b46f-71c75812e8c2
b3808214-4e99-4c1b-8a4e-a29da05aa50a	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	ef0ee95d-2607-4aa8-b8cf-267b94db76d1
1140af57-2bfc-400b-9650-3e540ad89534	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	5c4f1a53-b5be-49c3-8639-e0ef8b62826a
bfc6f799-73cd-4044-98f3-46ffb254e294	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	c88911a2-b1b8-496f-9c53-adea5384f7cf
e160dfa8-e647-44e1-833c-aed6e29fc568	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	678de476-da63-428c-9a8c-8d0de781400b
4c623bd1-9969-4805-aa63-a5703ec5a3ce	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	9206f1af-e598-4228-a352-e8b71701f500
d225d3b3-db6a-418b-a6bc-ba41e02508cd	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	52a2daaf-298d-41f8-b034-9b9352a00386
7e914409-a4c0-4333-be0b-35a05260292d	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	933f5bd1-6cdc-4d92-85fe-a13dfaa6b71c
41952190-e95e-4c84-bdd3-7ebf4b4ef81b	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	3a1b4156-55a1-446e-b188-df5e77dfd8b5
ca1c88f5-c996-41e8-b042-d12332392dae	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	f7876ae0-847a-46d0-896d-26a337f9605b
214464ad-a78f-4e67-b9fe-a7c614f9d85c	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	f596816e-a0ac-4396-b526-c0cc7e4f1547
eaeb208d-0758-4e04-9363-b76216bdedc0	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	34efa491-5e0f-451b-9897-829b40376ae9
43676682-a802-4f1e-b01f-2d8e9211123b	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	1d230fba-3517-4936-a3a3-65eb110b963d
817f6393-2b86-474b-bfea-946a45771a74	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	6710a77c-e35a-4f4c-a1d8-bd2a480faf9b
fbbf403d-07c6-4961-8144-f29e22bf101b	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	879b5348-dc23-4238-9770-618fca34f404
88aee88f-cb46-4ff3-8197-ab131376f6ee	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	f91b7933-b575-4783-bdeb-69883ff75b57
fb47a019-5799-4aa2-b6ab-33bd363a6e68	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	c5b7095e-b795-438b-9455-d4eabba5fbaa
70cc0533-2764-49b8-be12-6aa4be58bc3d	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	f08197bb-10f5-4097-b737-96bdc77dd673
ea8291fc-2f35-49c3-8af1-2030c58fe467	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	8c413273-dd5d-4e54-a23c-f516044e9961
17396d2d-53bd-4e2b-a7a0-cfa856de22de	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	b824f887-522b-42c3-bb6d-e9bf3fe2c68d
bf720dd9-278b-4bfe-9c86-930c2714b152	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	c795a61c-1525-4603-bc85-d04be7098f69
81fd4026-7ba9-4b87-9f7b-62c4cfcab3d9	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	eb624a8e-2ddc-4f3a-9f15-571996b861fc
77046901-9b27-4118-8a03-099fe8c26ab5	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	dc30661b-be68-476b-8fab-e75d843b454c
5b4e1bf3-2734-4cf8-9342-31c1cc92386f	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	8494e31f-b5a4-4895-8600-5613daaf2e7b
7c7b57d5-6414-4320-8cac-d7ea293c044d	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	2045a7fa-d8fe-4784-bda5-4bccf4d69809
b989fc8d-707e-43b2-9e44-d1c23fed692f	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	27b4f7cc-d8d9-4b12-bb83-a47153e5d135
f331f54e-7f59-41b0-9cd5-63c6489c85b7	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	250dfee3-8da0-479e-aad8-2a74f24b9f9d
08ddf974-72f3-4bab-9821-bbee083dd04c	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	b2ba2fe1-84ba-4d59-ad57-f1872021589d
9f2d85be-fffe-4843-8f82-c31c952a7ebe	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	4202bfd2-c595-4d18-aa0f-80ae538e4fea
331ba18e-d024-44a4-b3bf-d2e015b20a24	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	76d1637a-aaf4-451b-b1d0-7849957a42a8
4128a623-9a5f-4163-8dcb-bcd60d6ae2b1	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	e5395d8e-6cdc-4411-b2b5-835ad149e933
238a1b08-e895-460e-8775-ec77a499a3b0	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	57d21fef-512f-43cb-9aa0-0bebae2f355e
2751193f-0c50-4c08-b338-84ac67956a1b	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	db812fd9-919e-47e1-aa9d-7b0de37b9863
665f3020-2c2d-497f-b45b-ea04aef2c875	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	050305b3-edec-407f-91e8-eb7f6e9fa1b3
c0a3cf2e-bd30-4f9d-90cf-51cfe0006f63	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	bf762354-ead7-4be6-a836-f57bd7df1c1d
14f75947-69c1-4bc6-8457-658a78794e4a	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	2a5a1c0d-47b4-4e9f-9ab4-b9106ed67a9d
6a775062-1ceb-473b-8da0-1c8ccdca603c	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	f75c6bcc-c9ae-4a04-a8e0-f56d351009af
dcf0fa08-276a-40cd-a3e3-911c57fd18e6	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	8231e7d4-b4e8-495a-b881-3bfabbd85b67
ccc5b19b-9420-406a-85d4-0a376c01e616	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	5199b83d-34c6-4a7c-9bf9-d140a27f93c8
4d1fb036-cc23-4ac1-973c-6ee66695f0c6	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	e59e5d27-8afb-4b5f-9d8d-dc5c6f19708e
277d4574-6a4f-4deb-a401-8da3e88a7749	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	1cdef3b1-d9ec-4f0d-9b7f-e6e927643e9a
d2c992b8-bf31-4ca0-b67a-e26fcbcc704d	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	6a0ca14f-762d-4171-974e-c5870aa4076f
7c7c2c72-d5bb-48a1-bc61-7b750bf91016	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	bad99487-1598-4525-ad21-de5dce5a91dc
4874409c-7d45-49b1-8fe0-fca33a14a2e7	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	a590fd62-ff70-4e2f-aeb0-caf4b535c746
d844ae4d-9d4f-40f2-a972-355e2715669d	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	00ea86d7-62b3-4756-9abc-66dacc78c876
dc3d757c-c105-491b-b14b-02b7ac092806	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	17665863-3735-46dc-96b5-2d9ebecff977
f7ffe20a-5c2a-484d-a543-21341eaaa233	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	36876181-d912-41bd-b06a-60c741e04818
5bd2d378-ef07-4a36-adda-5cd01e27dd0f	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	6c32aa54-5304-4b8d-a2f2-2d822f61be12
c58f3216-7c19-46ce-aa54-f261443e84c1	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	110560c2-7eb4-4890-b004-659f0203dd83
6f6d56c1-acc9-44e8-a266-08ac65c9fc25	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	91afb109-c9f5-448c-a236-3d7f88c0f293
9a3c8784-db94-4dc8-a9d0-54443a4a6667	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	666022e6-ebb1-4567-b794-45b4c50c708f
84266952-4a99-4f88-9080-ed472f29dafe	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	bb7bfcf6-f92a-4d61-9111-9f9806601c2a
2f5384fc-8f3a-434d-ae44-ab5b5315f091	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	f2011e4a-07b4-4261-b2b5-f4539f8c416a
441610a3-c6e7-4ed7-9c78-7644e6e93df2	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	163342df-9367-4e54-ab5c-4a3b55a0eadf
27513fa1-02f0-4d0b-9d9d-f6876c743974	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	0504f8e1-168a-4ff6-ab0f-dd568397795c
11315149-d253-41e6-8de8-7e30749f40bb	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	ebe02472-e9c4-4989-a790-844163a82925
9ec9cbfe-a73e-4176-b582-8237883a88bf	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	6484136b-fe57-404d-a347-b69e93c13522
013ea332-b730-47e2-835d-fc8b7b93ac9b	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	4d94fe84-d560-491b-991c-e7178471a947
d203dab8-8e7b-4288-b322-591687552225	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	2cc0b75a-d873-405a-a0c0-16db2fbc6b0c
c12692df-daa5-418e-a739-61c858b8a8a0	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	51efca30-9d3f-4e11-a348-1dad485a5697
1fb08eef-2d3e-4f1a-a6d7-2e32404f406b	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	d4633090-107d-403d-97c2-2d0d55c27c6b
c1e5a51a-3b9f-44a4-9d30-3fd0737d5742	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	19a8509d-03ca-4da6-9df3-0b92df7ad979
2d50a659-a0b1-419d-9208-d03832bb87e9	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	108b4f24-756f-41e2-ac39-931accb6ea93
208bef03-7310-46bc-8ea4-05e5c039bde3	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	3ffa1f68-2f02-4324-978a-4c3f21f448ea
134b3c52-f740-45f1-97e8-fe8ce257f708	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	ba6d6b2d-f61e-4386-a25c-9970024aaaef
0d8b8196-07a7-44cb-8e73-0f57f9dc3a82	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	2d74c01e-2810-43d6-a55c-1ceab0927969
fe571240-4912-43bd-bab8-24ef874a4529	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	dd907879-5cbc-47f2-babb-ff4b2defdc6c
59b7bc64-de08-49ad-8147-b544c11a85ae	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	7a8ba668-b0af-4363-a8e4-f144a7505a1c
0062dbb2-616d-4efb-ada6-768d4e495a48	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	75a0377a-5654-48b7-beb7-de38c5ef3989
5adfbe67-2f65-4cd4-9600-69baf69f58a9	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	25ba7451-8f52-498b-a711-63e0912d3d96
e3ac22b1-0dc4-4a62-825f-1d322834057b	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	36ee221c-e9c7-4883-af27-f9fb34aea280
5b04f406-0f62-443e-a1d9-f1deee09ed63	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	a78b2610-91d9-45d7-995d-acd45cdb2467
0ebdd141-ae55-4fc4-8e90-496aba4a02d8	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	9fb4b34d-e40e-49a4-8792-2ea2bafd09e4
df2585e2-66ba-4e14-bf71-6c70f2724ff3	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	ae8acfa4-7627-4be5-850c-08e578e5120d
e2d522ec-4ef4-419b-8f9d-b440ee07de6e	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	4a0bb4f9-c62e-43be-8b7f-43c655b8ef87
d0451a00-e212-45d6-91e0-405aeae48332	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	32e6f002-686e-476d-927c-ce33afae643f
d2a59253-e93f-48fc-995b-2d9dc40b8162	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	00cef543-6279-4001-98e9-658888d00d4a
c8a1b72a-bcab-4e8a-8368-795351597e99	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	f7a4888a-cfde-423f-a37c-58da8a4a816d
21c72fb0-fe52-4963-980e-eb37467a111a	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	4b679c02-a189-48d9-bcf6-08f2e43b0e3c
51cc5373-3ce5-4ea0-bb9e-3dac52a0a19d	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	fe33b744-a71a-48df-a745-d3727090a952
1177d17d-d82c-47d2-be0c-b0d5bcf9c305	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	f951e8be-b16f-4c3d-8f09-e9876962c656
801b6352-0f54-44d8-995f-cd092e736c09	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	4476b209-eac9-4a2d-80b4-0ea8b554062b
813682cd-840c-4974-b338-8bf7b5309618	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	7816f54c-240a-4e69-b5ba-613841909a80
38e2a008-d916-4cc3-bcba-e1e33f9aaca1	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	91546a63-0f5f-4386-8cec-15f79688a2ab
078c5423-653d-405c-ad0c-25b4853e6641	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	77e68e9d-b065-45b3-806e-81a05f877331
44dc2610-362a-423a-b057-6673e1a4c3ca	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	a60d00c1-f5a6-418d-b33e-82262a17f27f
fb2ba607-0690-4311-9636-5f40d5228882	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	e618d856-394d-4dd2-a082-1c6ad0e1a536
300f865d-4a99-4eff-bf91-4b64794d474f	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	157f216b-29fc-4e27-b1f9-0037bc198653
17a19bef-417f-4ef8-bad2-0d13789a3b25	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	49327f7a-a0dd-49c2-9ebe-5f18b1678222
6fa9de21-e5d4-4986-ba61-bdd37d33d4a0	01428281-67d6-45f7-812f-3bc6d3310e88	4d386bdc-9a78-4215-a9c1-eb6d22b68b10
6c6dd6e9-bb7a-46dc-8da8-15b5555e519b	01428281-67d6-45f7-812f-3bc6d3310e88	4a4915f6-f177-463e-b39e-4da042aa8161
3f601a6b-286e-4a4a-9ee7-39068d4bb3b6	01428281-67d6-45f7-812f-3bc6d3310e88	56873e03-3c87-4d82-8269-9e6aa3db3032
659c14a6-5461-45e2-878f-34643b1e519e	01428281-67d6-45f7-812f-3bc6d3310e88	748d0cb1-56ff-4702-acb8-56dcb71ca5e7
2d10bc05-eba9-47d7-bc82-595b6f183667	01428281-67d6-45f7-812f-3bc6d3310e88	2dba0a89-468b-4549-87a8-235671b1359b
6bd30e71-cd14-4b5e-98b1-f63c56737ad1	01428281-67d6-45f7-812f-3bc6d3310e88	20e5c59f-7396-46dc-8297-142e40347332
40e7a0ec-ff37-467a-822e-722d64de9b34	01428281-67d6-45f7-812f-3bc6d3310e88	a3a2d2b2-4901-46b8-bfaf-163beede39e9
fa528381-4bd0-4064-b5a8-293749afad58	01428281-67d6-45f7-812f-3bc6d3310e88	5c4f1a53-b5be-49c3-8639-e0ef8b62826a
765d53ac-c830-4190-baa1-1d803b5a0bce	01428281-67d6-45f7-812f-3bc6d3310e88	c88911a2-b1b8-496f-9c53-adea5384f7cf
e3ae2701-1f86-4b22-85bb-fa2afa87ab31	01428281-67d6-45f7-812f-3bc6d3310e88	678de476-da63-428c-9a8c-8d0de781400b
8e9d23f4-956d-4625-a8ff-25b9f73d7ff2	01428281-67d6-45f7-812f-3bc6d3310e88	9206f1af-e598-4228-a352-e8b71701f500
16edbbda-2864-40fb-882d-f34a3464dc16	01428281-67d6-45f7-812f-3bc6d3310e88	52a2daaf-298d-41f8-b034-9b9352a00386
52600d4c-8c32-456a-a704-c3611c074605	01428281-67d6-45f7-812f-3bc6d3310e88	933f5bd1-6cdc-4d92-85fe-a13dfaa6b71c
8548ee09-2ebe-4757-ad70-4f556637a89c	01428281-67d6-45f7-812f-3bc6d3310e88	3a1b4156-55a1-446e-b188-df5e77dfd8b5
3b4f1cc6-3f23-41cb-bb95-a0f07577e523	01428281-67d6-45f7-812f-3bc6d3310e88	f7876ae0-847a-46d0-896d-26a337f9605b
5fd6a252-23dc-4b03-bb18-257978cfde12	01428281-67d6-45f7-812f-3bc6d3310e88	f596816e-a0ac-4396-b526-c0cc7e4f1547
c0795945-5eb3-4d2f-8cc6-1a86f8925ad3	01428281-67d6-45f7-812f-3bc6d3310e88	34efa491-5e0f-451b-9897-829b40376ae9
908ea44d-863c-4b28-94b7-d03b6044c1a6	01428281-67d6-45f7-812f-3bc6d3310e88	1d230fba-3517-4936-a3a3-65eb110b963d
86a1fa13-c6b6-42ca-95cf-ac258e65e662	01428281-67d6-45f7-812f-3bc6d3310e88	6710a77c-e35a-4f4c-a1d8-bd2a480faf9b
d3545ebd-934e-45b0-ac95-68564c726699	01428281-67d6-45f7-812f-3bc6d3310e88	879b5348-dc23-4238-9770-618fca34f404
580ab1ba-2662-45b4-8f98-c35e32806c93	01428281-67d6-45f7-812f-3bc6d3310e88	f91b7933-b575-4783-bdeb-69883ff75b57
8c8e2944-172a-4e8b-b73f-98bb78fe1ee1	01428281-67d6-45f7-812f-3bc6d3310e88	c5b7095e-b795-438b-9455-d4eabba5fbaa
f3334ed4-311f-46ae-99fa-51923bb53200	01428281-67d6-45f7-812f-3bc6d3310e88	f08197bb-10f5-4097-b737-96bdc77dd673
0825e53d-5b3f-4684-88ed-82562c8398db	01428281-67d6-45f7-812f-3bc6d3310e88	8c413273-dd5d-4e54-a23c-f516044e9961
420842fe-172f-4d5e-a4e2-d38d0cc6d70e	01428281-67d6-45f7-812f-3bc6d3310e88	b824f887-522b-42c3-bb6d-e9bf3fe2c68d
9b9c75eb-54d2-44f4-bf0e-05ee68ef41e8	01428281-67d6-45f7-812f-3bc6d3310e88	c795a61c-1525-4603-bc85-d04be7098f69
16759d69-07d2-4de4-bd58-a06a833c1714	01428281-67d6-45f7-812f-3bc6d3310e88	eb624a8e-2ddc-4f3a-9f15-571996b861fc
2234c4fa-da06-4361-a5fb-f5e42f9348d7	01428281-67d6-45f7-812f-3bc6d3310e88	8494e31f-b5a4-4895-8600-5613daaf2e7b
a833ecaa-5215-4799-809a-02d5e739f385	01428281-67d6-45f7-812f-3bc6d3310e88	2045a7fa-d8fe-4784-bda5-4bccf4d69809
7e135a2d-8b0a-4fcb-a589-7d7bc018fca1	01428281-67d6-45f7-812f-3bc6d3310e88	27b4f7cc-d8d9-4b12-bb83-a47153e5d135
a207f649-a0a0-4f8d-86bd-2efcd010aa18	01428281-67d6-45f7-812f-3bc6d3310e88	250dfee3-8da0-479e-aad8-2a74f24b9f9d
8186325e-3621-4ec5-a23d-a90e7da73127	01428281-67d6-45f7-812f-3bc6d3310e88	b2ba2fe1-84ba-4d59-ad57-f1872021589d
26f385fa-332b-42f0-a693-c35a33ca2d90	01428281-67d6-45f7-812f-3bc6d3310e88	4202bfd2-c595-4d18-aa0f-80ae538e4fea
0c64601b-4fc7-4a45-a9d9-c849079f6f1d	01428281-67d6-45f7-812f-3bc6d3310e88	76d1637a-aaf4-451b-b1d0-7849957a42a8
7256853f-fc29-4065-9463-da38b065f429	01428281-67d6-45f7-812f-3bc6d3310e88	e5395d8e-6cdc-4411-b2b5-835ad149e933
0048d73f-90d5-4b87-a4a3-d269c66451f3	01428281-67d6-45f7-812f-3bc6d3310e88	57d21fef-512f-43cb-9aa0-0bebae2f355e
aae87bdb-bec2-4179-a3e7-db05aaf69902	01428281-67d6-45f7-812f-3bc6d3310e88	db812fd9-919e-47e1-aa9d-7b0de37b9863
65f5ed17-71c9-4b01-9b3d-848993c4c6e6	01428281-67d6-45f7-812f-3bc6d3310e88	050305b3-edec-407f-91e8-eb7f6e9fa1b3
528da918-9613-4d9e-99ba-790902fb9758	01428281-67d6-45f7-812f-3bc6d3310e88	bf762354-ead7-4be6-a836-f57bd7df1c1d
6fc442d6-d572-48f7-b97b-8c81b8bd4c92	01428281-67d6-45f7-812f-3bc6d3310e88	2a5a1c0d-47b4-4e9f-9ab4-b9106ed67a9d
1350c631-1fd1-4f1b-9a11-741691ac3d04	01428281-67d6-45f7-812f-3bc6d3310e88	f75c6bcc-c9ae-4a04-a8e0-f56d351009af
35d1afdf-ba8a-4d84-b31e-d0ad70b02303	01428281-67d6-45f7-812f-3bc6d3310e88	8231e7d4-b4e8-495a-b881-3bfabbd85b67
dbfa44b2-2334-4ffa-b9c7-12c96c52b471	01428281-67d6-45f7-812f-3bc6d3310e88	e59e5d27-8afb-4b5f-9d8d-dc5c6f19708e
a6ffbe58-da6a-4020-aa25-be1198c2900a	01428281-67d6-45f7-812f-3bc6d3310e88	1cdef3b1-d9ec-4f0d-9b7f-e6e927643e9a
be0564e4-5f71-48ea-9285-a16c3cbbb677	01428281-67d6-45f7-812f-3bc6d3310e88	6a0ca14f-762d-4171-974e-c5870aa4076f
8743741f-a54b-4835-8882-bbb95d40518f	01428281-67d6-45f7-812f-3bc6d3310e88	bad99487-1598-4525-ad21-de5dce5a91dc
6aa1f67e-a72e-40a8-b266-d66eda27dac9	01428281-67d6-45f7-812f-3bc6d3310e88	a590fd62-ff70-4e2f-aeb0-caf4b535c746
d82959fa-c041-4b81-bf61-154d23dc0657	01428281-67d6-45f7-812f-3bc6d3310e88	00ea86d7-62b3-4756-9abc-66dacc78c876
1bf2c129-2013-42ea-ae68-90faf295e42d	01428281-67d6-45f7-812f-3bc6d3310e88	17665863-3735-46dc-96b5-2d9ebecff977
b19fcc2a-05af-4291-ac9e-83782684006e	01428281-67d6-45f7-812f-3bc6d3310e88	36876181-d912-41bd-b06a-60c741e04818
72229e41-9001-41b9-bc84-8d681ec67f1d	01428281-67d6-45f7-812f-3bc6d3310e88	6c32aa54-5304-4b8d-a2f2-2d822f61be12
a832d2db-d15b-4b1d-a636-afbe2faa7555	01428281-67d6-45f7-812f-3bc6d3310e88	110560c2-7eb4-4890-b004-659f0203dd83
105d90a1-2556-44ea-b133-e5045c943958	01428281-67d6-45f7-812f-3bc6d3310e88	91afb109-c9f5-448c-a236-3d7f88c0f293
90807577-24f5-4ccc-aa51-807968a4fafb	01428281-67d6-45f7-812f-3bc6d3310e88	666022e6-ebb1-4567-b794-45b4c50c708f
d563a4bc-80b8-4f65-a119-c12d0d5a14a6	01428281-67d6-45f7-812f-3bc6d3310e88	bb7bfcf6-f92a-4d61-9111-9f9806601c2a
e89bb2c3-3614-450a-86fa-b6449dbedabf	01428281-67d6-45f7-812f-3bc6d3310e88	f2011e4a-07b4-4261-b2b5-f4539f8c416a
79d880cc-36a6-4f08-963c-dfd590d46abf	01428281-67d6-45f7-812f-3bc6d3310e88	6484136b-fe57-404d-a347-b69e93c13522
3349403c-c47a-46de-a05f-ac821d44b1f0	01428281-67d6-45f7-812f-3bc6d3310e88	2cc0b75a-d873-405a-a0c0-16db2fbc6b0c
71ddb6ee-9dd1-4fac-9c96-64c9fb63d1d8	01428281-67d6-45f7-812f-3bc6d3310e88	2320bed8-da22-4c89-b9fb-ff4b418f4a8c
e1f1f6a7-c5f8-4211-984d-2e433ab1b743	01428281-67d6-45f7-812f-3bc6d3310e88	d4633090-107d-403d-97c2-2d0d55c27c6b
ade9433b-18ff-4036-8b8f-49489e64877f	01428281-67d6-45f7-812f-3bc6d3310e88	108b4f24-756f-41e2-ac39-931accb6ea93
4797d1d6-d3e2-48d5-aecc-e29232613dff	01428281-67d6-45f7-812f-3bc6d3310e88	3ffa1f68-2f02-4324-978a-4c3f21f448ea
65a609d6-5508-4c1f-a1a9-c694857f09a5	01428281-67d6-45f7-812f-3bc6d3310e88	ba6d6b2d-f61e-4386-a25c-9970024aaaef
e4338826-c0c5-4295-b434-a4bc815af728	01428281-67d6-45f7-812f-3bc6d3310e88	2d74c01e-2810-43d6-a55c-1ceab0927969
93c261eb-6fa8-4b61-b6b0-838aa9fbee0c	01428281-67d6-45f7-812f-3bc6d3310e88	dd907879-5cbc-47f2-babb-ff4b2defdc6c
3d52ad06-1af6-4fa0-a838-08c776983de0	01428281-67d6-45f7-812f-3bc6d3310e88	7a8ba668-b0af-4363-a8e4-f144a7505a1c
ebaf039d-78fa-41ca-be85-2c0f6b8c7097	01428281-67d6-45f7-812f-3bc6d3310e88	75a0377a-5654-48b7-beb7-de38c5ef3989
a2881e5e-1676-46c5-9b34-77555c8cb217	01428281-67d6-45f7-812f-3bc6d3310e88	25ba7451-8f52-498b-a711-63e0912d3d96
18353c31-071f-46c4-9261-7ec1103a2b11	01428281-67d6-45f7-812f-3bc6d3310e88	36ee221c-e9c7-4883-af27-f9fb34aea280
cc31cfa2-8b4c-4f97-88ef-4863612c0ba7	01428281-67d6-45f7-812f-3bc6d3310e88	a78b2610-91d9-45d7-995d-acd45cdb2467
7e2cb783-d6a9-433b-b893-2c215ed65f3d	01428281-67d6-45f7-812f-3bc6d3310e88	9fb4b34d-e40e-49a4-8792-2ea2bafd09e4
baeaa5dd-201e-4f94-81e4-bc532fb05ea3	01428281-67d6-45f7-812f-3bc6d3310e88	ae8acfa4-7627-4be5-850c-08e578e5120d
c90f8949-556a-411a-b4e9-8efb8fd70685	01428281-67d6-45f7-812f-3bc6d3310e88	4a0bb4f9-c62e-43be-8b7f-43c655b8ef87
ddf36ffe-71a9-47a8-86c4-4a28a2276116	01428281-67d6-45f7-812f-3bc6d3310e88	32e6f002-686e-476d-927c-ce33afae643f
ccc83995-bbdd-41df-beae-50f6c4467c97	01428281-67d6-45f7-812f-3bc6d3310e88	00cef543-6279-4001-98e9-658888d00d4a
99219d7d-272f-4721-86a2-22b8c51ae2d4	01428281-67d6-45f7-812f-3bc6d3310e88	f7a4888a-cfde-423f-a37c-58da8a4a816d
b7b4c24b-c3a6-469e-9797-5b5a4c35003e	01428281-67d6-45f7-812f-3bc6d3310e88	4b679c02-a189-48d9-bcf6-08f2e43b0e3c
d5080d5c-3d4c-42ff-b46f-0488eab6c59a	01428281-67d6-45f7-812f-3bc6d3310e88	fe33b744-a71a-48df-a745-d3727090a952
52a72a13-b503-42a6-9a0a-6bc12b363996	01428281-67d6-45f7-812f-3bc6d3310e88	f951e8be-b16f-4c3d-8f09-e9876962c656
9be30e5c-7365-431f-8cde-a74f6e85d59a	01428281-67d6-45f7-812f-3bc6d3310e88	4476b209-eac9-4a2d-80b4-0ea8b554062b
7e93c620-a11c-4727-ba84-7fde2f574c53	01428281-67d6-45f7-812f-3bc6d3310e88	a60d00c1-f5a6-418d-b33e-82262a17f27f
0c4b407a-cd8d-48e3-a103-3c574c402efe	01428281-67d6-45f7-812f-3bc6d3310e88	e618d856-394d-4dd2-a082-1c6ad0e1a536
9444c1e2-7b46-4ff7-a9f2-996581c6079a	01428281-67d6-45f7-812f-3bc6d3310e88	157f216b-29fc-4e27-b1f9-0037bc198653
cff0bf18-8881-47e0-8c12-649ef4146a44	01428281-67d6-45f7-812f-3bc6d3310e88	49327f7a-a0dd-49c2-9ebe-5f18b1678222
1bd40ae9-7683-4d57-b7e9-a0c604ba5b75	01428281-67d6-45f7-812f-3bc6d3310e88	19e05924-5d4f-4757-81e6-1c37d4916abc
93deec8c-3c6f-4104-8a96-ac43a012958a	6f220a6c-5ac7-476a-aa2a-88c4d6fd7f82	4d386bdc-9a78-4215-a9c1-eb6d22b68b10
e4e70245-46e2-4fd2-b89d-5b7b4ebf753b	6f220a6c-5ac7-476a-aa2a-88c4d6fd7f82	20e5c59f-7396-46dc-8297-142e40347332
c65e378b-9b77-4321-b921-fb34bc831e0e	6f220a6c-5ac7-476a-aa2a-88c4d6fd7f82	5c4f1a53-b5be-49c3-8639-e0ef8b62826a
f15d1e9d-dd73-4038-a44d-a0a8f84b0948	6f220a6c-5ac7-476a-aa2a-88c4d6fd7f82	c88911a2-b1b8-496f-9c53-adea5384f7cf
b85e695b-9b37-4898-b281-0d27593d8ffb	6f220a6c-5ac7-476a-aa2a-88c4d6fd7f82	933f5bd1-6cdc-4d92-85fe-a13dfaa6b71c
f0a35f21-071b-402d-a6d7-1d9550475a89	6f220a6c-5ac7-476a-aa2a-88c4d6fd7f82	6710a77c-e35a-4f4c-a1d8-bd2a480faf9b
7ca1a5b9-fa48-4597-b0ea-f6e2c8002e82	6f220a6c-5ac7-476a-aa2a-88c4d6fd7f82	879b5348-dc23-4238-9770-618fca34f404
fd62761c-5feb-40c5-b9d0-470eb39d6ac6	6f220a6c-5ac7-476a-aa2a-88c4d6fd7f82	f91b7933-b575-4783-bdeb-69883ff75b57
7b3bfc6c-b001-4f5f-99a1-caf9296559e7	6f220a6c-5ac7-476a-aa2a-88c4d6fd7f82	b824f887-522b-42c3-bb6d-e9bf3fe2c68d
8098488a-6b30-4bd6-be82-91b1f8dc9bce	6f220a6c-5ac7-476a-aa2a-88c4d6fd7f82	27b4f7cc-d8d9-4b12-bb83-a47153e5d135
d76167ea-bed7-4e5d-8378-9fc29cc275e6	6f220a6c-5ac7-476a-aa2a-88c4d6fd7f82	250dfee3-8da0-479e-aad8-2a74f24b9f9d
b31b1878-395a-40c7-afc3-71624bc88a83	6f220a6c-5ac7-476a-aa2a-88c4d6fd7f82	b2ba2fe1-84ba-4d59-ad57-f1872021589d
2a08b1d4-0c92-480d-bc17-d776c0dbaad0	6f220a6c-5ac7-476a-aa2a-88c4d6fd7f82	4202bfd2-c595-4d18-aa0f-80ae538e4fea
515ed0e3-9753-401a-9cd2-9b2c073a8321	6f220a6c-5ac7-476a-aa2a-88c4d6fd7f82	76d1637a-aaf4-451b-b1d0-7849957a42a8
3b02784c-164b-4120-a5cd-c246ad819b8f	6f220a6c-5ac7-476a-aa2a-88c4d6fd7f82	e5395d8e-6cdc-4411-b2b5-835ad149e933
ebb9840e-acd5-458e-baf8-d098591b2e84	6f220a6c-5ac7-476a-aa2a-88c4d6fd7f82	57d21fef-512f-43cb-9aa0-0bebae2f355e
03d75d06-f715-4a5c-ad67-220a66aec317	6f220a6c-5ac7-476a-aa2a-88c4d6fd7f82	db812fd9-919e-47e1-aa9d-7b0de37b9863
323ef7df-83d7-413c-bd74-bd8efb2d5f16	6f220a6c-5ac7-476a-aa2a-88c4d6fd7f82	050305b3-edec-407f-91e8-eb7f6e9fa1b3
a99b66ca-3fe0-4297-8b3b-217b23071426	6f220a6c-5ac7-476a-aa2a-88c4d6fd7f82	bf762354-ead7-4be6-a836-f57bd7df1c1d
9ed6518e-6780-416d-bbfc-5fd07995dcaa	6f220a6c-5ac7-476a-aa2a-88c4d6fd7f82	2a5a1c0d-47b4-4e9f-9ab4-b9106ed67a9d
d3126849-ef7f-42d7-849f-357d05c05ddd	6f220a6c-5ac7-476a-aa2a-88c4d6fd7f82	f75c6bcc-c9ae-4a04-a8e0-f56d351009af
d8813aec-1f30-4eb2-9c98-ee2669865b17	6f220a6c-5ac7-476a-aa2a-88c4d6fd7f82	8231e7d4-b4e8-495a-b881-3bfabbd85b67
8b144e30-d6a3-43b1-9c8a-b349c0e9659a	6f220a6c-5ac7-476a-aa2a-88c4d6fd7f82	1cdef3b1-d9ec-4f0d-9b7f-e6e927643e9a
e7bd9acf-f1b3-489a-ba70-a5d2045bbaa8	6f220a6c-5ac7-476a-aa2a-88c4d6fd7f82	6a0ca14f-762d-4171-974e-c5870aa4076f
128355ee-f08e-4a0d-861c-67dd04452121	6f220a6c-5ac7-476a-aa2a-88c4d6fd7f82	bad99487-1598-4525-ad21-de5dce5a91dc
46c8f448-35df-4d6a-8296-739d494d7796	6f220a6c-5ac7-476a-aa2a-88c4d6fd7f82	a590fd62-ff70-4e2f-aeb0-caf4b535c746
5eb8c18d-d347-44e4-b43c-a331efb089ca	6f220a6c-5ac7-476a-aa2a-88c4d6fd7f82	17665863-3735-46dc-96b5-2d9ebecff977
7589b5be-37ae-4b7e-998c-e31a7871bb35	6f220a6c-5ac7-476a-aa2a-88c4d6fd7f82	36876181-d912-41bd-b06a-60c741e04818
e553d682-4b89-4cc1-a495-d1a2577efaee	6f220a6c-5ac7-476a-aa2a-88c4d6fd7f82	6c32aa54-5304-4b8d-a2f2-2d822f61be12
bd2cd24b-bc52-4d97-9c4e-81957cb464a0	6f220a6c-5ac7-476a-aa2a-88c4d6fd7f82	110560c2-7eb4-4890-b004-659f0203dd83
5b0f21fb-7857-4c77-b180-3ff2193a157b	6f220a6c-5ac7-476a-aa2a-88c4d6fd7f82	2cc0b75a-d873-405a-a0c0-16db2fbc6b0c
580018f6-84ac-4ad5-b6b1-8ec0ed07f64f	6f220a6c-5ac7-476a-aa2a-88c4d6fd7f82	d86c4f72-d7de-4941-85fe-6961f64b2ea2
fb161371-373d-4632-bc65-24140ed41462	6f220a6c-5ac7-476a-aa2a-88c4d6fd7f82	6bd00f42-381f-4896-8623-b5544b4b0b22
1f86b4a3-fae5-4065-bfd5-077d49fdb6cb	6f220a6c-5ac7-476a-aa2a-88c4d6fd7f82	2320bed8-da22-4c89-b9fb-ff4b418f4a8c
724bf706-0b58-40c7-8934-78fe8ec02d4d	6f220a6c-5ac7-476a-aa2a-88c4d6fd7f82	d4633090-107d-403d-97c2-2d0d55c27c6b
b3caa667-4883-4725-a0b2-7c2e19a84a6a	6f220a6c-5ac7-476a-aa2a-88c4d6fd7f82	108b4f24-756f-41e2-ac39-931accb6ea93
0b6d0094-466d-4d7b-9dc6-fee848580e81	6f220a6c-5ac7-476a-aa2a-88c4d6fd7f82	a39d27bb-6303-421a-b7ce-72f7d99f5440
47dc5b18-df1e-49a3-a721-b0f74b8ad26c	6f220a6c-5ac7-476a-aa2a-88c4d6fd7f82	8ce60f0c-ccc9-4184-8e2b-c206676cf5c9
f5fc4327-0d12-4871-b292-75913d55a537	6f220a6c-5ac7-476a-aa2a-88c4d6fd7f82	dd907879-5cbc-47f2-babb-ff4b2defdc6c
d2017e02-9be3-4a67-895b-e5e6084e58ee	6f220a6c-5ac7-476a-aa2a-88c4d6fd7f82	c1f47380-0996-4290-b87e-077540b9b9d7
1eb1b69d-a7ba-4901-93ea-1de0a3dd4907	6f220a6c-5ac7-476a-aa2a-88c4d6fd7f82	00d3653e-11f3-4810-a61a-a1a332dfa2b9
3d1daaf5-b39f-4b59-88c7-dbc3885c64b3	6f220a6c-5ac7-476a-aa2a-88c4d6fd7f82	7a8ba668-b0af-4363-a8e4-f144a7505a1c
d1e2a3f0-9adf-4a9e-83bb-531a18e494df	6f220a6c-5ac7-476a-aa2a-88c4d6fd7f82	d5860be8-90b5-49c2-806f-afe0dd274de2
50d75d34-d4fd-446a-b228-c02385cc052f	6f220a6c-5ac7-476a-aa2a-88c4d6fd7f82	75a0377a-5654-48b7-beb7-de38c5ef3989
cddc6d6d-511e-4379-8b7b-361630ba8eff	6f220a6c-5ac7-476a-aa2a-88c4d6fd7f82	25ba7451-8f52-498b-a711-63e0912d3d96
b85e384c-17c5-45ca-8af7-4ffa5a55e04e	6f220a6c-5ac7-476a-aa2a-88c4d6fd7f82	a78b2610-91d9-45d7-995d-acd45cdb2467
c2294336-1dee-4b98-9eea-19228e29f09e	6f220a6c-5ac7-476a-aa2a-88c4d6fd7f82	9fb4b34d-e40e-49a4-8792-2ea2bafd09e4
bc314902-1829-4a9d-a8a3-d109b9ea2cc8	6f220a6c-5ac7-476a-aa2a-88c4d6fd7f82	ae8acfa4-7627-4be5-850c-08e578e5120d
f92f531b-7e21-4443-a0dc-2a03fe746705	6f220a6c-5ac7-476a-aa2a-88c4d6fd7f82	4a0bb4f9-c62e-43be-8b7f-43c655b8ef87
ba5743af-50af-483f-901a-bb4f4f745a3f	6f220a6c-5ac7-476a-aa2a-88c4d6fd7f82	32e6f002-686e-476d-927c-ce33afae643f
e11f99bf-92a8-4c7d-89b0-ba83ab0b32c8	6f220a6c-5ac7-476a-aa2a-88c4d6fd7f82	f7a4888a-cfde-423f-a37c-58da8a4a816d
c993032c-1df7-4f2a-b31f-7978fd69055c	6f220a6c-5ac7-476a-aa2a-88c4d6fd7f82	4b679c02-a189-48d9-bcf6-08f2e43b0e3c
40aabdd9-e341-4eea-b0e7-4630aafa0169	6f220a6c-5ac7-476a-aa2a-88c4d6fd7f82	f951e8be-b16f-4c3d-8f09-e9876962c656
9ace3473-7659-4876-87bc-aaa4aacef8ff	6f220a6c-5ac7-476a-aa2a-88c4d6fd7f82	4476b209-eac9-4a2d-80b4-0ea8b554062b
ea83be03-7e96-41e6-9215-ff043992daf9	6f220a6c-5ac7-476a-aa2a-88c4d6fd7f82	a60d00c1-f5a6-418d-b33e-82262a17f27f
781fe306-ef50-4691-9710-63f6c6721d86	6f220a6c-5ac7-476a-aa2a-88c4d6fd7f82	e618d856-394d-4dd2-a082-1c6ad0e1a536
75d267c5-336a-48dc-85b7-deae3ab5f1d6	6f220a6c-5ac7-476a-aa2a-88c4d6fd7f82	157f216b-29fc-4e27-b1f9-0037bc198653
80586cd6-2396-4fc8-8867-d98807f23aa6	6f220a6c-5ac7-476a-aa2a-88c4d6fd7f82	49327f7a-a0dd-49c2-9ebe-5f18b1678222
6b44c4d9-0c06-410e-9f21-791e195b2df9	6f220a6c-5ac7-476a-aa2a-88c4d6fd7f82	19e05924-5d4f-4757-81e6-1c37d4916abc
aba00856-3285-48f3-997c-a862fbd5f47c	6f220a6c-5ac7-476a-aa2a-88c4d6fd7f82	b269cf3b-410b-48b6-9b98-a767a359bfca
45472815-f38f-4cc3-a503-fc5d9430287f	6f220a6c-5ac7-476a-aa2a-88c4d6fd7f82	76e4c1f5-1cb3-4f6c-b1d1-c826260ff287
dfa75826-d2d8-4b89-910d-436dd357e385	6f220a6c-5ac7-476a-aa2a-88c4d6fd7f82	f56acff4-9d19-4438-a35a-57696e8c2e4b
99c7c57d-2957-4409-93ac-c38aab85c795	6f220a6c-5ac7-476a-aa2a-88c4d6fd7f82	b90df2f5-b568-46cd-bfd1-7e39893e634b
1d531366-ef08-4fe9-9f48-f09e524b40fd	6f220a6c-5ac7-476a-aa2a-88c4d6fd7f82	6bbf4a74-2e94-49e8-83bb-4110c19f0e13
54cf5867-35ee-4a9b-b91f-8832a7942fc8	6f220a6c-5ac7-476a-aa2a-88c4d6fd7f82	529daa10-dfbb-4401-80e8-fc9a363f3807
646ce1b3-8d3e-4ba5-96fd-fd995adb6e7f	6f220a6c-5ac7-476a-aa2a-88c4d6fd7f82	f5e90c0e-8733-43ac-879f-55c5fc15425a
9087d03b-d19f-46a5-bab5-c19a9abec122	6f220a6c-5ac7-476a-aa2a-88c4d6fd7f82	404c9ddd-8025-4581-8f27-decf8f551a16
3550a71c-9ffe-4adb-86fa-613450e0b1d7	6f220a6c-5ac7-476a-aa2a-88c4d6fd7f82	cbe13e0e-4693-45a0-8878-30ff3fdd825a
32874650-d412-4402-a2ec-011b5983f56e	6f220a6c-5ac7-476a-aa2a-88c4d6fd7f82	4539e17a-67ab-44cc-85f3-5e2d300899b2
0f61a57f-a43d-44d1-b057-d65d2495ad5b	6f220a6c-5ac7-476a-aa2a-88c4d6fd7f82	cd940f62-f215-4901-bfec-f38cf7713515
74255fa9-391f-4f1c-9263-3afdb082978c	c5871d62-fd0a-47b7-88ea-17e6b18b148f	4d386bdc-9a78-4215-a9c1-eb6d22b68b10
3f7e27fe-1961-4cc6-9917-4c6fe71f4365	c5871d62-fd0a-47b7-88ea-17e6b18b148f	20e5c59f-7396-46dc-8297-142e40347332
c75a120a-f2ae-4545-af4e-bf477352c015	c5871d62-fd0a-47b7-88ea-17e6b18b148f	5c4f1a53-b5be-49c3-8639-e0ef8b62826a
681570bc-07ee-4922-8e27-034ac0619ff1	c5871d62-fd0a-47b7-88ea-17e6b18b148f	c88911a2-b1b8-496f-9c53-adea5384f7cf
cb9f6c83-4695-4cd1-8ca1-be26a9fa1b64	c5871d62-fd0a-47b7-88ea-17e6b18b148f	933f5bd1-6cdc-4d92-85fe-a13dfaa6b71c
a72ea57c-bb29-42bd-b139-10bb93b23626	c5871d62-fd0a-47b7-88ea-17e6b18b148f	6710a77c-e35a-4f4c-a1d8-bd2a480faf9b
a6c0108b-f8c5-4013-9e5b-d5e6da87e1d9	c5871d62-fd0a-47b7-88ea-17e6b18b148f	879b5348-dc23-4238-9770-618fca34f404
bc16767c-cd9f-455f-bdd2-960675f4fe67	c5871d62-fd0a-47b7-88ea-17e6b18b148f	f91b7933-b575-4783-bdeb-69883ff75b57
af2e2349-26b0-4f51-88f7-e816172b5457	c5871d62-fd0a-47b7-88ea-17e6b18b148f	b824f887-522b-42c3-bb6d-e9bf3fe2c68d
d835de7e-b726-4103-8df2-558662b9a6c1	c5871d62-fd0a-47b7-88ea-17e6b18b148f	27b4f7cc-d8d9-4b12-bb83-a47153e5d135
6e3b767f-81ce-4316-942a-6d0d0568306b	c5871d62-fd0a-47b7-88ea-17e6b18b148f	250dfee3-8da0-479e-aad8-2a74f24b9f9d
329b10a3-5aa0-48a3-a4bd-522b883573ef	c5871d62-fd0a-47b7-88ea-17e6b18b148f	b2ba2fe1-84ba-4d59-ad57-f1872021589d
e44822c9-f1a3-4ff0-880c-6cd45f141d1b	c5871d62-fd0a-47b7-88ea-17e6b18b148f	4202bfd2-c595-4d18-aa0f-80ae538e4fea
f88bfde0-a4b7-4dd3-aebb-cf08f1a37755	c5871d62-fd0a-47b7-88ea-17e6b18b148f	76d1637a-aaf4-451b-b1d0-7849957a42a8
83ec3559-548b-4b50-8b38-4249a5c25480	c5871d62-fd0a-47b7-88ea-17e6b18b148f	e5395d8e-6cdc-4411-b2b5-835ad149e933
3c46657f-cc13-491b-92f2-e7d5b6296f77	c5871d62-fd0a-47b7-88ea-17e6b18b148f	57d21fef-512f-43cb-9aa0-0bebae2f355e
c1591de4-5327-4db6-b1a7-ffe5636292a1	c5871d62-fd0a-47b7-88ea-17e6b18b148f	db812fd9-919e-47e1-aa9d-7b0de37b9863
b664ba60-3b77-4d4c-8fea-efa04b2b6cba	c5871d62-fd0a-47b7-88ea-17e6b18b148f	050305b3-edec-407f-91e8-eb7f6e9fa1b3
c1c809e3-460f-4a0e-98b3-6cc96b3f5a3a	c5871d62-fd0a-47b7-88ea-17e6b18b148f	bf762354-ead7-4be6-a836-f57bd7df1c1d
8d2c053e-8c9e-474b-97c3-f089d2223a1e	c5871d62-fd0a-47b7-88ea-17e6b18b148f	2a5a1c0d-47b4-4e9f-9ab4-b9106ed67a9d
13ca8006-cd47-47ce-bd09-d2253acc5afa	c5871d62-fd0a-47b7-88ea-17e6b18b148f	f75c6bcc-c9ae-4a04-a8e0-f56d351009af
4c35ba59-9f21-4ff8-9322-da1f7710f74f	c5871d62-fd0a-47b7-88ea-17e6b18b148f	8231e7d4-b4e8-495a-b881-3bfabbd85b67
c4b0637c-461c-41e6-a8e1-034fbaafdc74	c5871d62-fd0a-47b7-88ea-17e6b18b148f	1cdef3b1-d9ec-4f0d-9b7f-e6e927643e9a
7323ca66-5f60-4f50-9695-fb488314fde9	c5871d62-fd0a-47b7-88ea-17e6b18b148f	6a0ca14f-762d-4171-974e-c5870aa4076f
f9bc4ae5-ae67-4d89-a2a2-de9bcbe2d9b0	c5871d62-fd0a-47b7-88ea-17e6b18b148f	bad99487-1598-4525-ad21-de5dce5a91dc
56b08ff5-e346-4795-adee-c7d985f78339	c5871d62-fd0a-47b7-88ea-17e6b18b148f	a590fd62-ff70-4e2f-aeb0-caf4b535c746
89326eeb-0069-4442-adb6-effb95f5002b	c5871d62-fd0a-47b7-88ea-17e6b18b148f	17665863-3735-46dc-96b5-2d9ebecff977
7723e2be-72ea-4975-a415-0299f59ac3ba	c5871d62-fd0a-47b7-88ea-17e6b18b148f	36876181-d912-41bd-b06a-60c741e04818
fc789a16-2ccd-49a2-ac3a-4b0b3eafdc42	c5871d62-fd0a-47b7-88ea-17e6b18b148f	6c32aa54-5304-4b8d-a2f2-2d822f61be12
5998f81c-38ea-4f95-96ac-41b59499fa21	c5871d62-fd0a-47b7-88ea-17e6b18b148f	110560c2-7eb4-4890-b004-659f0203dd83
160ded22-ed2d-4c67-be78-0c9ec30323db	c5871d62-fd0a-47b7-88ea-17e6b18b148f	2cc0b75a-d873-405a-a0c0-16db2fbc6b0c
52abb90b-ef4f-440f-bbbf-6719e45f0266	c5871d62-fd0a-47b7-88ea-17e6b18b148f	d86c4f72-d7de-4941-85fe-6961f64b2ea2
69044d1a-8d46-4875-a9a7-ef10e72900a0	c5871d62-fd0a-47b7-88ea-17e6b18b148f	6bd00f42-381f-4896-8623-b5544b4b0b22
669c834a-26c4-44ca-887e-fa18fd79c35c	c5871d62-fd0a-47b7-88ea-17e6b18b148f	2320bed8-da22-4c89-b9fb-ff4b418f4a8c
992c821e-dc05-4d87-93db-9f5240c84f4a	c5871d62-fd0a-47b7-88ea-17e6b18b148f	d4633090-107d-403d-97c2-2d0d55c27c6b
20a08b9a-dc02-4ebf-90c5-33681cab23cd	c5871d62-fd0a-47b7-88ea-17e6b18b148f	108b4f24-756f-41e2-ac39-931accb6ea93
7f36e440-5a30-4d0e-97c6-ad5550cfed71	c5871d62-fd0a-47b7-88ea-17e6b18b148f	a39d27bb-6303-421a-b7ce-72f7d99f5440
dd0d1590-5df0-4b66-85f4-873f10fb5833	c5871d62-fd0a-47b7-88ea-17e6b18b148f	8ce60f0c-ccc9-4184-8e2b-c206676cf5c9
512d44dc-f3dd-4422-b103-a7d928992a92	c5871d62-fd0a-47b7-88ea-17e6b18b148f	dd907879-5cbc-47f2-babb-ff4b2defdc6c
ffa1ab5f-9f73-48c5-8915-9f109e1733ef	c5871d62-fd0a-47b7-88ea-17e6b18b148f	c1f47380-0996-4290-b87e-077540b9b9d7
b5051a85-58d1-4d48-9c93-24640571fac3	c5871d62-fd0a-47b7-88ea-17e6b18b148f	00d3653e-11f3-4810-a61a-a1a332dfa2b9
66bf468d-1cd1-4c50-884d-aeaf2c19a3d9	c5871d62-fd0a-47b7-88ea-17e6b18b148f	7a8ba668-b0af-4363-a8e4-f144a7505a1c
ae902574-bcc7-426a-8597-df10499880d3	c5871d62-fd0a-47b7-88ea-17e6b18b148f	d5860be8-90b5-49c2-806f-afe0dd274de2
65daf4fd-9c89-467c-82b3-49117e9f3fe5	c5871d62-fd0a-47b7-88ea-17e6b18b148f	75a0377a-5654-48b7-beb7-de38c5ef3989
a2e1749d-3d83-44ff-8089-76351cdbfab4	c5871d62-fd0a-47b7-88ea-17e6b18b148f	25ba7451-8f52-498b-a711-63e0912d3d96
f2256a3b-49a6-4909-ab92-7809a9798984	c5871d62-fd0a-47b7-88ea-17e6b18b148f	a78b2610-91d9-45d7-995d-acd45cdb2467
52ba61d0-f4b8-4f99-b061-440fa5eaefbb	c5871d62-fd0a-47b7-88ea-17e6b18b148f	9fb4b34d-e40e-49a4-8792-2ea2bafd09e4
3d0cabc2-5958-485b-80df-b11e3faada53	c5871d62-fd0a-47b7-88ea-17e6b18b148f	ae8acfa4-7627-4be5-850c-08e578e5120d
f21b8df1-1fba-43d4-ad2d-17ad8a23f53b	c5871d62-fd0a-47b7-88ea-17e6b18b148f	4a0bb4f9-c62e-43be-8b7f-43c655b8ef87
ce4e96a0-bef2-48a3-9236-73f6403eea4b	c5871d62-fd0a-47b7-88ea-17e6b18b148f	32e6f002-686e-476d-927c-ce33afae643f
5e54f5cd-e624-45cf-9b1c-16db27db9c3a	c5871d62-fd0a-47b7-88ea-17e6b18b148f	f7a4888a-cfde-423f-a37c-58da8a4a816d
2a305acf-74da-45ce-b372-ac46bfe3936f	c5871d62-fd0a-47b7-88ea-17e6b18b148f	4b679c02-a189-48d9-bcf6-08f2e43b0e3c
08d422ce-6055-450f-aa2e-b928bbf2c433	c5871d62-fd0a-47b7-88ea-17e6b18b148f	f951e8be-b16f-4c3d-8f09-e9876962c656
f8ade05b-0037-429c-ba0d-71eb2de95ad6	c5871d62-fd0a-47b7-88ea-17e6b18b148f	4476b209-eac9-4a2d-80b4-0ea8b554062b
fd456985-c991-44d1-b78a-8658b80f10b2	c5871d62-fd0a-47b7-88ea-17e6b18b148f	a60d00c1-f5a6-418d-b33e-82262a17f27f
a03d7906-f9df-4734-adbe-414300de9f83	c5871d62-fd0a-47b7-88ea-17e6b18b148f	e618d856-394d-4dd2-a082-1c6ad0e1a536
f581bb68-61b0-4443-9d19-43d1d9265ebc	c5871d62-fd0a-47b7-88ea-17e6b18b148f	157f216b-29fc-4e27-b1f9-0037bc198653
bb152542-ff3c-4e1d-8e31-206bf9c80ec4	c5871d62-fd0a-47b7-88ea-17e6b18b148f	49327f7a-a0dd-49c2-9ebe-5f18b1678222
497eb4b4-82d4-497a-81bd-791753213fbe	c5871d62-fd0a-47b7-88ea-17e6b18b148f	19e05924-5d4f-4757-81e6-1c37d4916abc
d3f66e2c-e928-4767-b9fe-d48894855ae2	686f9b85-9087-40c8-bed8-651369cb3abf	4d386bdc-9a78-4215-a9c1-eb6d22b68b10
c1129393-32ea-443d-b625-722c926e78df	686f9b85-9087-40c8-bed8-651369cb3abf	20e5c59f-7396-46dc-8297-142e40347332
aabdb161-0d76-48b4-9422-565f2329d780	686f9b85-9087-40c8-bed8-651369cb3abf	5c4f1a53-b5be-49c3-8639-e0ef8b62826a
ecacb9a5-118f-45fb-9274-add7d7645f69	686f9b85-9087-40c8-bed8-651369cb3abf	c88911a2-b1b8-496f-9c53-adea5384f7cf
fca9dd87-3691-421b-b1a1-96d86bb0cffe	686f9b85-9087-40c8-bed8-651369cb3abf	933f5bd1-6cdc-4d92-85fe-a13dfaa6b71c
b90503bc-511a-4687-be45-e421cb764564	686f9b85-9087-40c8-bed8-651369cb3abf	6710a77c-e35a-4f4c-a1d8-bd2a480faf9b
96983084-25c9-4497-83fb-ce06a3faaeff	686f9b85-9087-40c8-bed8-651369cb3abf	879b5348-dc23-4238-9770-618fca34f404
996744bc-00df-4a05-8d9a-a2a466671e25	686f9b85-9087-40c8-bed8-651369cb3abf	f91b7933-b575-4783-bdeb-69883ff75b57
fab44243-e870-4925-b7df-26478f90cbb6	686f9b85-9087-40c8-bed8-651369cb3abf	b824f887-522b-42c3-bb6d-e9bf3fe2c68d
a49e33a9-dbc7-4c10-b4ab-ec1773b40307	686f9b85-9087-40c8-bed8-651369cb3abf	27b4f7cc-d8d9-4b12-bb83-a47153e5d135
8939f4cf-3ce4-4b7f-bf44-3e15240afd95	686f9b85-9087-40c8-bed8-651369cb3abf	250dfee3-8da0-479e-aad8-2a74f24b9f9d
41c35d0a-1d06-497a-914d-e0990010bb5f	686f9b85-9087-40c8-bed8-651369cb3abf	b2ba2fe1-84ba-4d59-ad57-f1872021589d
2635d79e-556e-45df-92a3-b24a935e711a	686f9b85-9087-40c8-bed8-651369cb3abf	4202bfd2-c595-4d18-aa0f-80ae538e4fea
0c18b996-9c6e-4d3b-b589-de5c9066a53a	686f9b85-9087-40c8-bed8-651369cb3abf	76d1637a-aaf4-451b-b1d0-7849957a42a8
6b12f061-3ac5-4498-82e4-734f2928d1f7	686f9b85-9087-40c8-bed8-651369cb3abf	e5395d8e-6cdc-4411-b2b5-835ad149e933
b6e58b39-3efe-4ba7-80db-44a87b2217c5	686f9b85-9087-40c8-bed8-651369cb3abf	57d21fef-512f-43cb-9aa0-0bebae2f355e
4a01d73a-eabc-4cd5-b49d-c0fbeb46429c	686f9b85-9087-40c8-bed8-651369cb3abf	db812fd9-919e-47e1-aa9d-7b0de37b9863
b49a36b5-d5c8-4dce-9f03-e222691b809a	686f9b85-9087-40c8-bed8-651369cb3abf	050305b3-edec-407f-91e8-eb7f6e9fa1b3
99107339-bd33-4cb9-b654-1a5d02a3d99d	686f9b85-9087-40c8-bed8-651369cb3abf	bf762354-ead7-4be6-a836-f57bd7df1c1d
229fb946-0cb7-42a6-ac3f-a0ee4e45888a	686f9b85-9087-40c8-bed8-651369cb3abf	2a5a1c0d-47b4-4e9f-9ab4-b9106ed67a9d
691381f6-6fa7-4710-9c5f-af1fd0dd44ec	686f9b85-9087-40c8-bed8-651369cb3abf	f75c6bcc-c9ae-4a04-a8e0-f56d351009af
c31ce431-08b0-449a-9b08-dde807f42bbd	686f9b85-9087-40c8-bed8-651369cb3abf	8231e7d4-b4e8-495a-b881-3bfabbd85b67
f62eab2e-dcae-44bf-8c38-927f3092aabb	686f9b85-9087-40c8-bed8-651369cb3abf	1cdef3b1-d9ec-4f0d-9b7f-e6e927643e9a
204bd7ff-5955-46c9-bdf8-eca446540e4c	686f9b85-9087-40c8-bed8-651369cb3abf	6a0ca14f-762d-4171-974e-c5870aa4076f
d88315f8-94da-4a30-ba7c-df63fa9824a8	686f9b85-9087-40c8-bed8-651369cb3abf	bad99487-1598-4525-ad21-de5dce5a91dc
82ba4c61-37ab-4b54-9053-0d04d6d3f1a2	686f9b85-9087-40c8-bed8-651369cb3abf	a590fd62-ff70-4e2f-aeb0-caf4b535c746
6f5356c3-14d0-4c7f-822a-affa00fc3040	686f9b85-9087-40c8-bed8-651369cb3abf	17665863-3735-46dc-96b5-2d9ebecff977
df9f2454-3e7e-4126-b89d-a17836edde92	686f9b85-9087-40c8-bed8-651369cb3abf	36876181-d912-41bd-b06a-60c741e04818
36fadfbe-bd01-4f8f-9d57-45b645b49416	686f9b85-9087-40c8-bed8-651369cb3abf	6c32aa54-5304-4b8d-a2f2-2d822f61be12
54f2fba0-cd67-467d-8e69-e53119d16043	686f9b85-9087-40c8-bed8-651369cb3abf	110560c2-7eb4-4890-b004-659f0203dd83
b3db7c79-c776-4472-93e1-279a21c6de09	686f9b85-9087-40c8-bed8-651369cb3abf	2cc0b75a-d873-405a-a0c0-16db2fbc6b0c
af47b06d-84a2-4157-9d6a-44cbfe15d8b2	686f9b85-9087-40c8-bed8-651369cb3abf	d86c4f72-d7de-4941-85fe-6961f64b2ea2
bc47c7c1-54b5-4cba-8ed6-d44cc959068c	686f9b85-9087-40c8-bed8-651369cb3abf	6bd00f42-381f-4896-8623-b5544b4b0b22
b0fad697-def8-40bd-b6c6-cee9abd4df1c	686f9b85-9087-40c8-bed8-651369cb3abf	2320bed8-da22-4c89-b9fb-ff4b418f4a8c
313ef35c-ba05-4294-9f46-be7eeeec7c93	686f9b85-9087-40c8-bed8-651369cb3abf	d4633090-107d-403d-97c2-2d0d55c27c6b
e837ead3-b76b-42b3-9912-a6da4bbaa938	686f9b85-9087-40c8-bed8-651369cb3abf	108b4f24-756f-41e2-ac39-931accb6ea93
12cb484c-bb37-4694-9ae2-77d7e3ca566f	686f9b85-9087-40c8-bed8-651369cb3abf	a39d27bb-6303-421a-b7ce-72f7d99f5440
171a26da-d3e0-4599-8894-2fa8c1af58a1	686f9b85-9087-40c8-bed8-651369cb3abf	8ce60f0c-ccc9-4184-8e2b-c206676cf5c9
02125443-fcf1-46be-bb50-c1842a55f23e	686f9b85-9087-40c8-bed8-651369cb3abf	dd907879-5cbc-47f2-babb-ff4b2defdc6c
b53d52be-710a-484d-a9ee-4e478afabd6c	686f9b85-9087-40c8-bed8-651369cb3abf	c1f47380-0996-4290-b87e-077540b9b9d7
fb44eec7-c419-4461-8358-bc9dfdeaecdd	686f9b85-9087-40c8-bed8-651369cb3abf	00d3653e-11f3-4810-a61a-a1a332dfa2b9
1bc29767-3813-487c-9c4e-7d209d22f765	686f9b85-9087-40c8-bed8-651369cb3abf	7a8ba668-b0af-4363-a8e4-f144a7505a1c
c0c6da3f-dffe-4154-87ea-847c60c71394	686f9b85-9087-40c8-bed8-651369cb3abf	d5860be8-90b5-49c2-806f-afe0dd274de2
333a14f8-f59a-422f-9e3e-d2cde5671a6e	686f9b85-9087-40c8-bed8-651369cb3abf	75a0377a-5654-48b7-beb7-de38c5ef3989
adfbf5dd-023d-4503-8cdc-fbe844bf0f7f	686f9b85-9087-40c8-bed8-651369cb3abf	25ba7451-8f52-498b-a711-63e0912d3d96
13aa22d4-d700-4c63-8daa-641d3184cf04	686f9b85-9087-40c8-bed8-651369cb3abf	a78b2610-91d9-45d7-995d-acd45cdb2467
68e7e96e-fdc2-43f2-b90e-4695cacee315	686f9b85-9087-40c8-bed8-651369cb3abf	9fb4b34d-e40e-49a4-8792-2ea2bafd09e4
ec18f6d6-8524-4388-b8c0-5ee81f814cf8	686f9b85-9087-40c8-bed8-651369cb3abf	ae8acfa4-7627-4be5-850c-08e578e5120d
57ae7bb1-861c-4749-918e-164768d7cb45	686f9b85-9087-40c8-bed8-651369cb3abf	4a0bb4f9-c62e-43be-8b7f-43c655b8ef87
59742939-66a0-486f-9b3d-41d8840bfd45	686f9b85-9087-40c8-bed8-651369cb3abf	32e6f002-686e-476d-927c-ce33afae643f
64386c9e-ff2f-4631-9898-3389d1641f93	686f9b85-9087-40c8-bed8-651369cb3abf	f7a4888a-cfde-423f-a37c-58da8a4a816d
1e76a3f4-4d2c-43a1-9830-27ed752e6f1c	686f9b85-9087-40c8-bed8-651369cb3abf	4b679c02-a189-48d9-bcf6-08f2e43b0e3c
310d67d7-16cd-49fd-8250-0404b9526001	686f9b85-9087-40c8-bed8-651369cb3abf	f951e8be-b16f-4c3d-8f09-e9876962c656
855698cc-079a-44ab-9820-4b0ae752e87f	686f9b85-9087-40c8-bed8-651369cb3abf	4476b209-eac9-4a2d-80b4-0ea8b554062b
5c3c48ae-54a9-4758-b433-be0ca5e35e61	686f9b85-9087-40c8-bed8-651369cb3abf	a60d00c1-f5a6-418d-b33e-82262a17f27f
e2d15bb8-0932-4f65-9fdf-2f78897bbcbd	686f9b85-9087-40c8-bed8-651369cb3abf	e618d856-394d-4dd2-a082-1c6ad0e1a536
a99aea10-3ffd-451c-a07b-f0eda5b86df2	686f9b85-9087-40c8-bed8-651369cb3abf	157f216b-29fc-4e27-b1f9-0037bc198653
36220340-f552-4d51-8b40-b1d14370fce9	686f9b85-9087-40c8-bed8-651369cb3abf	49327f7a-a0dd-49c2-9ebe-5f18b1678222
85a47a9e-8272-4c18-ab9b-470e8fc76c33	686f9b85-9087-40c8-bed8-651369cb3abf	19e05924-5d4f-4757-81e6-1c37d4916abc
605b8439-8290-4289-b303-788555152ff7	c43d1a51-bd5e-4ad6-a5cc-be2cf6e37862	4d386bdc-9a78-4215-a9c1-eb6d22b68b10
29940a97-dbd9-46cd-a854-66a3d4d44e62	c43d1a51-bd5e-4ad6-a5cc-be2cf6e37862	20e5c59f-7396-46dc-8297-142e40347332
ee0236de-9927-4c8e-9661-0701f710ba62	c43d1a51-bd5e-4ad6-a5cc-be2cf6e37862	933f5bd1-6cdc-4d92-85fe-a13dfaa6b71c
34187068-64ea-4795-af0b-bb7188480b85	c43d1a51-bd5e-4ad6-a5cc-be2cf6e37862	6710a77c-e35a-4f4c-a1d8-bd2a480faf9b
8f8d93d7-7fbf-49fd-b1d4-d4cc71c23450	c43d1a51-bd5e-4ad6-a5cc-be2cf6e37862	b824f887-522b-42c3-bb6d-e9bf3fe2c68d
b819e018-47ff-4449-878b-87d413dfde12	c43d1a51-bd5e-4ad6-a5cc-be2cf6e37862	27b4f7cc-d8d9-4b12-bb83-a47153e5d135
82d51566-e214-4a4b-be86-9f3b8d3482bc	c43d1a51-bd5e-4ad6-a5cc-be2cf6e37862	a4be3422-b10b-4422-b513-fbdc9eeb864a
c2e4e183-7483-4fc3-ac03-f1513bcaafb8	c43d1a51-bd5e-4ad6-a5cc-be2cf6e37862	db812fd9-919e-47e1-aa9d-7b0de37b9863
1055e866-34bb-4c3f-ba89-aeefee3cf3ba	c43d1a51-bd5e-4ad6-a5cc-be2cf6e37862	2a5a1c0d-47b4-4e9f-9ab4-b9106ed67a9d
a798b4d1-3640-465e-bfc3-1450f44f2f34	c43d1a51-bd5e-4ad6-a5cc-be2cf6e37862	1cdef3b1-d9ec-4f0d-9b7f-e6e927643e9a
3fbbf399-4e7e-455b-96ac-5e4f75e9db66	c43d1a51-bd5e-4ad6-a5cc-be2cf6e37862	36876181-d912-41bd-b06a-60c741e04818
8f90ecc1-bcf1-46cf-9ac4-56d79382eab4	c43d1a51-bd5e-4ad6-a5cc-be2cf6e37862	f2011e4a-07b4-4261-b2b5-f4539f8c416a
63ea66b5-b09a-4b62-9178-c1ffda11617a	c43d1a51-bd5e-4ad6-a5cc-be2cf6e37862	b2552d1f-ede7-4eae-8c25-6a76e5a21d3d
5c44d74d-6c5b-45f1-8d5d-9f2eb335b1ae	c43d1a51-bd5e-4ad6-a5cc-be2cf6e37862	6484136b-fe57-404d-a347-b69e93c13522
bfa3986a-5855-4bbd-8c5a-f10ad1d28e2f	c43d1a51-bd5e-4ad6-a5cc-be2cf6e37862	2cc0b75a-d873-405a-a0c0-16db2fbc6b0c
edee9959-dc8c-4cc1-8e7b-5eb638312c20	c43d1a51-bd5e-4ad6-a5cc-be2cf6e37862	6bd00f42-381f-4896-8623-b5544b4b0b22
48a1c364-f79d-4b94-9295-c59066905f1b	c43d1a51-bd5e-4ad6-a5cc-be2cf6e37862	2320bed8-da22-4c89-b9fb-ff4b418f4a8c
432ec799-de97-4c65-a423-1e4892fcdacf	c43d1a51-bd5e-4ad6-a5cc-be2cf6e37862	d4633090-107d-403d-97c2-2d0d55c27c6b
37926508-dc16-4199-92bd-d2feffeb71b6	c43d1a51-bd5e-4ad6-a5cc-be2cf6e37862	108b4f24-756f-41e2-ac39-931accb6ea93
40546df6-843b-4b64-b18c-dc568431a860	c43d1a51-bd5e-4ad6-a5cc-be2cf6e37862	a39d27bb-6303-421a-b7ce-72f7d99f5440
f931990b-3579-4873-a5a4-52ba0fa4bac4	c43d1a51-bd5e-4ad6-a5cc-be2cf6e37862	8ce60f0c-ccc9-4184-8e2b-c206676cf5c9
84eb9d77-928f-40e1-9c48-7421e23da49c	c43d1a51-bd5e-4ad6-a5cc-be2cf6e37862	dd907879-5cbc-47f2-babb-ff4b2defdc6c
b016827e-500e-4853-9b06-c3e0db519c97	c43d1a51-bd5e-4ad6-a5cc-be2cf6e37862	75a0377a-5654-48b7-beb7-de38c5ef3989
1869893c-8f94-4482-ba92-7e78373fb039	c43d1a51-bd5e-4ad6-a5cc-be2cf6e37862	25ba7451-8f52-498b-a711-63e0912d3d96
82299c6f-0314-4762-ad43-090866eeb4cb	c43d1a51-bd5e-4ad6-a5cc-be2cf6e37862	a78b2610-91d9-45d7-995d-acd45cdb2467
f656fa22-ef77-44ac-b962-a59a2d355eb1	c43d1a51-bd5e-4ad6-a5cc-be2cf6e37862	32e6f002-686e-476d-927c-ce33afae643f
59b12a52-c936-47ad-8962-611f5ad35c46	c43d1a51-bd5e-4ad6-a5cc-be2cf6e37862	4b679c02-a189-48d9-bcf6-08f2e43b0e3c
9223dd95-7b28-469e-94c7-dd8f1dc7aba3	c43d1a51-bd5e-4ad6-a5cc-be2cf6e37862	f951e8be-b16f-4c3d-8f09-e9876962c656
fd3a0c0d-cf1e-4cf4-8ba6-07eecb09d041	c43d1a51-bd5e-4ad6-a5cc-be2cf6e37862	4476b209-eac9-4a2d-80b4-0ea8b554062b
2169e400-92ca-4f1d-9a06-67aa3a252762	c43d1a51-bd5e-4ad6-a5cc-be2cf6e37862	a60d00c1-f5a6-418d-b33e-82262a17f27f
728142c9-5aa7-4c8b-a719-f69dcdb0cacc	c43d1a51-bd5e-4ad6-a5cc-be2cf6e37862	e618d856-394d-4dd2-a082-1c6ad0e1a536
0aadfe09-f6df-4bb9-befb-bb487d3ce06b	c43d1a51-bd5e-4ad6-a5cc-be2cf6e37862	157f216b-29fc-4e27-b1f9-0037bc198653
b8195109-489e-4d94-8f37-3cb92f427f63	c43d1a51-bd5e-4ad6-a5cc-be2cf6e37862	49327f7a-a0dd-49c2-9ebe-5f18b1678222
171ca609-5733-4986-8499-5fccf4d46637	52d627c1-d317-462c-b6df-a4da19d22472	4d386bdc-9a78-4215-a9c1-eb6d22b68b10
74628867-ee8e-4b2a-9ec8-383bfb92c3e0	52d627c1-d317-462c-b6df-a4da19d22472	20e5c59f-7396-46dc-8297-142e40347332
7aa92915-6f55-4f3a-9aa8-da13b6d5f92a	52d627c1-d317-462c-b6df-a4da19d22472	933f5bd1-6cdc-4d92-85fe-a13dfaa6b71c
5eb88146-dbc3-4e2d-95ee-f34b87e3a32d	52d627c1-d317-462c-b6df-a4da19d22472	6710a77c-e35a-4f4c-a1d8-bd2a480faf9b
27b2db67-c00c-4949-bfd3-e0d7554910bf	52d627c1-d317-462c-b6df-a4da19d22472	b824f887-522b-42c3-bb6d-e9bf3fe2c68d
acaf16d4-d9a0-4066-84f4-4b2a662c9d56	52d627c1-d317-462c-b6df-a4da19d22472	27b4f7cc-d8d9-4b12-bb83-a47153e5d135
872de3e3-acaa-41b6-a3c3-4f59a674dc3c	52d627c1-d317-462c-b6df-a4da19d22472	db812fd9-919e-47e1-aa9d-7b0de37b9863
4f5e5b84-f117-4886-80b1-4ffd20867df2	52d627c1-d317-462c-b6df-a4da19d22472	2a5a1c0d-47b4-4e9f-9ab4-b9106ed67a9d
992b1450-d371-45d2-a94b-45e22a50d244	52d627c1-d317-462c-b6df-a4da19d22472	1cdef3b1-d9ec-4f0d-9b7f-e6e927643e9a
a99be8cc-4d48-4cc6-a017-3019c5c4e705	52d627c1-d317-462c-b6df-a4da19d22472	36876181-d912-41bd-b06a-60c741e04818
5df4a087-f66f-41ad-bf02-409a0c0e457c	52d627c1-d317-462c-b6df-a4da19d22472	f2011e4a-07b4-4261-b2b5-f4539f8c416a
7e392dd8-34a8-4612-82f1-08c7d114ff3e	52d627c1-d317-462c-b6df-a4da19d22472	b2552d1f-ede7-4eae-8c25-6a76e5a21d3d
f811c112-e24a-48dc-88c4-3c3c75d2cabd	52d627c1-d317-462c-b6df-a4da19d22472	6484136b-fe57-404d-a347-b69e93c13522
0920f61b-3576-40b5-bfe3-a3ca3df8f4d9	52d627c1-d317-462c-b6df-a4da19d22472	2cc0b75a-d873-405a-a0c0-16db2fbc6b0c
38f68b46-689e-43dd-afa7-20cae73e7f26	52d627c1-d317-462c-b6df-a4da19d22472	2320bed8-da22-4c89-b9fb-ff4b418f4a8c
d84db8ac-26b1-40fe-9c5f-024336560993	52d627c1-d317-462c-b6df-a4da19d22472	d4633090-107d-403d-97c2-2d0d55c27c6b
9b243707-3f18-4466-b6c3-d698a59ee9d5	52d627c1-d317-462c-b6df-a4da19d22472	108b4f24-756f-41e2-ac39-931accb6ea93
488f816e-8d79-427a-9262-3648b15a3a16	52d627c1-d317-462c-b6df-a4da19d22472	a39d27bb-6303-421a-b7ce-72f7d99f5440
bee4c08d-51e6-46d5-bf51-a4454cff5833	52d627c1-d317-462c-b6df-a4da19d22472	8ce60f0c-ccc9-4184-8e2b-c206676cf5c9
2c52d185-b1c7-4988-b5dd-14ba05917599	52d627c1-d317-462c-b6df-a4da19d22472	dd907879-5cbc-47f2-babb-ff4b2defdc6c
2f351a4a-0920-4eef-bc17-3635d6ca34ed	52d627c1-d317-462c-b6df-a4da19d22472	d95430d1-61e7-454b-a558-484d7ad0660f
0e373108-650b-443c-bf5f-e8d893683455	52d627c1-d317-462c-b6df-a4da19d22472	d5860be8-90b5-49c2-806f-afe0dd274de2
d298a2b9-adce-40b2-99b5-2bc9c19756f1	52d627c1-d317-462c-b6df-a4da19d22472	75a0377a-5654-48b7-beb7-de38c5ef3989
30168042-1b66-4ceb-b8ab-757d1c091e34	52d627c1-d317-462c-b6df-a4da19d22472	25ba7451-8f52-498b-a711-63e0912d3d96
f321e24e-ab2e-4c19-9688-8e96c5c65679	52d627c1-d317-462c-b6df-a4da19d22472	a78b2610-91d9-45d7-995d-acd45cdb2467
7c306228-be16-4475-b5f3-a837f45965c9	52d627c1-d317-462c-b6df-a4da19d22472	32e6f002-686e-476d-927c-ce33afae643f
82d34e69-7b08-4d3f-9649-9e712e48ce79	52d627c1-d317-462c-b6df-a4da19d22472	4b679c02-a189-48d9-bcf6-08f2e43b0e3c
be3cec0e-5698-4e82-8f04-36fcd0259341	52d627c1-d317-462c-b6df-a4da19d22472	f951e8be-b16f-4c3d-8f09-e9876962c656
8aee167c-3e7a-4da4-9116-2a81fe2a6aa2	52d627c1-d317-462c-b6df-a4da19d22472	4476b209-eac9-4a2d-80b4-0ea8b554062b
5d734196-f4a1-4a1a-892e-ee9c9201c1cc	52d627c1-d317-462c-b6df-a4da19d22472	a60d00c1-f5a6-418d-b33e-82262a17f27f
a34ac5aa-d900-47e8-b31b-fd0d8dc512be	52d627c1-d317-462c-b6df-a4da19d22472	e618d856-394d-4dd2-a082-1c6ad0e1a536
03c2d37d-12f7-46d0-bfcc-c0b380201c77	52d627c1-d317-462c-b6df-a4da19d22472	157f216b-29fc-4e27-b1f9-0037bc198653
bdf940a5-823c-46d5-bcdd-585043f4aa8f	52d627c1-d317-462c-b6df-a4da19d22472	49327f7a-a0dd-49c2-9ebe-5f18b1678222
c3d9734b-4fb1-47f6-b659-48ab96bb23ab	18f215ab-603c-4280-9ea0-69d54b285084	4d386bdc-9a78-4215-a9c1-eb6d22b68b10
769b1398-4c55-4bbb-a907-a82f1648b535	18f215ab-603c-4280-9ea0-69d54b285084	20e5c59f-7396-46dc-8297-142e40347332
de77329a-4a7f-4819-acc3-40d4c54b1525	18f215ab-603c-4280-9ea0-69d54b285084	5c4f1a53-b5be-49c3-8639-e0ef8b62826a
2838e91d-050c-49ec-adba-6d2377ec11b4	18f215ab-603c-4280-9ea0-69d54b285084	f2011e4a-07b4-4261-b2b5-f4539f8c416a
f0474d8e-2ad1-4b4f-96f4-d24c1e6b26e6	18f215ab-603c-4280-9ea0-69d54b285084	163342df-9367-4e54-ab5c-4a3b55a0eadf
b7d1c882-3465-4d97-b9fe-28092a0fd9ad	18f215ab-603c-4280-9ea0-69d54b285084	0504f8e1-168a-4ff6-ab0f-dd568397795c
c702d7b3-1389-4908-af8f-312213aacd07	18f215ab-603c-4280-9ea0-69d54b285084	053efc51-5d68-493e-9463-4a1bf18f3e48
2a8f412b-d212-403e-84b1-d54a71ad7bf4	18f215ab-603c-4280-9ea0-69d54b285084	ebe02472-e9c4-4989-a790-844163a82925
0694f531-76d3-4f22-acfe-93680b58e562	18f215ab-603c-4280-9ea0-69d54b285084	f7626507-7853-4068-9040-38e777f25125
ffc3e539-5d4e-465b-9c9c-0ee65b823bd6	18f215ab-603c-4280-9ea0-69d54b285084	6484136b-fe57-404d-a347-b69e93c13522
c1fd1d35-dcc9-4e6b-8dae-fae8e92a7467	18f215ab-603c-4280-9ea0-69d54b285084	4d94fe84-d560-491b-991c-e7178471a947
268cb88b-0e7a-4192-84e5-97486603125a	18f215ab-603c-4280-9ea0-69d54b285084	94334195-e94b-4573-9741-bdb8b6136ff9
7c4667ad-5bb0-4f2f-95c9-7bc15f8b4aff	18f215ab-603c-4280-9ea0-69d54b285084	ed1f3bdb-ad27-4f05-822d-b2fdaf075597
7f1617af-0995-4d01-8d75-36e5cd7df738	18f215ab-603c-4280-9ea0-69d54b285084	19e05924-5d4f-4757-81e6-1c37d4916abc
2a82f97b-7a86-476d-bd34-faef8287fca7	18f215ab-603c-4280-9ea0-69d54b285084	32e6f002-686e-476d-927c-ce33afae643f
ff03f3fc-4db1-4c6c-a924-7d260ef1e475	18f215ab-603c-4280-9ea0-69d54b285084	00cef543-6279-4001-98e9-658888d00d4a
ca00baf0-7ca2-4655-a975-56f7196c6457	18f215ab-603c-4280-9ea0-69d54b285084	f7a4888a-cfde-423f-a37c-58da8a4a816d
a8a3c719-9222-431d-8db8-30f0ea91812d	18f215ab-603c-4280-9ea0-69d54b285084	4b679c02-a189-48d9-bcf6-08f2e43b0e3c
6e462618-587e-4353-9b6b-87b6d3fb8424	18f215ab-603c-4280-9ea0-69d54b285084	f951e8be-b16f-4c3d-8f09-e9876962c656
3f17c955-9223-48a8-872f-e022884643dd	18f215ab-603c-4280-9ea0-69d54b285084	4476b209-eac9-4a2d-80b4-0ea8b554062b
9f14f611-e82f-41bb-8fc5-26a9a3dc76b4	18f215ab-603c-4280-9ea0-69d54b285084	75a0377a-5654-48b7-beb7-de38c5ef3989
0ed42eee-d66a-4f0b-a5ce-b951f764c467	18f215ab-603c-4280-9ea0-69d54b285084	25ba7451-8f52-498b-a711-63e0912d3d96
29af35c3-549d-434b-bbec-3d6a75d41cc8	18f215ab-603c-4280-9ea0-69d54b285084	a78b2610-91d9-45d7-995d-acd45cdb2467
081cf6ec-cdfb-4d1e-808c-77ef824235db	18f215ab-603c-4280-9ea0-69d54b285084	108b4f24-756f-41e2-ac39-931accb6ea93
df802ea7-c360-4a32-9760-51b14d5688b0	18f215ab-603c-4280-9ea0-69d54b285084	a60d00c1-f5a6-418d-b33e-82262a17f27f
fad246be-4cc0-49ac-900a-06242d97e489	18f215ab-603c-4280-9ea0-69d54b285084	e618d856-394d-4dd2-a082-1c6ad0e1a536
e6e724c9-7cb1-48be-b572-403ace3c69a5	18f215ab-603c-4280-9ea0-69d54b285084	157f216b-29fc-4e27-b1f9-0037bc198653
b5aaf080-7fff-4bc7-860f-445331973f3c	18f215ab-603c-4280-9ea0-69d54b285084	49327f7a-a0dd-49c2-9ebe-5f18b1678222
cbd2805d-392b-4651-b5e0-5c35114cdbd8	9ed7fcec-d186-4c2f-b466-8d264b98887c	4d386bdc-9a78-4215-a9c1-eb6d22b68b10
c72387c0-894d-4c73-8901-16d1a7b579d7	9ed7fcec-d186-4c2f-b466-8d264b98887c	20e5c59f-7396-46dc-8297-142e40347332
94ae51b0-dd2e-4a10-a780-52c0e69de249	9ed7fcec-d186-4c2f-b466-8d264b98887c	5c4f1a53-b5be-49c3-8639-e0ef8b62826a
3b7bba0c-a4d3-4cac-83bf-7c17680a9a6b	9ed7fcec-d186-4c2f-b466-8d264b98887c	2cc0b75a-d873-405a-a0c0-16db2fbc6b0c
de0cdf6c-2c8b-49e8-82b5-beb8662cbd8f	9ed7fcec-d186-4c2f-b466-8d264b98887c	51efca30-9d3f-4e11-a348-1dad485a5697
1c10f520-2a88-47a4-9e4d-a10861a98090	9ed7fcec-d186-4c2f-b466-8d264b98887c	d86c4f72-d7de-4941-85fe-6961f64b2ea2
069dc02c-170a-454d-9a43-a20c2aea1305	9ed7fcec-d186-4c2f-b466-8d264b98887c	6bd00f42-381f-4896-8623-b5544b4b0b22
89d93698-d0ab-441a-b6a5-b7ebc9e99fb9	9ed7fcec-d186-4c2f-b466-8d264b98887c	2320bed8-da22-4c89-b9fb-ff4b418f4a8c
18497196-8f70-4fd9-aefb-f4e3bf71359e	9ed7fcec-d186-4c2f-b466-8d264b98887c	32e6f002-686e-476d-927c-ce33afae643f
ff3c9e1b-5c8e-4e12-a6a2-22e62eaff6b1	9ed7fcec-d186-4c2f-b466-8d264b98887c	f951e8be-b16f-4c3d-8f09-e9876962c656
1fac3198-f547-4903-aa56-8ca8b3389c56	9ed7fcec-d186-4c2f-b466-8d264b98887c	4476b209-eac9-4a2d-80b4-0ea8b554062b
03f051c9-030a-4f6b-982c-5bdafc6b3349	9ed7fcec-d186-4c2f-b466-8d264b98887c	75a0377a-5654-48b7-beb7-de38c5ef3989
b56aa4e0-53b6-4e07-b903-976016a17e0e	9ed7fcec-d186-4c2f-b466-8d264b98887c	25ba7451-8f52-498b-a711-63e0912d3d96
1dfb7a0f-42ed-40d3-ac3c-95c22976c394	9ed7fcec-d186-4c2f-b466-8d264b98887c	a78b2610-91d9-45d7-995d-acd45cdb2467
4fde2714-e85a-4208-a81d-01f95ce70951	9ed7fcec-d186-4c2f-b466-8d264b98887c	a60d00c1-f5a6-418d-b33e-82262a17f27f
f77ab00e-fa2e-40df-81d7-185bd5fe2b8f	9ed7fcec-d186-4c2f-b466-8d264b98887c	e618d856-394d-4dd2-a082-1c6ad0e1a536
d8dd508b-3059-4ac9-85bb-3bf20118a764	9ed7fcec-d186-4c2f-b466-8d264b98887c	157f216b-29fc-4e27-b1f9-0037bc198653
aa17381f-8474-4c3e-8187-375c4ff95609	9ed7fcec-d186-4c2f-b466-8d264b98887c	49327f7a-a0dd-49c2-9ebe-5f18b1678222
f3473536-d46e-4aae-9f03-fb7a5c2f7bc3	30c1b546-d6be-476d-a28b-f9b8fa4a74f3	4d386bdc-9a78-4215-a9c1-eb6d22b68b10
5b6bb94d-3365-4049-8c5d-d32d4cb78568	30c1b546-d6be-476d-a28b-f9b8fa4a74f3	20e5c59f-7396-46dc-8297-142e40347332
e46328d5-6960-4c80-90c8-327319aaabb9	30c1b546-d6be-476d-a28b-f9b8fa4a74f3	d4633090-107d-403d-97c2-2d0d55c27c6b
24190793-8e77-4a76-b32b-4b2529b967b4	30c1b546-d6be-476d-a28b-f9b8fa4a74f3	19a8509d-03ca-4da6-9df3-0b92df7ad979
e2c32d21-4d0b-4599-9226-5a9a5f5af894	30c1b546-d6be-476d-a28b-f9b8fa4a74f3	58072bb2-4d54-4ae8-b0c5-dc9f6097919f
9b14be12-40b5-48db-b9bd-b2a73b7e2ce9	30c1b546-d6be-476d-a28b-f9b8fa4a74f3	5053f6ca-436a-451a-93ee-c4ad12438907
38e7b2d4-1b48-4d55-8cc5-4b46702264c5	30c1b546-d6be-476d-a28b-f9b8fa4a74f3	32e6f002-686e-476d-927c-ce33afae643f
7be4dcd4-edcf-43fa-b82b-2095c748088e	30c1b546-d6be-476d-a28b-f9b8fa4a74f3	f951e8be-b16f-4c3d-8f09-e9876962c656
34e2c39a-8163-409c-b75d-a8e333d0780a	30c1b546-d6be-476d-a28b-f9b8fa4a74f3	4476b209-eac9-4a2d-80b4-0ea8b554062b
f873c6e1-746d-4e85-8531-49b98ef13467	30c1b546-d6be-476d-a28b-f9b8fa4a74f3	75a0377a-5654-48b7-beb7-de38c5ef3989
dfecd38a-6595-4c98-a6cd-b1435ef6e84d	30c1b546-d6be-476d-a28b-f9b8fa4a74f3	25ba7451-8f52-498b-a711-63e0912d3d96
1c913a24-30db-46fa-95fe-835a3da652f8	30c1b546-d6be-476d-a28b-f9b8fa4a74f3	a78b2610-91d9-45d7-995d-acd45cdb2467
d4a71336-09da-4edc-a4de-248ea180f6b6	30c1b546-d6be-476d-a28b-f9b8fa4a74f3	a60d00c1-f5a6-418d-b33e-82262a17f27f
d69970b9-7357-44b5-a401-43938cf33aa5	30c1b546-d6be-476d-a28b-f9b8fa4a74f3	e618d856-394d-4dd2-a082-1c6ad0e1a536
aa670165-d61e-4c85-a230-abe2f96641ae	30c1b546-d6be-476d-a28b-f9b8fa4a74f3	157f216b-29fc-4e27-b1f9-0037bc198653
53f79156-1a63-46ae-a36d-43560fa71503	30c1b546-d6be-476d-a28b-f9b8fa4a74f3	49327f7a-a0dd-49c2-9ebe-5f18b1678222
68665be1-fd50-4822-bca1-2669dbcc0b07	d96e7e61-4fcf-478a-aa8e-3af2da78754c	4d386bdc-9a78-4215-a9c1-eb6d22b68b10
5e2ac9f7-2fe4-4bb7-b336-10000c6461a6	d96e7e61-4fcf-478a-aa8e-3af2da78754c	4a4915f6-f177-463e-b39e-4da042aa8161
382d29ec-f9ca-4dfe-b1c2-900817435ecb	d96e7e61-4fcf-478a-aa8e-3af2da78754c	56873e03-3c87-4d82-8269-9e6aa3db3032
cd8733a5-635c-408f-84be-bb754a7bbd29	d96e7e61-4fcf-478a-aa8e-3af2da78754c	20e5c59f-7396-46dc-8297-142e40347332
a0890240-ff0a-4b93-9990-38b83893cfac	d96e7e61-4fcf-478a-aa8e-3af2da78754c	933f5bd1-6cdc-4d92-85fe-a13dfaa6b71c
080296ca-5cf2-4fd8-9411-9ebb44ea567e	d96e7e61-4fcf-478a-aa8e-3af2da78754c	6710a77c-e35a-4f4c-a1d8-bd2a480faf9b
ec8749b5-4d22-4645-a972-c7e7b294465f	d96e7e61-4fcf-478a-aa8e-3af2da78754c	b824f887-522b-42c3-bb6d-e9bf3fe2c68d
bdf406d2-3a1a-4ed2-8633-a5f071c570ef	d96e7e61-4fcf-478a-aa8e-3af2da78754c	75a0377a-5654-48b7-beb7-de38c5ef3989
4b8aaafe-9e9a-45e2-b0f4-432901bece6f	d96e7e61-4fcf-478a-aa8e-3af2da78754c	25ba7451-8f52-498b-a711-63e0912d3d96
0a6116b9-8f8e-4778-a16b-768e0b92dcad	d96e7e61-4fcf-478a-aa8e-3af2da78754c	a78b2610-91d9-45d7-995d-acd45cdb2467
45180a6e-c514-4e06-b2ae-60785dbbaa68	d96e7e61-4fcf-478a-aa8e-3af2da78754c	f951e8be-b16f-4c3d-8f09-e9876962c656
792602ce-1b6f-4a09-a4f6-bba296a47e60	d96e7e61-4fcf-478a-aa8e-3af2da78754c	4476b209-eac9-4a2d-80b4-0ea8b554062b
f3246959-47f3-4ff1-a8da-ba20d40bf2ba	d96e7e61-4fcf-478a-aa8e-3af2da78754c	a60d00c1-f5a6-418d-b33e-82262a17f27f
ff1b1e04-b0c6-4d2d-ac62-4626c5486c93	d96e7e61-4fcf-478a-aa8e-3af2da78754c	e618d856-394d-4dd2-a082-1c6ad0e1a536
0f3b20ce-65a4-4a3d-a5af-6eef1c178d0a	d96e7e61-4fcf-478a-aa8e-3af2da78754c	157f216b-29fc-4e27-b1f9-0037bc198653
a61bec64-888e-4836-8cb2-b20555f2a4c5	d96e7e61-4fcf-478a-aa8e-3af2da78754c	49327f7a-a0dd-49c2-9ebe-5f18b1678222
cd1d3d60-b7dc-4fd9-82bf-8e9fb7d94dd1	ffedd356-f752-411c-a857-25cd9734fefb	402faa4a-dee4-4bb4-917d-b51fe11342bf
ddd98132-4dc4-4715-9db3-1f86fec9dda8	8a213533-674c-4ab7-9511-f49ef20ce50c	402faa4a-dee4-4bb4-917d-b51fe11342bf
65ba0a37-2797-49f7-be4d-1e7ce633be8e	4833ecaa-cf51-465e-8bc2-28bcf2b08cf8	402faa4a-dee4-4bb4-917d-b51fe11342bf
\.


--
-- Data for Name: salarypayment; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.salarypayment (id, school_id, employee_id, month, gross, deductions, net, status, paid_on) FROM stdin;
\.


--
-- Data for Name: school; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.school (id, name, code, email, phone, address, is_active, created_at) FROM stdin;
26fc741e-7270-4f5a-98fd-63a548c315a3	ABC School	abc	office@abc	+91 90000 00001	Sector 1, Demo City	t	2026-10-21 11:44:42.2191
329eb5b7-10d1-42c9-b309-19477157eeb5	Delhi Public School	dps	office@dps	+91 90000 00002	Sector 9, Demo City	t	2026-10-21 11:44:42.470347
\.


--
-- Data for Name: section; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.section (id, school_id, name, classroom_id, class_teacher_id) FROM stdin;
2755244f-ebfe-46fd-9dc2-b20af10bb288	26fc741e-7270-4f5a-98fd-63a548c315a3	A	8348a30b-c177-4d70-91b5-2e4b48f4eff1	\N
0c1bd452-0717-4302-81c8-fa3005891c90	26fc741e-7270-4f5a-98fd-63a548c315a3	B	8348a30b-c177-4d70-91b5-2e4b48f4eff1	\N
8f60e3e2-7d5d-4f32-a29a-3bb38274749a	26fc741e-7270-4f5a-98fd-63a548c315a3	C	8348a30b-c177-4d70-91b5-2e4b48f4eff1	\N
0c2a8b3a-050d-4ef1-a426-835818283a76	26fc741e-7270-4f5a-98fd-63a548c315a3	D	8348a30b-c177-4d70-91b5-2e4b48f4eff1	\N
34f11d4c-6dcc-41a4-b650-e394a0c0c5f7	26fc741e-7270-4f5a-98fd-63a548c315a3	E	8348a30b-c177-4d70-91b5-2e4b48f4eff1	\N
0f488e94-ba3c-4fb6-ac3d-0610b8cd1c17	26fc741e-7270-4f5a-98fd-63a548c315a3	F	8348a30b-c177-4d70-91b5-2e4b48f4eff1	\N
053dd32d-b5b6-4646-97d9-9767c8ee6205	26fc741e-7270-4f5a-98fd-63a548c315a3	G	8348a30b-c177-4d70-91b5-2e4b48f4eff1	\N
884142a6-6647-4572-9ef1-e3eadaa9a61a	26fc741e-7270-4f5a-98fd-63a548c315a3	H	8348a30b-c177-4d70-91b5-2e4b48f4eff1	\N
952c01a0-eea1-4ebc-b7ac-f5f167dc866f	26fc741e-7270-4f5a-98fd-63a548c315a3	I	8348a30b-c177-4d70-91b5-2e4b48f4eff1	\N
97f16252-ec8a-434f-aeba-c2246c2c0df1	26fc741e-7270-4f5a-98fd-63a548c315a3	J	8348a30b-c177-4d70-91b5-2e4b48f4eff1	\N
2d9ce854-cd97-4adf-ac48-496a5abc8e7d	26fc741e-7270-4f5a-98fd-63a548c315a3	A	39eb951e-7827-4de4-9ae5-24cf9ae530f9	\N
fa764b61-214d-449c-9746-92d9a730751e	26fc741e-7270-4f5a-98fd-63a548c315a3	B	39eb951e-7827-4de4-9ae5-24cf9ae530f9	\N
3dc104ec-4bb3-4fa8-aad0-e60656f5897c	26fc741e-7270-4f5a-98fd-63a548c315a3	C	39eb951e-7827-4de4-9ae5-24cf9ae530f9	\N
63dd3bc3-086f-49c9-be26-5ca46351621a	26fc741e-7270-4f5a-98fd-63a548c315a3	D	39eb951e-7827-4de4-9ae5-24cf9ae530f9	\N
afb7a87b-021f-456f-84be-7c9133e0fff1	26fc741e-7270-4f5a-98fd-63a548c315a3	E	39eb951e-7827-4de4-9ae5-24cf9ae530f9	\N
950171ec-d9ad-41e8-9ca3-01b14631355c	26fc741e-7270-4f5a-98fd-63a548c315a3	F	39eb951e-7827-4de4-9ae5-24cf9ae530f9	\N
46ad6379-e61a-41f0-a734-f83d4d2bc684	26fc741e-7270-4f5a-98fd-63a548c315a3	G	39eb951e-7827-4de4-9ae5-24cf9ae530f9	\N
4725ecc3-17d3-45c6-ad0f-581dbd3eab18	26fc741e-7270-4f5a-98fd-63a548c315a3	H	39eb951e-7827-4de4-9ae5-24cf9ae530f9	\N
94c01026-5823-4687-9e0f-5a7fa9a404e9	26fc741e-7270-4f5a-98fd-63a548c315a3	I	39eb951e-7827-4de4-9ae5-24cf9ae530f9	\N
e188b8f9-8a1e-46bb-82ff-c30832283ae4	26fc741e-7270-4f5a-98fd-63a548c315a3	J	39eb951e-7827-4de4-9ae5-24cf9ae530f9	\N
13cf88bd-5670-42e3-a0ce-09dc7cc0121f	26fc741e-7270-4f5a-98fd-63a548c315a3	A	ebd99f35-32c7-407e-9468-3266f36d0da7	\N
a16dde01-3b08-4e5d-82f1-3dfdabfc9ce8	26fc741e-7270-4f5a-98fd-63a548c315a3	B	ebd99f35-32c7-407e-9468-3266f36d0da7	\N
b9730812-ace1-41f9-b2f2-8154078ec5e7	26fc741e-7270-4f5a-98fd-63a548c315a3	C	ebd99f35-32c7-407e-9468-3266f36d0da7	\N
44942867-06bb-4523-aeef-efd9ce6579bd	26fc741e-7270-4f5a-98fd-63a548c315a3	D	ebd99f35-32c7-407e-9468-3266f36d0da7	\N
f9a2d2c3-d35f-4314-b2be-cc7520adb46e	26fc741e-7270-4f5a-98fd-63a548c315a3	E	ebd99f35-32c7-407e-9468-3266f36d0da7	\N
d7f267bd-7300-4afb-92ae-448dffc3a2a2	26fc741e-7270-4f5a-98fd-63a548c315a3	F	ebd99f35-32c7-407e-9468-3266f36d0da7	\N
946f074a-9b34-445c-a455-b0cbc1d331fc	26fc741e-7270-4f5a-98fd-63a548c315a3	G	ebd99f35-32c7-407e-9468-3266f36d0da7	\N
194e3dba-68a0-4831-a989-91bfe3c7ded4	26fc741e-7270-4f5a-98fd-63a548c315a3	H	ebd99f35-32c7-407e-9468-3266f36d0da7	\N
9fef4097-c438-4c5a-8345-1a65abbc69a1	26fc741e-7270-4f5a-98fd-63a548c315a3	I	ebd99f35-32c7-407e-9468-3266f36d0da7	\N
183ecbb9-c884-4e78-9e99-d5d0f7866592	26fc741e-7270-4f5a-98fd-63a548c315a3	J	ebd99f35-32c7-407e-9468-3266f36d0da7	\N
fe697889-63ba-403e-b600-75dfbb5fef5b	26fc741e-7270-4f5a-98fd-63a548c315a3	A	de0e7fe8-0234-48ef-9c27-68c22bfc2c0e	\N
3e7bc770-3c77-4234-be13-324316bebf82	26fc741e-7270-4f5a-98fd-63a548c315a3	B	de0e7fe8-0234-48ef-9c27-68c22bfc2c0e	\N
dd77ebc1-6480-48a2-95b6-b6520282878a	26fc741e-7270-4f5a-98fd-63a548c315a3	C	de0e7fe8-0234-48ef-9c27-68c22bfc2c0e	\N
e12e3923-980d-4cb2-9a3d-9c316396b8a9	26fc741e-7270-4f5a-98fd-63a548c315a3	D	de0e7fe8-0234-48ef-9c27-68c22bfc2c0e	\N
73001f3a-75f5-42ce-a7b3-cc2262470fb6	26fc741e-7270-4f5a-98fd-63a548c315a3	E	de0e7fe8-0234-48ef-9c27-68c22bfc2c0e	\N
bff3519d-3861-4293-b699-f1acf5489738	26fc741e-7270-4f5a-98fd-63a548c315a3	F	de0e7fe8-0234-48ef-9c27-68c22bfc2c0e	\N
7f143de4-2b32-434d-bbfb-20e4702687fe	26fc741e-7270-4f5a-98fd-63a548c315a3	G	de0e7fe8-0234-48ef-9c27-68c22bfc2c0e	\N
f56f81bf-d107-41e8-bc46-5944a700f7d6	26fc741e-7270-4f5a-98fd-63a548c315a3	H	de0e7fe8-0234-48ef-9c27-68c22bfc2c0e	\N
a68a841a-a442-4cfe-9c01-301ae5bc12c6	26fc741e-7270-4f5a-98fd-63a548c315a3	I	de0e7fe8-0234-48ef-9c27-68c22bfc2c0e	\N
db5b606f-8464-4b56-853f-4d433ddbba04	26fc741e-7270-4f5a-98fd-63a548c315a3	J	de0e7fe8-0234-48ef-9c27-68c22bfc2c0e	\N
de918aad-aa0c-439c-a875-904a0a18837c	26fc741e-7270-4f5a-98fd-63a548c315a3	A	39ed03d2-eb15-40dd-8f62-7eba0495fc5b	\N
53738141-0ef4-4244-9ef7-c8144a54f458	26fc741e-7270-4f5a-98fd-63a548c315a3	B	39ed03d2-eb15-40dd-8f62-7eba0495fc5b	\N
5ffb9baa-5f10-4ecd-bc9b-2f228680dfc1	26fc741e-7270-4f5a-98fd-63a548c315a3	C	39ed03d2-eb15-40dd-8f62-7eba0495fc5b	\N
1e3ef4fd-b9c2-4c23-a256-0ae654c55614	26fc741e-7270-4f5a-98fd-63a548c315a3	D	39ed03d2-eb15-40dd-8f62-7eba0495fc5b	\N
e5432c28-0abe-467d-8217-acbc09e36b36	26fc741e-7270-4f5a-98fd-63a548c315a3	E	39ed03d2-eb15-40dd-8f62-7eba0495fc5b	\N
62852af3-6712-40f5-88bd-045ba42121b6	26fc741e-7270-4f5a-98fd-63a548c315a3	F	39ed03d2-eb15-40dd-8f62-7eba0495fc5b	\N
881b10f1-e7da-445e-91b8-0904b71bb2c8	26fc741e-7270-4f5a-98fd-63a548c315a3	G	39ed03d2-eb15-40dd-8f62-7eba0495fc5b	\N
6cc0165f-8b9c-4f99-a8c2-a5fbaf7811ad	26fc741e-7270-4f5a-98fd-63a548c315a3	H	39ed03d2-eb15-40dd-8f62-7eba0495fc5b	\N
c2adbb32-32a9-439f-908f-33387a09b43d	26fc741e-7270-4f5a-98fd-63a548c315a3	I	39ed03d2-eb15-40dd-8f62-7eba0495fc5b	\N
02d02c8d-1b49-40ed-a478-9ea5f120f520	26fc741e-7270-4f5a-98fd-63a548c315a3	J	39ed03d2-eb15-40dd-8f62-7eba0495fc5b	\N
d86fff5f-68c2-4d9f-ad2d-776b5e503dc3	26fc741e-7270-4f5a-98fd-63a548c315a3	A	5aacf61c-8088-4f62-a3e9-40f279163878	\N
6a99ae18-27eb-4601-ac12-3d85f7cc6d02	26fc741e-7270-4f5a-98fd-63a548c315a3	B	5aacf61c-8088-4f62-a3e9-40f279163878	\N
716803cf-55d9-4ff5-bccc-57686d4571f0	26fc741e-7270-4f5a-98fd-63a548c315a3	C	5aacf61c-8088-4f62-a3e9-40f279163878	\N
202e1767-1b8c-438e-95f5-93f79ecc7df4	26fc741e-7270-4f5a-98fd-63a548c315a3	D	5aacf61c-8088-4f62-a3e9-40f279163878	\N
81a4bb40-2684-49a9-901b-c5c0b0ffe4ff	26fc741e-7270-4f5a-98fd-63a548c315a3	E	5aacf61c-8088-4f62-a3e9-40f279163878	\N
9f22d0c2-ef7f-44db-a34f-ea8482e25fab	26fc741e-7270-4f5a-98fd-63a548c315a3	F	5aacf61c-8088-4f62-a3e9-40f279163878	\N
f3c3ecf8-a69e-445e-bdb2-32c46ed80344	26fc741e-7270-4f5a-98fd-63a548c315a3	G	5aacf61c-8088-4f62-a3e9-40f279163878	\N
e082ff99-49f4-4799-9a8e-f6957703a097	26fc741e-7270-4f5a-98fd-63a548c315a3	H	5aacf61c-8088-4f62-a3e9-40f279163878	\N
3c3e5153-25e4-4abc-a16e-f220ed8dd06c	26fc741e-7270-4f5a-98fd-63a548c315a3	I	5aacf61c-8088-4f62-a3e9-40f279163878	\N
0112266c-339f-4369-9665-d9fa6f97c46b	26fc741e-7270-4f5a-98fd-63a548c315a3	J	5aacf61c-8088-4f62-a3e9-40f279163878	\N
d5695ec4-1478-4d91-b466-1e3ba796b569	26fc741e-7270-4f5a-98fd-63a548c315a3	A	28b751e1-27c6-416e-bdba-7555dae76eea	\N
fe1a4c62-bdfc-42d8-8ae2-ace599fe5df4	26fc741e-7270-4f5a-98fd-63a548c315a3	B	28b751e1-27c6-416e-bdba-7555dae76eea	\N
4dee53b7-ad3c-41cf-b974-3aa5de95b9f3	26fc741e-7270-4f5a-98fd-63a548c315a3	C	28b751e1-27c6-416e-bdba-7555dae76eea	\N
407d4342-fdbb-407c-b531-d39fbddd8203	26fc741e-7270-4f5a-98fd-63a548c315a3	D	28b751e1-27c6-416e-bdba-7555dae76eea	\N
678bbdc2-172f-4ec3-891d-728eae3935c0	26fc741e-7270-4f5a-98fd-63a548c315a3	E	28b751e1-27c6-416e-bdba-7555dae76eea	\N
888e5689-9bd7-42d7-a8bc-fccf32b10cf7	26fc741e-7270-4f5a-98fd-63a548c315a3	F	28b751e1-27c6-416e-bdba-7555dae76eea	\N
d507e062-8f0d-407b-9eed-006e3017043c	26fc741e-7270-4f5a-98fd-63a548c315a3	G	28b751e1-27c6-416e-bdba-7555dae76eea	\N
963e857b-382d-463f-b952-ce5217cb76aa	26fc741e-7270-4f5a-98fd-63a548c315a3	H	28b751e1-27c6-416e-bdba-7555dae76eea	\N
b86d86bc-118c-4e7c-9ade-5afeb2a69fa8	26fc741e-7270-4f5a-98fd-63a548c315a3	I	28b751e1-27c6-416e-bdba-7555dae76eea	\N
c9efa09b-f6c5-4f36-b9a5-bd86cbf88822	26fc741e-7270-4f5a-98fd-63a548c315a3	J	28b751e1-27c6-416e-bdba-7555dae76eea	\N
de29f24d-d991-4610-ae11-2e728fdf3cc8	26fc741e-7270-4f5a-98fd-63a548c315a3	A	2c600b56-0685-4a55-9d8d-1d3bac400924	\N
396a15d7-4693-4983-8cc2-6fb0e0ae9d65	26fc741e-7270-4f5a-98fd-63a548c315a3	B	2c600b56-0685-4a55-9d8d-1d3bac400924	\N
8bc2c537-10cc-406d-bd9e-5711507e0550	26fc741e-7270-4f5a-98fd-63a548c315a3	C	2c600b56-0685-4a55-9d8d-1d3bac400924	\N
3f40c17f-1c01-4fb6-a2a9-7702c00fbdce	26fc741e-7270-4f5a-98fd-63a548c315a3	D	2c600b56-0685-4a55-9d8d-1d3bac400924	\N
6de621dc-3bdb-4bd7-9905-462fcd399b62	26fc741e-7270-4f5a-98fd-63a548c315a3	E	2c600b56-0685-4a55-9d8d-1d3bac400924	\N
9016c56d-1c4b-40df-8b6e-3115cdc9e3b1	26fc741e-7270-4f5a-98fd-63a548c315a3	F	2c600b56-0685-4a55-9d8d-1d3bac400924	\N
884600e7-1283-4441-baf3-bf00938eb82c	26fc741e-7270-4f5a-98fd-63a548c315a3	G	2c600b56-0685-4a55-9d8d-1d3bac400924	\N
8d7c838e-a23c-4999-860c-99ae4c302978	26fc741e-7270-4f5a-98fd-63a548c315a3	H	2c600b56-0685-4a55-9d8d-1d3bac400924	\N
6de20a9b-3cb8-4f5f-899e-8e70f420a602	26fc741e-7270-4f5a-98fd-63a548c315a3	I	2c600b56-0685-4a55-9d8d-1d3bac400924	\N
546ec1de-412f-48ea-8cb6-79ec036cf953	26fc741e-7270-4f5a-98fd-63a548c315a3	J	2c600b56-0685-4a55-9d8d-1d3bac400924	\N
b81169a1-0e69-4b8a-ad20-c43e8bb906d9	26fc741e-7270-4f5a-98fd-63a548c315a3	A	f6f903cb-4ce2-4bba-b0aa-7c8d3bb8e8b1	\N
8f7c44b0-29b9-4f06-a451-124d99b6c7d2	26fc741e-7270-4f5a-98fd-63a548c315a3	B	f6f903cb-4ce2-4bba-b0aa-7c8d3bb8e8b1	\N
45a360f5-d94a-4a64-8858-cee9ad3a96e6	26fc741e-7270-4f5a-98fd-63a548c315a3	C	f6f903cb-4ce2-4bba-b0aa-7c8d3bb8e8b1	\N
cfbf5dda-6e46-448e-a340-9e603740dcf1	26fc741e-7270-4f5a-98fd-63a548c315a3	D	f6f903cb-4ce2-4bba-b0aa-7c8d3bb8e8b1	\N
7dd14dfa-22d6-4b2d-910e-624178b555cd	26fc741e-7270-4f5a-98fd-63a548c315a3	E	f6f903cb-4ce2-4bba-b0aa-7c8d3bb8e8b1	\N
76d1b064-13ce-460a-90e1-51a1d1d447d2	26fc741e-7270-4f5a-98fd-63a548c315a3	F	f6f903cb-4ce2-4bba-b0aa-7c8d3bb8e8b1	\N
ae705a8d-1b46-4ab7-9567-b54558c7f5b2	26fc741e-7270-4f5a-98fd-63a548c315a3	G	f6f903cb-4ce2-4bba-b0aa-7c8d3bb8e8b1	\N
035d66ac-25c0-4ba6-aa60-9d26655a4e00	26fc741e-7270-4f5a-98fd-63a548c315a3	H	f6f903cb-4ce2-4bba-b0aa-7c8d3bb8e8b1	\N
f6f00fb2-5b77-4661-a12f-5da02f034d98	26fc741e-7270-4f5a-98fd-63a548c315a3	I	f6f903cb-4ce2-4bba-b0aa-7c8d3bb8e8b1	\N
abfa2860-1393-44de-8d4b-3a4788b26dc8	26fc741e-7270-4f5a-98fd-63a548c315a3	J	f6f903cb-4ce2-4bba-b0aa-7c8d3bb8e8b1	\N
e596eebd-968c-4e3d-987a-2aefeee96b67	26fc741e-7270-4f5a-98fd-63a548c315a3	A	fe8a2bd0-aa9e-408b-96bb-b5ae62b09143	\N
cb6537fc-c58f-4c49-885b-430c5a8b50e6	26fc741e-7270-4f5a-98fd-63a548c315a3	B	fe8a2bd0-aa9e-408b-96bb-b5ae62b09143	\N
af18cf1a-d84e-4d7b-bfec-6bc368890b9d	26fc741e-7270-4f5a-98fd-63a548c315a3	C	fe8a2bd0-aa9e-408b-96bb-b5ae62b09143	\N
d1b245ea-fd98-43ca-9604-905c36ce96f5	26fc741e-7270-4f5a-98fd-63a548c315a3	D	fe8a2bd0-aa9e-408b-96bb-b5ae62b09143	\N
27f386eb-0dde-4213-9550-8bdd3f4f8d39	26fc741e-7270-4f5a-98fd-63a548c315a3	E	fe8a2bd0-aa9e-408b-96bb-b5ae62b09143	\N
554188e4-b78b-445c-9ba1-a70f6bd81117	26fc741e-7270-4f5a-98fd-63a548c315a3	F	fe8a2bd0-aa9e-408b-96bb-b5ae62b09143	\N
f3e59d25-db10-48fc-a053-6b2588eddd6b	26fc741e-7270-4f5a-98fd-63a548c315a3	G	fe8a2bd0-aa9e-408b-96bb-b5ae62b09143	\N
2b9c54bf-0b65-462d-9b12-13a44e73dfbd	26fc741e-7270-4f5a-98fd-63a548c315a3	H	fe8a2bd0-aa9e-408b-96bb-b5ae62b09143	\N
5843c46e-0e3f-42c4-b24e-277af289e680	26fc741e-7270-4f5a-98fd-63a548c315a3	I	fe8a2bd0-aa9e-408b-96bb-b5ae62b09143	\N
e7b5f999-71c2-4857-9c6c-c7848a487fd2	26fc741e-7270-4f5a-98fd-63a548c315a3	J	fe8a2bd0-aa9e-408b-96bb-b5ae62b09143	\N
353c5e20-68eb-4a12-96fe-cb072d895320	26fc741e-7270-4f5a-98fd-63a548c315a3	A	565a7d90-d741-433d-a8f0-c283dcf322b4	\N
14da5fe1-651a-4418-a6fe-0bf7234cbbcb	26fc741e-7270-4f5a-98fd-63a548c315a3	B	565a7d90-d741-433d-a8f0-c283dcf322b4	\N
c510d80d-4b27-4edf-a258-ed95431d4442	26fc741e-7270-4f5a-98fd-63a548c315a3	C	565a7d90-d741-433d-a8f0-c283dcf322b4	\N
2f5474af-d9eb-4a96-8194-87bbf311a8ab	26fc741e-7270-4f5a-98fd-63a548c315a3	D	565a7d90-d741-433d-a8f0-c283dcf322b4	\N
2dea4dcc-c740-4c79-a4d7-5943e35cec14	26fc741e-7270-4f5a-98fd-63a548c315a3	E	565a7d90-d741-433d-a8f0-c283dcf322b4	\N
c29e7115-2997-47fc-8311-e7e146e2f558	26fc741e-7270-4f5a-98fd-63a548c315a3	F	565a7d90-d741-433d-a8f0-c283dcf322b4	\N
eaa26354-83e0-4277-ab9b-90aefbc4ca97	26fc741e-7270-4f5a-98fd-63a548c315a3	G	565a7d90-d741-433d-a8f0-c283dcf322b4	\N
01de5b22-0aef-432e-991d-c6228e42e979	26fc741e-7270-4f5a-98fd-63a548c315a3	H	565a7d90-d741-433d-a8f0-c283dcf322b4	\N
3ffb00b9-3289-4125-a531-88aec54fb225	26fc741e-7270-4f5a-98fd-63a548c315a3	I	565a7d90-d741-433d-a8f0-c283dcf322b4	\N
e63bc77b-aea3-41e5-8ea9-12c564fee524	26fc741e-7270-4f5a-98fd-63a548c315a3	J	565a7d90-d741-433d-a8f0-c283dcf322b4	\N
5694e7f6-8f49-486a-ae1c-216bfc29e876	26fc741e-7270-4f5a-98fd-63a548c315a3	A	7523d809-73e0-4bf8-ad41-37b3f3c894a5	\N
d31f4592-ce46-448f-8158-191663d95052	26fc741e-7270-4f5a-98fd-63a548c315a3	B	7523d809-73e0-4bf8-ad41-37b3f3c894a5	\N
512409ea-bf4e-4adf-96e3-a124b6ce283d	26fc741e-7270-4f5a-98fd-63a548c315a3	C	7523d809-73e0-4bf8-ad41-37b3f3c894a5	\N
1676d5bc-bcd6-4688-9054-3557fb6e7778	26fc741e-7270-4f5a-98fd-63a548c315a3	D	7523d809-73e0-4bf8-ad41-37b3f3c894a5	\N
2a27629c-08b3-4224-9f7c-992d20135963	26fc741e-7270-4f5a-98fd-63a548c315a3	E	7523d809-73e0-4bf8-ad41-37b3f3c894a5	\N
0626f1d9-23a7-4705-b237-dac5fd20be94	26fc741e-7270-4f5a-98fd-63a548c315a3	F	7523d809-73e0-4bf8-ad41-37b3f3c894a5	\N
a9fbda6c-274a-45c1-b6f3-f21347fdf450	26fc741e-7270-4f5a-98fd-63a548c315a3	G	7523d809-73e0-4bf8-ad41-37b3f3c894a5	\N
3d412b02-36b4-4a66-8105-63274611add4	26fc741e-7270-4f5a-98fd-63a548c315a3	H	7523d809-73e0-4bf8-ad41-37b3f3c894a5	\N
2eee1c0e-21a9-4443-808f-4b7a27838478	26fc741e-7270-4f5a-98fd-63a548c315a3	I	7523d809-73e0-4bf8-ad41-37b3f3c894a5	\N
a602b068-eecd-4eea-816b-3423409d59ad	26fc741e-7270-4f5a-98fd-63a548c315a3	J	7523d809-73e0-4bf8-ad41-37b3f3c894a5	\N
d5b5d093-4467-4583-93f4-0ddfd0ce1806	26fc741e-7270-4f5a-98fd-63a548c315a3	B	1f267193-8747-453c-a927-93a5b3be2394	\N
5a19bbf1-18fa-40d8-9e05-d1721a404011	26fc741e-7270-4f5a-98fd-63a548c315a3	C	1f267193-8747-453c-a927-93a5b3be2394	\N
639fb45f-cc8c-4f74-b84e-3d998ca46c06	26fc741e-7270-4f5a-98fd-63a548c315a3	D	1f267193-8747-453c-a927-93a5b3be2394	\N
182ca979-be51-4a80-a53d-c8c5675d5de7	26fc741e-7270-4f5a-98fd-63a548c315a3	E	1f267193-8747-453c-a927-93a5b3be2394	\N
b7d63cc7-efca-47cb-9ea3-6c396e5225f1	26fc741e-7270-4f5a-98fd-63a548c315a3	F	1f267193-8747-453c-a927-93a5b3be2394	\N
a08e4d12-cc38-483f-970a-610dc8da622e	26fc741e-7270-4f5a-98fd-63a548c315a3	G	1f267193-8747-453c-a927-93a5b3be2394	\N
a6384bc7-4bc1-4c73-be72-f38ae23a95a4	26fc741e-7270-4f5a-98fd-63a548c315a3	H	1f267193-8747-453c-a927-93a5b3be2394	\N
c4ae360c-80d9-4e32-b8ee-ca1148e2f521	26fc741e-7270-4f5a-98fd-63a548c315a3	I	1f267193-8747-453c-a927-93a5b3be2394	\N
db2bb0be-4f0e-4497-b169-552912383cb7	26fc741e-7270-4f5a-98fd-63a548c315a3	J	1f267193-8747-453c-a927-93a5b3be2394	\N
c580cfd4-52ce-4d46-b337-2a6dce329911	26fc741e-7270-4f5a-98fd-63a548c315a3	A	005350a3-5dae-4186-a621-7fcf575f0d87	\N
7d795cd3-051f-4a67-81e2-405470571d7d	26fc741e-7270-4f5a-98fd-63a548c315a3	B	005350a3-5dae-4186-a621-7fcf575f0d87	\N
657d3d59-fe1d-4c7f-8aaf-ed352e5f79b9	26fc741e-7270-4f5a-98fd-63a548c315a3	C	005350a3-5dae-4186-a621-7fcf575f0d87	\N
b5bebea6-260d-4a33-ab24-b4c9b103ec5e	26fc741e-7270-4f5a-98fd-63a548c315a3	D	005350a3-5dae-4186-a621-7fcf575f0d87	\N
1d395f62-64fd-41de-bb32-8fab5a29acb1	26fc741e-7270-4f5a-98fd-63a548c315a3	E	005350a3-5dae-4186-a621-7fcf575f0d87	\N
5e47bf64-2244-4a8f-aaac-d245d20c83b6	26fc741e-7270-4f5a-98fd-63a548c315a3	F	005350a3-5dae-4186-a621-7fcf575f0d87	\N
398e36d8-d875-46b4-babc-03ff4509ed7d	26fc741e-7270-4f5a-98fd-63a548c315a3	G	005350a3-5dae-4186-a621-7fcf575f0d87	\N
14ea9e14-f4a6-4456-a5f7-62c6dcf75d76	26fc741e-7270-4f5a-98fd-63a548c315a3	H	005350a3-5dae-4186-a621-7fcf575f0d87	\N
59496825-b669-4ecd-be0a-5bf2f10576a5	26fc741e-7270-4f5a-98fd-63a548c315a3	I	005350a3-5dae-4186-a621-7fcf575f0d87	\N
103371f7-2d92-4f5d-b480-467a89be9249	26fc741e-7270-4f5a-98fd-63a548c315a3	J	005350a3-5dae-4186-a621-7fcf575f0d87	\N
277c0e58-90be-49fe-a281-42518058529d	26fc741e-7270-4f5a-98fd-63a548c315a3	A	83a115e0-81d4-4ac6-99cc-be57968fe628	\N
e690135e-3df2-4e4b-bb2a-fdae74ae2a2d	26fc741e-7270-4f5a-98fd-63a548c315a3	B	83a115e0-81d4-4ac6-99cc-be57968fe628	\N
9919e8f5-efcb-418e-9a3a-2a7459b6f636	26fc741e-7270-4f5a-98fd-63a548c315a3	C	83a115e0-81d4-4ac6-99cc-be57968fe628	\N
d2c316e7-71ba-4bf5-97d5-bacf06a51a04	26fc741e-7270-4f5a-98fd-63a548c315a3	D	83a115e0-81d4-4ac6-99cc-be57968fe628	\N
b58ebfee-4fc6-4976-a899-de432a5d7a0f	26fc741e-7270-4f5a-98fd-63a548c315a3	E	83a115e0-81d4-4ac6-99cc-be57968fe628	\N
e7f6b94a-9289-4a30-aebb-4175ceaba742	26fc741e-7270-4f5a-98fd-63a548c315a3	F	83a115e0-81d4-4ac6-99cc-be57968fe628	\N
180bd70e-9098-4bf4-82bd-53dfc55f7fa4	26fc741e-7270-4f5a-98fd-63a548c315a3	G	83a115e0-81d4-4ac6-99cc-be57968fe628	\N
1a958d1f-d9ef-40e4-9d3c-6043c9d01891	26fc741e-7270-4f5a-98fd-63a548c315a3	H	83a115e0-81d4-4ac6-99cc-be57968fe628	\N
ddcbb838-cd8c-491b-99cc-c36b77e9d736	26fc741e-7270-4f5a-98fd-63a548c315a3	I	83a115e0-81d4-4ac6-99cc-be57968fe628	\N
07b58b93-a0a0-4e0d-8b30-a68960814d14	26fc741e-7270-4f5a-98fd-63a548c315a3	J	83a115e0-81d4-4ac6-99cc-be57968fe628	\N
ba5cd21b-c925-4c7d-ab33-ee123fa9d796	329eb5b7-10d1-42c9-b309-19477157eeb5	A	cf3aaa3a-a212-4f56-828a-29ce291347b7	\N
bb34c5cb-5041-4ce9-8ddd-c35fa116aedb	329eb5b7-10d1-42c9-b309-19477157eeb5	B	cf3aaa3a-a212-4f56-828a-29ce291347b7	\N
afece5b4-f949-4f14-acf2-10a9d9e40165	329eb5b7-10d1-42c9-b309-19477157eeb5	C	cf3aaa3a-a212-4f56-828a-29ce291347b7	\N
7ae5ea1e-dd14-4084-b52a-30dea16b6844	329eb5b7-10d1-42c9-b309-19477157eeb5	D	cf3aaa3a-a212-4f56-828a-29ce291347b7	\N
3bebd436-3817-45d0-8977-b58693bdec36	329eb5b7-10d1-42c9-b309-19477157eeb5	E	cf3aaa3a-a212-4f56-828a-29ce291347b7	\N
d6e2bc95-3e36-44a1-b98a-5e923ea103b3	329eb5b7-10d1-42c9-b309-19477157eeb5	F	cf3aaa3a-a212-4f56-828a-29ce291347b7	\N
2e46f24f-7807-4c02-af1e-d24029a7483c	329eb5b7-10d1-42c9-b309-19477157eeb5	G	cf3aaa3a-a212-4f56-828a-29ce291347b7	\N
218c9e20-5cb5-4556-9ea6-060d0b24d853	329eb5b7-10d1-42c9-b309-19477157eeb5	H	cf3aaa3a-a212-4f56-828a-29ce291347b7	\N
df61c02f-811f-488d-8ee6-a6db37c8f34a	329eb5b7-10d1-42c9-b309-19477157eeb5	I	cf3aaa3a-a212-4f56-828a-29ce291347b7	\N
2e070a05-4b39-42df-a0af-c59a1bf3df22	329eb5b7-10d1-42c9-b309-19477157eeb5	J	cf3aaa3a-a212-4f56-828a-29ce291347b7	\N
b476a8de-1cec-4c75-993a-9622b72c63b9	329eb5b7-10d1-42c9-b309-19477157eeb5	A	ca8ca282-cbef-4812-9f7c-6f244814e979	\N
c5ccc2d4-56e5-4b31-969b-04b48d854984	329eb5b7-10d1-42c9-b309-19477157eeb5	B	ca8ca282-cbef-4812-9f7c-6f244814e979	\N
eb4e1672-67cb-41bc-8e8e-3de0d6b58b2c	329eb5b7-10d1-42c9-b309-19477157eeb5	C	ca8ca282-cbef-4812-9f7c-6f244814e979	\N
ff4f8b97-816c-4c42-b809-b1f30f218ca9	329eb5b7-10d1-42c9-b309-19477157eeb5	D	ca8ca282-cbef-4812-9f7c-6f244814e979	\N
db2112f3-42ba-42ec-880d-2783447370dc	329eb5b7-10d1-42c9-b309-19477157eeb5	E	ca8ca282-cbef-4812-9f7c-6f244814e979	\N
2613a640-c98a-42e5-a6a0-e7dbec5cf449	329eb5b7-10d1-42c9-b309-19477157eeb5	F	ca8ca282-cbef-4812-9f7c-6f244814e979	\N
6afcc08a-b844-4812-89a9-68c4f368ddbf	329eb5b7-10d1-42c9-b309-19477157eeb5	G	ca8ca282-cbef-4812-9f7c-6f244814e979	\N
65b28b5f-37b0-4cf8-bd15-df3d4b5113e8	329eb5b7-10d1-42c9-b309-19477157eeb5	H	ca8ca282-cbef-4812-9f7c-6f244814e979	\N
088d69ff-f74f-44c9-892b-04389347e36f	329eb5b7-10d1-42c9-b309-19477157eeb5	I	ca8ca282-cbef-4812-9f7c-6f244814e979	\N
c8edac95-9a75-4ccf-9c1c-eb9bfc062da1	329eb5b7-10d1-42c9-b309-19477157eeb5	J	ca8ca282-cbef-4812-9f7c-6f244814e979	\N
7a557f4e-0802-41ec-8d37-a502ef2b2ed8	329eb5b7-10d1-42c9-b309-19477157eeb5	A	a5ee9016-6e98-44eb-939e-2660e18d5924	\N
a47398c1-3376-4992-a60f-3632e2cd4a1d	329eb5b7-10d1-42c9-b309-19477157eeb5	B	a5ee9016-6e98-44eb-939e-2660e18d5924	\N
7013bccc-b373-4bb0-b753-41e62bf315d2	329eb5b7-10d1-42c9-b309-19477157eeb5	C	a5ee9016-6e98-44eb-939e-2660e18d5924	\N
2c407b2b-d207-4dbb-9364-392e0675962d	329eb5b7-10d1-42c9-b309-19477157eeb5	D	a5ee9016-6e98-44eb-939e-2660e18d5924	\N
43a56af0-9222-428b-bb16-d4b015918a9d	329eb5b7-10d1-42c9-b309-19477157eeb5	E	a5ee9016-6e98-44eb-939e-2660e18d5924	\N
0a74fd7f-28fc-4da0-9ee6-f41f09042431	329eb5b7-10d1-42c9-b309-19477157eeb5	F	a5ee9016-6e98-44eb-939e-2660e18d5924	\N
2dfbb269-83ea-4a02-9143-5820cf0c5ce6	329eb5b7-10d1-42c9-b309-19477157eeb5	G	a5ee9016-6e98-44eb-939e-2660e18d5924	\N
0d3c1607-f016-45eb-af80-f0f30a84b79b	329eb5b7-10d1-42c9-b309-19477157eeb5	H	a5ee9016-6e98-44eb-939e-2660e18d5924	\N
e319b99c-ca9b-42ed-a66a-22bf0c95675a	329eb5b7-10d1-42c9-b309-19477157eeb5	I	a5ee9016-6e98-44eb-939e-2660e18d5924	\N
c38210d4-ce6a-4a51-9089-9108d46f0872	329eb5b7-10d1-42c9-b309-19477157eeb5	J	a5ee9016-6e98-44eb-939e-2660e18d5924	\N
711532a8-3606-4fcc-adb5-6d63c4a152df	329eb5b7-10d1-42c9-b309-19477157eeb5	A	c51c1348-ff2b-4fce-90a8-a59b44c4a9c3	\N
9949e72c-6160-4ea1-a87a-ff139c80cc90	329eb5b7-10d1-42c9-b309-19477157eeb5	B	c51c1348-ff2b-4fce-90a8-a59b44c4a9c3	\N
1f4733e0-ca60-4f7a-a99b-f237a5efacba	329eb5b7-10d1-42c9-b309-19477157eeb5	C	c51c1348-ff2b-4fce-90a8-a59b44c4a9c3	\N
cf778d69-925b-4a11-894b-54982cd090e0	329eb5b7-10d1-42c9-b309-19477157eeb5	D	c51c1348-ff2b-4fce-90a8-a59b44c4a9c3	\N
0f916984-5d8e-428e-8593-2d04ffb12f60	329eb5b7-10d1-42c9-b309-19477157eeb5	E	c51c1348-ff2b-4fce-90a8-a59b44c4a9c3	\N
99079924-c949-41f3-92a8-bf781a5b734e	329eb5b7-10d1-42c9-b309-19477157eeb5	F	c51c1348-ff2b-4fce-90a8-a59b44c4a9c3	\N
61b3c176-fdc0-41ab-81f1-5fc2b024ffe3	329eb5b7-10d1-42c9-b309-19477157eeb5	G	c51c1348-ff2b-4fce-90a8-a59b44c4a9c3	\N
3a1c6acd-b5dd-439f-ba7b-de95eab73faf	329eb5b7-10d1-42c9-b309-19477157eeb5	H	c51c1348-ff2b-4fce-90a8-a59b44c4a9c3	\N
55657f98-24d4-4018-b54f-868fd64dffbc	329eb5b7-10d1-42c9-b309-19477157eeb5	I	c51c1348-ff2b-4fce-90a8-a59b44c4a9c3	\N
0063718e-73da-47d7-a368-0a293c6dc268	329eb5b7-10d1-42c9-b309-19477157eeb5	J	c51c1348-ff2b-4fce-90a8-a59b44c4a9c3	\N
8eb63ae7-3334-46cd-b510-0837de17a03f	329eb5b7-10d1-42c9-b309-19477157eeb5	A	6d68246e-df3d-40b3-8071-3c412f22e260	\N
e64c0acb-4785-44d1-a25a-e2007a951196	329eb5b7-10d1-42c9-b309-19477157eeb5	B	6d68246e-df3d-40b3-8071-3c412f22e260	\N
cc619cae-934a-44c6-821b-0bf82186b507	329eb5b7-10d1-42c9-b309-19477157eeb5	C	6d68246e-df3d-40b3-8071-3c412f22e260	\N
6a693e73-0866-4fd0-962c-273f70f7bdf8	329eb5b7-10d1-42c9-b309-19477157eeb5	D	6d68246e-df3d-40b3-8071-3c412f22e260	\N
f1f8c252-dda8-4360-8ead-5d5913da62ba	329eb5b7-10d1-42c9-b309-19477157eeb5	E	6d68246e-df3d-40b3-8071-3c412f22e260	\N
0e43b48d-62bb-4e96-beed-f653d0c93320	329eb5b7-10d1-42c9-b309-19477157eeb5	F	6d68246e-df3d-40b3-8071-3c412f22e260	\N
6e883899-7b4d-48fc-9e15-70c78e92d62e	329eb5b7-10d1-42c9-b309-19477157eeb5	G	6d68246e-df3d-40b3-8071-3c412f22e260	\N
25172eac-0c83-481a-9456-9478b73317aa	329eb5b7-10d1-42c9-b309-19477157eeb5	H	6d68246e-df3d-40b3-8071-3c412f22e260	\N
78065434-6c9a-45cf-964d-74b8d7366648	329eb5b7-10d1-42c9-b309-19477157eeb5	I	6d68246e-df3d-40b3-8071-3c412f22e260	\N
83b98b8b-33a2-45ea-9f32-b9b6b634c0ae	329eb5b7-10d1-42c9-b309-19477157eeb5	J	6d68246e-df3d-40b3-8071-3c412f22e260	\N
a40709f6-78f8-494d-8373-774d064bfc5b	329eb5b7-10d1-42c9-b309-19477157eeb5	A	cd445379-afec-4e9d-8477-922da7540044	\N
99f9e5e4-7f57-432d-b348-1d87fd776869	329eb5b7-10d1-42c9-b309-19477157eeb5	B	cd445379-afec-4e9d-8477-922da7540044	\N
5e2da0d1-7aa5-44a3-89f3-fdba89f54e38	329eb5b7-10d1-42c9-b309-19477157eeb5	C	cd445379-afec-4e9d-8477-922da7540044	\N
4b88e6a8-4b6b-438e-94e3-b15c946337ea	329eb5b7-10d1-42c9-b309-19477157eeb5	D	cd445379-afec-4e9d-8477-922da7540044	\N
156705f4-1317-4fb2-b9d9-ec8cda1b0b1b	329eb5b7-10d1-42c9-b309-19477157eeb5	E	cd445379-afec-4e9d-8477-922da7540044	\N
3fccd323-accd-4baf-8db8-9aaa414e6b81	329eb5b7-10d1-42c9-b309-19477157eeb5	F	cd445379-afec-4e9d-8477-922da7540044	\N
0b4127ad-98ce-4a88-84a6-0543b8142d92	329eb5b7-10d1-42c9-b309-19477157eeb5	G	cd445379-afec-4e9d-8477-922da7540044	\N
ba8b37f9-346e-4e8e-abac-972dd0e81a28	329eb5b7-10d1-42c9-b309-19477157eeb5	H	cd445379-afec-4e9d-8477-922da7540044	\N
163cfe99-60c1-4dc3-aa10-fe187d81e8d1	329eb5b7-10d1-42c9-b309-19477157eeb5	I	cd445379-afec-4e9d-8477-922da7540044	\N
173196de-1388-41f2-9958-56b46728b184	329eb5b7-10d1-42c9-b309-19477157eeb5	J	cd445379-afec-4e9d-8477-922da7540044	\N
f36327fe-5df6-4e54-9f51-186958a914b2	329eb5b7-10d1-42c9-b309-19477157eeb5	A	540f6289-8115-4da3-aa73-8d5343fefc16	\N
b963c2b9-ebfc-44b4-811b-9cf1195b3677	329eb5b7-10d1-42c9-b309-19477157eeb5	B	540f6289-8115-4da3-aa73-8d5343fefc16	\N
7dc04928-1df6-4bf5-8f29-2c9845018a41	329eb5b7-10d1-42c9-b309-19477157eeb5	C	540f6289-8115-4da3-aa73-8d5343fefc16	\N
23404706-da90-4577-8513-9480c44627d4	329eb5b7-10d1-42c9-b309-19477157eeb5	D	540f6289-8115-4da3-aa73-8d5343fefc16	\N
b619af29-7b63-4f69-9cfb-178970d00395	329eb5b7-10d1-42c9-b309-19477157eeb5	E	540f6289-8115-4da3-aa73-8d5343fefc16	\N
15bf2b0c-9267-43f3-8034-3c015e8ae503	329eb5b7-10d1-42c9-b309-19477157eeb5	F	540f6289-8115-4da3-aa73-8d5343fefc16	\N
82aa71f4-2ef3-4518-b1b1-0dbee7672c92	329eb5b7-10d1-42c9-b309-19477157eeb5	G	540f6289-8115-4da3-aa73-8d5343fefc16	\N
3d003453-cdde-4338-ab9e-5d3e846e3cf2	329eb5b7-10d1-42c9-b309-19477157eeb5	H	540f6289-8115-4da3-aa73-8d5343fefc16	\N
f5361a69-1a0b-4436-8055-0fd286e2c425	329eb5b7-10d1-42c9-b309-19477157eeb5	I	540f6289-8115-4da3-aa73-8d5343fefc16	\N
77f49b8b-5404-4756-8c64-93a72bfb8923	329eb5b7-10d1-42c9-b309-19477157eeb5	J	540f6289-8115-4da3-aa73-8d5343fefc16	\N
052f41c8-a3a5-4904-a48e-50570f34df24	329eb5b7-10d1-42c9-b309-19477157eeb5	A	b977bd8b-ebac-4d24-b264-e2f23bf52911	\N
878358ff-98e8-4f7e-bb34-29ff209e685b	329eb5b7-10d1-42c9-b309-19477157eeb5	B	b977bd8b-ebac-4d24-b264-e2f23bf52911	\N
14414ff1-d4a9-4ecd-8ac6-334480ab7a3f	329eb5b7-10d1-42c9-b309-19477157eeb5	C	b977bd8b-ebac-4d24-b264-e2f23bf52911	\N
7f7ae999-9e4f-4055-9935-a0f5a985b696	329eb5b7-10d1-42c9-b309-19477157eeb5	D	b977bd8b-ebac-4d24-b264-e2f23bf52911	\N
b01c297b-eb32-4204-b8d7-142dfe9a118b	329eb5b7-10d1-42c9-b309-19477157eeb5	E	b977bd8b-ebac-4d24-b264-e2f23bf52911	\N
6b2c2513-1028-4165-9784-44386cbb04a5	329eb5b7-10d1-42c9-b309-19477157eeb5	F	b977bd8b-ebac-4d24-b264-e2f23bf52911	\N
b3d10ade-b32a-4b10-acad-ecb9c4831d19	329eb5b7-10d1-42c9-b309-19477157eeb5	G	b977bd8b-ebac-4d24-b264-e2f23bf52911	\N
6e17dbac-ec82-44ed-836d-9f9adb1bbb53	329eb5b7-10d1-42c9-b309-19477157eeb5	H	b977bd8b-ebac-4d24-b264-e2f23bf52911	\N
ae744911-fd9c-4ea2-9059-be953f97e85c	329eb5b7-10d1-42c9-b309-19477157eeb5	I	b977bd8b-ebac-4d24-b264-e2f23bf52911	\N
56c12f02-da20-4934-92ff-d195307aba81	329eb5b7-10d1-42c9-b309-19477157eeb5	J	b977bd8b-ebac-4d24-b264-e2f23bf52911	\N
7bc1d9fc-26bd-4a39-add0-ea220af5a39d	329eb5b7-10d1-42c9-b309-19477157eeb5	A	84362e32-cde0-4fbf-82a3-ad7f1781818c	\N
f1facf94-b707-4ff3-ac23-9520944ab06c	329eb5b7-10d1-42c9-b309-19477157eeb5	B	84362e32-cde0-4fbf-82a3-ad7f1781818c	\N
40f50d99-5365-4523-8862-30734566a48f	329eb5b7-10d1-42c9-b309-19477157eeb5	C	84362e32-cde0-4fbf-82a3-ad7f1781818c	\N
576fbfd5-21bd-4f9a-8522-e362184d4d9c	329eb5b7-10d1-42c9-b309-19477157eeb5	D	84362e32-cde0-4fbf-82a3-ad7f1781818c	\N
16ec1d99-b5f6-4876-bb3d-89c126b62680	329eb5b7-10d1-42c9-b309-19477157eeb5	E	84362e32-cde0-4fbf-82a3-ad7f1781818c	\N
03410726-b3a6-4edf-9e28-42e4085b33c9	329eb5b7-10d1-42c9-b309-19477157eeb5	F	84362e32-cde0-4fbf-82a3-ad7f1781818c	\N
a2e3ed23-25e4-4b92-bf5d-c276bd496e77	329eb5b7-10d1-42c9-b309-19477157eeb5	G	84362e32-cde0-4fbf-82a3-ad7f1781818c	\N
467699d7-f5e8-46bb-a407-9e4394fd0957	329eb5b7-10d1-42c9-b309-19477157eeb5	H	84362e32-cde0-4fbf-82a3-ad7f1781818c	\N
6a4d2aa5-29ab-4441-8c34-dfba7a94f956	329eb5b7-10d1-42c9-b309-19477157eeb5	I	84362e32-cde0-4fbf-82a3-ad7f1781818c	\N
c5c552d4-c1ba-43cc-a8a1-4d8289a2d2a9	329eb5b7-10d1-42c9-b309-19477157eeb5	J	84362e32-cde0-4fbf-82a3-ad7f1781818c	\N
63608af2-9b20-4075-a240-22b0e9fc96ff	329eb5b7-10d1-42c9-b309-19477157eeb5	A	43cc5754-c358-4f1c-b0cc-f5122280183c	\N
08e0e44d-3cb4-419f-b5c7-6067a9f753f4	329eb5b7-10d1-42c9-b309-19477157eeb5	B	43cc5754-c358-4f1c-b0cc-f5122280183c	\N
8194a376-40c5-496b-a951-05e8723eeab8	329eb5b7-10d1-42c9-b309-19477157eeb5	C	43cc5754-c358-4f1c-b0cc-f5122280183c	\N
3d201aaa-af8e-4bfc-8a6b-06335ab62812	329eb5b7-10d1-42c9-b309-19477157eeb5	D	43cc5754-c358-4f1c-b0cc-f5122280183c	\N
91ad88a2-4213-4847-a0ab-46021d785e8a	329eb5b7-10d1-42c9-b309-19477157eeb5	E	43cc5754-c358-4f1c-b0cc-f5122280183c	\N
5ce2d656-2e59-4969-941f-5d48ad7e78f5	329eb5b7-10d1-42c9-b309-19477157eeb5	F	43cc5754-c358-4f1c-b0cc-f5122280183c	\N
7079a739-32e9-49c3-b174-46bfcaa1e400	329eb5b7-10d1-42c9-b309-19477157eeb5	G	43cc5754-c358-4f1c-b0cc-f5122280183c	\N
732c7472-941f-4945-a3e3-bca832401d30	329eb5b7-10d1-42c9-b309-19477157eeb5	H	43cc5754-c358-4f1c-b0cc-f5122280183c	\N
b8f53644-3c52-4b35-bf01-5846a01157aa	329eb5b7-10d1-42c9-b309-19477157eeb5	I	43cc5754-c358-4f1c-b0cc-f5122280183c	\N
4a59faaf-2b4d-4052-b704-89b63c37609b	329eb5b7-10d1-42c9-b309-19477157eeb5	J	43cc5754-c358-4f1c-b0cc-f5122280183c	\N
efaff1b8-6cf6-4479-b70e-3780e8ae2132	329eb5b7-10d1-42c9-b309-19477157eeb5	A	b2400fea-d404-4af7-ac20-7a6e63c9da98	\N
5f5f597f-198e-42a8-9b95-f1ca67572026	329eb5b7-10d1-42c9-b309-19477157eeb5	B	b2400fea-d404-4af7-ac20-7a6e63c9da98	\N
cc25967f-5225-4d80-ae14-f66bd74973dc	329eb5b7-10d1-42c9-b309-19477157eeb5	C	b2400fea-d404-4af7-ac20-7a6e63c9da98	\N
6e09fff0-cb21-463d-86c0-fc00044ac2e5	329eb5b7-10d1-42c9-b309-19477157eeb5	D	b2400fea-d404-4af7-ac20-7a6e63c9da98	\N
4a8e5495-2a8c-4b70-8cd4-d0fb56bd2a3e	329eb5b7-10d1-42c9-b309-19477157eeb5	E	b2400fea-d404-4af7-ac20-7a6e63c9da98	\N
d98e1cbb-f4a5-48c5-8e80-4fa17890582a	329eb5b7-10d1-42c9-b309-19477157eeb5	F	b2400fea-d404-4af7-ac20-7a6e63c9da98	\N
22eb878a-9780-4ea1-b12d-cc4d48401b39	329eb5b7-10d1-42c9-b309-19477157eeb5	G	b2400fea-d404-4af7-ac20-7a6e63c9da98	\N
87cbc7ae-7c34-4a99-9392-9d560a56dd7c	329eb5b7-10d1-42c9-b309-19477157eeb5	H	b2400fea-d404-4af7-ac20-7a6e63c9da98	\N
d94fa5e8-cc89-4f1a-b943-08a6d3bd4f05	329eb5b7-10d1-42c9-b309-19477157eeb5	I	b2400fea-d404-4af7-ac20-7a6e63c9da98	\N
9ae23c47-4dbd-49e4-a579-8ba051d192e1	329eb5b7-10d1-42c9-b309-19477157eeb5	J	b2400fea-d404-4af7-ac20-7a6e63c9da98	\N
d032dc0f-5eba-4716-aa25-2aa62e65c743	329eb5b7-10d1-42c9-b309-19477157eeb5	A	8c6f96e3-facf-4b40-b19c-db13ccac2d92	\N
70cb193e-a29e-4634-842a-8d60181e7961	329eb5b7-10d1-42c9-b309-19477157eeb5	B	8c6f96e3-facf-4b40-b19c-db13ccac2d92	\N
96902094-8e4f-4623-bc3c-eae5576800c9	329eb5b7-10d1-42c9-b309-19477157eeb5	C	8c6f96e3-facf-4b40-b19c-db13ccac2d92	\N
ba318c6f-db1c-4684-a9fe-71c3302c4642	329eb5b7-10d1-42c9-b309-19477157eeb5	D	8c6f96e3-facf-4b40-b19c-db13ccac2d92	\N
745c1a9d-5588-44be-8c82-2a33bb3e8ee0	329eb5b7-10d1-42c9-b309-19477157eeb5	E	8c6f96e3-facf-4b40-b19c-db13ccac2d92	\N
1d783011-0391-49c6-90af-e895d70f3ae3	329eb5b7-10d1-42c9-b309-19477157eeb5	F	8c6f96e3-facf-4b40-b19c-db13ccac2d92	\N
94a2ad4d-26c7-456e-a937-790a4ac719e1	329eb5b7-10d1-42c9-b309-19477157eeb5	G	8c6f96e3-facf-4b40-b19c-db13ccac2d92	\N
448b0fb4-cd3e-405c-9817-0a887376c240	329eb5b7-10d1-42c9-b309-19477157eeb5	H	8c6f96e3-facf-4b40-b19c-db13ccac2d92	\N
0ef61ab3-babb-401b-941c-ecb2c0426779	329eb5b7-10d1-42c9-b309-19477157eeb5	I	8c6f96e3-facf-4b40-b19c-db13ccac2d92	\N
17caf008-686c-47a5-a149-eeaa7feae7ce	329eb5b7-10d1-42c9-b309-19477157eeb5	J	8c6f96e3-facf-4b40-b19c-db13ccac2d92	\N
e93ae9f0-71e5-4d67-b046-3ee39affcfef	329eb5b7-10d1-42c9-b309-19477157eeb5	A	5855d269-b8c2-4f20-8d30-5520bc195aed	\N
647b53af-7870-461e-aa05-0bdd468abf2a	329eb5b7-10d1-42c9-b309-19477157eeb5	B	5855d269-b8c2-4f20-8d30-5520bc195aed	\N
57e47495-e0b0-4cd8-9a3b-3630ed3e27ce	329eb5b7-10d1-42c9-b309-19477157eeb5	C	5855d269-b8c2-4f20-8d30-5520bc195aed	\N
247ed142-3f83-4bb9-956d-6fda1c424a27	329eb5b7-10d1-42c9-b309-19477157eeb5	D	5855d269-b8c2-4f20-8d30-5520bc195aed	\N
c4091a82-dfa1-4c42-bfe0-6baa0729901c	329eb5b7-10d1-42c9-b309-19477157eeb5	E	5855d269-b8c2-4f20-8d30-5520bc195aed	\N
b02e8ace-3324-4ec4-a756-48b0ef5b51bf	329eb5b7-10d1-42c9-b309-19477157eeb5	F	5855d269-b8c2-4f20-8d30-5520bc195aed	\N
0dca29a8-1962-4990-82f4-550214bdbba5	329eb5b7-10d1-42c9-b309-19477157eeb5	G	5855d269-b8c2-4f20-8d30-5520bc195aed	\N
af525064-2d74-4e66-9b06-d37e9ff4a86f	329eb5b7-10d1-42c9-b309-19477157eeb5	H	5855d269-b8c2-4f20-8d30-5520bc195aed	\N
dd70bb18-43c2-40c8-be6b-a4a07b60ee13	329eb5b7-10d1-42c9-b309-19477157eeb5	I	5855d269-b8c2-4f20-8d30-5520bc195aed	\N
35ce6be4-c94b-44b9-9707-6449f65a7c28	329eb5b7-10d1-42c9-b309-19477157eeb5	J	5855d269-b8c2-4f20-8d30-5520bc195aed	\N
ac80b5ba-a22e-42d7-be80-a1481cd542b7	329eb5b7-10d1-42c9-b309-19477157eeb5	A	d0f1ad44-a1a1-477e-814c-2bd430b98959	\N
83f59556-7ca5-43dc-a792-8a3aa95578a3	329eb5b7-10d1-42c9-b309-19477157eeb5	B	d0f1ad44-a1a1-477e-814c-2bd430b98959	\N
60892a04-3564-4b00-ae12-0cdaca6ab80b	329eb5b7-10d1-42c9-b309-19477157eeb5	C	d0f1ad44-a1a1-477e-814c-2bd430b98959	\N
22ee11c4-615f-4d73-bd51-c6654b45d366	329eb5b7-10d1-42c9-b309-19477157eeb5	D	d0f1ad44-a1a1-477e-814c-2bd430b98959	\N
c7c2cc9a-7fbc-4a9f-96a7-173df29b6835	329eb5b7-10d1-42c9-b309-19477157eeb5	E	d0f1ad44-a1a1-477e-814c-2bd430b98959	\N
94d424a4-de09-4eab-8b68-a18b692765af	329eb5b7-10d1-42c9-b309-19477157eeb5	F	d0f1ad44-a1a1-477e-814c-2bd430b98959	\N
16753efd-b086-4941-ba5b-ced756e325c3	329eb5b7-10d1-42c9-b309-19477157eeb5	G	d0f1ad44-a1a1-477e-814c-2bd430b98959	\N
cb5c047a-104c-474c-bf3b-980ff9d9de07	329eb5b7-10d1-42c9-b309-19477157eeb5	H	d0f1ad44-a1a1-477e-814c-2bd430b98959	\N
5a2b1c95-7cfc-4e6e-9adf-d52b0f5a0132	329eb5b7-10d1-42c9-b309-19477157eeb5	I	d0f1ad44-a1a1-477e-814c-2bd430b98959	\N
fd4c121a-c2ec-4304-aecb-f86dd1c29f6b	329eb5b7-10d1-42c9-b309-19477157eeb5	J	d0f1ad44-a1a1-477e-814c-2bd430b98959	\N
c7f882dc-b0ef-4932-a455-2087d8782eac	329eb5b7-10d1-42c9-b309-19477157eeb5	A	6bf1c57c-2e52-47dc-bde7-058e72505c00	\N
95a245b6-831a-46d9-af4c-21beb9344016	329eb5b7-10d1-42c9-b309-19477157eeb5	B	6bf1c57c-2e52-47dc-bde7-058e72505c00	\N
1e416120-9ac4-4bad-a917-535d972ce040	329eb5b7-10d1-42c9-b309-19477157eeb5	C	6bf1c57c-2e52-47dc-bde7-058e72505c00	\N
37f1e115-8b93-4831-8e91-4f7ed5680d28	329eb5b7-10d1-42c9-b309-19477157eeb5	D	6bf1c57c-2e52-47dc-bde7-058e72505c00	\N
1c42db38-3d76-48af-9336-b604d7ba280d	329eb5b7-10d1-42c9-b309-19477157eeb5	E	6bf1c57c-2e52-47dc-bde7-058e72505c00	\N
94a98dc6-085a-42db-815a-1def00b2bcc1	329eb5b7-10d1-42c9-b309-19477157eeb5	F	6bf1c57c-2e52-47dc-bde7-058e72505c00	\N
3e0d054c-8474-403b-878f-aae3d1c807f0	329eb5b7-10d1-42c9-b309-19477157eeb5	G	6bf1c57c-2e52-47dc-bde7-058e72505c00	\N
1d537393-ac13-4635-8c31-577ed0acb5f8	329eb5b7-10d1-42c9-b309-19477157eeb5	H	6bf1c57c-2e52-47dc-bde7-058e72505c00	\N
2f38f4f0-7074-437b-84dc-c9ede9e267b1	329eb5b7-10d1-42c9-b309-19477157eeb5	I	6bf1c57c-2e52-47dc-bde7-058e72505c00	\N
fe80d6fb-e9d5-498e-b097-c8bb6bb2599b	329eb5b7-10d1-42c9-b309-19477157eeb5	J	6bf1c57c-2e52-47dc-bde7-058e72505c00	\N
675009ce-3835-40d1-8368-b6f2188759cb	26fc741e-7270-4f5a-98fd-63a548c315a3	A	1f267193-8747-453c-a927-93a5b3be2394	\N
\.


--
-- Data for Name: securitylog; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.securitylog (id, school_id, event, "user", "when") FROM stdin;
\.


--
-- Data for Name: student_admission_form; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.student_admission_form (id, school_id, application_no, status, created_on, notes, student_first_name, student_middle_name, student_last_name, student_email, date_of_birth, gender, blood_group, religion, category, mother_tongue, nationality, aadhaar_id, address, permanent_address, previous_school_name, previous_class_passed, previous_board, transfer_certificate_no, old_unique_id, father_name, father_occupation, father_phone, father_email, father_annual_income, mother_name, mother_occupation, mother_phone, mother_email, mother_annual_income, guardian_name, guardian_relation, guardian_phone, guardian_email, guardian_occupation, guardian_address, applied_for_class_level, current_class_or_last_class, applied_section_preference, needs_transport, transport_route, needs_hostel, separation_dropped_class, separation_reason, separation_session, separation_date, student_id, student_user_id, guardian_user_id, promoted_at) FROM stdin;
5afe5060-bb69-425a-a08d-d1458d16dd01	26fc741e-7270-4f5a-98fd-63a548c315a3	ADM-2026-0001	Registered	2026-11-02	goes to whitefield	Tanya 		Saxena	chemistryisnoteasy@gmail.com	2000-11-24	Female	B+	indian	General	hindi	indian		mathri layout, shri sai niwas	khariar road , basant nager	army school	9	CBSE	56956518		Rakesh Shrivastav	Government Service	454665985652	rakeshshrivasta123@gmail.com	20K – 50K	Madhulika Shrivastav	Homemaker	846465996262	madhulika shrivastav	50K – 1L	Rakesh shrivastav	Father	454548946	rakeshshrivastav	Self Employed	kdjfas;lkd	Class 10	Class 10	A	Yes	whitefiled	Yes	\N	\N	\N	\N	077f4e06-318d-441d-8ac3-e8c8114ee49b	89d590aa-92f2-4b45-83a6-10f22a6c013d	cf3732e5-02ed-487b-8e8f-207e8f22889f	2026-11-02 11:33:55.163967
0714cba5-817d-48d1-852c-4dc9ef2913cd	26fc741e-7270-4f5a-98fd-63a548c315a3	ADM-2026-0002	Registered	2026-11-02		Prashant		Saxena	chemistryisnoteasy@gmail.com	2009-01-08	Male	A+				India 	dnkdfm	dg																							Class 11	Class 11	D				\N	\N	\N	\N	dfadbd7f-9d6a-4839-b248-60c035592d70	48efb0fb-a2ef-4b8f-983c-20ed155ae465	\N	2026-11-02 12:37:46.615382
7f62a430-5829-483c-b4e7-7c6623b178f2	26fc741e-7270-4f5a-98fd-63a548c315a3	ADM-2026-0003	Registered	2026-11-02		shubham 		dkcji		2005-03-11	Female																														Class 10	Class 10	B				\N	\N	\N	\N	312f4da0-73ef-41e3-90ef-f3b1e182bd80	d12ccdba-d9b7-4256-aa99-cc043a2fd5b1	\N	2026-11-02 12:38:51.661073
15710c80-74e3-4964-af88-245731345dac	26fc741e-7270-4f5a-98fd-63a548c315a3	ADM-2026-0004	Registered	2026-11-02		abhay		dkdk		2026-11-11	Male	B+	Hindu	General	Tamil	Indian		dkdjk	ekf	dkkd	10																				Class 10	Class 10	D				\N	\N	\N	\N	0f47d2db-3bef-4b9d-bd4e-100207dd27fe	99b60d39-36f9-48a6-ac56-ef1da63b86cf	\N	2026-11-02 12:41:48.106775
a64bc2f8-88fa-4e1c-95c6-ab7bff53e557	26fc741e-7270-4f5a-98fd-63a548c315a3	ADM-2026-0005	Registered	2026-11-02		irmfoakf		kjcnie	cijkdjcj	2000-07-02	Female	B+	jain	OBC	hindi	amercian		fghjkl	hjkl																						Class 10	Class 10	E				\N	\N	\N	\N	a895ede0-578b-44f8-9934-b705ee048fe1	7afee78c-085b-46b0-bc93-283cc4fe7f48	\N	2026-11-02 12:44:19.32581
\.


--
-- Data for Name: studentparentrelationship; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.studentparentrelationship (id, school_id, student_id, parent_user_id, relationship_type) FROM stdin;
f8acfaca-a7a2-48b4-b2c5-094e5f1bdf69	26fc741e-7270-4f5a-98fd-63a548c315a3	077f4e06-318d-441d-8ac3-e8c8114ee49b	cf3732e5-02ed-487b-8e8f-207e8f22889f	Father
\.


--
-- Data for Name: studentprofile; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.studentprofile (id, school_id, user_id, admission_number, date_of_birth, guardian_name, gender, classroom_id, section_id) FROM stdin;
077f4e06-318d-441d-8ac3-e8c8114ee49b	26fc741e-7270-4f5a-98fd-63a548c315a3	89d590aa-92f2-4b45-83a6-10f22a6c013d	ADM-2026-0001	2000-11-24	Rakesh shrivastav	Female	1f267193-8747-453c-a927-93a5b3be2394	675009ce-3835-40d1-8368-b6f2188759cb
312f4da0-73ef-41e3-90ef-f3b1e182bd80	26fc741e-7270-4f5a-98fd-63a548c315a3	d12ccdba-d9b7-4256-aa99-cc043a2fd5b1	ADM-2026-0003	2005-03-11		Female	1f267193-8747-453c-a927-93a5b3be2394	d5b5d093-4467-4583-93f4-0ddfd0ce1806
0f47d2db-3bef-4b9d-bd4e-100207dd27fe	26fc741e-7270-4f5a-98fd-63a548c315a3	99b60d39-36f9-48a6-ac56-ef1da63b86cf	ADM-2026-0004	2026-11-11		Male	1f267193-8747-453c-a927-93a5b3be2394	639fb45f-cc8c-4f74-b84e-3d998ca46c06
a895ede0-578b-44f8-9934-b705ee048fe1	26fc741e-7270-4f5a-98fd-63a548c315a3	7afee78c-085b-46b0-bc93-283cc4fe7f48	ADM-2026-0005	2000-07-02		Female	1f267193-8747-453c-a927-93a5b3be2394	182ca979-be51-4a80-a53d-c8c5675d5de7
dfadbd7f-9d6a-4839-b248-60c035592d70	26fc741e-7270-4f5a-98fd-63a548c315a3	48efb0fb-a2ef-4b8f-983c-20ed155ae465	ADM-2026-0002	2009-01-08		Male	005350a3-5dae-4186-a621-7fcf575f0d87	b5bebea6-260d-4a33-ab24-b4c9b103ec5e
\.


--
-- Data for Name: subject; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.subject (id, school_id, name, code) FROM stdin;
141f472d-5333-4e3d-af1c-fa8865a8cfdb	26fc741e-7270-4f5a-98fd-63a548c315a3	Mathematics	MATH
7d1c187d-79e4-438a-86ed-bce672323552	26fc741e-7270-4f5a-98fd-63a548c315a3	English	ENG
0015a192-ac39-45ac-ac17-9fd321a345b4	26fc741e-7270-4f5a-98fd-63a548c315a3	Hindi	HIN
aa9f5194-c4f0-4f4f-a60a-3c72432e3fe4	26fc741e-7270-4f5a-98fd-63a548c315a3	Physics	PHY
24506b8a-6679-4473-b319-07c7b822c25a	26fc741e-7270-4f5a-98fd-63a548c315a3	Chemistry	CHEM
036283e0-8f3b-4c55-9901-00fd922607fd	26fc741e-7270-4f5a-98fd-63a548c315a3	Biology	BIO
f4b4cc8a-426e-47ab-95d2-fb8b61c0bd13	26fc741e-7270-4f5a-98fd-63a548c315a3	Computer Science	CS
f22fd6d7-40e3-496d-8e65-43af7ee41bc1	26fc741e-7270-4f5a-98fd-63a548c315a3	Social Science	SST
259e6a00-61b3-4646-96bc-401f1e7231ab	26fc741e-7270-4f5a-98fd-63a548c315a3	History	HIS
e48d0768-b72a-457c-be8f-87ac7f68bbe2	26fc741e-7270-4f5a-98fd-63a548c315a3	Geography	GEO
c287aea5-5ff5-469f-a410-1301e2ffdee5	26fc741e-7270-4f5a-98fd-63a548c315a3	Physical Education	PE
c95cd4ac-cbb1-497e-b17e-443261b7fd78	26fc741e-7270-4f5a-98fd-63a548c315a3	Art	ART
5f39d2f3-4829-4ce2-8468-1f92a58ce305	26fc741e-7270-4f5a-98fd-63a548c315a3	Music	MUS
b1f6e801-c938-4654-8601-e33359a2322f	329eb5b7-10d1-42c9-b309-19477157eeb5	Mathematics	MATH
ed5b503b-05ce-4cb6-88a2-4b2c14efb124	329eb5b7-10d1-42c9-b309-19477157eeb5	English	ENG
cf22dcf8-3357-460f-a4ca-e6312ad78fa3	329eb5b7-10d1-42c9-b309-19477157eeb5	Hindi	HIN
25da1808-3626-420c-a4f0-a3e81f8567ad	329eb5b7-10d1-42c9-b309-19477157eeb5	Physics	PHY
a13a1db8-0dfc-4980-b5b5-cbae9ef4c717	329eb5b7-10d1-42c9-b309-19477157eeb5	Chemistry	CHEM
67b0b523-d6c0-44d5-830b-899eeccac21d	329eb5b7-10d1-42c9-b309-19477157eeb5	Biology	BIO
f17991cc-56e7-4085-a20a-dc15eaaa8fff	329eb5b7-10d1-42c9-b309-19477157eeb5	Computer Science	CS
37a517c0-b968-46cd-b258-9825e636d839	329eb5b7-10d1-42c9-b309-19477157eeb5	Social Science	SST
bb55403a-4bc9-453d-843f-fcfc97fb2559	329eb5b7-10d1-42c9-b309-19477157eeb5	History	HIS
266adc19-5b0c-4bf0-8de8-36b9ba625a3a	329eb5b7-10d1-42c9-b309-19477157eeb5	Geography	GEO
e05c2c49-bfd3-4557-8b41-c495c45fcfd9	329eb5b7-10d1-42c9-b309-19477157eeb5	Physical Education	PE
2f28a500-66c3-4e0d-a117-83c36a0dcfaa	329eb5b7-10d1-42c9-b309-19477157eeb5	Art	ART
77a25c62-c9db-4390-a3cc-0ce02c64a10c	329eb5b7-10d1-42c9-b309-19477157eeb5	Music	MUS
\.


--
-- Data for Name: subjectteacher; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.subjectteacher (id, school_id, section_id, subject_id, teacher_id) FROM stdin;
\.


--
-- Data for Name: supportticket; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.supportticket (id, school_id, subject, category, priority, status, reporter_user_id, assignee, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: syllabusprogress; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.syllabusprogress (id, school_id, section_id, subject_id, chapters_total, chapters_done, updated_at) FROM stdin;
\.


--
-- Data for Name: teacherreview; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.teacherreview (id, school_id, teacher_id, rating, reviewer_role, comment, created_at) FROM stdin;
\.


--
-- Data for Name: teachersubject; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.teachersubject (id, school_id, teacher_id, subject_id) FROM stdin;
d1cc147b-b38f-40d0-83df-16f52a14cef4	26fc741e-7270-4f5a-98fd-63a548c315a3	2f03984b-388e-4701-9a4f-bd74ab6ff76d	c287aea5-5ff5-469f-a410-1301e2ffdee5
\.


--
-- Data for Name: timetableperiod; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.timetableperiod (id, school_id, classroom_id, section_id, subject_id, teacher_id, day_of_week, start_time, end_time, room) FROM stdin;
\.


--
-- Data for Name: transportroute; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.transportroute (id, school_id, name, bus_id, driver, stops, students, status) FROM stdin;
\.


--
-- Data for Name: user; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public."user" (id, school_id, email, full_name, is_active, hashed_password, created_at) FROM stdin;
8859c8d9-d761-4ec3-bd79-8f4adae8eb45	26fc741e-7270-4f5a-98fd-63a548c315a3	admin@abc	ABC School	t	$2b$12$X8kVc2uZiT3YQgs3ZUhpo.hGwFnb837gM8./aBFbnuICMrnOPCGA2	2026-10-21 11:44:42.444897
c122747f-06d5-47d9-ba16-d87cc3d62039	329eb5b7-10d1-42c9-b309-19477157eeb5	office@dps	Delhi Public School	t	$2b$12$SjnwqgICWhUmf2OFeUwbLOydW5yl6Ry/xOtDFcm1zB0Yrf0VdLjie	2026-10-21 11:44:42.684223
09a1e74a-c4f2-4169-8b49-df3b5d0b92df	26fc741e-7270-4f5a-98fd-63a548c315a3	kckckcG@gmail.com	kailash chandra saxena	t	$2b$12$Pskyb5h6oJleUf5nWPKqdu878VKHEJU3u9qJP/DXYgA24R0m0b4a2	2026-10-28 16:50:37.917992
cf3732e5-02ed-487b-8e8f-207e8f22889f	26fc741e-7270-4f5a-98fd-63a548c315a3	rakeshshrivastav@educonnect.com	Rakesh shrivastav	t	$2b$12$xrEGkF07xjQQ/CklqrHi1OZQyMNt0fxhO1TYQmUDXUioTCglNIQY.	2026-11-02 11:33:55.136312
89d590aa-92f2-4b45-83a6-10f22a6c013d	26fc741e-7270-4f5a-98fd-63a548c315a3	chemistryisnoteasy@gmail.com	Tanya Saxena	t	$2b$12$Altip7/TEu0MluYg5GgekeBS1NOFdn8N5v8PfCu2xY2KdoJ0e/Qmi	2026-11-02 11:33:54.849852
908cf9dd-602f-4653-87ac-13b3e83958aa	26fc741e-7270-4f5a-98fd-63a548c315a3	tanyashrivastav123@gmail.com	Tanu shrivastav	t	$2b$12$LJHMxatoLPgoI6cuivyuwembyusv8lrPK7kQRDe.GKfjt0o83/gyu	2026-11-02 11:37:46.940237
48efb0fb-a2ef-4b8f-983c-20ed155ae465	26fc741e-7270-4f5a-98fd-63a548c315a3	chemistryisnoteasy.2@gmail.com	Prashant Saxena	t	$2b$12$2gCweiMNgT1whMgXXGTKZ.uI8SawSpcOw.HUs46fscUoKRIMqzNoO	2026-11-02 12:37:46.565228
d12ccdba-d9b7-4256-aa99-cc043a2fd5b1	26fc741e-7270-4f5a-98fd-63a548c315a3	stu.shubham.dkcji.10b@educonnect.com	shubham dkcji	t	$2b$12$q4Z1e2EaDo7Wo7OmmTBsMOf47JT83nutpiUlos2BjHQoGSkWf0fwm	2026-11-02 12:38:51.629125
99b60d39-36f9-48a6-ac56-ef1da63b86cf	26fc741e-7270-4f5a-98fd-63a548c315a3	stu.abhay.dkdk.10d@educonnect.com	abhay dkdk	t	$2b$12$vOiToPBAzLuhMXHbGKvV/OaKiuAbkFC0sabuB3jqxDNhs7AiH7PZ.	2026-11-02 12:41:48.074546
7afee78c-085b-46b0-bc93-283cc4fe7f48	26fc741e-7270-4f5a-98fd-63a548c315a3	cijkdjcj@educonnect.com	irmfoakf kjcnie	t	$2b$12$L7mgihfff/iKx5RxZAUF6OK/Jl82xO90.9.0Tlt2KaN1ElQjtCVMe	2026-11-02 12:44:19.290672
\.


--
-- Data for Name: user_role; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.user_role (id, user_id, role_id, is_primary, assigned_at) FROM stdin;
3be45ee7-80e5-4cb4-846f-a700d299fcea	09a1e74a-c4f2-4169-8b49-df3b5d0b92df	52d627c1-d317-462c-b6df-a4da19d22472	t	2026-10-28 16:50:37.924529
f24552f6-f21f-4455-89c6-5fd10424ab89	48efb0fb-a2ef-4b8f-983c-20ed155ae465	c43d1a51-bd5e-4ad6-a5cc-be2cf6e37862	t	2026-11-02 12:37:46.579826
883d7854-ca6c-43ad-9f28-7464b5e71171	d12ccdba-d9b7-4256-aa99-cc043a2fd5b1	c43d1a51-bd5e-4ad6-a5cc-be2cf6e37862	t	2026-11-02 12:38:51.640548
9bd0369f-a023-4365-a304-41deac533dae	99b60d39-36f9-48a6-ac56-ef1da63b86cf	c43d1a51-bd5e-4ad6-a5cc-be2cf6e37862	t	2026-11-02 12:41:48.088645
27169d38-e1f6-4150-8b66-5661a2ccc3fb	7afee78c-085b-46b0-bc93-283cc4fe7f48	c43d1a51-bd5e-4ad6-a5cc-be2cf6e37862	t	2026-11-02 12:44:19.302501
ba302c9a-d256-4e99-b44d-021c19a54421	89d590aa-92f2-4b45-83a6-10f22a6c013d	c43d1a51-bd5e-4ad6-a5cc-be2cf6e37862	t	2026-11-02 11:33:54.862597
0551a94f-86a6-465b-ac3b-30577e0372f4	cf3732e5-02ed-487b-8e8f-207e8f22889f	52d627c1-d317-462c-b6df-a4da19d22472	t	2026-11-02 11:33:55.14552
cd9ec335-d891-4f45-8ea9-57eedaceac3a	908cf9dd-602f-4653-87ac-13b3e83958aa	686f9b85-9087-40c8-bed8-651369cb3abf	t	2026-11-02 11:37:46.948677
624509b2-0f45-4c29-a3aa-c83c480a9477	8859c8d9-d761-4ec3-bd79-8f4adae8eb45	8a213533-674c-4ab7-9511-f49ef20ce50c	t	2026-11-02 15:12:10.820794
8b0516e9-a557-41fd-8557-82bd873e2abc	c122747f-06d5-47d9-ba16-d87cc3d62039	8a213533-674c-4ab7-9511-f49ef20ce50c	t	2026-11-02 15:12:10.835159
\.


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: attendanceauditlog attendanceauditlog_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.attendanceauditlog
    ADD CONSTRAINT attendanceauditlog_pkey PRIMARY KEY (id);


--
-- Name: attendancerecord attendancerecord_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.attendancerecord
    ADD CONSTRAINT attendancerecord_pkey PRIMARY KEY (id);


--
-- Name: bus bus_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.bus
    ADD CONSTRAINT bus_pkey PRIMARY KEY (id);


--
-- Name: chatfile chatfile_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chatfile
    ADD CONSTRAINT chatfile_pkey PRIMARY KEY (id);


--
-- Name: chatmessage chatmessage_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chatmessage
    ADD CONSTRAINT chatmessage_pkey PRIMARY KEY (id);


--
-- Name: chatthread chatthread_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chatthread
    ADD CONSTRAINT chatthread_pkey PRIMARY KEY (id);


--
-- Name: chatthreadparticipant chatthreadparticipant_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chatthreadparticipant
    ADD CONSTRAINT chatthreadparticipant_pkey PRIMARY KEY (id);


--
-- Name: classdiary classdiary_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.classdiary
    ADD CONSTRAINT classdiary_pkey PRIMARY KEY (id);


--
-- Name: classroom classroom_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.classroom
    ADD CONSTRAINT classroom_pkey PRIMARY KEY (id);


--
-- Name: copilotautomation copilotautomation_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.copilotautomation
    ADD CONSTRAINT copilotautomation_pkey PRIMARY KEY (id);


--
-- Name: copilotsuggestion copilotsuggestion_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.copilotsuggestion
    ADD CONSTRAINT copilotsuggestion_pkey PRIMARY KEY (id);


--
-- Name: dataquality dataquality_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.dataquality
    ADD CONSTRAINT dataquality_pkey PRIMARY KEY (id);


--
-- Name: educationreport educationreport_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.educationreport
    ADD CONSTRAINT educationreport_pkey PRIMARY KEY (id);


--
-- Name: employee employee_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.employee
    ADD CONSTRAINT employee_pkey PRIMARY KEY (id);


--
-- Name: employeesalary employeesalary_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.employeesalary
    ADD CONSTRAINT employeesalary_pkey PRIMARY KEY (id);


--
-- Name: exam exam_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.exam
    ADD CONSTRAINT exam_pkey PRIMARY KEY (id);


--
-- Name: examsource examsource_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.examsource
    ADD CONSTRAINT examsource_pkey PRIMARY KEY (id);


--
-- Name: feestructure feestructure_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.feestructure
    ADD CONSTRAINT feestructure_pkey PRIMARY KEY (id);


--
-- Name: feetransaction feetransaction_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.feetransaction
    ADD CONSTRAINT feetransaction_pkey PRIMARY KEY (id);


--
-- Name: gatewaystatus gatewaystatus_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.gatewaystatus
    ADD CONSTRAINT gatewaystatus_pkey PRIMARY KEY (id);


--
-- Name: generationjob generationjob_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.generationjob
    ADD CONSTRAINT generationjob_pkey PRIMARY KEY (id);


--
-- Name: homeworkassignment homeworkassignment_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.homeworkassignment
    ADD CONSTRAINT homeworkassignment_pkey PRIMARY KEY (id);


--
-- Name: homeworksubmission homeworksubmission_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.homeworksubmission
    ADD CONSTRAINT homeworksubmission_pkey PRIMARY KEY (id);


--
-- Name: impersonationlog impersonationlog_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.impersonationlog
    ADD CONSTRAINT impersonationlog_pkey PRIMARY KEY (id);


--
-- Name: leaverequest leaverequest_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.leaverequest
    ADD CONSTRAINT leaverequest_pkey PRIMARY KEY (id);


--
-- Name: librarybook librarybook_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.librarybook
    ADD CONSTRAINT librarybook_pkey PRIMARY KEY (id);


--
-- Name: libraryissue libraryissue_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.libraryissue
    ADD CONSTRAINT libraryissue_pkey PRIMARY KEY (id);


--
-- Name: marks marks_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.marks
    ADD CONSTRAINT marks_pkey PRIMARY KEY (id);


--
-- Name: meeting meeting_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.meeting
    ADD CONSTRAINT meeting_pkey PRIMARY KEY (id);


--
-- Name: notification notification_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.notification
    ADD CONSTRAINT notification_pkey PRIMARY KEY (id);


--
-- Name: palettecommand palettecommand_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.palettecommand
    ADD CONSTRAINT palettecommand_pkey PRIMARY KEY (id);


--
-- Name: paperdraft paperdraft_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.paperdraft
    ADD CONSTRAINT paperdraft_pkey PRIMARY KEY (id);


--
-- Name: permission permission_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.permission
    ADD CONSTRAINT permission_pkey PRIMARY KEY (id);


--
-- Name: pipeline_hiring_table pipeline_hiring_table_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.pipeline_hiring_table
    ADD CONSTRAINT pipeline_hiring_table_pkey PRIMARY KEY (id);


--
-- Name: questionusagelog questionusagelog_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.questionusagelog
    ADD CONSTRAINT questionusagelog_pkey PRIMARY KEY (id);


--
-- Name: reportcard reportcard_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.reportcard
    ADD CONSTRAINT reportcard_pkey PRIMARY KEY (id);


--
-- Name: role role_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.role
    ADD CONSTRAINT role_pkey PRIMARY KEY (id);


--
-- Name: rolepermission rolepermission_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.rolepermission
    ADD CONSTRAINT rolepermission_pkey PRIMARY KEY (id);


--
-- Name: salarypayment salarypayment_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.salarypayment
    ADD CONSTRAINT salarypayment_pkey PRIMARY KEY (id);


--
-- Name: school school_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.school
    ADD CONSTRAINT school_pkey PRIMARY KEY (id);


--
-- Name: section section_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.section
    ADD CONSTRAINT section_pkey PRIMARY KEY (id);


--
-- Name: securitylog securitylog_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.securitylog
    ADD CONSTRAINT securitylog_pkey PRIMARY KEY (id);


--
-- Name: student_admission_form student_admission_form_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.student_admission_form
    ADD CONSTRAINT student_admission_form_pkey PRIMARY KEY (id);


--
-- Name: student_admission_form student_admission_form_student_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.student_admission_form
    ADD CONSTRAINT student_admission_form_student_id_key UNIQUE (student_id);


--
-- Name: studentparentrelationship studentparentrelationship_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.studentparentrelationship
    ADD CONSTRAINT studentparentrelationship_pkey PRIMARY KEY (id);


--
-- Name: studentprofile studentprofile_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.studentprofile
    ADD CONSTRAINT studentprofile_pkey PRIMARY KEY (id);


--
-- Name: studentprofile studentprofile_user_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.studentprofile
    ADD CONSTRAINT studentprofile_user_id_key UNIQUE (user_id);


--
-- Name: subject subject_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.subject
    ADD CONSTRAINT subject_pkey PRIMARY KEY (id);


--
-- Name: subjectteacher subjectteacher_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.subjectteacher
    ADD CONSTRAINT subjectteacher_pkey PRIMARY KEY (id);


--
-- Name: supportticket supportticket_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.supportticket
    ADD CONSTRAINT supportticket_pkey PRIMARY KEY (id);


--
-- Name: syllabusprogress syllabusprogress_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.syllabusprogress
    ADD CONSTRAINT syllabusprogress_pkey PRIMARY KEY (id);


--
-- Name: teacherreview teacherreview_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.teacherreview
    ADD CONSTRAINT teacherreview_pkey PRIMARY KEY (id);


--
-- Name: teachersubject teachersubject_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.teachersubject
    ADD CONSTRAINT teachersubject_pkey PRIMARY KEY (id);


--
-- Name: timetableperiod timetableperiod_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.timetableperiod
    ADD CONSTRAINT timetableperiod_pkey PRIMARY KEY (id);


--
-- Name: transportroute transportroute_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.transportroute
    ADD CONSTRAINT transportroute_pkey PRIMARY KEY (id);


--
-- Name: chatthreadparticipant uq_chatparticipant_thread_user; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chatthreadparticipant
    ADD CONSTRAINT uq_chatparticipant_thread_user UNIQUE (thread_id, user_id);


--
-- Name: classroom uq_classroom_school_name; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.classroom
    ADD CONSTRAINT uq_classroom_school_name UNIQUE (school_id, name);


--
-- Name: marks uq_marks_exam_student_subject; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.marks
    ADD CONSTRAINT uq_marks_exam_student_subject UNIQUE (exam_id, student_id, subject_id);


--
-- Name: rolepermission uq_rolepermission_role_permission; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.rolepermission
    ADD CONSTRAINT uq_rolepermission_role_permission UNIQUE (role_id, permission_id);


--
-- Name: section uq_section_school_classroom_name; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.section
    ADD CONSTRAINT uq_section_school_classroom_name UNIQUE (school_id, classroom_id, name);


--
-- Name: subject uq_subject_school_code; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.subject
    ADD CONSTRAINT uq_subject_school_code UNIQUE (school_id, code);


--
-- Name: subject uq_subject_school_name; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.subject
    ADD CONSTRAINT uq_subject_school_name UNIQUE (school_id, name);


--
-- Name: subjectteacher uq_subjectteacher_section_subject; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.subjectteacher
    ADD CONSTRAINT uq_subjectteacher_section_subject UNIQUE (section_id, subject_id);


--
-- Name: syllabusprogress uq_syllabusprogress_section_subject; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.syllabusprogress
    ADD CONSTRAINT uq_syllabusprogress_section_subject UNIQUE (section_id, subject_id);


--
-- Name: teachersubject uq_teachersubject_teacher_subject; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.teachersubject
    ADD CONSTRAINT uq_teachersubject_teacher_subject UNIQUE (teacher_id, subject_id);


--
-- Name: user_role uq_user_role_user_role; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_role
    ADD CONSTRAINT uq_user_role_user_role UNIQUE (user_id, role_id);


--
-- Name: user user_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public."user"
    ADD CONSTRAINT user_pkey PRIMARY KEY (id);


--
-- Name: user_role user_role_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_role
    ADD CONSTRAINT user_role_pkey PRIMARY KEY (id);


--
-- Name: ix_attendanceauditlog_school_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_attendanceauditlog_school_id ON public.attendanceauditlog USING btree (school_id);


--
-- Name: ix_attendancerecord_school_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_attendancerecord_school_id ON public.attendancerecord USING btree (school_id);


--
-- Name: ix_bus_school_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_bus_school_id ON public.bus USING btree (school_id);


--
-- Name: ix_chatfile_school_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_chatfile_school_id ON public.chatfile USING btree (school_id);


--
-- Name: ix_chatmessage_school_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_chatmessage_school_id ON public.chatmessage USING btree (school_id);


--
-- Name: ix_chatthread_school_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_chatthread_school_id ON public.chatthread USING btree (school_id);


--
-- Name: ix_chatthreadparticipant_school_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_chatthreadparticipant_school_id ON public.chatthreadparticipant USING btree (school_id);


--
-- Name: ix_classdiary_classroom_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_classdiary_classroom_id ON public.classdiary USING btree (classroom_id);


--
-- Name: ix_classdiary_school_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_classdiary_school_id ON public.classdiary USING btree (school_id);


--
-- Name: ix_classdiary_section_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_classdiary_section_id ON public.classdiary USING btree (section_id);


--
-- Name: ix_classroom_name; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_classroom_name ON public.classroom USING btree (name);


--
-- Name: ix_classroom_school_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_classroom_school_id ON public.classroom USING btree (school_id);


--
-- Name: ix_copilotautomation_school_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_copilotautomation_school_id ON public.copilotautomation USING btree (school_id);


--
-- Name: ix_copilotsuggestion_school_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_copilotsuggestion_school_id ON public.copilotsuggestion USING btree (school_id);


--
-- Name: ix_dataquality_school_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_dataquality_school_id ON public.dataquality USING btree (school_id);


--
-- Name: ix_educationreport_school_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_educationreport_school_id ON public.educationreport USING btree (school_id);


--
-- Name: ix_employee_aadhaar_no; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_employee_aadhaar_no ON public.employee USING btree (aadhaar_no);


--
-- Name: ix_employee_employee_code; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_employee_employee_code ON public.employee USING btree (employee_code);


--
-- Name: ix_employee_school_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_employee_school_id ON public.employee USING btree (school_id);


--
-- Name: ix_employee_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_employee_user_id ON public.employee USING btree (user_id);


--
-- Name: ix_employeesalary_employee_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_employeesalary_employee_id ON public.employeesalary USING btree (employee_id);


--
-- Name: ix_employeesalary_school_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_employeesalary_school_id ON public.employeesalary USING btree (school_id);


--
-- Name: ix_exam_school_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_exam_school_id ON public.exam USING btree (school_id);


--
-- Name: ix_examsource_classroom_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_examsource_classroom_id ON public.examsource USING btree (classroom_id);


--
-- Name: ix_examsource_content_hash; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_examsource_content_hash ON public.examsource USING btree (content_hash);


--
-- Name: ix_examsource_school_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_examsource_school_id ON public.examsource USING btree (school_id);


--
-- Name: ix_examsource_subject_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_examsource_subject_id ON public.examsource USING btree (subject_id);


--
-- Name: ix_feestructure_school_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_feestructure_school_id ON public.feestructure USING btree (school_id);


--
-- Name: ix_feetransaction_receipt_number; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_feetransaction_receipt_number ON public.feetransaction USING btree (receipt_number);


--
-- Name: ix_feetransaction_school_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_feetransaction_school_id ON public.feetransaction USING btree (school_id);


--
-- Name: ix_gatewaystatus_school_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_gatewaystatus_school_id ON public.gatewaystatus USING btree (school_id);


--
-- Name: ix_generationjob_paper_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_generationjob_paper_id ON public.generationjob USING btree (paper_id);


--
-- Name: ix_generationjob_school_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_generationjob_school_id ON public.generationjob USING btree (school_id);


--
-- Name: ix_homeworkassignment_school_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_homeworkassignment_school_id ON public.homeworkassignment USING btree (school_id);


--
-- Name: ix_homeworksubmission_school_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_homeworksubmission_school_id ON public.homeworksubmission USING btree (school_id);


--
-- Name: ix_impersonationlog_actor_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_impersonationlog_actor_user_id ON public.impersonationlog USING btree (actor_user_id);


--
-- Name: ix_impersonationlog_target_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_impersonationlog_target_user_id ON public.impersonationlog USING btree (target_user_id);


--
-- Name: ix_leaverequest_school_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_leaverequest_school_id ON public.leaverequest USING btree (school_id);


--
-- Name: ix_librarybook_school_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_librarybook_school_id ON public.librarybook USING btree (school_id);


--
-- Name: ix_libraryissue_school_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_libraryissue_school_id ON public.libraryissue USING btree (school_id);


--
-- Name: ix_marks_exam_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_marks_exam_id ON public.marks USING btree (exam_id);


--
-- Name: ix_marks_school_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_marks_school_id ON public.marks USING btree (school_id);


--
-- Name: ix_marks_student_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_marks_student_id ON public.marks USING btree (student_id);


--
-- Name: ix_meeting_school_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_meeting_school_id ON public.meeting USING btree (school_id);


--
-- Name: ix_notification_school_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_notification_school_id ON public.notification USING btree (school_id);


--
-- Name: ix_palettecommand_school_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_palettecommand_school_id ON public.palettecommand USING btree (school_id);


--
-- Name: ix_paperdraft_classroom_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_paperdraft_classroom_id ON public.paperdraft USING btree (classroom_id);


--
-- Name: ix_paperdraft_school_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_paperdraft_school_id ON public.paperdraft USING btree (school_id);


--
-- Name: ix_paperdraft_subject_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_paperdraft_subject_id ON public.paperdraft USING btree (subject_id);


--
-- Name: ix_permission_codename; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_permission_codename ON public.permission USING btree (codename);


--
-- Name: ix_pipeline_hiring_table_candidate_no; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_pipeline_hiring_table_candidate_no ON public.pipeline_hiring_table USING btree (candidate_no);


--
-- Name: ix_pipeline_hiring_table_emp_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_pipeline_hiring_table_emp_id ON public.pipeline_hiring_table USING btree (emp_id);


--
-- Name: ix_pipeline_hiring_table_school_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_pipeline_hiring_table_school_id ON public.pipeline_hiring_table USING btree (school_id);


--
-- Name: ix_questionusagelog_class_name; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_questionusagelog_class_name ON public.questionusagelog USING btree (class_name);


--
-- Name: ix_questionusagelog_fingerprint; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_questionusagelog_fingerprint ON public.questionusagelog USING btree (fingerprint);


--
-- Name: ix_questionusagelog_paper_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_questionusagelog_paper_id ON public.questionusagelog USING btree (paper_id);


--
-- Name: ix_questionusagelog_school_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_questionusagelog_school_id ON public.questionusagelog USING btree (school_id);


--
-- Name: ix_questionusagelog_subject; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_questionusagelog_subject ON public.questionusagelog USING btree (subject);


--
-- Name: ix_reportcard_school_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_reportcard_school_id ON public.reportcard USING btree (school_id);


--
-- Name: ix_role_codename; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_role_codename ON public.role USING btree (codename);


--
-- Name: ix_rolepermission_permission_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_rolepermission_permission_id ON public.rolepermission USING btree (permission_id);


--
-- Name: ix_salarypayment_employee_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_salarypayment_employee_id ON public.salarypayment USING btree (employee_id);


--
-- Name: ix_salarypayment_month; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_salarypayment_month ON public.salarypayment USING btree (month);


--
-- Name: ix_salarypayment_school_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_salarypayment_school_id ON public.salarypayment USING btree (school_id);


--
-- Name: ix_school_code; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_school_code ON public.school USING btree (code);


--
-- Name: ix_school_email; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_school_email ON public.school USING btree (email);


--
-- Name: ix_school_name; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_school_name ON public.school USING btree (name);


--
-- Name: ix_section_class_teacher_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_section_class_teacher_id ON public.section USING btree (class_teacher_id);


--
-- Name: ix_section_school_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_section_school_id ON public.section USING btree (school_id);


--
-- Name: ix_securitylog_school_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_securitylog_school_id ON public.securitylog USING btree (school_id);


--
-- Name: ix_student_admission_form_application_no; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_student_admission_form_application_no ON public.student_admission_form USING btree (application_no);


--
-- Name: ix_student_admission_form_school_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_student_admission_form_school_id ON public.student_admission_form USING btree (school_id);


--
-- Name: ix_studentparentrelationship_school_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_studentparentrelationship_school_id ON public.studentparentrelationship USING btree (school_id);


--
-- Name: ix_studentprofile_admission_number; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_studentprofile_admission_number ON public.studentprofile USING btree (admission_number);


--
-- Name: ix_studentprofile_school_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_studentprofile_school_id ON public.studentprofile USING btree (school_id);


--
-- Name: ix_subject_code; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_subject_code ON public.subject USING btree (code);


--
-- Name: ix_subject_name; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_subject_name ON public.subject USING btree (name);


--
-- Name: ix_subject_school_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_subject_school_id ON public.subject USING btree (school_id);


--
-- Name: ix_subjectteacher_school_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_subjectteacher_school_id ON public.subjectteacher USING btree (school_id);


--
-- Name: ix_supportticket_school_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_supportticket_school_id ON public.supportticket USING btree (school_id);


--
-- Name: ix_syllabusprogress_school_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_syllabusprogress_school_id ON public.syllabusprogress USING btree (school_id);


--
-- Name: ix_teacherreview_school_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_teacherreview_school_id ON public.teacherreview USING btree (school_id);


--
-- Name: ix_teachersubject_school_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_teachersubject_school_id ON public.teachersubject USING btree (school_id);


--
-- Name: ix_timetableperiod_school_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_timetableperiod_school_id ON public.timetableperiod USING btree (school_id);


--
-- Name: ix_transportroute_school_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_transportroute_school_id ON public.transportroute USING btree (school_id);


--
-- Name: ix_user_email; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_user_email ON public."user" USING btree (email);


--
-- Name: ix_user_role_role_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_user_role_role_id ON public.user_role USING btree (role_id);


--
-- Name: ix_user_school_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_user_school_id ON public."user" USING btree (school_id);


--
-- Name: attendanceauditlog attendanceauditlog_attendance_record_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.attendanceauditlog
    ADD CONSTRAINT attendanceauditlog_attendance_record_id_fkey FOREIGN KEY (attendance_record_id) REFERENCES public.attendancerecord(id);


--
-- Name: attendanceauditlog attendanceauditlog_changed_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.attendanceauditlog
    ADD CONSTRAINT attendanceauditlog_changed_by_id_fkey FOREIGN KEY (changed_by_id) REFERENCES public."user"(id);


--
-- Name: attendanceauditlog attendanceauditlog_school_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.attendanceauditlog
    ADD CONSTRAINT attendanceauditlog_school_id_fkey FOREIGN KEY (school_id) REFERENCES public.school(id);


--
-- Name: attendancerecord attendancerecord_classroom_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.attendancerecord
    ADD CONSTRAINT attendancerecord_classroom_id_fkey FOREIGN KEY (classroom_id) REFERENCES public.classroom(id);


--
-- Name: attendancerecord attendancerecord_overridden_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.attendancerecord
    ADD CONSTRAINT attendancerecord_overridden_by_id_fkey FOREIGN KEY (overridden_by_id) REFERENCES public."user"(id);


--
-- Name: attendancerecord attendancerecord_school_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.attendancerecord
    ADD CONSTRAINT attendancerecord_school_id_fkey FOREIGN KEY (school_id) REFERENCES public.school(id);


--
-- Name: attendancerecord attendancerecord_section_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.attendancerecord
    ADD CONSTRAINT attendancerecord_section_id_fkey FOREIGN KEY (section_id) REFERENCES public.section(id);


--
-- Name: attendancerecord attendancerecord_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.attendancerecord
    ADD CONSTRAINT attendancerecord_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.studentprofile(id);


--
-- Name: attendancerecord attendancerecord_subject_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.attendancerecord
    ADD CONSTRAINT attendancerecord_subject_id_fkey FOREIGN KEY (subject_id) REFERENCES public.subject(id);


--
-- Name: bus bus_school_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.bus
    ADD CONSTRAINT bus_school_id_fkey FOREIGN KEY (school_id) REFERENCES public.school(id);


--
-- Name: chatfile chatfile_school_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chatfile
    ADD CONSTRAINT chatfile_school_id_fkey FOREIGN KEY (school_id) REFERENCES public.school(id);


--
-- Name: chatmessage chatmessage_school_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chatmessage
    ADD CONSTRAINT chatmessage_school_id_fkey FOREIGN KEY (school_id) REFERENCES public.school(id);


--
-- Name: chatmessage chatmessage_sender_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chatmessage
    ADD CONSTRAINT chatmessage_sender_id_fkey FOREIGN KEY (sender_id) REFERENCES public."user"(id);


--
-- Name: chatmessage chatmessage_thread_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chatmessage
    ADD CONSTRAINT chatmessage_thread_id_fkey FOREIGN KEY (thread_id) REFERENCES public.chatthread(id);


--
-- Name: chatthread chatthread_school_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chatthread
    ADD CONSTRAINT chatthread_school_id_fkey FOREIGN KEY (school_id) REFERENCES public.school(id);


--
-- Name: chatthreadparticipant chatthreadparticipant_school_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chatthreadparticipant
    ADD CONSTRAINT chatthreadparticipant_school_id_fkey FOREIGN KEY (school_id) REFERENCES public.school(id);


--
-- Name: chatthreadparticipant chatthreadparticipant_thread_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chatthreadparticipant
    ADD CONSTRAINT chatthreadparticipant_thread_id_fkey FOREIGN KEY (thread_id) REFERENCES public.chatthread(id);


--
-- Name: chatthreadparticipant chatthreadparticipant_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chatthreadparticipant
    ADD CONSTRAINT chatthreadparticipant_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user"(id);


--
-- Name: classdiary classdiary_classroom_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.classdiary
    ADD CONSTRAINT classdiary_classroom_id_fkey FOREIGN KEY (classroom_id) REFERENCES public.classroom(id);


--
-- Name: classdiary classdiary_school_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.classdiary
    ADD CONSTRAINT classdiary_school_id_fkey FOREIGN KEY (school_id) REFERENCES public.school(id);


--
-- Name: classdiary classdiary_section_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.classdiary
    ADD CONSTRAINT classdiary_section_id_fkey FOREIGN KEY (section_id) REFERENCES public.section(id);


--
-- Name: classdiary classdiary_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.classdiary
    ADD CONSTRAINT classdiary_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.studentprofile(id);


--
-- Name: classdiary classdiary_teacher_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.classdiary
    ADD CONSTRAINT classdiary_teacher_id_fkey FOREIGN KEY (teacher_id) REFERENCES public.employee(id);


--
-- Name: classroom classroom_school_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.classroom
    ADD CONSTRAINT classroom_school_id_fkey FOREIGN KEY (school_id) REFERENCES public.school(id);


--
-- Name: copilotautomation copilotautomation_school_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.copilotautomation
    ADD CONSTRAINT copilotautomation_school_id_fkey FOREIGN KEY (school_id) REFERENCES public.school(id);


--
-- Name: copilotsuggestion copilotsuggestion_school_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.copilotsuggestion
    ADD CONSTRAINT copilotsuggestion_school_id_fkey FOREIGN KEY (school_id) REFERENCES public.school(id);


--
-- Name: dataquality dataquality_school_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.dataquality
    ADD CONSTRAINT dataquality_school_id_fkey FOREIGN KEY (school_id) REFERENCES public.school(id);


--
-- Name: educationreport educationreport_school_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.educationreport
    ADD CONSTRAINT educationreport_school_id_fkey FOREIGN KEY (school_id) REFERENCES public.school(id);


--
-- Name: employee employee_school_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.employee
    ADD CONSTRAINT employee_school_id_fkey FOREIGN KEY (school_id) REFERENCES public.school(id);


--
-- Name: employee employee_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.employee
    ADD CONSTRAINT employee_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user"(id);


--
-- Name: employeesalary employeesalary_employee_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.employeesalary
    ADD CONSTRAINT employeesalary_employee_id_fkey FOREIGN KEY (employee_id) REFERENCES public.employee(id);


--
-- Name: employeesalary employeesalary_school_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.employeesalary
    ADD CONSTRAINT employeesalary_school_id_fkey FOREIGN KEY (school_id) REFERENCES public.school(id);


--
-- Name: exam exam_school_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.exam
    ADD CONSTRAINT exam_school_id_fkey FOREIGN KEY (school_id) REFERENCES public.school(id);


--
-- Name: examsource examsource_classroom_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.examsource
    ADD CONSTRAINT examsource_classroom_id_fkey FOREIGN KEY (classroom_id) REFERENCES public.classroom(id);


--
-- Name: examsource examsource_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.examsource
    ADD CONSTRAINT examsource_created_by_fkey FOREIGN KEY (created_by) REFERENCES public."user"(id);


--
-- Name: examsource examsource_replaces_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.examsource
    ADD CONSTRAINT examsource_replaces_id_fkey FOREIGN KEY (replaces_id) REFERENCES public.examsource(id);


--
-- Name: examsource examsource_school_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.examsource
    ADD CONSTRAINT examsource_school_id_fkey FOREIGN KEY (school_id) REFERENCES public.school(id);


--
-- Name: examsource examsource_subject_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.examsource
    ADD CONSTRAINT examsource_subject_id_fkey FOREIGN KEY (subject_id) REFERENCES public.subject(id);


--
-- Name: feestructure feestructure_classroom_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.feestructure
    ADD CONSTRAINT feestructure_classroom_id_fkey FOREIGN KEY (classroom_id) REFERENCES public.classroom(id);


--
-- Name: feestructure feestructure_school_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.feestructure
    ADD CONSTRAINT feestructure_school_id_fkey FOREIGN KEY (school_id) REFERENCES public.school(id);


--
-- Name: feetransaction feetransaction_fee_structure_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.feetransaction
    ADD CONSTRAINT feetransaction_fee_structure_id_fkey FOREIGN KEY (fee_structure_id) REFERENCES public.feestructure(id);


--
-- Name: feetransaction feetransaction_school_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.feetransaction
    ADD CONSTRAINT feetransaction_school_id_fkey FOREIGN KEY (school_id) REFERENCES public.school(id);


--
-- Name: feetransaction feetransaction_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.feetransaction
    ADD CONSTRAINT feetransaction_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.studentprofile(id);


--
-- Name: gatewaystatus gatewaystatus_school_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.gatewaystatus
    ADD CONSTRAINT gatewaystatus_school_id_fkey FOREIGN KEY (school_id) REFERENCES public.school(id);


--
-- Name: generationjob generationjob_paper_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.generationjob
    ADD CONSTRAINT generationjob_paper_id_fkey FOREIGN KEY (paper_id) REFERENCES public.paperdraft(id);


--
-- Name: generationjob generationjob_school_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.generationjob
    ADD CONSTRAINT generationjob_school_id_fkey FOREIGN KEY (school_id) REFERENCES public.school(id);


--
-- Name: homeworkassignment homeworkassignment_classroom_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.homeworkassignment
    ADD CONSTRAINT homeworkassignment_classroom_id_fkey FOREIGN KEY (classroom_id) REFERENCES public.classroom(id);


--
-- Name: homeworkassignment homeworkassignment_school_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.homeworkassignment
    ADD CONSTRAINT homeworkassignment_school_id_fkey FOREIGN KEY (school_id) REFERENCES public.school(id);


--
-- Name: homeworkassignment homeworkassignment_section_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.homeworkassignment
    ADD CONSTRAINT homeworkassignment_section_id_fkey FOREIGN KEY (section_id) REFERENCES public.section(id);


--
-- Name: homeworkassignment homeworkassignment_subject_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.homeworkassignment
    ADD CONSTRAINT homeworkassignment_subject_id_fkey FOREIGN KEY (subject_id) REFERENCES public.subject(id);


--
-- Name: homeworkassignment homeworkassignment_teacher_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.homeworkassignment
    ADD CONSTRAINT homeworkassignment_teacher_id_fkey FOREIGN KEY (teacher_id) REFERENCES public.employee(id);


--
-- Name: homeworksubmission homeworksubmission_homework_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.homeworksubmission
    ADD CONSTRAINT homeworksubmission_homework_id_fkey FOREIGN KEY (homework_id) REFERENCES public.homeworkassignment(id);


--
-- Name: homeworksubmission homeworksubmission_school_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.homeworksubmission
    ADD CONSTRAINT homeworksubmission_school_id_fkey FOREIGN KEY (school_id) REFERENCES public.school(id);


--
-- Name: homeworksubmission homeworksubmission_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.homeworksubmission
    ADD CONSTRAINT homeworksubmission_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.studentprofile(id);


--
-- Name: impersonationlog impersonationlog_actor_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.impersonationlog
    ADD CONSTRAINT impersonationlog_actor_user_id_fkey FOREIGN KEY (actor_user_id) REFERENCES public."user"(id);


--
-- Name: impersonationlog impersonationlog_target_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.impersonationlog
    ADD CONSTRAINT impersonationlog_target_user_id_fkey FOREIGN KEY (target_user_id) REFERENCES public."user"(id);


--
-- Name: leaverequest leaverequest_requester_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.leaverequest
    ADD CONSTRAINT leaverequest_requester_user_id_fkey FOREIGN KEY (requester_user_id) REFERENCES public."user"(id);


--
-- Name: leaverequest leaverequest_school_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.leaverequest
    ADD CONSTRAINT leaverequest_school_id_fkey FOREIGN KEY (school_id) REFERENCES public.school(id);


--
-- Name: leaverequest leaverequest_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.leaverequest
    ADD CONSTRAINT leaverequest_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.studentprofile(id);


--
-- Name: librarybook librarybook_school_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.librarybook
    ADD CONSTRAINT librarybook_school_id_fkey FOREIGN KEY (school_id) REFERENCES public.school(id);


--
-- Name: libraryissue libraryissue_book_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.libraryissue
    ADD CONSTRAINT libraryissue_book_id_fkey FOREIGN KEY (book_id) REFERENCES public.librarybook(id);


--
-- Name: libraryissue libraryissue_school_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.libraryissue
    ADD CONSTRAINT libraryissue_school_id_fkey FOREIGN KEY (school_id) REFERENCES public.school(id);


--
-- Name: libraryissue libraryissue_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.libraryissue
    ADD CONSTRAINT libraryissue_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.studentprofile(id);


--
-- Name: marks marks_entered_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.marks
    ADD CONSTRAINT marks_entered_by_fkey FOREIGN KEY (entered_by) REFERENCES public."user"(id);


--
-- Name: marks marks_exam_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.marks
    ADD CONSTRAINT marks_exam_id_fkey FOREIGN KEY (exam_id) REFERENCES public.exam(id);


--
-- Name: marks marks_school_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.marks
    ADD CONSTRAINT marks_school_id_fkey FOREIGN KEY (school_id) REFERENCES public.school(id);


--
-- Name: marks marks_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.marks
    ADD CONSTRAINT marks_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.studentprofile(id);


--
-- Name: marks marks_subject_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.marks
    ADD CONSTRAINT marks_subject_id_fkey FOREIGN KEY (subject_id) REFERENCES public.subject(id);


--
-- Name: meeting meeting_school_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.meeting
    ADD CONSTRAINT meeting_school_id_fkey FOREIGN KEY (school_id) REFERENCES public.school(id);


--
-- Name: notification notification_school_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.notification
    ADD CONSTRAINT notification_school_id_fkey FOREIGN KEY (school_id) REFERENCES public.school(id);


--
-- Name: notification notification_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.notification
    ADD CONSTRAINT notification_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user"(id);


--
-- Name: palettecommand palettecommand_school_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.palettecommand
    ADD CONSTRAINT palettecommand_school_id_fkey FOREIGN KEY (school_id) REFERENCES public.school(id);


--
-- Name: paperdraft paperdraft_classroom_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.paperdraft
    ADD CONSTRAINT paperdraft_classroom_id_fkey FOREIGN KEY (classroom_id) REFERENCES public.classroom(id);


--
-- Name: paperdraft paperdraft_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.paperdraft
    ADD CONSTRAINT paperdraft_created_by_fkey FOREIGN KEY (created_by) REFERENCES public."user"(id);


--
-- Name: paperdraft paperdraft_school_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.paperdraft
    ADD CONSTRAINT paperdraft_school_id_fkey FOREIGN KEY (school_id) REFERENCES public.school(id);


--
-- Name: paperdraft paperdraft_subject_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.paperdraft
    ADD CONSTRAINT paperdraft_subject_id_fkey FOREIGN KEY (subject_id) REFERENCES public.subject(id);


--
-- Name: pipeline_hiring_table pipeline_hiring_table_decided_by_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.pipeline_hiring_table
    ADD CONSTRAINT pipeline_hiring_table_decided_by_user_id_fkey FOREIGN KEY (decided_by_user_id) REFERENCES public."user"(id);


--
-- Name: pipeline_hiring_table pipeline_hiring_table_school_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.pipeline_hiring_table
    ADD CONSTRAINT pipeline_hiring_table_school_id_fkey FOREIGN KEY (school_id) REFERENCES public.school(id);


--
-- Name: pipeline_hiring_table pipeline_hiring_table_subject_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.pipeline_hiring_table
    ADD CONSTRAINT pipeline_hiring_table_subject_id_fkey FOREIGN KEY (subject_id) REFERENCES public.subject(id);


--
-- Name: questionusagelog questionusagelog_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.questionusagelog
    ADD CONSTRAINT questionusagelog_created_by_fkey FOREIGN KEY (created_by) REFERENCES public."user"(id);


--
-- Name: questionusagelog questionusagelog_paper_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.questionusagelog
    ADD CONSTRAINT questionusagelog_paper_id_fkey FOREIGN KEY (paper_id) REFERENCES public.paperdraft(id);


--
-- Name: questionusagelog questionusagelog_school_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.questionusagelog
    ADD CONSTRAINT questionusagelog_school_id_fkey FOREIGN KEY (school_id) REFERENCES public.school(id);


--
-- Name: reportcard reportcard_school_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.reportcard
    ADD CONSTRAINT reportcard_school_id_fkey FOREIGN KEY (school_id) REFERENCES public.school(id);


--
-- Name: rolepermission rolepermission_permission_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.rolepermission
    ADD CONSTRAINT rolepermission_permission_id_fkey FOREIGN KEY (permission_id) REFERENCES public.permission(id);


--
-- Name: rolepermission rolepermission_role_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.rolepermission
    ADD CONSTRAINT rolepermission_role_id_fkey FOREIGN KEY (role_id) REFERENCES public.role(id);


--
-- Name: salarypayment salarypayment_employee_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.salarypayment
    ADD CONSTRAINT salarypayment_employee_id_fkey FOREIGN KEY (employee_id) REFERENCES public.employee(id);


--
-- Name: salarypayment salarypayment_school_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.salarypayment
    ADD CONSTRAINT salarypayment_school_id_fkey FOREIGN KEY (school_id) REFERENCES public.school(id);


--
-- Name: section section_class_teacher_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.section
    ADD CONSTRAINT section_class_teacher_id_fkey FOREIGN KEY (class_teacher_id) REFERENCES public.employee(id);


--
-- Name: section section_classroom_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.section
    ADD CONSTRAINT section_classroom_id_fkey FOREIGN KEY (classroom_id) REFERENCES public.classroom(id);


--
-- Name: section section_school_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.section
    ADD CONSTRAINT section_school_id_fkey FOREIGN KEY (school_id) REFERENCES public.school(id);


--
-- Name: securitylog securitylog_school_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.securitylog
    ADD CONSTRAINT securitylog_school_id_fkey FOREIGN KEY (school_id) REFERENCES public.school(id);


--
-- Name: student_admission_form student_admission_form_guardian_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.student_admission_form
    ADD CONSTRAINT student_admission_form_guardian_user_id_fkey FOREIGN KEY (guardian_user_id) REFERENCES public."user"(id);


--
-- Name: student_admission_form student_admission_form_school_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.student_admission_form
    ADD CONSTRAINT student_admission_form_school_id_fkey FOREIGN KEY (school_id) REFERENCES public.school(id);


--
-- Name: student_admission_form student_admission_form_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.student_admission_form
    ADD CONSTRAINT student_admission_form_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.studentprofile(id);


--
-- Name: student_admission_form student_admission_form_student_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.student_admission_form
    ADD CONSTRAINT student_admission_form_student_user_id_fkey FOREIGN KEY (student_user_id) REFERENCES public."user"(id);


--
-- Name: studentparentrelationship studentparentrelationship_parent_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.studentparentrelationship
    ADD CONSTRAINT studentparentrelationship_parent_user_id_fkey FOREIGN KEY (parent_user_id) REFERENCES public."user"(id);


--
-- Name: studentparentrelationship studentparentrelationship_school_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.studentparentrelationship
    ADD CONSTRAINT studentparentrelationship_school_id_fkey FOREIGN KEY (school_id) REFERENCES public.school(id);


--
-- Name: studentparentrelationship studentparentrelationship_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.studentparentrelationship
    ADD CONSTRAINT studentparentrelationship_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.studentprofile(id);


--
-- Name: studentprofile studentprofile_classroom_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.studentprofile
    ADD CONSTRAINT studentprofile_classroom_id_fkey FOREIGN KEY (classroom_id) REFERENCES public.classroom(id);


--
-- Name: studentprofile studentprofile_school_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.studentprofile
    ADD CONSTRAINT studentprofile_school_id_fkey FOREIGN KEY (school_id) REFERENCES public.school(id);


--
-- Name: studentprofile studentprofile_section_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.studentprofile
    ADD CONSTRAINT studentprofile_section_id_fkey FOREIGN KEY (section_id) REFERENCES public.section(id);


--
-- Name: studentprofile studentprofile_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.studentprofile
    ADD CONSTRAINT studentprofile_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user"(id);


--
-- Name: subject subject_school_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.subject
    ADD CONSTRAINT subject_school_id_fkey FOREIGN KEY (school_id) REFERENCES public.school(id);


--
-- Name: subjectteacher subjectteacher_school_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.subjectteacher
    ADD CONSTRAINT subjectteacher_school_id_fkey FOREIGN KEY (school_id) REFERENCES public.school(id);


--
-- Name: subjectteacher subjectteacher_section_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.subjectteacher
    ADD CONSTRAINT subjectteacher_section_id_fkey FOREIGN KEY (section_id) REFERENCES public.section(id);


--
-- Name: subjectteacher subjectteacher_subject_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.subjectteacher
    ADD CONSTRAINT subjectteacher_subject_id_fkey FOREIGN KEY (subject_id) REFERENCES public.subject(id);


--
-- Name: subjectteacher subjectteacher_teacher_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.subjectteacher
    ADD CONSTRAINT subjectteacher_teacher_id_fkey FOREIGN KEY (teacher_id) REFERENCES public.employee(id);


--
-- Name: supportticket supportticket_reporter_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.supportticket
    ADD CONSTRAINT supportticket_reporter_user_id_fkey FOREIGN KEY (reporter_user_id) REFERENCES public."user"(id);


--
-- Name: supportticket supportticket_school_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.supportticket
    ADD CONSTRAINT supportticket_school_id_fkey FOREIGN KEY (school_id) REFERENCES public.school(id);


--
-- Name: syllabusprogress syllabusprogress_school_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.syllabusprogress
    ADD CONSTRAINT syllabusprogress_school_id_fkey FOREIGN KEY (school_id) REFERENCES public.school(id);


--
-- Name: syllabusprogress syllabusprogress_section_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.syllabusprogress
    ADD CONSTRAINT syllabusprogress_section_id_fkey FOREIGN KEY (section_id) REFERENCES public.section(id);


--
-- Name: syllabusprogress syllabusprogress_subject_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.syllabusprogress
    ADD CONSTRAINT syllabusprogress_subject_id_fkey FOREIGN KEY (subject_id) REFERENCES public.subject(id);


--
-- Name: teacherreview teacherreview_school_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.teacherreview
    ADD CONSTRAINT teacherreview_school_id_fkey FOREIGN KEY (school_id) REFERENCES public.school(id);


--
-- Name: teacherreview teacherreview_teacher_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.teacherreview
    ADD CONSTRAINT teacherreview_teacher_id_fkey FOREIGN KEY (teacher_id) REFERENCES public.employee(id);


--
-- Name: teachersubject teachersubject_school_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.teachersubject
    ADD CONSTRAINT teachersubject_school_id_fkey FOREIGN KEY (school_id) REFERENCES public.school(id);


--
-- Name: teachersubject teachersubject_subject_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.teachersubject
    ADD CONSTRAINT teachersubject_subject_id_fkey FOREIGN KEY (subject_id) REFERENCES public.subject(id);


--
-- Name: teachersubject teachersubject_teacher_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.teachersubject
    ADD CONSTRAINT teachersubject_teacher_id_fkey FOREIGN KEY (teacher_id) REFERENCES public.employee(id);


--
-- Name: timetableperiod timetableperiod_classroom_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.timetableperiod
    ADD CONSTRAINT timetableperiod_classroom_id_fkey FOREIGN KEY (classroom_id) REFERENCES public.classroom(id);


--
-- Name: timetableperiod timetableperiod_school_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.timetableperiod
    ADD CONSTRAINT timetableperiod_school_id_fkey FOREIGN KEY (school_id) REFERENCES public.school(id);


--
-- Name: timetableperiod timetableperiod_section_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.timetableperiod
    ADD CONSTRAINT timetableperiod_section_id_fkey FOREIGN KEY (section_id) REFERENCES public.section(id);


--
-- Name: timetableperiod timetableperiod_subject_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.timetableperiod
    ADD CONSTRAINT timetableperiod_subject_id_fkey FOREIGN KEY (subject_id) REFERENCES public.subject(id);


--
-- Name: timetableperiod timetableperiod_teacher_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.timetableperiod
    ADD CONSTRAINT timetableperiod_teacher_id_fkey FOREIGN KEY (teacher_id) REFERENCES public.employee(id);


--
-- Name: transportroute transportroute_school_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.transportroute
    ADD CONSTRAINT transportroute_school_id_fkey FOREIGN KEY (school_id) REFERENCES public.school(id);


--
-- Name: user_role user_role_role_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_role
    ADD CONSTRAINT user_role_role_id_fkey FOREIGN KEY (role_id) REFERENCES public.role(id);


--
-- Name: user_role user_role_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_role
    ADD CONSTRAINT user_role_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user"(id);


--
-- Name: user user_school_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public."user"
    ADD CONSTRAINT user_school_id_fkey FOREIGN KEY (school_id) REFERENCES public.school(id);


--
-- PostgreSQL database dump complete
--

\unrestrict ubesctVdeTpbCWMd6p7u4NcOGjux4fwc3AiNEzU7Iw0hAheDJjBOj89HLP9KTgS

