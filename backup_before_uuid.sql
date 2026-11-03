--
-- PostgreSQL database dump
--

\restrict qcfJBE3wRNjLpKpLPWN5a1f9fJhqcaHHpaMyaYLwUcioTsu8WT2TB8NG1IX0BCu

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
-- Name: student_admission_form; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.student_admission_form (
    student_first_name character varying,
    student_last_name character varying,
    date_of_birth date,
    guardian_name character varying,
    guardian_email character varying,
    guardian_phone character varying,
    applied_for_class_level character varying,
    status character varying NOT NULL,
    notes character varying,
    id integer NOT NULL,
    student_middle_name character varying,
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
    guardian_relation character varying,
    guardian_occupation character varying,
    guardian_address character varying,
    current_class_or_last_class character varying,
    applied_section_preference character varying,
    needs_transport character varying,
    transport_route character varying,
    needs_hostel character varying,
    separation_dropped_class character varying,
    separation_reason character varying,
    separation_session character varying,
    separation_date date,
    application_no character varying NOT NULL,
    created_on date NOT NULL,
    student_id integer,
    student_user_id integer,
    guardian_user_id integer,
    promoted_at timestamp without time zone,
    school_id integer,
    student_email character varying
);


ALTER TABLE public.student_admission_form OWNER TO postgres;

--
-- Name: admissionapplication_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.admissionapplication_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.admissionapplication_id_seq OWNER TO postgres;

--
-- Name: admissionapplication_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.admissionapplication_id_seq OWNED BY public.student_admission_form.id;


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
    attendance_record_id integer NOT NULL,
    changed_by_id integer NOT NULL,
    changed_at timestamp without time zone NOT NULL,
    previous_status public.attendancestatus,
    new_status public.attendancestatus NOT NULL,
    previous_remarks character varying,
    new_remarks character varying,
    id integer NOT NULL,
    school_id integer
);


ALTER TABLE public.attendanceauditlog OWNER TO postgres;

--
-- Name: attendanceauditlog_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.attendanceauditlog_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.attendanceauditlog_id_seq OWNER TO postgres;

--
-- Name: attendanceauditlog_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.attendanceauditlog_id_seq OWNED BY public.attendanceauditlog.id;


--
-- Name: attendancerecord; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.attendancerecord (
    student_id integer NOT NULL,
    classroom_id integer NOT NULL,
    section_id integer NOT NULL,
    date date NOT NULL,
    status public.attendancestatus NOT NULL,
    remarks character varying,
    id integer NOT NULL,
    subject_id integer,
    overridden_by_id integer,
    school_id integer
);


ALTER TABLE public.attendancerecord OWNER TO postgres;

--
-- Name: attendancerecord_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.attendancerecord_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.attendancerecord_id_seq OWNER TO postgres;

--
-- Name: attendancerecord_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.attendancerecord_id_seq OWNED BY public.attendancerecord.id;


--
-- Name: bus; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.bus (
    name character varying NOT NULL,
    plate character varying NOT NULL,
    route character varying NOT NULL,
    capacity integer DEFAULT 0 NOT NULL,
    occupied integer DEFAULT 0 NOT NULL,
    status character varying DEFAULT 'Parked'::character varying NOT NULL,
    school_id integer,
    id integer NOT NULL
);


ALTER TABLE public.bus OWNER TO postgres;

--
-- Name: bus_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.bus_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.bus_id_seq OWNER TO postgres;

--
-- Name: bus_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.bus_id_seq OWNED BY public.bus.id;


--
-- Name: chatfile; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.chatfile (
    name character varying NOT NULL,
    shared_by character varying NOT NULL,
    size character varying NOT NULL,
    "when" character varying NOT NULL,
    school_id integer,
    id integer NOT NULL
);


ALTER TABLE public.chatfile OWNER TO postgres;

--
-- Name: chatfile_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.chatfile_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.chatfile_id_seq OWNER TO postgres;

--
-- Name: chatfile_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.chatfile_id_seq OWNED BY public.chatfile.id;


--
-- Name: chatmessage; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.chatmessage (
    thread_id integer NOT NULL,
    sender_id integer NOT NULL,
    content_text character varying NOT NULL,
    attachment_url character varying,
    id integer NOT NULL,
    created_at timestamp without time zone NOT NULL,
    school_id integer
);


ALTER TABLE public.chatmessage OWNER TO postgres;

--
-- Name: chatmessage_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.chatmessage_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.chatmessage_id_seq OWNER TO postgres;

--
-- Name: chatmessage_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.chatmessage_id_seq OWNED BY public.chatmessage.id;


--
-- Name: chatthread; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.chatthread (
    name character varying,
    is_group boolean NOT NULL,
    id integer NOT NULL,
    school_id integer
);


ALTER TABLE public.chatthread OWNER TO postgres;

--
-- Name: chatthread_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.chatthread_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.chatthread_id_seq OWNER TO postgres;

--
-- Name: chatthread_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.chatthread_id_seq OWNED BY public.chatthread.id;


--
-- Name: chatthreadparticipant; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.chatthreadparticipant (
    thread_id integer NOT NULL,
    user_id integer NOT NULL,
    school_id integer
);


ALTER TABLE public.chatthreadparticipant OWNER TO postgres;

--
-- Name: classdiary; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.classdiary (
    student_id integer NOT NULL,
    teacher_id integer NOT NULL,
    date date NOT NULL,
    note character varying NOT NULL,
    id integer NOT NULL,
    school_id integer,
    classroom_id integer,
    section_id integer
);


ALTER TABLE public.classdiary OWNER TO postgres;

--
-- Name: classdiary_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.classdiary_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.classdiary_id_seq OWNER TO postgres;

--
-- Name: classdiary_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.classdiary_id_seq OWNED BY public.classdiary.id;


--
-- Name: classroom; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.classroom (
    name character varying NOT NULL,
    level integer NOT NULL,
    id integer NOT NULL,
    stage character varying NOT NULL
);


ALTER TABLE public.classroom OWNER TO postgres;

--
-- Name: classroom_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.classroom_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.classroom_id_seq OWNER TO postgres;

--
-- Name: classroom_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.classroom_id_seq OWNED BY public.classroom.id;


--
-- Name: classteacherassignment; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.classteacherassignment (
    teacher_id integer NOT NULL,
    classroom_id integer NOT NULL,
    section_id integer,
    id integer NOT NULL,
    school_id integer
);


ALTER TABLE public.classteacherassignment OWNER TO postgres;

--
-- Name: classteacherassignment_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.classteacherassignment_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.classteacherassignment_id_seq OWNER TO postgres;

--
-- Name: classteacherassignment_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.classteacherassignment_id_seq OWNED BY public.classteacherassignment.id;


--
-- Name: copilotautomation; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.copilotautomation (
    title character varying NOT NULL,
    schedule character varying NOT NULL,
    last_run character varying NOT NULL,
    active boolean DEFAULT true NOT NULL,
    school_id integer,
    id integer NOT NULL
);


ALTER TABLE public.copilotautomation OWNER TO postgres;

--
-- Name: copilotautomation_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.copilotautomation_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.copilotautomation_id_seq OWNER TO postgres;

--
-- Name: copilotautomation_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.copilotautomation_id_seq OWNED BY public.copilotautomation.id;


--
-- Name: copilotsuggestion; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.copilotsuggestion (
    prompt character varying NOT NULL,
    tag character varying NOT NULL,
    school_id integer,
    id integer NOT NULL
);


ALTER TABLE public.copilotsuggestion OWNER TO postgres;

--
-- Name: copilotsuggestion_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.copilotsuggestion_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.copilotsuggestion_id_seq OWNER TO postgres;

--
-- Name: copilotsuggestion_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.copilotsuggestion_id_seq OWNED BY public.copilotsuggestion.id;


--
-- Name: dataquality; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.dataquality (
    area character varying NOT NULL,
    score integer NOT NULL,
    issue character varying NOT NULL,
    status character varying NOT NULL,
    school_id integer,
    id integer NOT NULL
);


ALTER TABLE public.dataquality OWNER TO postgres;

--
-- Name: dataquality_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.dataquality_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.dataquality_id_seq OWNER TO postgres;

--
-- Name: dataquality_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.dataquality_id_seq OWNED BY public.dataquality.id;


--
-- Name: educationreport; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.educationreport (
    metric character varying NOT NULL,
    class_name character varying NOT NULL,
    value character varying NOT NULL,
    trend character varying NOT NULL,
    school_id integer,
    id integer NOT NULL
);


ALTER TABLE public.educationreport OWNER TO postgres;

--
-- Name: educationreport_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.educationreport_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.educationreport_id_seq OWNER TO postgres;

--
-- Name: educationreport_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.educationreport_id_seq OWNED BY public.educationreport.id;


--
-- Name: employee; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.employee (
    user_id integer NOT NULL,
    employee_code character varying NOT NULL,
    department character varying NOT NULL,
    qualification character varying,
    experience_years integer NOT NULL,
    joining_date date NOT NULL,
    created_at timestamp without time zone NOT NULL,
    id integer NOT NULL,
    school_id integer,
    email character varying,
    phone character varying,
    address character varying,
    emergency_contact character varying,
    aadhaar_no character varying,
    pan_no character varying,
    bank_name character varying,
    bank_account_no character varying,
    ifsc character varying,
    previous_employer_monthly_salary double precision
);


ALTER TABLE public.employee OWNER TO postgres;

--
-- Name: employeesalary; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.employeesalary (
    employee_id integer NOT NULL,
    salary_monthly double precision DEFAULT '0'::double precision NOT NULL,
    effective_from date NOT NULL,
    id integer NOT NULL,
    school_id integer,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.employeesalary OWNER TO postgres;

--
-- Name: employeesalary_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.employeesalary_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.employeesalary_id_seq OWNER TO postgres;

--
-- Name: employeesalary_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.employeesalary_id_seq OWNED BY public.employeesalary.id;


--
-- Name: exam; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.exam (
    name character varying NOT NULL,
    term character varying,
    start_date date,
    end_date date,
    status character varying NOT NULL,
    id integer NOT NULL,
    school_id integer,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.exam OWNER TO postgres;

--
-- Name: exam_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.exam_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.exam_id_seq OWNER TO postgres;

--
-- Name: exam_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.exam_id_seq OWNED BY public.exam.id;


--
-- Name: examsource; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.examsource (
    id integer NOT NULL,
    classroom_id integer,
    subject_id integer,
    created_by integer,
    source_type public.sourcetype NOT NULL,
    title character varying NOT NULL,
    chapters json NOT NULL,
    storage_key character varying,
    metadata_json json NOT NULL,
    page_count integer,
    version integer NOT NULL,
    created_at timestamp without time zone NOT NULL,
    class_name character varying NOT NULL,
    subject character varying NOT NULL,
    board character varying NOT NULL,
    teacher_name character varying NOT NULL,
    kind character varying NOT NULL,
    strictness character varying NOT NULL,
    status character varying NOT NULL,
    tags json NOT NULL,
    chunk_count integer NOT NULL,
    error character varying,
    updated_at timestamp without time zone NOT NULL,
    content_hash character varying,
    replaces_id integer,
    school_id integer
);


ALTER TABLE public.examsource OWNER TO postgres;

--
-- Name: examsource_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.examsource_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.examsource_id_seq OWNER TO postgres;

--
-- Name: examsource_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.examsource_id_seq OWNED BY public.examsource.id;


--
-- Name: feestructure; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.feestructure (
    name character varying NOT NULL,
    amount double precision NOT NULL,
    classroom_id integer NOT NULL,
    frequency public.feefrequency NOT NULL,
    id integer NOT NULL,
    due_day character varying,
    status character varying NOT NULL,
    school_id integer
);


ALTER TABLE public.feestructure OWNER TO postgres;

--
-- Name: feestructure_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.feestructure_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.feestructure_id_seq OWNER TO postgres;

--
-- Name: feestructure_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.feestructure_id_seq OWNED BY public.feestructure.id;


--
-- Name: feetransaction; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.feetransaction (
    student_id integer NOT NULL,
    fee_structure_id integer NOT NULL,
    amount_paid double precision NOT NULL,
    date date NOT NULL,
    payment_mode public.paymentmode NOT NULL,
    receipt_number character varying NOT NULL,
    id integer NOT NULL,
    school_id integer
);


ALTER TABLE public.feetransaction OWNER TO postgres;

--
-- Name: feetransaction_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.feetransaction_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.feetransaction_id_seq OWNER TO postgres;

--
-- Name: feetransaction_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.feetransaction_id_seq OWNED BY public.feetransaction.id;


--
-- Name: gatewaystatus; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.gatewaystatus (
    name character varying NOT NULL,
    type character varying NOT NULL,
    status character varying NOT NULL,
    quota character varying NOT NULL,
    school_id integer,
    id integer NOT NULL
);


ALTER TABLE public.gatewaystatus OWNER TO postgres;

--
-- Name: gatewaystatus_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.gatewaystatus_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.gatewaystatus_id_seq OWNER TO postgres;

--
-- Name: gatewaystatus_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.gatewaystatus_id_seq OWNED BY public.gatewaystatus.id;


--
-- Name: generationjob; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.generationjob (
    id integer NOT NULL,
    paper_id integer,
    status public.generationjobstatus NOT NULL,
    graph_state json NOT NULL,
    stages json NOT NULL,
    blueprint_snapshot json NOT NULL,
    coverage_snapshot json NOT NULL,
    model_info json NOT NULL,
    error character varying,
    trace_id character varying,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    config_snapshot json NOT NULL,
    result_snapshot json NOT NULL,
    school_id integer
);


ALTER TABLE public.generationjob OWNER TO postgres;

--
-- Name: generationjob_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.generationjob_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.generationjob_id_seq OWNER TO postgres;

--
-- Name: generationjob_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.generationjob_id_seq OWNED BY public.generationjob.id;


--
-- Name: pipeline_hiring_table; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.pipeline_hiring_table (
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
    id integer NOT NULL,
    school_id integer,
    phone character varying,
    email character varying,
    applied_for character varying,
    subject_id integer,
    subject_name character varying,
    resume_path character varying,
    interview_at timestamp without time zone,
    interview_note character varying,
    decided_by_user_id integer,
    decided_at timestamp without time zone
);


ALTER TABLE public.pipeline_hiring_table OWNER TO postgres;

--
-- Name: hiringcandidate_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.hiringcandidate_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.hiringcandidate_id_seq OWNER TO postgres;

--
-- Name: hiringcandidate_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.hiringcandidate_id_seq OWNED BY public.pipeline_hiring_table.id;


--
-- Name: homeworkassignment; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.homeworkassignment (
    title character varying NOT NULL,
    description character varying NOT NULL,
    classroom_id integer NOT NULL,
    section_id integer,
    subject_id integer NOT NULL,
    teacher_id integer NOT NULL,
    due_date date NOT NULL,
    id integer NOT NULL,
    school_id integer
);


ALTER TABLE public.homeworkassignment OWNER TO postgres;

--
-- Name: homeworkassignment_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.homeworkassignment_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.homeworkassignment_id_seq OWNER TO postgres;

--
-- Name: homeworkassignment_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.homeworkassignment_id_seq OWNED BY public.homeworkassignment.id;


--
-- Name: homeworksubmission; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.homeworksubmission (
    homework_id integer NOT NULL,
    student_id integer NOT NULL,
    content_url character varying,
    status public.submissionstatus NOT NULL,
    teacher_feedback character varying,
    id integer NOT NULL,
    school_id integer
);


ALTER TABLE public.homeworksubmission OWNER TO postgres;

--
-- Name: homeworksubmission_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.homeworksubmission_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.homeworksubmission_id_seq OWNER TO postgres;

--
-- Name: homeworksubmission_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.homeworksubmission_id_seq OWNED BY public.homeworksubmission.id;


--
-- Name: impersonationlog; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.impersonationlog (
    id integer NOT NULL,
    actor_user_id integer NOT NULL,
    target_user_id integer NOT NULL,
    started_at timestamp without time zone NOT NULL,
    ended_at timestamp without time zone,
    reason character varying
);


ALTER TABLE public.impersonationlog OWNER TO postgres;

--
-- Name: impersonationlog_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.impersonationlog_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.impersonationlog_id_seq OWNER TO postgres;

--
-- Name: impersonationlog_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.impersonationlog_id_seq OWNED BY public.impersonationlog.id;


--
-- Name: leaverequest; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.leaverequest (
    student_id integer,
    requester_user_id integer NOT NULL,
    leave_type character varying NOT NULL,
    from_date date NOT NULL,
    to_date date NOT NULL,
    days integer NOT NULL,
    reason character varying,
    status character varying DEFAULT 'Pending'::character varying NOT NULL,
    created_at timestamp without time zone,
    school_id integer,
    id integer NOT NULL
);


ALTER TABLE public.leaverequest OWNER TO postgres;

--
-- Name: leaverequest_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.leaverequest_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.leaverequest_id_seq OWNER TO postgres;

--
-- Name: leaverequest_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.leaverequest_id_seq OWNED BY public.leaverequest.id;


--
-- Name: librarybook; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.librarybook (
    isbn character varying NOT NULL,
    title character varying NOT NULL,
    author character varying NOT NULL,
    category character varying NOT NULL,
    copies integer DEFAULT 1 NOT NULL,
    available integer DEFAULT 1 NOT NULL,
    school_id integer,
    id integer NOT NULL
);


ALTER TABLE public.librarybook OWNER TO postgres;

--
-- Name: librarybook_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.librarybook_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.librarybook_id_seq OWNER TO postgres;

--
-- Name: librarybook_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.librarybook_id_seq OWNED BY public.librarybook.id;


--
-- Name: libraryissue; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.libraryissue (
    book_id integer NOT NULL,
    student_id integer NOT NULL,
    issued_date date NOT NULL,
    due_date date NOT NULL,
    status character varying DEFAULT 'Issued'::character varying NOT NULL,
    school_id integer,
    id integer NOT NULL
);


ALTER TABLE public.libraryissue OWNER TO postgres;

--
-- Name: libraryissue_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.libraryissue_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.libraryissue_id_seq OWNER TO postgres;

--
-- Name: libraryissue_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.libraryissue_id_seq OWNED BY public.libraryissue.id;


--
-- Name: marks; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.marks (
    exam_id integer NOT NULL,
    student_id integer NOT NULL,
    subject_id integer NOT NULL,
    marks_obtained double precision NOT NULL,
    max_marks double precision NOT NULL,
    grade character varying,
    entered_by integer,
    id integer NOT NULL,
    school_id integer,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.marks OWNER TO postgres;

--
-- Name: marks_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.marks_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.marks_id_seq OWNER TO postgres;

--
-- Name: marks_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.marks_id_seq OWNED BY public.marks.id;


--
-- Name: meeting; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.meeting (
    title character varying NOT NULL,
    with_whom character varying NOT NULL,
    meeting_date date NOT NULL,
    meeting_time character varying NOT NULL,
    room character varying,
    status character varying DEFAULT 'Scheduled'::character varying NOT NULL,
    school_id integer,
    id integer NOT NULL
);


ALTER TABLE public.meeting OWNER TO postgres;

--
-- Name: meeting_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.meeting_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.meeting_id_seq OWNER TO postgres;

--
-- Name: meeting_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.meeting_id_seq OWNED BY public.meeting.id;


--
-- Name: notification; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.notification (
    user_id integer NOT NULL,
    title character varying NOT NULL,
    body character varying NOT NULL,
    kind character varying NOT NULL,
    read boolean DEFAULT false NOT NULL,
    created_at timestamp without time zone,
    school_id integer,
    id integer NOT NULL
);


ALTER TABLE public.notification OWNER TO postgres;

--
-- Name: notification_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.notification_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.notification_id_seq OWNER TO postgres;

--
-- Name: notification_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.notification_id_seq OWNED BY public.notification.id;


--
-- Name: palettecommand; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.palettecommand (
    label character varying NOT NULL,
    shortcut character varying NOT NULL,
    category character varying NOT NULL,
    school_id integer,
    id integer NOT NULL
);


ALTER TABLE public.palettecommand OWNER TO postgres;

--
-- Name: palettecommand_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.palettecommand_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.palettecommand_id_seq OWNER TO postgres;

--
-- Name: palettecommand_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.palettecommand_id_seq OWNED BY public.palettecommand.id;


--
-- Name: paperdraft; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.paperdraft (
    id integer NOT NULL,
    title character varying NOT NULL,
    classroom_id integer,
    subject_id integer,
    created_by integer,
    total_marks integer NOT NULL,
    duration_minutes integer NOT NULL,
    blueprint json NOT NULL,
    coverage_mode public.coveragemode NOT NULL,
    coverage_plan json NOT NULL,
    part_a json NOT NULL,
    part_b json NOT NULL,
    status public.paperstatus NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
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
    school_id integer
);


ALTER TABLE public.paperdraft OWNER TO postgres;

--
-- Name: paperdraft_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.paperdraft_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.paperdraft_id_seq OWNER TO postgres;

--
-- Name: paperdraft_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.paperdraft_id_seq OWNED BY public.paperdraft.id;


--
-- Name: permission; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.permission (
    id integer NOT NULL,
    codename character varying NOT NULL,
    category character varying DEFAULT 'General'::character varying NOT NULL,
    label character varying DEFAULT ''::character varying NOT NULL
);


ALTER TABLE public.permission OWNER TO postgres;

--
-- Name: permission_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.permission_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.permission_id_seq OWNER TO postgres;

--
-- Name: permission_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.permission_id_seq OWNED BY public.permission.id;


--
-- Name: questionusagelog; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.questionusagelog (
    id integer NOT NULL,
    fingerprint character varying NOT NULL,
    text character varying NOT NULL,
    paper_id integer,
    class_name character varying DEFAULT ''::character varying NOT NULL,
    subject character varying DEFAULT ''::character varying NOT NULL,
    chapter character varying DEFAULT ''::character varying NOT NULL,
    topic character varying DEFAULT ''::character varying NOT NULL,
    qtype character varying DEFAULT ''::character varying NOT NULL,
    marks integer DEFAULT 0 NOT NULL,
    created_by integer,
    used_at timestamp without time zone NOT NULL,
    school_id integer
);


ALTER TABLE public.questionusagelog OWNER TO postgres;

--
-- Name: questionusagelog_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.questionusagelog_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.questionusagelog_id_seq OWNER TO postgres;

--
-- Name: questionusagelog_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.questionusagelog_id_seq OWNED BY public.questionusagelog.id;


--
-- Name: reportcard; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.reportcard (
    title character varying NOT NULL,
    metric character varying NOT NULL,
    value character varying NOT NULL,
    trend character varying NOT NULL,
    tone character varying NOT NULL,
    school_id integer,
    id integer NOT NULL
);


ALTER TABLE public.reportcard OWNER TO postgres;

--
-- Name: reportcard_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.reportcard_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.reportcard_id_seq OWNER TO postgres;

--
-- Name: reportcard_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.reportcard_id_seq OWNED BY public.reportcard.id;


--
-- Name: role; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.role (
    id integer NOT NULL,
    codename character varying NOT NULL,
    label character varying NOT NULL,
    description character varying,
    is_system boolean NOT NULL
);


ALTER TABLE public.role OWNER TO postgres;

--
-- Name: role_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.role_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.role_id_seq OWNER TO postgres;

--
-- Name: role_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.role_id_seq OWNED BY public.role.id;


--
-- Name: rolepermission; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.rolepermission (
    role_id integer NOT NULL,
    permission_id integer NOT NULL,
    id integer NOT NULL
);


ALTER TABLE public.rolepermission OWNER TO postgres;

--
-- Name: rolepermission_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.rolepermission_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.rolepermission_id_seq OWNER TO postgres;

--
-- Name: rolepermission_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.rolepermission_id_seq OWNED BY public.rolepermission.id;


--
-- Name: salarypayment; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.salarypayment (
    month character varying NOT NULL,
    gross double precision NOT NULL,
    deductions double precision NOT NULL,
    net double precision NOT NULL,
    status character varying NOT NULL,
    paid_on date,
    id integer NOT NULL,
    school_id integer,
    employee_id integer NOT NULL
);


ALTER TABLE public.salarypayment OWNER TO postgres;

--
-- Name: salarypayment_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.salarypayment_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.salarypayment_id_seq OWNER TO postgres;

--
-- Name: salarypayment_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.salarypayment_id_seq OWNED BY public.salarypayment.id;


--
-- Name: school; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.school (
    id integer NOT NULL,
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
-- Name: school_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.school_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.school_id_seq OWNER TO postgres;

--
-- Name: school_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.school_id_seq OWNED BY public.school.id;


--
-- Name: section; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.section (
    name character varying NOT NULL,
    classroom_id integer NOT NULL,
    id integer NOT NULL
);


ALTER TABLE public.section OWNER TO postgres;

--
-- Name: section_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.section_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.section_id_seq OWNER TO postgres;

--
-- Name: section_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.section_id_seq OWNED BY public.section.id;


--
-- Name: securitylog; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.securitylog (
    event character varying NOT NULL,
    "user" character varying NOT NULL,
    "when" character varying NOT NULL,
    school_id integer,
    id integer NOT NULL
);


ALTER TABLE public.securitylog OWNER TO postgres;

--
-- Name: securitylog_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.securitylog_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.securitylog_id_seq OWNER TO postgres;

--
-- Name: securitylog_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.securitylog_id_seq OWNED BY public.securitylog.id;


--
-- Name: staffprofile_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.staffprofile_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.staffprofile_id_seq OWNER TO postgres;

--
-- Name: staffprofile_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.staffprofile_id_seq OWNED BY public.employee.id;


--
-- Name: studentparentrelationship; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.studentparentrelationship (
    student_id integer NOT NULL,
    parent_user_id integer NOT NULL,
    relationship_type character varying NOT NULL,
    id integer NOT NULL,
    school_id integer
);


ALTER TABLE public.studentparentrelationship OWNER TO postgres;

--
-- Name: studentparentrelationship_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.studentparentrelationship_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.studentparentrelationship_id_seq OWNER TO postgres;

--
-- Name: studentparentrelationship_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.studentparentrelationship_id_seq OWNED BY public.studentparentrelationship.id;


--
-- Name: studentprofile; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.studentprofile (
    user_id integer NOT NULL,
    admission_number character varying NOT NULL,
    date_of_birth date NOT NULL,
    guardian_name character varying NOT NULL,
    classroom_id integer,
    section_id integer,
    id integer NOT NULL,
    gender character varying,
    school_id integer
);


ALTER TABLE public.studentprofile OWNER TO postgres;

--
-- Name: studentprofile_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.studentprofile_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.studentprofile_id_seq OWNER TO postgres;

--
-- Name: studentprofile_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.studentprofile_id_seq OWNED BY public.studentprofile.id;


--
-- Name: subject; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.subject (
    name character varying NOT NULL,
    code character varying NOT NULL,
    id integer NOT NULL,
    school_id integer
);


ALTER TABLE public.subject OWNER TO postgres;

--
-- Name: subject_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.subject_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.subject_id_seq OWNER TO postgres;

--
-- Name: subject_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.subject_id_seq OWNED BY public.subject.id;


--
-- Name: supportticket; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.supportticket (
    subject character varying NOT NULL,
    category character varying NOT NULL,
    priority character varying DEFAULT 'Medium'::character varying NOT NULL,
    status character varying DEFAULT 'Open'::character varying NOT NULL,
    reporter_user_id integer NOT NULL,
    assignee character varying,
    created_at timestamp without time zone,
    updated_at timestamp without time zone,
    school_id integer,
    id integer NOT NULL
);


ALTER TABLE public.supportticket OWNER TO postgres;

--
-- Name: supportticket_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.supportticket_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.supportticket_id_seq OWNER TO postgres;

--
-- Name: supportticket_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.supportticket_id_seq OWNED BY public.supportticket.id;


--
-- Name: syllabusprogress; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.syllabusprogress (
    section_id integer NOT NULL,
    subject_id integer NOT NULL,
    chapters_total integer NOT NULL,
    chapters_done integer NOT NULL,
    id integer NOT NULL,
    school_id integer,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.syllabusprogress OWNER TO postgres;

--
-- Name: syllabusprogress_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.syllabusprogress_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.syllabusprogress_id_seq OWNER TO postgres;

--
-- Name: syllabusprogress_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.syllabusprogress_id_seq OWNED BY public.syllabusprogress.id;


--
-- Name: teacherassignment; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.teacherassignment (
    teacher_id integer NOT NULL,
    classroom_id integer NOT NULL,
    section_id integer,
    subject_id integer NOT NULL,
    id integer NOT NULL,
    school_id integer
);


ALTER TABLE public.teacherassignment OWNER TO postgres;

--
-- Name: teacherassignment_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.teacherassignment_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.teacherassignment_id_seq OWNER TO postgres;

--
-- Name: teacherassignment_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.teacherassignment_id_seq OWNED BY public.teacherassignment.id;


--
-- Name: teacherreview; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.teacherreview (
    teacher_id integer NOT NULL,
    rating integer NOT NULL,
    reviewer_role character varying DEFAULT 'Parent'::character varying NOT NULL,
    comment character varying,
    school_id integer,
    id integer NOT NULL,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.teacherreview OWNER TO postgres;

--
-- Name: teacherreview_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.teacherreview_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.teacherreview_id_seq OWNER TO postgres;

--
-- Name: teacherreview_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.teacherreview_id_seq OWNED BY public.teacherreview.id;


--
-- Name: teachersubject; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.teachersubject (
    teacher_id integer NOT NULL,
    subject_id integer NOT NULL,
    id integer NOT NULL,
    school_id integer
);


ALTER TABLE public.teachersubject OWNER TO postgres;

--
-- Name: teachersubject_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.teachersubject_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.teachersubject_id_seq OWNER TO postgres;

--
-- Name: teachersubject_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.teachersubject_id_seq OWNED BY public.teachersubject.id;


--
-- Name: timetableperiod; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.timetableperiod (
    classroom_id integer NOT NULL,
    section_id integer,
    subject_id integer NOT NULL,
    teacher_id integer NOT NULL,
    day_of_week public.dayofweek NOT NULL,
    start_time time without time zone NOT NULL,
    end_time time without time zone NOT NULL,
    room character varying,
    id integer NOT NULL,
    school_id integer
);


ALTER TABLE public.timetableperiod OWNER TO postgres;

--
-- Name: timetableperiod_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.timetableperiod_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.timetableperiod_id_seq OWNER TO postgres;

--
-- Name: timetableperiod_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.timetableperiod_id_seq OWNED BY public.timetableperiod.id;


--
-- Name: transportroute; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.transportroute (
    name character varying NOT NULL,
    bus_id character varying NOT NULL,
    driver character varying NOT NULL,
    stops integer DEFAULT 0 NOT NULL,
    students integer DEFAULT 0 NOT NULL,
    status character varying DEFAULT 'Active'::character varying NOT NULL,
    school_id integer,
    id integer NOT NULL
);


ALTER TABLE public.transportroute OWNER TO postgres;

--
-- Name: transportroute_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.transportroute_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.transportroute_id_seq OWNER TO postgres;

--
-- Name: transportroute_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.transportroute_id_seq OWNED BY public.transportroute.id;


--
-- Name: user; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public."user" (
    email character varying NOT NULL,
    full_name character varying NOT NULL,
    is_active boolean NOT NULL,
    id integer NOT NULL,
    hashed_password character varying NOT NULL,
    created_at timestamp without time zone NOT NULL,
    school_id integer
);


ALTER TABLE public."user" OWNER TO postgres;

--
-- Name: user_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.user_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.user_id_seq OWNER TO postgres;

--
-- Name: user_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.user_id_seq OWNED BY public."user".id;


--
-- Name: user_role; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.user_role (
    user_id integer NOT NULL,
    role_id integer NOT NULL,
    is_primary boolean NOT NULL,
    assigned_at timestamp without time zone NOT NULL,
    id integer NOT NULL
);


ALTER TABLE public.user_role OWNER TO postgres;

--
-- Name: user_role_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.user_role_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.user_role_id_seq OWNER TO postgres;

--
-- Name: user_role_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.user_role_id_seq OWNED BY public.user_role.id;


--
-- Name: attendanceauditlog id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.attendanceauditlog ALTER COLUMN id SET DEFAULT nextval('public.attendanceauditlog_id_seq'::regclass);


--
-- Name: attendancerecord id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.attendancerecord ALTER COLUMN id SET DEFAULT nextval('public.attendancerecord_id_seq'::regclass);


--
-- Name: bus id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.bus ALTER COLUMN id SET DEFAULT nextval('public.bus_id_seq'::regclass);


--
-- Name: chatfile id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chatfile ALTER COLUMN id SET DEFAULT nextval('public.chatfile_id_seq'::regclass);


--
-- Name: chatmessage id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chatmessage ALTER COLUMN id SET DEFAULT nextval('public.chatmessage_id_seq'::regclass);


--
-- Name: chatthread id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chatthread ALTER COLUMN id SET DEFAULT nextval('public.chatthread_id_seq'::regclass);


--
-- Name: classdiary id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.classdiary ALTER COLUMN id SET DEFAULT nextval('public.classdiary_id_seq'::regclass);


--
-- Name: classroom id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.classroom ALTER COLUMN id SET DEFAULT nextval('public.classroom_id_seq'::regclass);


--
-- Name: classteacherassignment id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.classteacherassignment ALTER COLUMN id SET DEFAULT nextval('public.classteacherassignment_id_seq'::regclass);


--
-- Name: copilotautomation id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.copilotautomation ALTER COLUMN id SET DEFAULT nextval('public.copilotautomation_id_seq'::regclass);


--
-- Name: copilotsuggestion id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.copilotsuggestion ALTER COLUMN id SET DEFAULT nextval('public.copilotsuggestion_id_seq'::regclass);


--
-- Name: dataquality id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.dataquality ALTER COLUMN id SET DEFAULT nextval('public.dataquality_id_seq'::regclass);


--
-- Name: educationreport id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.educationreport ALTER COLUMN id SET DEFAULT nextval('public.educationreport_id_seq'::regclass);


--
-- Name: employee id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.employee ALTER COLUMN id SET DEFAULT nextval('public.staffprofile_id_seq'::regclass);


--
-- Name: employeesalary id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.employeesalary ALTER COLUMN id SET DEFAULT nextval('public.employeesalary_id_seq'::regclass);


--
-- Name: exam id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.exam ALTER COLUMN id SET DEFAULT nextval('public.exam_id_seq'::regclass);


--
-- Name: examsource id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.examsource ALTER COLUMN id SET DEFAULT nextval('public.examsource_id_seq'::regclass);


--
-- Name: feestructure id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.feestructure ALTER COLUMN id SET DEFAULT nextval('public.feestructure_id_seq'::regclass);


--
-- Name: feetransaction id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.feetransaction ALTER COLUMN id SET DEFAULT nextval('public.feetransaction_id_seq'::regclass);


--
-- Name: gatewaystatus id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.gatewaystatus ALTER COLUMN id SET DEFAULT nextval('public.gatewaystatus_id_seq'::regclass);


--
-- Name: generationjob id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.generationjob ALTER COLUMN id SET DEFAULT nextval('public.generationjob_id_seq'::regclass);


--
-- Name: homeworkassignment id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.homeworkassignment ALTER COLUMN id SET DEFAULT nextval('public.homeworkassignment_id_seq'::regclass);


--
-- Name: homeworksubmission id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.homeworksubmission ALTER COLUMN id SET DEFAULT nextval('public.homeworksubmission_id_seq'::regclass);


--
-- Name: impersonationlog id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.impersonationlog ALTER COLUMN id SET DEFAULT nextval('public.impersonationlog_id_seq'::regclass);


--
-- Name: leaverequest id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.leaverequest ALTER COLUMN id SET DEFAULT nextval('public.leaverequest_id_seq'::regclass);


--
-- Name: librarybook id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.librarybook ALTER COLUMN id SET DEFAULT nextval('public.librarybook_id_seq'::regclass);


--
-- Name: libraryissue id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.libraryissue ALTER COLUMN id SET DEFAULT nextval('public.libraryissue_id_seq'::regclass);


--
-- Name: marks id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.marks ALTER COLUMN id SET DEFAULT nextval('public.marks_id_seq'::regclass);


--
-- Name: meeting id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.meeting ALTER COLUMN id SET DEFAULT nextval('public.meeting_id_seq'::regclass);


--
-- Name: notification id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.notification ALTER COLUMN id SET DEFAULT nextval('public.notification_id_seq'::regclass);


--
-- Name: palettecommand id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.palettecommand ALTER COLUMN id SET DEFAULT nextval('public.palettecommand_id_seq'::regclass);


--
-- Name: paperdraft id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.paperdraft ALTER COLUMN id SET DEFAULT nextval('public.paperdraft_id_seq'::regclass);


--
-- Name: permission id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.permission ALTER COLUMN id SET DEFAULT nextval('public.permission_id_seq'::regclass);


--
-- Name: pipeline_hiring_table id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.pipeline_hiring_table ALTER COLUMN id SET DEFAULT nextval('public.hiringcandidate_id_seq'::regclass);


--
-- Name: questionusagelog id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.questionusagelog ALTER COLUMN id SET DEFAULT nextval('public.questionusagelog_id_seq'::regclass);


--
-- Name: reportcard id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.reportcard ALTER COLUMN id SET DEFAULT nextval('public.reportcard_id_seq'::regclass);


--
-- Name: role id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.role ALTER COLUMN id SET DEFAULT nextval('public.role_id_seq'::regclass);


--
-- Name: rolepermission id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.rolepermission ALTER COLUMN id SET DEFAULT nextval('public.rolepermission_id_seq'::regclass);


--
-- Name: salarypayment id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.salarypayment ALTER COLUMN id SET DEFAULT nextval('public.salarypayment_id_seq'::regclass);


--
-- Name: school id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.school ALTER COLUMN id SET DEFAULT nextval('public.school_id_seq'::regclass);


--
-- Name: section id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.section ALTER COLUMN id SET DEFAULT nextval('public.section_id_seq'::regclass);


--
-- Name: securitylog id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.securitylog ALTER COLUMN id SET DEFAULT nextval('public.securitylog_id_seq'::regclass);


--
-- Name: student_admission_form id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.student_admission_form ALTER COLUMN id SET DEFAULT nextval('public.admissionapplication_id_seq'::regclass);


--
-- Name: studentparentrelationship id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.studentparentrelationship ALTER COLUMN id SET DEFAULT nextval('public.studentparentrelationship_id_seq'::regclass);


--
-- Name: studentprofile id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.studentprofile ALTER COLUMN id SET DEFAULT nextval('public.studentprofile_id_seq'::regclass);


--
-- Name: subject id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.subject ALTER COLUMN id SET DEFAULT nextval('public.subject_id_seq'::regclass);


--
-- Name: supportticket id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.supportticket ALTER COLUMN id SET DEFAULT nextval('public.supportticket_id_seq'::regclass);


--
-- Name: syllabusprogress id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.syllabusprogress ALTER COLUMN id SET DEFAULT nextval('public.syllabusprogress_id_seq'::regclass);


--
-- Name: teacherassignment id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.teacherassignment ALTER COLUMN id SET DEFAULT nextval('public.teacherassignment_id_seq'::regclass);


--
-- Name: teacherreview id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.teacherreview ALTER COLUMN id SET DEFAULT nextval('public.teacherreview_id_seq'::regclass);


--
-- Name: teachersubject id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.teachersubject ALTER COLUMN id SET DEFAULT nextval('public.teachersubject_id_seq'::regclass);


--
-- Name: timetableperiod id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.timetableperiod ALTER COLUMN id SET DEFAULT nextval('public.timetableperiod_id_seq'::regclass);


--
-- Name: transportroute id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.transportroute ALTER COLUMN id SET DEFAULT nextval('public.transportroute_id_seq'::regclass);


--
-- Name: user id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public."user" ALTER COLUMN id SET DEFAULT nextval('public.user_id_seq'::regclass);


--
-- Name: user_role id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_role ALTER COLUMN id SET DEFAULT nextval('public.user_role_id_seq'::regclass);


--
-- Data for Name: alembic_version; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.alembic_version (version_num) FROM stdin;
f7c8d9e0f1a2
\.


--
-- Data for Name: attendanceauditlog; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.attendanceauditlog (attendance_record_id, changed_by_id, changed_at, previous_status, new_status, previous_remarks, new_remarks, id, school_id) FROM stdin;
\.


--
-- Data for Name: attendancerecord; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.attendancerecord (student_id, classroom_id, section_id, date, status, remarks, id, subject_id, overridden_by_id, school_id) FROM stdin;
\.


--
-- Data for Name: bus; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.bus (name, plate, route, capacity, occupied, status, school_id, id) FROM stdin;
\.


--
-- Data for Name: chatfile; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.chatfile (name, shared_by, size, "when", school_id, id) FROM stdin;
\.


--
-- Data for Name: chatmessage; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.chatmessage (thread_id, sender_id, content_text, attachment_url, id, created_at, school_id) FROM stdin;
\.


--
-- Data for Name: chatthread; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.chatthread (name, is_group, id, school_id) FROM stdin;
\.


--
-- Data for Name: chatthreadparticipant; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.chatthreadparticipant (thread_id, user_id, school_id) FROM stdin;
\.


--
-- Data for Name: classdiary; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.classdiary (student_id, teacher_id, date, note, id, school_id, classroom_id, section_id) FROM stdin;
\.


--
-- Data for Name: classroom; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.classroom (name, level, id, stage) FROM stdin;
Nursery	0	1	pre_primary
LKG	1	2	pre_primary
UKG	2	3	pre_primary
Class 1	3	4	primary
Class 2	4	5	primary
Class 3	5	6	primary
Class 4	6	7	primary
Class 5	7	8	primary
Class 6	8	9	middle
Class 7	9	10	middle
Class 8	10	11	middle
Class 9	11	12	secondary
Class 10	12	13	secondary
Class 11	13	14	senior_secondary
Class 12	14	15	senior_secondary
\.


--
-- Data for Name: classteacherassignment; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.classteacherassignment (teacher_id, classroom_id, section_id, id, school_id) FROM stdin;
\.


--
-- Data for Name: copilotautomation; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.copilotautomation (title, schedule, last_run, active, school_id, id) FROM stdin;
\.


--
-- Data for Name: copilotsuggestion; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.copilotsuggestion (prompt, tag, school_id, id) FROM stdin;
\.


--
-- Data for Name: dataquality; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.dataquality (area, score, issue, status, school_id, id) FROM stdin;
\.


--
-- Data for Name: educationreport; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.educationreport (metric, class_name, value, trend, school_id, id) FROM stdin;
\.


--
-- Data for Name: employee; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.employee (user_id, employee_code, department, qualification, experience_years, joining_date, created_at, id, school_id, email, phone, address, emergency_contact, aadhaar_no, pan_no, bank_name, bank_account_no, ifsc, previous_employer_monthly_salary) FROM stdin;
32	EMP-0038	Sports	Bped	4	2026-11-02	2026-11-02 11:37:46.96086	14	1	tanyashrivastav123@gmail.com	85454984848	dnfsjkldjfa	48781214656	98413184561	7784552	Kotak mahindra	849844489646	dkdkc0001	24964
\.


--
-- Data for Name: employeesalary; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.employeesalary (employee_id, salary_monthly, effective_from, id, school_id, created_at) FROM stdin;
14	32000	2026-11-02	7	1	2026-11-02 11:37:46.978426
\.


--
-- Data for Name: exam; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.exam (name, term, start_date, end_date, status, id, school_id, created_at) FROM stdin;
\.


--
-- Data for Name: examsource; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.examsource (id, classroom_id, subject_id, created_by, source_type, title, chapters, storage_key, metadata_json, page_count, version, created_at, class_name, subject, board, teacher_name, kind, strictness, status, tags, chunk_count, error, updated_at, content_hash, replaces_id, school_id) FROM stdin;
\.


--
-- Data for Name: feestructure; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.feestructure (name, amount, classroom_id, frequency, id, due_day, status, school_id) FROM stdin;
Tuestion fees	12000	13	monthly	1	500	Draft	1
\.


--
-- Data for Name: feetransaction; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.feetransaction (student_id, fee_structure_id, amount_paid, date, payment_mode, receipt_number, id, school_id) FROM stdin;
\.


--
-- Data for Name: gatewaystatus; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.gatewaystatus (name, type, status, quota, school_id, id) FROM stdin;
\.


--
-- Data for Name: generationjob; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.generationjob (id, paper_id, status, graph_state, stages, blueprint_snapshot, coverage_snapshot, model_info, error, trace_id, created_at, updated_at, config_snapshot, result_snapshot, school_id) FROM stdin;
\.


--
-- Data for Name: homeworkassignment; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.homeworkassignment (title, description, classroom_id, section_id, subject_id, teacher_id, due_date, id, school_id) FROM stdin;
\.


--
-- Data for Name: homeworksubmission; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.homeworksubmission (homework_id, student_id, content_url, status, teacher_feedback, id, school_id) FROM stdin;
\.


--
-- Data for Name: impersonationlog; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.impersonationlog (id, actor_user_id, target_user_id, started_at, ended_at, reason) FROM stdin;
\.


--
-- Data for Name: leaverequest; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.leaverequest (student_id, requester_user_id, leave_type, from_date, to_date, days, reason, status, created_at, school_id, id) FROM stdin;
\.


--
-- Data for Name: librarybook; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.librarybook (isbn, title, author, category, copies, available, school_id, id) FROM stdin;
\.


--
-- Data for Name: libraryissue; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.libraryissue (book_id, student_id, issued_date, due_date, status, school_id, id) FROM stdin;
\.


--
-- Data for Name: marks; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.marks (exam_id, student_id, subject_id, marks_obtained, max_marks, grade, entered_by, id, school_id, created_at) FROM stdin;
\.


--
-- Data for Name: meeting; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.meeting (title, with_whom, meeting_date, meeting_time, room, status, school_id, id) FROM stdin;
\.


--
-- Data for Name: notification; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.notification (user_id, title, body, kind, read, created_at, school_id, id) FROM stdin;
\.


--
-- Data for Name: palettecommand; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.palettecommand (label, shortcut, category, school_id, id) FROM stdin;
\.


--
-- Data for Name: paperdraft; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.paperdraft (id, title, classroom_id, subject_id, created_by, total_marks, duration_minutes, blueprint, coverage_mode, coverage_plan, part_a, part_b, status, created_at, updated_at, class_name, subject, board, exam_type, language, chapters, sources, instructions, scope, constraints, school_id) FROM stdin;
\.


--
-- Data for Name: permission; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.permission (id, codename, category, label) FROM stdin;
1	dashboard.read	Dashboard	Read
2	students.read	Students	Read
3	students.create	Students	Create
4	students.update	Students	Update
5	students.delete	Students	Delete
6	students.export	Students	Export
7	students.assign_class	Students	Assign Class
8	students.transfer	Students	Transfer
9	students.promote	Students	Promote
10	teachers.read	Teachers	Read
11	teachers.create	Teachers	Create
12	teachers.update	Teachers	Update
13	teachers.delete	Teachers	Delete
14	teachers.assign_class	Teachers	Assign Class
15	teachers.assign_subject	Teachers	Assign Subject
16	teachers.export	Teachers	Export
17	teachers.view_workload	Teachers	View Workload
18	classes.read	Classes	Read
19	classes.create	Classes	Create
20	classes.update	Classes	Update
21	classes.delete	Classes	Delete
22	classes.assign_teacher	Classes	Assign Teacher
23	classes.assign_student	Classes	Assign Student
24	classes.export	Classes	Export
25	attendance.read	Attendance	Read
26	attendance.mark	Attendance	Mark
27	attendance.update	Attendance	Update
28	attendance.override	Attendance	Override
29	attendance.approve	Attendance	Approve
30	attendance.export	Attendance	Export
31	timetable.read	Timetable	Read
32	timetable.create	Timetable	Create
33	timetable.update	Timetable	Update
34	timetable.delete	Timetable	Delete
35	timetable.publish	Timetable	Publish
36	timetable.manage_rooms	Timetable	Manage Rooms
37	homework.read	Homework	Read
38	homework.create	Homework	Create
39	homework.update	Homework	Update
40	homework.delete	Homework	Delete
41	homework.publish	Homework	Publish
42	homework.review	Homework	Review
43	homework.monitor	Homework	Monitor
44	homework.submit	Homework	Submit
45	diary.read	Diary	Read
46	diary.create	Diary	Create
47	diary.update	Diary	Update
48	diary.delete	Diary	Delete
49	exams.read	Exams	Read
50	exams.create	Exams	Create
51	exams.update	Exams	Update
52	exams.delete	Exams	Delete
53	exams.publish	Exams	Publish
54	marks.read	Marks	Read
55	marks.create	Marks	Create
56	marks.update	Marks	Update
57	marks.approve	Marks	Approve
58	marks.publish	Marks	Publish
59	marks.export	Marks	Export
60	report_cards.read	Report Cards	Read
61	report_cards.create	Report Cards	Create
62	report_cards.update	Report Cards	Update
63	report_cards.approve	Report Cards	Approve
64	report_cards.publish	Report Cards	Publish
65	report_cards.export	Report Cards	Export
66	fees.read	Fees	Read
67	fees.create	Fees	Create
68	fees.update	Fees	Update
69	fees.refund	Fees	Refund
70	fees.export	Fees	Export
71	fees.manage_structure	Fees	Manage Structure
72	fees.view_receipt	Fees	View Receipt
73	fees.pay	Fees	Pay
74	admissions.read	Admissions	Read
75	admissions.manage	Admissions	Manage
76	hiring.read	Hiring	Read
77	hiring.manage	Hiring	Manage
78	payroll.read	Payroll	Read
79	payroll.manage	Payroll	Manage
80	payroll.export	Payroll	Export
81	payroll.view_payslip	Payroll	View Payslip
82	library.read	Library	Read
83	library.manage	Library	Manage
84	library.issue	Library	Issue
85	library.return	Library	Return
86	library.view_history	Library	View History
87	transport.read	Transport	Read
88	transport.manage	Transport	Manage
89	transport.assign	Transport	Assign
90	transport.export	Transport	Export
91	leave.read	Leave	Read
92	leave.create	Leave	Create
93	leave.update	Leave	Update
94	leave.approve	Leave	Approve
95	leave.reject	Leave	Reject
96	leave.export	Leave	Export
97	ptm.read	Ptm	Read
98	ptm.create	Ptm	Create
99	ptm.update	Ptm	Update
100	ptm.manage	Ptm	Manage
101	ptm.book	Ptm	Book
102	ptm.cancel	Ptm	Cancel
103	messages.read	Messages	Read
104	messages.send	Messages	Send
105	messages.broadcast	Messages	Broadcast
106	messages.delete	Messages	Delete
107	announcements.read	Announcements	Read
108	announcements.create	Announcements	Create
109	announcements.update	Announcements	Update
110	announcements.publish	Announcements	Publish
111	announcements.delete	Announcements	Delete
112	reports.read	Reports	Read
113	reports.create	Reports	Create
114	reports.export	Reports	Export
115	analytics.read	Analytics	Read
116	analytics.export	Analytics	Export
117	ai_copilot.use	Ai Copilot	Use
118	settings.read	Settings	Read
119	settings.update	Settings	Update
120	users.manage	Users	Manage
121	roles.manage	Roles	Manage
122	users.impersonate	Users	Impersonate
123	permissions.manage	Permissions	Manage
124	school.configure	School	Configure
125	academic_year.manage	Academic Year	Manage
126	classes.configure	Classes	Configure
127	subjects.configure	Subjects	Configure
128	profile.read	Profile	Read
129	profile.update	Profile	Update
130	profile.change_password	Profile	Change Password
131	profile.change_avatar	Profile	Change Avatar
132	class.students.read	Class	Students Read
133	class.attendance.read	Class	Attendance Read
134	class.attendance.mark	Class	Attendance Mark
135	class.attendance.update	Class	Attendance Update
136	class.homework.monitor	Class	Homework Monitor
137	class.diary.manage	Class	Diary Manage
138	class.leave.read	Class	Leave Read
139	class.ptm.read	Class	Ptm Read
140	class.communication.send	Class	Communication Send
141	class.analytics.read	Class	Analytics Read
142	class.announcements.create	Class	Announcements Create
143	hiring.hire	Hiring	Hire
\.


--
-- Data for Name: pipeline_hiring_table; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.pipeline_hiring_table (candidate_no, candidate_name, role, department, qualification, experience, applied_on, interview_on, emp_id, status, id, school_id, phone, email, applied_for, subject_id, subject_name, resume_path, interview_at, interview_note, decided_by_user_id, decided_at) FROM stdin;
CAN-2026-0031	aditya jain	Teacher	Science	Msc.	4	2026-10-31	2026-10-31	EMP-0037	Hired	1	1	7845962321	sdjldkajfk@gmail.com	teacher	6	Biology	\N	\N		1	2026-10-31 11:07:50.788479
\.


--
-- Data for Name: questionusagelog; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.questionusagelog (id, fingerprint, text, paper_id, class_name, subject, chapter, topic, qtype, marks, created_by, used_at, school_id) FROM stdin;
\.


--
-- Data for Name: reportcard; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.reportcard (title, metric, value, trend, tone, school_id, id) FROM stdin;
\.


--
-- Data for Name: role; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.role (id, codename, label, description, is_system) FROM stdin;
1	system_admin	System Admin	Platform administrator: unrestricted access, manages roles and grants.	t
3	principal	Principal	Heads academics; approves papers, fee cards and payroll.	t
4	vice_principal	Vice Principal	Deputy to the principal: timetable, discipline, approvals.	t
5	hod	Head of Department	Leads a department's teachers, syllabus and results.	t
6	teacher	Teacher	Teaching staff: classroom, homework, marks, attendance.	t
7	class_teacher	Class Teacher	Owns one section: attendance register, diary, report cards.	t
8	subject_teacher	Subject Teacher	Teaches one subject across several classes.	t
9	accountant	Accountant	Fees, receipts, payroll and collection reports.	t
10	librarian	Librarian	Catalogue, issues and returns.	t
11	transport	Transport Manager	Buses, routes and stop assignments.	t
12	staff	Staff	Support staff: front office, lab, maintenance.	t
13	student	Student	Learner login: own timetable, homework and fees.	t
14	guardian	Parent / Guardian	Parent login: their children's records only.	t
15	school_admin	School Admin	Runs one registered school: every permission inside that school only.	t
\.


--
-- Data for Name: rolepermission; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.rolepermission (role_id, permission_id, id) FROM stdin;
1	1	1
1	2	2
1	3	3
1	4	4
1	5	5
1	6	6
1	7	7
1	8	8
1	9	9
1	10	10
1	11	11
1	12	12
1	13	13
1	14	14
1	15	15
1	16	16
1	17	17
1	18	18
1	19	19
1	20	20
1	21	21
1	22	22
1	23	23
1	24	24
1	25	25
1	26	26
1	27	27
1	28	28
1	29	29
1	30	30
1	31	31
1	32	32
1	33	33
1	34	34
1	35	35
1	36	36
1	37	37
1	38	38
1	39	39
1	40	40
1	41	41
1	42	42
1	43	43
1	44	44
1	45	45
1	46	46
1	47	47
1	48	48
1	49	49
1	50	50
1	51	51
1	52	52
1	53	53
1	54	54
1	55	55
1	56	56
1	57	57
1	58	58
1	59	59
1	60	60
1	61	61
1	62	62
1	63	63
1	64	64
1	65	65
1	66	66
1	67	67
1	68	68
1	69	69
1	70	70
1	71	71
1	72	72
1	73	73
1	74	74
1	75	75
1	76	76
1	77	77
1	78	78
1	79	79
1	80	80
1	81	81
1	82	82
1	83	83
1	84	84
1	85	85
1	86	86
1	87	87
1	88	88
1	89	89
1	90	90
1	91	91
1	92	92
1	93	93
1	94	94
1	95	95
1	96	96
1	97	97
1	98	98
1	99	99
1	100	100
1	101	101
1	102	102
1	103	103
1	104	104
1	105	105
1	106	106
1	107	107
1	108	108
1	109	109
1	110	110
1	111	111
1	112	112
1	113	113
1	114	114
1	115	115
1	116	116
1	117	117
1	118	118
1	119	119
1	120	120
1	121	121
1	122	122
1	123	123
1	124	124
1	125	125
1	126	126
1	127	127
1	128	128
1	129	129
1	130	130
1	131	131
1	132	132
1	133	133
1	134	134
1	135	135
1	136	136
1	137	137
1	138	138
1	139	139
1	140	140
1	141	141
1	142	142
15	1	143
15	2	144
15	3	145
15	4	146
15	5	147
15	6	148
15	7	149
15	8	150
15	9	151
15	10	152
15	11	153
15	12	154
15	13	155
15	14	156
15	15	157
15	16	158
15	17	159
15	18	160
15	19	161
15	20	162
15	21	163
15	22	164
15	23	165
15	24	166
15	25	167
15	26	168
15	27	169
15	28	170
15	29	171
15	30	172
15	31	173
15	32	174
15	33	175
15	34	176
15	35	177
15	36	178
15	37	179
15	38	180
15	39	181
15	40	182
15	41	183
15	42	184
15	43	185
15	44	186
15	45	187
15	46	188
15	47	189
15	48	190
15	49	191
15	50	192
15	51	193
15	52	194
15	53	195
15	54	196
15	55	197
15	56	198
15	57	199
15	58	200
15	59	201
15	60	202
15	61	203
15	62	204
15	63	205
15	64	206
15	65	207
15	66	208
15	67	209
15	68	210
15	69	211
15	70	212
15	71	213
15	72	214
15	73	215
15	74	216
15	75	217
15	76	218
15	77	219
15	78	220
15	79	221
15	80	222
15	81	223
15	82	224
15	83	225
15	84	226
15	85	227
15	86	228
15	87	229
15	88	230
15	89	231
15	90	232
15	91	233
15	92	234
15	93	235
15	94	236
15	95	237
15	96	238
15	97	239
15	98	240
15	99	241
15	100	242
15	101	243
15	102	244
15	103	245
15	104	246
15	105	247
15	106	248
15	107	249
15	108	250
15	109	251
15	110	252
15	111	253
15	112	254
15	113	255
15	114	256
15	115	257
15	116	258
15	117	259
15	118	260
15	119	261
15	120	262
15	121	263
15	123	264
15	124	265
15	125	266
15	126	267
15	127	268
15	128	269
15	129	270
15	130	271
15	131	272
15	132	273
15	133	274
15	134	275
15	135	276
15	136	277
15	137	278
15	138	279
15	139	280
15	140	281
15	141	282
15	142	283
4	1	284
4	74	285
4	75	286
4	76	287
4	77	288
4	71	289
4	79	290
4	2	291
4	4	292
4	6	293
4	7	294
4	8	295
4	9	296
4	10	297
4	12	298
4	14	299
4	15	300
4	17	301
4	18	302
4	19	303
4	20	304
4	22	305
4	23	306
4	24	307
4	25	308
4	26	309
4	27	310
4	28	311
4	29	312
4	30	313
4	31	314
4	32	315
4	33	316
4	34	317
4	35	318
4	36	319
4	37	320
4	38	321
4	39	322
4	40	323
4	41	324
4	42	325
4	43	326
4	45	327
4	46	328
4	47	329
4	49	330
4	50	331
4	51	332
4	52	333
4	53	334
4	54	335
4	55	336
4	56	337
4	57	338
4	58	339
4	59	340
4	60	341
4	61	342
4	62	343
4	63	344
4	64	345
4	65	346
4	66	347
4	67	348
4	68	349
4	70	350
4	72	351
4	78	352
4	82	353
4	83	354
4	87	355
4	88	356
4	91	357
4	94	358
4	95	359
4	96	360
4	97	361
4	100	362
4	103	363
4	104	364
4	105	365
4	107	366
4	108	367
4	109	368
4	110	369
4	112	370
4	113	371
4	114	372
4	115	373
4	116	374
4	117	375
4	118	376
4	125	377
4	126	378
4	127	379
4	128	380
4	129	381
4	130	382
4	131	383
3	1	384
3	74	385
3	75	386
3	76	387
3	77	388
3	71	389
3	79	390
3	2	391
3	4	392
3	6	393
3	7	394
3	8	395
3	9	396
3	10	397
3	12	398
3	14	399
3	15	400
3	17	401
3	18	402
3	19	403
3	20	404
3	22	405
3	23	406
3	24	407
3	25	408
3	26	409
3	27	410
3	28	411
3	29	412
3	30	413
3	31	414
3	32	415
3	33	416
3	34	417
3	35	418
3	36	419
3	37	420
3	38	421
3	39	422
3	40	423
3	41	424
3	42	425
3	43	426
3	45	427
3	46	428
3	47	429
3	49	430
3	50	431
3	51	432
3	52	433
3	53	434
3	54	435
3	55	436
3	56	437
3	57	438
3	58	439
3	59	440
3	60	441
3	61	442
3	62	443
3	63	444
3	64	445
3	65	446
3	66	447
3	67	448
3	68	449
3	70	450
3	72	451
3	78	452
3	82	453
3	83	454
3	87	455
3	88	456
3	91	457
3	94	458
3	95	459
3	96	460
3	97	461
3	100	462
3	103	463
3	104	464
3	105	465
3	107	466
3	108	467
3	109	468
3	110	469
3	112	470
3	113	471
3	114	472
3	115	473
3	116	474
3	117	475
3	118	476
3	125	477
3	126	478
3	127	479
3	128	480
3	129	481
3	130	482
3	131	483
5	1	484
5	74	485
5	75	486
5	76	487
5	77	488
5	2	489
5	6	490
5	10	491
5	12	492
5	14	493
5	15	494
5	17	495
5	18	496
5	19	497
5	20	498
5	22	499
5	23	500
5	24	501
5	25	502
5	26	503
5	27	504
5	28	505
5	29	506
5	30	507
5	31	508
5	32	509
5	33	510
5	35	511
5	36	512
5	37	513
5	38	514
5	39	515
5	40	516
5	41	517
5	42	518
5	43	519
5	45	520
5	46	521
5	47	522
5	49	523
5	50	524
5	51	525
5	53	526
5	54	527
5	55	528
5	56	529
5	57	530
5	58	531
5	59	532
5	60	533
5	61	534
5	62	535
5	63	536
5	64	537
5	65	538
5	66	539
5	72	540
5	82	541
5	86	542
5	87	543
5	91	544
5	94	545
5	95	546
5	96	547
5	97	548
5	100	549
5	103	550
5	104	551
5	105	552
5	107	553
5	108	554
5	109	555
5	110	556
5	112	557
5	113	558
5	114	559
5	115	560
5	116	561
5	117	562
5	118	563
5	128	564
5	129	565
5	130	566
5	131	567
5	81	568
7	1	569
7	2	570
7	10	571
7	12	572
7	18	573
7	25	574
7	26	575
7	27	576
7	31	577
7	37	578
7	38	579
7	39	580
7	40	581
7	41	582
7	42	583
7	43	584
7	45	585
7	46	586
7	47	587
7	49	588
7	50	589
7	51	590
7	54	591
7	55	592
7	56	593
7	57	594
7	59	595
7	60	596
7	61	597
7	62	598
7	82	599
7	84	600
7	85	601
7	86	602
7	87	603
7	91	604
7	92	605
7	93	606
7	97	607
7	98	608
7	99	609
7	100	610
7	102	611
7	103	612
7	104	613
7	107	614
7	108	615
7	109	616
7	110	617
7	112	618
7	114	619
7	115	620
7	117	621
7	118	622
7	128	623
7	129	624
7	130	625
7	131	626
7	81	627
7	132	628
7	133	629
7	134	630
7	135	631
7	136	632
7	137	633
7	138	634
7	139	635
7	140	636
7	141	637
7	142	638
8	1	639
8	2	640
8	10	641
8	12	642
8	18	643
8	25	644
8	26	645
8	27	646
8	31	647
8	37	648
8	38	649
8	39	650
8	40	651
8	41	652
8	42	653
8	43	654
8	45	655
8	46	656
8	47	657
8	49	658
8	50	659
8	51	660
8	54	661
8	55	662
8	56	663
8	57	664
8	59	665
8	60	666
8	61	667
8	62	668
8	82	669
8	84	670
8	85	671
8	86	672
8	87	673
8	91	674
8	92	675
8	93	676
8	97	677
8	98	678
8	99	679
8	100	680
8	102	681
8	103	682
8	104	683
8	107	684
8	108	685
8	109	686
8	110	687
8	112	688
8	114	689
8	115	690
8	117	691
8	118	692
8	128	693
8	129	694
8	130	695
8	131	696
8	81	697
6	1	698
6	2	699
6	10	700
6	12	701
6	18	702
6	25	703
6	26	704
6	27	705
6	31	706
6	37	707
6	38	708
6	39	709
6	40	710
6	41	711
6	42	712
6	43	713
6	45	714
6	46	715
6	47	716
6	49	717
6	50	718
6	51	719
6	54	720
6	55	721
6	56	722
6	57	723
6	59	724
6	60	725
6	61	726
6	62	727
6	82	728
6	84	729
6	85	730
6	86	731
6	87	732
6	91	733
6	92	734
6	93	735
6	97	736
6	98	737
6	99	738
6	100	739
6	102	740
6	103	741
6	104	742
6	107	743
6	108	744
6	109	745
6	110	746
6	112	747
6	114	748
6	115	749
6	117	750
6	118	751
6	128	752
6	129	753
6	130	754
6	131	755
6	81	756
13	1	757
13	2	758
13	18	759
13	25	760
13	31	761
13	37	762
13	44	763
13	45	764
13	49	765
13	54	766
13	60	767
13	66	768
13	73	769
13	72	770
13	82	771
13	85	772
13	86	773
13	87	774
13	91	775
13	92	776
13	93	777
13	97	778
13	103	779
13	104	780
13	107	781
13	112	782
13	115	783
13	117	784
13	118	785
13	128	786
13	129	787
13	130	788
13	131	789
14	1	790
14	2	791
14	18	792
14	25	793
14	31	794
14	37	795
14	45	796
14	49	797
14	54	798
14	60	799
14	66	800
14	73	801
14	72	802
14	82	803
14	86	804
14	87	805
14	91	806
14	92	807
14	93	808
14	97	809
14	101	810
14	102	811
14	103	812
14	104	813
14	107	814
14	112	815
14	115	816
14	117	817
14	118	818
14	128	819
14	129	820
14	130	821
14	131	822
9	1	823
9	2	824
9	10	825
9	66	826
9	67	827
9	68	828
9	69	829
9	70	830
9	71	831
9	72	832
9	78	833
9	79	834
9	80	835
9	81	836
9	112	837
9	113	838
9	114	839
9	115	840
9	117	841
9	118	842
9	103	843
9	104	844
9	107	845
9	91	846
9	128	847
9	129	848
9	130	849
9	131	850
10	1	851
10	2	852
10	10	853
10	82	854
10	83	855
10	84	856
10	85	857
10	86	858
10	112	859
10	117	860
10	118	861
10	103	862
10	104	863
10	107	864
10	128	865
10	129	866
10	130	867
10	131	868
11	1	869
11	2	870
11	87	871
11	88	872
11	89	873
11	90	874
11	112	875
11	117	876
11	118	877
11	103	878
11	104	879
11	107	880
11	128	881
11	129	882
11	130	883
11	131	884
12	1	885
12	74	886
12	75	887
12	2	888
12	18	889
12	25	890
12	31	891
12	103	892
12	104	893
12	107	894
12	117	895
12	118	896
12	128	897
12	129	898
12	130	899
12	131	900
1	143	901
15	143	902
3	143	903
\.


--
-- Data for Name: salarypayment; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.salarypayment (month, gross, deductions, net, status, paid_on, id, school_id, employee_id) FROM stdin;
\.


--
-- Data for Name: school; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.school (id, name, code, email, phone, address, is_active, created_at) FROM stdin;
1	ABC School	abc	office@abc	+91 90000 00001	Sector 1, Demo City	t	2026-10-21 11:44:42.2191
2	Delhi Public School	dps	office@dps	+91 90000 00002	Sector 9, Demo City	t	2026-10-21 11:44:42.470347
\.


--
-- Data for Name: section; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.section (name, classroom_id, id) FROM stdin;
A	1	1
B	1	2
C	1	3
D	1	4
E	1	5
F	1	6
G	1	7
H	1	8
I	1	9
J	1	10
A	2	11
B	2	12
C	2	13
D	2	14
E	2	15
F	2	16
G	2	17
H	2	18
I	2	19
J	2	20
A	3	21
B	3	22
C	3	23
D	3	24
E	3	25
F	3	26
G	3	27
H	3	28
I	3	29
J	3	30
A	4	31
B	4	32
C	4	33
D	4	34
E	4	35
F	4	36
G	4	37
H	4	38
I	4	39
J	4	40
A	5	41
B	5	42
C	5	43
D	5	44
E	5	45
F	5	46
G	5	47
H	5	48
I	5	49
J	5	50
A	6	51
B	6	52
C	6	53
D	6	54
E	6	55
F	6	56
G	6	57
H	6	58
I	6	59
J	6	60
A	7	61
B	7	62
C	7	63
D	7	64
E	7	65
F	7	66
G	7	67
H	7	68
I	7	69
J	7	70
A	8	71
B	8	72
C	8	73
D	8	74
E	8	75
F	8	76
G	8	77
H	8	78
I	8	79
J	8	80
A	9	81
B	9	82
C	9	83
D	9	84
E	9	85
F	9	86
G	9	87
H	9	88
I	9	89
J	9	90
A	10	91
B	10	92
C	10	93
D	10	94
E	10	95
F	10	96
G	10	97
H	10	98
I	10	99
J	10	100
A	11	101
B	11	102
C	11	103
D	11	104
E	11	105
F	11	106
G	11	107
H	11	108
I	11	109
J	11	110
A	12	111
B	12	112
C	12	113
D	12	114
E	12	115
F	12	116
G	12	117
H	12	118
I	12	119
J	12	120
A	13	121
B	13	122
C	13	123
D	13	124
E	13	125
F	13	126
G	13	127
H	13	128
I	13	129
J	13	130
A	14	131
B	14	132
C	14	133
D	14	134
E	14	135
F	14	136
G	14	137
H	14	138
I	14	139
J	14	140
A	15	141
B	15	142
C	15	143
D	15	144
E	15	145
F	15	146
G	15	147
H	15	148
I	15	149
J	15	150
\.


--
-- Data for Name: securitylog; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.securitylog (event, "user", "when", school_id, id) FROM stdin;
\.


--
-- Data for Name: student_admission_form; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.student_admission_form (student_first_name, student_last_name, date_of_birth, guardian_name, guardian_email, guardian_phone, applied_for_class_level, status, notes, id, student_middle_name, gender, blood_group, religion, category, mother_tongue, nationality, aadhaar_id, address, permanent_address, previous_school_name, previous_class_passed, previous_board, transfer_certificate_no, old_unique_id, father_name, father_occupation, father_phone, father_email, father_annual_income, mother_name, mother_occupation, mother_phone, mother_email, mother_annual_income, guardian_relation, guardian_occupation, guardian_address, current_class_or_last_class, applied_section_preference, needs_transport, transport_route, needs_hostel, separation_dropped_class, separation_reason, separation_session, separation_date, application_no, created_on, student_id, student_user_id, guardian_user_id, promoted_at, school_id, student_email) FROM stdin;
Tanya 	Saxena	2000-11-24	Rakesh shrivastav	rakeshshrivastav	454548946	Class 10	Registered	goes to whitefield	11		Female	B+	indian	General	hindi	indian		mathri layout, shri sai niwas	khariar road , basant nager	army school	9	CBSE	56956518		Rakesh Shrivastav	Government Service	454665985652	rakeshshrivasta123@gmail.com	20K – 50K	Madhulika Shrivastav	Homemaker	846465996262	madhulika shrivastav	50K – 1L	Father	Self Employed	kdjfas;lkd	Class 10	A	Yes	whitefiled	Yes	\N	\N	\N	\N	ADM-2026-0001	2026-11-02	11	30	31	2026-11-02 11:33:55.163967	1	chemistryisnoteasy@gmail.com
Prashant	Saxena	2009-01-08				Class 11	Registered		12		Male	A+				India 	dnkdfm	dg																				Class 11	D				\N	\N	\N	\N	ADM-2026-0002	2026-11-02	12	34	\N	2026-11-02 12:37:46.615382	1	chemistryisnoteasy@gmail.com
shubham 	dkcji	2005-03-11				Class 10	Registered		13		Female																											Class 10	B				\N	\N	\N	\N	ADM-2026-0003	2026-11-02	13	35	\N	2026-11-02 12:38:51.661073	1	
abhay	dkdk	2026-11-11				Class 10	Registered		14		Male	B+	Hindu	General	Tamil	Indian		dkdjk	ekf	dkkd	10																	Class 10	D				\N	\N	\N	\N	ADM-2026-0004	2026-11-02	14	36	\N	2026-11-02 12:41:48.106775	1	
irmfoakf	kjcnie	2000-07-02				Class 10	Registered		15		Female	B+	jain	OBC	hindi	amercian		fghjkl	hjkl																			Class 10	E				\N	\N	\N	\N	ADM-2026-0005	2026-11-02	15	37	\N	2026-11-02 12:44:19.32581	1	cijkdjcj
\.


--
-- Data for Name: studentparentrelationship; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.studentparentrelationship (student_id, parent_user_id, relationship_type, id, school_id) FROM stdin;
11	31	Father	10	1
\.


--
-- Data for Name: studentprofile; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.studentprofile (user_id, admission_number, date_of_birth, guardian_name, classroom_id, section_id, id, gender, school_id) FROM stdin;
30	ADM-2026-0001	2000-11-24	Rakesh shrivastav	13	121	11	Female	1
34	ADM-2026-0002	2009-01-08		14	134	12	Male	1
35	ADM-2026-0003	2005-03-11		13	122	13	Female	1
36	ADM-2026-0004	2026-11-11		13	124	14	Male	1
37	ADM-2026-0005	2000-07-02		13	125	15	Female	1
\.


--
-- Data for Name: subject; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.subject (name, code, id, school_id) FROM stdin;
Mathematics	MATH	1	1
English	ENG	2	1
Hindi	HIN	3	1
Physics	PHY	4	1
Chemistry	CHEM	5	1
Biology	BIO	6	1
Computer Science	CS	7	1
Social Science	SST	8	1
History	HIS	9	1
Geography	GEO	10	1
Physical Education	PE	11	1
Art	ART	12	1
Music	MUS	13	1
Mathematics	MATH	14	2
English	ENG	15	2
Hindi	HIN	16	2
Physics	PHY	17	2
Chemistry	CHEM	18	2
Biology	BIO	19	2
Computer Science	CS	20	2
Social Science	SST	21	2
History	HIS	22	2
Geography	GEO	23	2
Physical Education	PE	24	2
Art	ART	25	2
Music	MUS	26	2
\.


--
-- Data for Name: supportticket; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.supportticket (subject, category, priority, status, reporter_user_id, assignee, created_at, updated_at, school_id, id) FROM stdin;
\.


--
-- Data for Name: syllabusprogress; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.syllabusprogress (section_id, subject_id, chapters_total, chapters_done, id, school_id, updated_at) FROM stdin;
\.


--
-- Data for Name: teacherassignment; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.teacherassignment (teacher_id, classroom_id, section_id, subject_id, id, school_id) FROM stdin;
\.


--
-- Data for Name: teacherreview; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.teacherreview (teacher_id, rating, reviewer_role, comment, school_id, id, created_at) FROM stdin;
\.


--
-- Data for Name: teachersubject; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.teachersubject (teacher_id, subject_id, id, school_id) FROM stdin;
14	11	4	1
\.


--
-- Data for Name: timetableperiod; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.timetableperiod (classroom_id, section_id, subject_id, teacher_id, day_of_week, start_time, end_time, room, id, school_id) FROM stdin;
\.


--
-- Data for Name: transportroute; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.transportroute (name, bus_id, driver, stops, students, status, school_id, id) FROM stdin;
\.


--
-- Data for Name: user; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public."user" (email, full_name, is_active, id, hashed_password, created_at, school_id) FROM stdin;
admin@abc	ABC School	t	1	$2b$12$X8kVc2uZiT3YQgs3ZUhpo.hGwFnb837gM8./aBFbnuICMrnOPCGA2	2026-10-21 11:44:42.444897	1
office@dps	Delhi Public School	t	2	$2b$12$SjnwqgICWhUmf2OFeUwbLOydW5yl6Ry/xOtDFcm1zB0Yrf0VdLjie	2026-10-21 11:44:42.684223	2
kckckcG@gmail.com	kailash chandra saxena	t	4	$2b$12$Pskyb5h6oJleUf5nWPKqdu878VKHEJU3u9qJP/DXYgA24R0m0b4a2	2026-10-28 16:50:37.917992	1
rakeshshrivastav@educonnect.com	Rakesh shrivastav	t	31	$2b$12$xrEGkF07xjQQ/CklqrHi1OZQyMNt0fxhO1TYQmUDXUioTCglNIQY.	2026-11-02 11:33:55.136312	1
chemistryisnoteasy@gmail.com	Tanya Saxena	t	30	$2b$12$Altip7/TEu0MluYg5GgekeBS1NOFdn8N5v8PfCu2xY2KdoJ0e/Qmi	2026-11-02 11:33:54.849852	1
tanyashrivastav123@gmail.com	Tanu shrivastav	t	32	$2b$12$LJHMxatoLPgoI6cuivyuwembyusv8lrPK7kQRDe.GKfjt0o83/gyu	2026-11-02 11:37:46.940237	1
chemistryisnoteasy.2@gmail.com	Prashant Saxena	t	34	$2b$12$2gCweiMNgT1whMgXXGTKZ.uI8SawSpcOw.HUs46fscUoKRIMqzNoO	2026-11-02 12:37:46.565228	1
stu.shubham.dkcji.10b@educonnect.com	shubham dkcji	t	35	$2b$12$q4Z1e2EaDo7Wo7OmmTBsMOf47JT83nutpiUlos2BjHQoGSkWf0fwm	2026-11-02 12:38:51.629125	1
stu.abhay.dkdk.10d@educonnect.com	abhay dkdk	t	36	$2b$12$vOiToPBAzLuhMXHbGKvV/OaKiuAbkFC0sabuB3jqxDNhs7AiH7PZ.	2026-11-02 12:41:48.074546	1
cijkdjcj@educonnect.com	irmfoakf kjcnie	t	37	$2b$12$L7mgihfff/iKx5RxZAUF6OK/Jl82xO90.9.0Tlt2KaN1ElQjtCVMe	2026-11-02 12:44:19.290672	1
\.


--
-- Data for Name: user_role; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.user_role (user_id, role_id, is_primary, assigned_at, id) FROM stdin;
4	14	t	2026-10-28 16:50:37.924529	2
34	13	t	2026-11-02 12:37:46.579826	70
35	13	t	2026-11-02 12:38:51.640548	71
36	13	t	2026-11-02 12:41:48.088645	72
37	13	t	2026-11-02 12:44:19.302501	73
1	15	t	2026-11-02 12:53:10.832761	80
2	15	t	2026-11-02 12:53:10.849577	81
30	13	t	2026-11-02 11:33:54.862597	47
31	14	t	2026-11-02 11:33:55.14552	48
32	6	t	2026-11-02 11:37:46.948677	49
\.


--
-- Name: admissionapplication_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.admissionapplication_id_seq', 15, true);


--
-- Name: attendanceauditlog_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.attendanceauditlog_id_seq', 1, false);


--
-- Name: attendancerecord_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.attendancerecord_id_seq', 2, true);


--
-- Name: bus_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.bus_id_seq', 1, false);


--
-- Name: chatfile_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.chatfile_id_seq', 1, false);


--
-- Name: chatmessage_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.chatmessage_id_seq', 1, false);


--
-- Name: chatthread_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.chatthread_id_seq', 6, true);


--
-- Name: classdiary_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.classdiary_id_seq', 1, false);


--
-- Name: classroom_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.classroom_id_seq', 15, true);


--
-- Name: classteacherassignment_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.classteacherassignment_id_seq', 1, true);


--
-- Name: copilotautomation_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.copilotautomation_id_seq', 1, false);


--
-- Name: copilotsuggestion_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.copilotsuggestion_id_seq', 1, false);


--
-- Name: dataquality_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.dataquality_id_seq', 1, false);


--
-- Name: educationreport_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.educationreport_id_seq', 1, false);


--
-- Name: employeesalary_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.employeesalary_id_seq', 7, true);


--
-- Name: exam_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.exam_id_seq', 1, true);


--
-- Name: examsource_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.examsource_id_seq', 1, false);


--
-- Name: feestructure_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.feestructure_id_seq', 1, true);


--
-- Name: feetransaction_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.feetransaction_id_seq', 1, true);


--
-- Name: gatewaystatus_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.gatewaystatus_id_seq', 1, false);


--
-- Name: generationjob_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.generationjob_id_seq', 1, false);


--
-- Name: hiringcandidate_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.hiringcandidate_id_seq', 1, true);


--
-- Name: homeworkassignment_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.homeworkassignment_id_seq', 1, true);


--
-- Name: homeworksubmission_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.homeworksubmission_id_seq', 1, false);


--
-- Name: impersonationlog_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.impersonationlog_id_seq', 1, false);


--
-- Name: leaverequest_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.leaverequest_id_seq', 1, false);


--
-- Name: librarybook_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.librarybook_id_seq', 1, false);


--
-- Name: libraryissue_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.libraryissue_id_seq', 1, false);


--
-- Name: marks_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.marks_id_seq', 1, true);


--
-- Name: meeting_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.meeting_id_seq', 1, false);


--
-- Name: notification_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.notification_id_seq', 1, false);


--
-- Name: palettecommand_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.palettecommand_id_seq', 1, false);


--
-- Name: paperdraft_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.paperdraft_id_seq', 1, false);


--
-- Name: permission_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.permission_id_seq', 143, true);


--
-- Name: questionusagelog_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.questionusagelog_id_seq', 1, false);


--
-- Name: reportcard_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.reportcard_id_seq', 1, false);


--
-- Name: role_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.role_id_seq', 15, true);


--
-- Name: rolepermission_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.rolepermission_id_seq', 903, true);


--
-- Name: salarypayment_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.salarypayment_id_seq', 1, false);


--
-- Name: school_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.school_id_seq', 2, true);


--
-- Name: section_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.section_id_seq', 150, true);


--
-- Name: securitylog_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.securitylog_id_seq', 1, false);


--
-- Name: staffprofile_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.staffprofile_id_seq', 15, true);


--
-- Name: studentparentrelationship_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.studentparentrelationship_id_seq', 10, true);


--
-- Name: studentprofile_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.studentprofile_id_seq', 15, true);


--
-- Name: subject_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.subject_id_seq', 26, true);


--
-- Name: supportticket_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.supportticket_id_seq', 1, false);


--
-- Name: syllabusprogress_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.syllabusprogress_id_seq', 1, true);


--
-- Name: teacherassignment_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.teacherassignment_id_seq', 1, false);


--
-- Name: teacherreview_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.teacherreview_id_seq', 1, false);


--
-- Name: teachersubject_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.teachersubject_id_seq', 4, true);


--
-- Name: timetableperiod_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.timetableperiod_id_seq', 1, true);


--
-- Name: transportroute_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.transportroute_id_seq', 1, false);


--
-- Name: user_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.user_id_seq', 37, true);


--
-- Name: user_role_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.user_role_id_seq', 81, true);


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
    ADD CONSTRAINT chatthreadparticipant_pkey PRIMARY KEY (thread_id, user_id);


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
-- Name: classteacherassignment classteacherassignment_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.classteacherassignment
    ADD CONSTRAINT classteacherassignment_pkey PRIMARY KEY (id);


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
-- Name: pipeline_hiring_table hiringcandidate_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.pipeline_hiring_table
    ADD CONSTRAINT hiringcandidate_pkey PRIMARY KEY (id);


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
-- Name: employee staffprofile_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.employee
    ADD CONSTRAINT staffprofile_pkey PRIMARY KEY (id);


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
-- Name: teacherassignment teacherassignment_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.teacherassignment
    ADD CONSTRAINT teacherassignment_pkey PRIMARY KEY (id);


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

CREATE UNIQUE INDEX ix_classroom_name ON public.classroom USING btree (name);


--
-- Name: ix_classteacherassignment_school_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_classteacherassignment_school_id ON public.classteacherassignment USING btree (school_id);


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
-- Name: ix_hiringcandidate_applied_for; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_hiringcandidate_applied_for ON public.pipeline_hiring_table USING btree (applied_for);


--
-- Name: ix_hiringcandidate_candidate_no; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_hiringcandidate_candidate_no ON public.pipeline_hiring_table USING btree (candidate_no);


--
-- Name: ix_hiringcandidate_emp_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_hiringcandidate_emp_id ON public.pipeline_hiring_table USING btree (emp_id);


--
-- Name: ix_hiringcandidate_school_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_hiringcandidate_school_id ON public.pipeline_hiring_table USING btree (school_id);


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
-- Name: ix_securitylog_school_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_securitylog_school_id ON public.securitylog USING btree (school_id);


--
-- Name: ix_staffprofile_aadhaar_no; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_staffprofile_aadhaar_no ON public.employee USING btree (aadhaar_no);


--
-- Name: ix_staffprofile_employee_code; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_staffprofile_employee_code ON public.employee USING btree (employee_code);


--
-- Name: ix_staffprofile_school_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_staffprofile_school_id ON public.employee USING btree (school_id);


--
-- Name: ix_staffprofile_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_staffprofile_user_id ON public.employee USING btree (user_id);


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
-- Name: ix_supportticket_school_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_supportticket_school_id ON public.supportticket USING btree (school_id);


--
-- Name: ix_syllabusprogress_school_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_syllabusprogress_school_id ON public.syllabusprogress USING btree (school_id);


--
-- Name: ix_teacherassignment_school_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_teacherassignment_school_id ON public.teacherassignment USING btree (school_id);


--
-- Name: ix_teacherreview_school_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_teacherreview_school_id ON public.teacherreview USING btree (school_id);


--
-- Name: ix_teachersubject_school_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_teachersubject_school_id ON public.teachersubject USING btree (school_id);


--
-- Name: ix_teachersubject_subject_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_teachersubject_subject_id ON public.teachersubject USING btree (subject_id);


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
-- Name: uq_subject_school_code; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX uq_subject_school_code ON public.subject USING btree (school_id, code);


--
-- Name: uq_subject_school_name; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX uq_subject_school_name ON public.subject USING btree (school_id, name);


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
-- Name: classteacherassignment classteacherassignment_classroom_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.classteacherassignment
    ADD CONSTRAINT classteacherassignment_classroom_id_fkey FOREIGN KEY (classroom_id) REFERENCES public.classroom(id);


--
-- Name: classteacherassignment classteacherassignment_school_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.classteacherassignment
    ADD CONSTRAINT classteacherassignment_school_id_fkey FOREIGN KEY (school_id) REFERENCES public.school(id);


--
-- Name: classteacherassignment classteacherassignment_section_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.classteacherassignment
    ADD CONSTRAINT classteacherassignment_section_id_fkey FOREIGN KEY (section_id) REFERENCES public.section(id);


--
-- Name: classteacherassignment classteacherassignment_teacher_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.classteacherassignment
    ADD CONSTRAINT classteacherassignment_teacher_id_fkey FOREIGN KEY (teacher_id) REFERENCES public.employee(id);


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
-- Name: examsource fk_examsource_replaces_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.examsource
    ADD CONSTRAINT fk_examsource_replaces_id FOREIGN KEY (replaces_id) REFERENCES public.examsource(id);


--
-- Name: pipeline_hiring_table fk_hiringcandidate_subject_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.pipeline_hiring_table
    ADD CONSTRAINT fk_hiringcandidate_subject_id FOREIGN KEY (subject_id) REFERENCES public.subject(id);


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
-- Name: pipeline_hiring_table hiringcandidate_school_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.pipeline_hiring_table
    ADD CONSTRAINT hiringcandidate_school_id_fkey FOREIGN KEY (school_id) REFERENCES public.school(id);


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
-- Name: section section_classroom_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.section
    ADD CONSTRAINT section_classroom_id_fkey FOREIGN KEY (classroom_id) REFERENCES public.classroom(id);


--
-- Name: securitylog securitylog_school_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.securitylog
    ADD CONSTRAINT securitylog_school_id_fkey FOREIGN KEY (school_id) REFERENCES public.school(id);


--
-- Name: employee staffprofile_school_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.employee
    ADD CONSTRAINT staffprofile_school_id_fkey FOREIGN KEY (school_id) REFERENCES public.school(id);


--
-- Name: employee staffprofile_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.employee
    ADD CONSTRAINT staffprofile_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user"(id);


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
-- Name: teacherassignment teacherassignment_classroom_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.teacherassignment
    ADD CONSTRAINT teacherassignment_classroom_id_fkey FOREIGN KEY (classroom_id) REFERENCES public.classroom(id);


--
-- Name: teacherassignment teacherassignment_school_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.teacherassignment
    ADD CONSTRAINT teacherassignment_school_id_fkey FOREIGN KEY (school_id) REFERENCES public.school(id);


--
-- Name: teacherassignment teacherassignment_section_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.teacherassignment
    ADD CONSTRAINT teacherassignment_section_id_fkey FOREIGN KEY (section_id) REFERENCES public.section(id);


--
-- Name: teacherassignment teacherassignment_subject_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.teacherassignment
    ADD CONSTRAINT teacherassignment_subject_id_fkey FOREIGN KEY (subject_id) REFERENCES public.subject(id);


--
-- Name: teacherassignment teacherassignment_teacher_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.teacherassignment
    ADD CONSTRAINT teacherassignment_teacher_id_fkey FOREIGN KEY (teacher_id) REFERENCES public.employee(id);


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

\unrestrict qcfJBE3wRNjLpKpLPWN5a1f9fJhqcaHHpaMyaYLwUcioTsu8WT2TB8NG1IX0BCu

