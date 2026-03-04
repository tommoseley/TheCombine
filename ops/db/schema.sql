-- Canonical schema dump from prod
-- Generated: 2026-03-04T20:01:02Z
-- Source: combine@the-combine-db.cyqzjxl9c9jd.us-east-1.rds.amazonaws.com

--
-- PostgreSQL database dump
--

\restrict Ls9d5hvykq8Wd98wnwcdonuwLYyrBTAVRqW8rHmR4MRG1JHGyQxndLaiwIonkpD

-- Dumped from database version 18.1
-- Dumped by pg_dump version 18.3 (Ubuntu 18.3-1.pgdg22.04+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: public; Type: SCHEMA; Schema: -; Owner: -
--

-- *not* creating schema, since initdb creates it


--
-- Name: btree_gin; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS btree_gin WITH SCHEMA public;


--
-- Name: uuid-ossp; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA public;


--
-- Name: document_lifecycle_state; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.document_lifecycle_state AS ENUM (
    'generating',
    'partial',
    'complete',
    'stale'
);


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


--
-- Name: auth_audit_log; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.auth_audit_log (
    log_id uuid NOT NULL,
    user_id uuid,
    event_type character varying(64) NOT NULL,
    provider_id character varying(32),
    ip_address inet,
    user_agent text,
    metadata jsonb,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: component_artifacts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.component_artifacts (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    component_id character varying(150) NOT NULL,
    schema_artifact_id uuid NOT NULL,
    schema_id character varying(100) NOT NULL,
    generation_guidance jsonb NOT NULL,
    view_bindings jsonb NOT NULL,
    status character varying(20) DEFAULT 'draft'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by character varying(100),
    accepted_at timestamp with time zone,
    CONSTRAINT ck_component_artifacts_status CHECK (((status)::text = ANY ((ARRAY['draft'::character varying, 'accepted'::character varying])::text[])))
);


--
-- Name: document_definitions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.document_definitions (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    document_def_id character varying(150) NOT NULL,
    document_schema_id uuid,
    prompt_header jsonb NOT NULL,
    sections jsonb NOT NULL,
    status character varying(20) DEFAULT 'draft'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by character varying(100),
    accepted_at timestamp with time zone,
    CONSTRAINT ck_document_definitions_status CHECK (((status)::text = ANY ((ARRAY['draft'::character varying, 'accepted'::character varying])::text[])))
);


--
-- Name: document_relations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.document_relations (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    from_document_id uuid NOT NULL,
    to_document_id uuid NOT NULL,
    relation_type character varying(50) NOT NULL,
    pinned_version integer,
    pinned_revision character varying(64),
    notes text,
    relation_metadata jsonb,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by character varying(200),
    CONSTRAINT no_self_reference CHECK ((from_document_id <> to_document_id))
);


--
-- Name: document_types; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.document_types (
    id uuid NOT NULL,
    doc_type_id character varying(100) NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    category character varying(100) NOT NULL,
    icon character varying(50),
    schema_definition jsonb,
    schema_version character varying(20) NOT NULL,
    builder_role character varying(50) NOT NULL,
    builder_task character varying(100) NOT NULL,
    system_prompt_id uuid,
    handler_id character varying(100) NOT NULL,
    required_inputs jsonb NOT NULL,
    optional_inputs jsonb NOT NULL,
    gating_rules jsonb NOT NULL,
    acceptance_required boolean NOT NULL,
    accepted_by_role character varying(64),
    cardinality character varying(20) NOT NULL,
    instance_key character varying(100),
    scope character varying(50) NOT NULL,
    display_order integer NOT NULL,
    view_docdef character varying(100),
    status_badges jsonb,
    primary_action jsonb,
    display_config jsonb,
    is_active boolean NOT NULL,
    version character varying(20) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by character varying(200),
    notes text
);


--
-- Name: documents; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.documents (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    space_type character varying(50) NOT NULL,
    space_id uuid NOT NULL,
    parent_document_id uuid,
    instance_id character varying(200),
    doc_type_id character varying(100) NOT NULL,
    version integer NOT NULL,
    revision_hash character varying(64),
    schema_bundle_sha256 character varying(100),
    is_latest boolean NOT NULL,
    title character varying(500) NOT NULL,
    summary text,
    content jsonb NOT NULL,
    status character varying(50) NOT NULL,
    is_stale boolean NOT NULL,
    lifecycle_state public.document_lifecycle_state NOT NULL,
    state_changed_at timestamp with time zone DEFAULT now() NOT NULL,
    accepted_at timestamp with time zone,
    accepted_by character varying(200),
    rejected_at timestamp with time zone,
    rejected_by character varying(200),
    rejection_reason text,
    created_by character varying(200),
    created_by_type character varying(50),
    builder_metadata jsonb,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    search_vector tsvector
);


--
-- Name: files; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.files (
    id uuid NOT NULL,
    file_path character varying(500) NOT NULL,
    content text,
    content_hash character varying(64),
    file_type character varying(50),
    size_bytes integer,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    search_vector tsvector
);


--
-- Name: fragment_artifacts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.fragment_artifacts (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    fragment_id character varying(100) NOT NULL,
    version character varying(20) DEFAULT '1.0'::character varying NOT NULL,
    schema_type_id character varying(100) NOT NULL,
    status character varying(20) DEFAULT 'draft'::character varying NOT NULL,
    fragment_markup text NOT NULL,
    sha256 character varying(64) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by character varying(100),
    updated_at timestamp with time zone,
    CONSTRAINT ck_fragment_artifacts_status CHECK (((status)::text = ANY ((ARRAY['draft'::character varying, 'accepted'::character varying, 'deprecated'::character varying])::text[])))
);


--
-- Name: fragment_bindings; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.fragment_bindings (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    schema_type_id character varying(100) NOT NULL,
    fragment_id character varying(100) NOT NULL,
    fragment_version character varying(20) NOT NULL,
    is_active boolean DEFAULT false NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by character varying(100)
);


--
-- Name: governance_outcomes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.governance_outcomes (
    id uuid NOT NULL,
    execution_id character varying(36) NOT NULL,
    document_id character varying(100) NOT NULL,
    document_type character varying(100) NOT NULL,
    workflow_id character varying(100) NOT NULL,
    thread_id character varying(36),
    gate_type character varying(50) NOT NULL,
    gate_outcome character varying(50) NOT NULL,
    terminal_outcome character varying(50) NOT NULL,
    ready_for character varying(100),
    routing_rationale text,
    options_offered jsonb,
    option_selected character varying(100),
    selection_method character varying(50),
    retry_count integer,
    circuit_breaker_active boolean NOT NULL,
    recorded_at timestamp with time zone DEFAULT now() NOT NULL,
    recorded_by character varying(100)
);


--
-- Name: link_intent_nonces; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.link_intent_nonces (
    nonce character varying(64) NOT NULL,
    user_id uuid NOT NULL,
    provider_id character varying(50) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    expires_at timestamp with time zone NOT NULL
);


--
-- Name: llm_content; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.llm_content (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    content_hash text NOT NULL,
    content_text text NOT NULL,
    content_size integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    accessed_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: llm_ledger_entries; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.llm_ledger_entries (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    thread_id uuid NOT NULL,
    work_item_id uuid,
    entry_type character varying(50) NOT NULL,
    payload jsonb NOT NULL,
    payload_hash character varying(64),
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: llm_run; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.llm_run (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    correlation_id uuid NOT NULL,
    project_id uuid,
    workflow_execution_id character varying(36),
    artifact_type text,
    role text NOT NULL,
    model_provider text NOT NULL,
    model_name text NOT NULL,
    prompt_id text NOT NULL,
    prompt_version text NOT NULL,
    effective_prompt_hash text NOT NULL,
    schema_version text,
    schema_id character varying(100),
    schema_bundle_hash character varying(64),
    status text NOT NULL,
    started_at timestamp with time zone NOT NULL,
    ended_at timestamp with time zone,
    input_tokens integer,
    output_tokens integer,
    total_tokens integer,
    cost_usd numeric(10,6),
    primary_error_code text,
    primary_error_message text,
    error_count integer DEFAULT 0 NOT NULL,
    metadata jsonb,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: llm_run_error; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.llm_run_error (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    llm_run_id uuid NOT NULL,
    sequence integer NOT NULL,
    stage text NOT NULL,
    severity text NOT NULL,
    error_code text,
    message text NOT NULL,
    details jsonb,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_llm_run_error_sequence_positive CHECK ((sequence > 0))
);


--
-- Name: llm_run_input_ref; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.llm_run_input_ref (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    llm_run_id uuid NOT NULL,
    kind text NOT NULL,
    content_ref text NOT NULL,
    content_hash text NOT NULL,
    content_redacted boolean DEFAULT false NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: llm_run_output_ref; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.llm_run_output_ref (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    llm_run_id uuid NOT NULL,
    kind text NOT NULL,
    content_ref text NOT NULL,
    content_hash text NOT NULL,
    parse_status text,
    validation_status text,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: llm_run_tool_call; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.llm_run_tool_call (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    llm_run_id uuid NOT NULL,
    sequence integer NOT NULL,
    tool_name text NOT NULL,
    started_at timestamp with time zone NOT NULL,
    ended_at timestamp with time zone,
    status text NOT NULL,
    input_ref text NOT NULL,
    output_ref text,
    error_ref text,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: llm_threads; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.llm_threads (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    kind character varying(100) NOT NULL,
    space_type character varying(50) NOT NULL,
    space_id uuid NOT NULL,
    target_ref jsonb NOT NULL,
    status character varying(20) NOT NULL,
    parent_thread_id uuid,
    idempotency_key character varying(255),
    created_by character varying(100),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    closed_at timestamp with time zone
);


--
-- Name: llm_work_items; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.llm_work_items (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    thread_id uuid NOT NULL,
    sequence integer NOT NULL,
    status character varying(20) NOT NULL,
    attempt integer NOT NULL,
    lock_scope character varying(255),
    not_before timestamp with time zone,
    error_code character varying(50),
    error_message text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    started_at timestamp with time zone,
    finished_at timestamp with time zone
);


--
-- Name: personal_access_tokens; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.personal_access_tokens (
    token_id uuid NOT NULL,
    user_id uuid NOT NULL,
    token_name character varying(128) NOT NULL,
    token_hash character varying(128) NOT NULL,
    token_display character varying(32) NOT NULL,
    key_id character varying(16) NOT NULL,
    last_used_at timestamp with time zone,
    expires_at timestamp with time zone,
    token_created_at timestamp with time zone NOT NULL,
    is_active boolean NOT NULL
);


--
-- Name: pgc_answers; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pgc_answers (
    id uuid NOT NULL,
    execution_id character varying(36) NOT NULL,
    workflow_id character varying(100) NOT NULL,
    project_id uuid NOT NULL,
    pgc_node_id character varying(100) NOT NULL,
    schema_ref character varying(255) NOT NULL,
    questions jsonb NOT NULL,
    answers jsonb NOT NULL,
    created_at timestamp without time zone
);


--
-- Name: project_audit; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.project_audit (
    id uuid NOT NULL,
    project_id uuid NOT NULL,
    actor_user_id uuid,
    action character varying NOT NULL,
    reason text,
    metadata jsonb,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: projects; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.projects (
    id uuid NOT NULL,
    project_id character varying(20) NOT NULL,
    name character varying(200) NOT NULL,
    description text,
    status character varying(50),
    icon character varying(32),
    owner_id uuid,
    organization_id uuid,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by character varying(100),
    archived_at timestamp with time zone,
    archived_by uuid,
    archived_reason text,
    deleted_at timestamp with time zone,
    deleted_by uuid,
    deleted_reason text,
    metadata jsonb
);


--
-- Name: role_prompts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.role_prompts (
    id character varying(64) NOT NULL,
    role_name character varying(64) NOT NULL,
    version character varying(16) NOT NULL,
    instructions text NOT NULL,
    expected_schema json,
    is_active boolean NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by character varying(128),
    notes text
);


--
-- Name: role_tasks; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.role_tasks (
    id uuid NOT NULL,
    role_id uuid NOT NULL,
    task_name character varying(100) NOT NULL,
    task_prompt text NOT NULL,
    expected_schema jsonb,
    progress_steps jsonb,
    is_active boolean NOT NULL,
    version character varying(16) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by character varying(128),
    notes text
);


--
-- Name: roles; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.roles (
    id uuid NOT NULL,
    name character varying(50) NOT NULL,
    identity_prompt text NOT NULL,
    description text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: schema_artifacts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.schema_artifacts (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    schema_id character varying(100) NOT NULL,
    version character varying(20) DEFAULT '1.0'::character varying NOT NULL,
    kind character varying(20) NOT NULL,
    status character varying(20) DEFAULT 'draft'::character varying NOT NULL,
    schema_json jsonb NOT NULL,
    sha256 character varying(64) NOT NULL,
    governance_refs jsonb,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by character varying(100),
    updated_at timestamp with time zone,
    CONSTRAINT ck_schema_artifacts_kind CHECK (((kind)::text = ANY ((ARRAY['type'::character varying, 'document'::character varying, 'envelope'::character varying])::text[]))),
    CONSTRAINT ck_schema_artifacts_status CHECK (((status)::text = ANY ((ARRAY['draft'::character varying, 'accepted'::character varying, 'deprecated'::character varying])::text[])))
);


--
-- Name: system_config; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.system_config (
    id uuid NOT NULL,
    key character varying(100) NOT NULL,
    value character varying(500) NOT NULL,
    description character varying(500),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: user_oauth_identities; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.user_oauth_identities (
    identity_id uuid NOT NULL,
    user_id uuid NOT NULL,
    provider_id character varying(32) NOT NULL,
    provider_user_id character varying(256) NOT NULL,
    provider_email character varying(320),
    email_verified boolean NOT NULL,
    provider_metadata jsonb,
    identity_created_at timestamp with time zone NOT NULL,
    last_used_at timestamp with time zone NOT NULL
);


--
-- Name: user_sessions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.user_sessions (
    session_id uuid NOT NULL,
    user_id uuid NOT NULL,
    session_token character varying(64) NOT NULL,
    csrf_token character varying(64) NOT NULL,
    ip_address inet,
    user_agent text,
    session_created_at timestamp with time zone NOT NULL,
    last_activity_at timestamp with time zone NOT NULL,
    expires_at timestamp with time zone NOT NULL
);


--
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users (
    user_id uuid NOT NULL,
    email character varying(320) NOT NULL,
    email_verified boolean NOT NULL,
    name character varying(256) NOT NULL,
    avatar_url character varying(2048),
    is_active boolean NOT NULL,
    user_created_at timestamp with time zone NOT NULL,
    user_updated_at timestamp with time zone NOT NULL,
    last_login_at timestamp with time zone
);


--
-- Name: workflow_executions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.workflow_executions (
    execution_id character varying(36) NOT NULL,
    document_id character varying(255),
    document_type character varying(100),
    workflow_id character varying(100),
    project_id uuid,
    user_id uuid,
    current_node_id character varying(100) NOT NULL,
    status character varying(20) NOT NULL,
    execution_log jsonb NOT NULL,
    retry_counts jsonb NOT NULL,
    gate_outcome character varying(50),
    terminal_outcome character varying(50),
    pending_user_input boolean NOT NULL,
    pending_prompt text,
    pending_choices jsonb,
    pending_user_input_payload jsonb,
    pending_user_input_schema_ref character varying(255),
    thread_id character varying(36),
    context_state jsonb
);


--
-- Name: workflow_instance_history; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.workflow_instance_history (
    id uuid NOT NULL,
    instance_id uuid NOT NULL,
    change_type character varying(50) NOT NULL,
    change_detail jsonb,
    changed_at timestamp with time zone DEFAULT now() NOT NULL,
    changed_by character varying(100)
);


--
-- Name: workflow_instances; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.workflow_instances (
    id uuid NOT NULL,
    project_id uuid NOT NULL,
    base_workflow_ref jsonb NOT NULL,
    effective_workflow jsonb NOT NULL,
    status character varying(50) DEFAULT 'active'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: ws_bug_fixes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.ws_bug_fixes (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    ws_execution_id uuid NOT NULL,
    scope_id character varying(100),
    description text NOT NULL,
    root_cause text NOT NULL,
    test_name character varying(200) NOT NULL,
    fix_summary text NOT NULL,
    files_modified jsonb,
    autonomous boolean DEFAULT false NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: ws_executions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.ws_executions (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    ws_id character varying(100) NOT NULL,
    wp_id character varying(100),
    scope_id character varying(100),
    executor character varying(50) NOT NULL,
    status character varying(20) NOT NULL,
    started_at timestamp with time zone NOT NULL,
    completed_at timestamp with time zone,
    duration_seconds integer,
    phase_metrics jsonb,
    test_metrics jsonb,
    file_metrics jsonb,
    rework_cycles integer DEFAULT 0 NOT NULL,
    llm_calls integer DEFAULT 0 NOT NULL,
    llm_tokens_in integer DEFAULT 0 NOT NULL,
    llm_tokens_out integer DEFAULT 0 NOT NULL,
    llm_cost_usd numeric(10,6),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_ws_exec_status CHECK (((status)::text = ANY ((ARRAY['STARTED'::character varying, 'COMPLETED'::character varying, 'FAILED'::character varying, 'HARD_STOP'::character varying, 'BLOCKED'::character varying])::text[])))
);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: auth_audit_log auth_audit_log_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_audit_log
    ADD CONSTRAINT auth_audit_log_pkey PRIMARY KEY (log_id);


--
-- Name: component_artifacts component_artifacts_component_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.component_artifacts
    ADD CONSTRAINT component_artifacts_component_id_key UNIQUE (component_id);


--
-- Name: component_artifacts component_artifacts_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.component_artifacts
    ADD CONSTRAINT component_artifacts_pkey PRIMARY KEY (id);


--
-- Name: document_definitions document_definitions_document_def_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_definitions
    ADD CONSTRAINT document_definitions_document_def_id_key UNIQUE (document_def_id);


--
-- Name: document_definitions document_definitions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_definitions
    ADD CONSTRAINT document_definitions_pkey PRIMARY KEY (id);


--
-- Name: document_relations document_relations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_relations
    ADD CONSTRAINT document_relations_pkey PRIMARY KEY (id);


--
-- Name: document_types document_types_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_types
    ADD CONSTRAINT document_types_pkey PRIMARY KEY (id);


--
-- Name: documents documents_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documents
    ADD CONSTRAINT documents_pkey PRIMARY KEY (id);


--
-- Name: files files_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.files
    ADD CONSTRAINT files_pkey PRIMARY KEY (id);


--
-- Name: fragment_artifacts fragment_artifacts_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fragment_artifacts
    ADD CONSTRAINT fragment_artifacts_pkey PRIMARY KEY (id);


--
-- Name: fragment_bindings fragment_bindings_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fragment_bindings
    ADD CONSTRAINT fragment_bindings_pkey PRIMARY KEY (id);


--
-- Name: governance_outcomes governance_outcomes_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.governance_outcomes
    ADD CONSTRAINT governance_outcomes_pkey PRIMARY KEY (id);


--
-- Name: link_intent_nonces link_intent_nonces_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.link_intent_nonces
    ADD CONSTRAINT link_intent_nonces_pkey PRIMARY KEY (nonce);


--
-- Name: llm_content llm_content_content_hash_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.llm_content
    ADD CONSTRAINT llm_content_content_hash_key UNIQUE (content_hash);


--
-- Name: llm_content llm_content_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.llm_content
    ADD CONSTRAINT llm_content_pkey PRIMARY KEY (id);


--
-- Name: llm_ledger_entries llm_ledger_entries_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.llm_ledger_entries
    ADD CONSTRAINT llm_ledger_entries_pkey PRIMARY KEY (id);


--
-- Name: llm_run_error llm_run_error_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.llm_run_error
    ADD CONSTRAINT llm_run_error_pkey PRIMARY KEY (id);


--
-- Name: llm_run_input_ref llm_run_input_ref_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.llm_run_input_ref
    ADD CONSTRAINT llm_run_input_ref_pkey PRIMARY KEY (id);


--
-- Name: llm_run_output_ref llm_run_output_ref_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.llm_run_output_ref
    ADD CONSTRAINT llm_run_output_ref_pkey PRIMARY KEY (id);


--
-- Name: llm_run llm_run_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.llm_run
    ADD CONSTRAINT llm_run_pkey PRIMARY KEY (id);


--
-- Name: llm_run_tool_call llm_run_tool_call_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.llm_run_tool_call
    ADD CONSTRAINT llm_run_tool_call_pkey PRIMARY KEY (id);


--
-- Name: llm_threads llm_threads_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.llm_threads
    ADD CONSTRAINT llm_threads_pkey PRIMARY KEY (id);


--
-- Name: llm_work_items llm_work_items_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.llm_work_items
    ADD CONSTRAINT llm_work_items_pkey PRIMARY KEY (id);


--
-- Name: user_oauth_identities oauth_provider_user_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_oauth_identities
    ADD CONSTRAINT oauth_provider_user_unique UNIQUE (provider_id, provider_user_id);


--
-- Name: personal_access_tokens personal_access_tokens_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.personal_access_tokens
    ADD CONSTRAINT personal_access_tokens_pkey PRIMARY KEY (token_id);


--
-- Name: pgc_answers pgc_answers_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pgc_answers
    ADD CONSTRAINT pgc_answers_pkey PRIMARY KEY (id);


--
-- Name: project_audit project_audit_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project_audit
    ADD CONSTRAINT project_audit_pkey PRIMARY KEY (id);


--
-- Name: projects projects_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.projects
    ADD CONSTRAINT projects_pkey PRIMARY KEY (id);


--
-- Name: role_prompts role_prompts_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.role_prompts
    ADD CONSTRAINT role_prompts_pkey PRIMARY KEY (id);


--
-- Name: role_tasks role_tasks_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.role_tasks
    ADD CONSTRAINT role_tasks_pkey PRIMARY KEY (id);


--
-- Name: roles roles_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.roles
    ADD CONSTRAINT roles_pkey PRIMARY KEY (id);


--
-- Name: schema_artifacts schema_artifacts_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.schema_artifacts
    ADD CONSTRAINT schema_artifacts_pkey PRIMARY KEY (id);


--
-- Name: system_config system_config_key_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.system_config
    ADD CONSTRAINT system_config_key_key UNIQUE (key);


--
-- Name: system_config system_config_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.system_config
    ADD CONSTRAINT system_config_pkey PRIMARY KEY (id);


--
-- Name: document_relations unique_relation; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_relations
    ADD CONSTRAINT unique_relation UNIQUE (from_document_id, to_document_id, relation_type);


--
-- Name: llm_work_items uq_work_item_thread_sequence; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.llm_work_items
    ADD CONSTRAINT uq_work_item_thread_sequence UNIQUE (thread_id, sequence);


--
-- Name: user_oauth_identities user_oauth_identities_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_oauth_identities
    ADD CONSTRAINT user_oauth_identities_pkey PRIMARY KEY (identity_id);


--
-- Name: user_sessions user_sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_sessions
    ADD CONSTRAINT user_sessions_pkey PRIMARY KEY (session_id);


--
-- Name: user_sessions user_sessions_session_token_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_sessions
    ADD CONSTRAINT user_sessions_session_token_unique UNIQUE (session_token);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (user_id);


--
-- Name: workflow_executions workflow_executions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workflow_executions
    ADD CONSTRAINT workflow_executions_pkey PRIMARY KEY (execution_id);


--
-- Name: workflow_instance_history workflow_instance_history_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workflow_instance_history
    ADD CONSTRAINT workflow_instance_history_pkey PRIMARY KEY (id);


--
-- Name: workflow_instances workflow_instances_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workflow_instances
    ADD CONSTRAINT workflow_instances_pkey PRIMARY KEY (id);


--
-- Name: workflow_instances workflow_instances_project_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workflow_instances
    ADD CONSTRAINT workflow_instances_project_id_key UNIQUE (project_id);


--
-- Name: ws_bug_fixes ws_bug_fixes_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ws_bug_fixes
    ADD CONSTRAINT ws_bug_fixes_pkey PRIMARY KEY (id);


--
-- Name: ws_executions ws_executions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ws_executions
    ADD CONSTRAINT ws_executions_pkey PRIMARY KEY (id);


--
-- Name: idx_auth_log_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_auth_log_created ON public.auth_audit_log USING btree (created_at);


--
-- Name: idx_auth_log_event; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_auth_log_event ON public.auth_audit_log USING btree (event_type);


--
-- Name: idx_auth_log_user; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_auth_log_user ON public.auth_audit_log USING btree (user_id);


--
-- Name: idx_document_types_acceptance_required; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_document_types_acceptance_required ON public.document_types USING btree (acceptance_required) WHERE (acceptance_required = true);


--
-- Name: idx_document_types_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_document_types_active ON public.document_types USING btree (is_active);


--
-- Name: idx_document_types_builder; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_document_types_builder ON public.document_types USING btree (builder_role, builder_task);


--
-- Name: idx_document_types_category; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_document_types_category ON public.document_types USING btree (category);


--
-- Name: idx_document_types_scope; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_document_types_scope ON public.document_types USING btree (scope);


--
-- Name: idx_documents_acceptance; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_documents_acceptance ON public.documents USING btree (accepted_at, rejected_at) WHERE (is_latest = true);


--
-- Name: idx_documents_instance_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_documents_instance_id ON public.documents USING btree (instance_id) WHERE (instance_id IS NOT NULL);


--
-- Name: idx_documents_latest_multi; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX idx_documents_latest_multi ON public.documents USING btree (space_type, space_id, doc_type_id, instance_id) WHERE ((is_latest = true) AND (instance_id IS NOT NULL));


--
-- Name: idx_documents_latest_single; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX idx_documents_latest_single ON public.documents USING btree (space_type, space_id, doc_type_id) WHERE ((is_latest = true) AND (instance_id IS NULL));


--
-- Name: idx_documents_search; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_documents_search ON public.documents USING gin (search_vector);


--
-- Name: idx_documents_space; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_documents_space ON public.documents USING btree (space_type, space_id);


--
-- Name: idx_files_hash; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_files_hash ON public.files USING btree (content_hash);


--
-- Name: idx_files_path; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_files_path ON public.files USING btree (file_path);


--
-- Name: idx_files_search; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_files_search ON public.files USING gin (search_vector);


--
-- Name: idx_files_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_files_type ON public.files USING btree (file_type);


--
-- Name: idx_link_nonces_expires; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_link_nonces_expires ON public.link_intent_nonces USING btree (expires_at);


--
-- Name: idx_link_nonces_user; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_link_nonces_user ON public.link_intent_nonces USING btree (user_id);


--
-- Name: idx_llm_content_accessed; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_llm_content_accessed ON public.llm_content USING btree (accessed_at);


--
-- Name: idx_llm_content_hash; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_llm_content_hash ON public.llm_content USING btree (content_hash);


--
-- Name: idx_llm_error_run; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_llm_error_run ON public.llm_run_error USING btree (llm_run_id);


--
-- Name: idx_llm_error_severity; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_llm_error_severity ON public.llm_run_error USING btree (severity);


--
-- Name: idx_llm_error_stage; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_llm_error_stage ON public.llm_run_error USING btree (stage);


--
-- Name: idx_llm_input_ref_kind; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_llm_input_ref_kind ON public.llm_run_input_ref USING btree (llm_run_id, kind);


--
-- Name: idx_llm_input_ref_run; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_llm_input_ref_run ON public.llm_run_input_ref USING btree (llm_run_id);


--
-- Name: idx_llm_output_ref_kind; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_llm_output_ref_kind ON public.llm_run_output_ref USING btree (llm_run_id, kind);


--
-- Name: idx_llm_output_ref_run; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_llm_output_ref_run ON public.llm_run_output_ref USING btree (llm_run_id);


--
-- Name: idx_llm_run_correlation; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_llm_run_correlation ON public.llm_run USING btree (correlation_id);


--
-- Name: idx_llm_run_project_time; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_llm_run_project_time ON public.llm_run USING btree (project_id, started_at DESC) WHERE (project_id IS NOT NULL);


--
-- Name: idx_llm_run_role_time; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_llm_run_role_time ON public.llm_run USING btree (role, started_at DESC);


--
-- Name: idx_llm_run_started; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_llm_run_started ON public.llm_run USING btree (started_at DESC);


--
-- Name: idx_llm_run_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_llm_run_status ON public.llm_run USING btree (status);


--
-- Name: idx_llm_tool_call_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_llm_tool_call_name ON public.llm_run_tool_call USING btree (tool_name);


--
-- Name: idx_llm_tool_call_run; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_llm_tool_call_run ON public.llm_run_tool_call USING btree (llm_run_id);


--
-- Name: idx_llm_tool_call_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_llm_tool_call_status ON public.llm_run_tool_call USING btree (status);


--
-- Name: idx_oauth_provider; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_oauth_provider ON public.user_oauth_identities USING btree (provider_id, provider_user_id);


--
-- Name: idx_oauth_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_oauth_user_id ON public.user_oauth_identities USING btree (user_id);


--
-- Name: idx_pat_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_pat_active ON public.personal_access_tokens USING btree (is_active) WHERE (is_active = true);


--
-- Name: idx_pat_token_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_pat_token_id ON public.personal_access_tokens USING btree (token_id);


--
-- Name: idx_pat_user; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_pat_user ON public.personal_access_tokens USING btree (user_id);


--
-- Name: idx_projects_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_projects_created_at ON public.projects USING btree (created_at);


--
-- Name: idx_projects_deleted_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_projects_deleted_at ON public.projects USING btree (deleted_at);


--
-- Name: idx_projects_owner_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_projects_owner_id ON public.projects USING btree (owner_id);


--
-- Name: idx_projects_project_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_projects_project_id ON public.projects USING btree (project_id);


--
-- Name: idx_projects_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_projects_status ON public.projects USING btree (status);


--
-- Name: idx_relations_from; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_relations_from ON public.document_relations USING btree (from_document_id);


--
-- Name: idx_relations_to; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_relations_to ON public.document_relations USING btree (to_document_id);


--
-- Name: idx_relations_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_relations_type ON public.document_relations USING btree (relation_type);


--
-- Name: idx_role_prompts_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_role_prompts_active ON public.role_prompts USING btree (is_active);


--
-- Name: idx_role_prompts_role_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_role_prompts_role_name ON public.role_prompts USING btree (role_name);


--
-- Name: idx_role_prompts_version; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_role_prompts_version ON public.role_prompts USING btree (role_name, version);


--
-- Name: idx_session_expires; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_session_expires ON public.user_sessions USING btree (expires_at);


--
-- Name: idx_session_token; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_session_token ON public.user_sessions USING btree (session_token);


--
-- Name: idx_session_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_session_user_id ON public.user_sessions USING btree (user_id);


--
-- Name: idx_users_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_users_active ON public.users USING btree (is_active) WHERE (is_active = true);


--
-- Name: idx_users_email; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_users_email ON public.users USING btree (email);


--
-- Name: idx_ws_bugfix_exec; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ws_bugfix_exec ON public.ws_bug_fixes USING btree (ws_execution_id);


--
-- Name: idx_ws_exec_started; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ws_exec_started ON public.ws_executions USING btree (started_at DESC);


--
-- Name: idx_ws_exec_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ws_exec_status ON public.ws_executions USING btree (status);


--
-- Name: idx_ws_exec_wp_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ws_exec_wp_id ON public.ws_executions USING btree (wp_id, started_at DESC) WHERE (wp_id IS NOT NULL);


--
-- Name: idx_ws_exec_ws_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ws_exec_ws_id ON public.ws_executions USING btree (ws_id, started_at DESC);


--
-- Name: ix_component_artifacts_accepted_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_component_artifacts_accepted_at ON public.component_artifacts USING btree (accepted_at);


--
-- Name: ix_component_artifacts_schema_artifact_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_component_artifacts_schema_artifact_id ON public.component_artifacts USING btree (schema_artifact_id);


--
-- Name: ix_component_artifacts_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_component_artifacts_status ON public.component_artifacts USING btree (status);


--
-- Name: ix_document_definitions_accepted_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_document_definitions_accepted_at ON public.document_definitions USING btree (accepted_at);


--
-- Name: ix_document_definitions_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_document_definitions_status ON public.document_definitions USING btree (status);


--
-- Name: ix_document_relations_from_document_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_document_relations_from_document_id ON public.document_relations USING btree (from_document_id);


--
-- Name: ix_document_relations_relation_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_document_relations_relation_type ON public.document_relations USING btree (relation_type);


--
-- Name: ix_document_relations_to_document_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_document_relations_to_document_id ON public.document_relations USING btree (to_document_id);


--
-- Name: ix_document_types_category; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_document_types_category ON public.document_types USING btree (category);


--
-- Name: ix_document_types_doc_type_id; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_document_types_doc_type_id ON public.document_types USING btree (doc_type_id);


--
-- Name: ix_documents_doc_type_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_documents_doc_type_id ON public.documents USING btree (doc_type_id);


--
-- Name: ix_documents_parent_document_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_documents_parent_document_id ON public.documents USING btree (parent_document_id);


--
-- Name: ix_documents_space_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_documents_space_id ON public.documents USING btree (space_id);


--
-- Name: ix_documents_space_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_documents_space_type ON public.documents USING btree (space_type);


--
-- Name: ix_files_content_hash; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_files_content_hash ON public.files USING btree (content_hash);


--
-- Name: ix_files_file_path; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_files_file_path ON public.files USING btree (file_path);


--
-- Name: ix_files_file_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_files_file_type ON public.files USING btree (file_type);


--
-- Name: ix_fragment_artifacts_fragment_id_version; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_fragment_artifacts_fragment_id_version ON public.fragment_artifacts USING btree (fragment_id, version);


--
-- Name: ix_fragment_artifacts_schema_type_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_fragment_artifacts_schema_type_id ON public.fragment_artifacts USING btree (schema_type_id);


--
-- Name: ix_fragment_artifacts_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_fragment_artifacts_status ON public.fragment_artifacts USING btree (status);


--
-- Name: ix_fragment_bindings_fragment_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_fragment_bindings_fragment_id ON public.fragment_bindings USING btree (fragment_id);


--
-- Name: ix_fragment_bindings_unique_active; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_fragment_bindings_unique_active ON public.fragment_bindings USING btree (schema_type_id) WHERE (is_active = true);


--
-- Name: ix_governance_outcomes_execution_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_governance_outcomes_execution_id ON public.governance_outcomes USING btree (execution_id);


--
-- Name: ix_llm_run_correlation_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_llm_run_correlation_id ON public.llm_run USING btree (correlation_id);


--
-- Name: ix_llm_run_workflow_execution_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_llm_run_workflow_execution_id ON public.llm_run USING btree (workflow_execution_id);


--
-- Name: ix_pgc_answers_execution_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_pgc_answers_execution_id ON public.pgc_answers USING btree (execution_id);


--
-- Name: ix_projects_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_projects_created_at ON public.projects USING btree (created_at);


--
-- Name: ix_projects_owner_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_projects_owner_id ON public.projects USING btree (owner_id);


--
-- Name: ix_projects_project_id; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_projects_project_id ON public.projects USING btree (project_id);


--
-- Name: ix_projects_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_projects_status ON public.projects USING btree (status);


--
-- Name: ix_role_prompts_is_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_role_prompts_is_active ON public.role_prompts USING btree (is_active);


--
-- Name: ix_role_prompts_role_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_role_prompts_role_name ON public.role_prompts USING btree (role_name);


--
-- Name: ix_roles_name; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_roles_name ON public.roles USING btree (name);


--
-- Name: ix_schema_artifacts_kind; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_schema_artifacts_kind ON public.schema_artifacts USING btree (kind);


--
-- Name: ix_schema_artifacts_schema_id_version; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_schema_artifacts_schema_id_version ON public.schema_artifacts USING btree (schema_id, version);


--
-- Name: ix_schema_artifacts_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_schema_artifacts_status ON public.schema_artifacts USING btree (status);


--
-- Name: ix_user_sessions_session_token; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_user_sessions_session_token ON public.user_sessions USING btree (session_token);


--
-- Name: ix_users_email; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_users_email ON public.users USING btree (email);


--
-- Name: ix_users_is_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_users_is_active ON public.users USING btree (is_active);


--
-- Name: auth_audit_log auth_audit_log_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_audit_log
    ADD CONSTRAINT auth_audit_log_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE SET NULL;


--
-- Name: component_artifacts component_artifacts_schema_artifact_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.component_artifacts
    ADD CONSTRAINT component_artifacts_schema_artifact_id_fkey FOREIGN KEY (schema_artifact_id) REFERENCES public.schema_artifacts(id);


--
-- Name: document_definitions document_definitions_document_schema_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_definitions
    ADD CONSTRAINT document_definitions_document_schema_id_fkey FOREIGN KEY (document_schema_id) REFERENCES public.schema_artifacts(id);


--
-- Name: document_relations document_relations_from_document_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_relations
    ADD CONSTRAINT document_relations_from_document_id_fkey FOREIGN KEY (from_document_id) REFERENCES public.documents(id) ON DELETE CASCADE;


--
-- Name: document_relations document_relations_to_document_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_relations
    ADD CONSTRAINT document_relations_to_document_id_fkey FOREIGN KEY (to_document_id) REFERENCES public.documents(id) ON DELETE CASCADE;


--
-- Name: document_types document_types_system_prompt_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_types
    ADD CONSTRAINT document_types_system_prompt_id_fkey FOREIGN KEY (system_prompt_id) REFERENCES public.role_tasks(id);


--
-- Name: documents documents_doc_type_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documents
    ADD CONSTRAINT documents_doc_type_id_fkey FOREIGN KEY (doc_type_id) REFERENCES public.document_types(doc_type_id) ON DELETE RESTRICT;


--
-- Name: documents documents_parent_document_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documents
    ADD CONSTRAINT documents_parent_document_id_fkey FOREIGN KEY (parent_document_id) REFERENCES public.documents(id) ON DELETE RESTRICT;


--
-- Name: link_intent_nonces link_intent_nonces_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.link_intent_nonces
    ADD CONSTRAINT link_intent_nonces_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- Name: llm_ledger_entries llm_ledger_entries_thread_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.llm_ledger_entries
    ADD CONSTRAINT llm_ledger_entries_thread_id_fkey FOREIGN KEY (thread_id) REFERENCES public.llm_threads(id);


--
-- Name: llm_ledger_entries llm_ledger_entries_work_item_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.llm_ledger_entries
    ADD CONSTRAINT llm_ledger_entries_work_item_id_fkey FOREIGN KEY (work_item_id) REFERENCES public.llm_work_items(id);


--
-- Name: llm_run_error llm_run_error_llm_run_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.llm_run_error
    ADD CONSTRAINT llm_run_error_llm_run_id_fkey FOREIGN KEY (llm_run_id) REFERENCES public.llm_run(id) ON DELETE CASCADE;


--
-- Name: llm_run_input_ref llm_run_input_ref_llm_run_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.llm_run_input_ref
    ADD CONSTRAINT llm_run_input_ref_llm_run_id_fkey FOREIGN KEY (llm_run_id) REFERENCES public.llm_run(id) ON DELETE CASCADE;


--
-- Name: llm_run_output_ref llm_run_output_ref_llm_run_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.llm_run_output_ref
    ADD CONSTRAINT llm_run_output_ref_llm_run_id_fkey FOREIGN KEY (llm_run_id) REFERENCES public.llm_run(id) ON DELETE CASCADE;


--
-- Name: llm_run llm_run_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.llm_run
    ADD CONSTRAINT llm_run_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id) ON DELETE SET NULL;


--
-- Name: llm_run_tool_call llm_run_tool_call_llm_run_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.llm_run_tool_call
    ADD CONSTRAINT llm_run_tool_call_llm_run_id_fkey FOREIGN KEY (llm_run_id) REFERENCES public.llm_run(id) ON DELETE CASCADE;


--
-- Name: llm_threads llm_threads_parent_thread_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.llm_threads
    ADD CONSTRAINT llm_threads_parent_thread_id_fkey FOREIGN KEY (parent_thread_id) REFERENCES public.llm_threads(id);


--
-- Name: llm_work_items llm_work_items_thread_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.llm_work_items
    ADD CONSTRAINT llm_work_items_thread_id_fkey FOREIGN KEY (thread_id) REFERENCES public.llm_threads(id);


--
-- Name: personal_access_tokens personal_access_tokens_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.personal_access_tokens
    ADD CONSTRAINT personal_access_tokens_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- Name: pgc_answers pgc_answers_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pgc_answers
    ADD CONSTRAINT pgc_answers_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id);


--
-- Name: project_audit project_audit_actor_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project_audit
    ADD CONSTRAINT project_audit_actor_user_id_fkey FOREIGN KEY (actor_user_id) REFERENCES public.users(user_id) ON DELETE SET NULL;


--
-- Name: project_audit project_audit_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project_audit
    ADD CONSTRAINT project_audit_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id) ON DELETE RESTRICT;


--
-- Name: role_tasks role_tasks_role_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.role_tasks
    ADD CONSTRAINT role_tasks_role_id_fkey FOREIGN KEY (role_id) REFERENCES public.roles(id) ON DELETE CASCADE;


--
-- Name: user_oauth_identities user_oauth_identities_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_oauth_identities
    ADD CONSTRAINT user_oauth_identities_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- Name: user_sessions user_sessions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_sessions
    ADD CONSTRAINT user_sessions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- Name: workflow_executions workflow_executions_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workflow_executions
    ADD CONSTRAINT workflow_executions_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id) ON DELETE CASCADE;


--
-- Name: workflow_executions workflow_executions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workflow_executions
    ADD CONSTRAINT workflow_executions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE SET NULL;


--
-- Name: workflow_instance_history workflow_instance_history_instance_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workflow_instance_history
    ADD CONSTRAINT workflow_instance_history_instance_id_fkey FOREIGN KEY (instance_id) REFERENCES public.workflow_instances(id) ON DELETE CASCADE;


--
-- Name: workflow_instances workflow_instances_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workflow_instances
    ADD CONSTRAINT workflow_instances_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id) ON DELETE CASCADE;


--
-- Name: ws_bug_fixes ws_bug_fixes_ws_execution_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ws_bug_fixes
    ADD CONSTRAINT ws_bug_fixes_ws_execution_id_fkey FOREIGN KEY (ws_execution_id) REFERENCES public.ws_executions(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict Ls9d5hvykq8Wd98wnwcdonuwLYyrBTAVRqW8rHmR4MRG1JHGyQxndLaiwIonkpD


-- Seed data: alembic_version + document_types (required for bootstrap)
--
-- PostgreSQL database dump
--

\restrict pOdUTQpXZdoOzuF2M8CbZ3uIcZb3OihwlQoG734AT2xjlGEZB5QVxMBsBkIRlgH

-- Dumped from database version 18.1
-- Dumped by pg_dump version 18.3 (Ubuntu 18.3-1.pgdg22.04+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Data for Name: alembic_version; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.alembic_version (version_num) FROM stdin;
20260301_001
\.


--
-- Data for Name: document_types; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.document_types (id, doc_type_id, name, description, category, icon, schema_definition, schema_version, builder_role, builder_task, system_prompt_id, handler_id, required_inputs, optional_inputs, gating_rules, acceptance_required, accepted_by_role, cardinality, instance_key, scope, display_order, view_docdef, status_badges, primary_action, display_config, is_active, version, created_at, updated_at, created_by, notes) FROM stdin;
498988d4-b3f8-45e4-90fe-a6ba5878c509	concierge_intake	Concierge Intake	Structured intake document produced by the Concierge workflow. Contains synthesized intent, constraints, and gate outcomes.	intake	message-circle	{"$ref": "schema:ConciergeIntakeDocumentV1"}	1.0	concierge	intake	\N	concierge_intake	[]	[]	{}	f	\N	single	\N	project	5	ConciergeIntakeView	\N	\N	\N	t	1.0	2026-02-20 15:42:05.510815+00	2026-02-20 15:42:05.510815+00	\N	\N
f7d91b34-bf37-44ac-8877-aaaacaa0bd80	project_discovery	Project Discovery	Early architectural discovery performed before PM decomposition. Surfaces critical questions, identifies constraints and risks, proposes candidate directions, and establishes guardrails.	architecture	search	{"type": "object", "required": ["project_name", "preliminary_summary"], "properties": {"unknowns": {"type": "array", "items": {"type": "object"}}, "project_name": {"type": "string"}, "mvp_guardrails": {"type": "array", "items": {"type": "object"}}, "blocking_questions": {"type": "array", "items": {"type": "object"}}, "preliminary_summary": {"type": "string"}, "early_decision_points": {"type": "array", "items": {"type": "object"}}, "architectural_directions": {"type": "array", "items": {"type": "object"}}}}	1.0	architect	preliminary	\N	project_discovery	[]	[]	{}	f	\N	single	\N	project	10	ProjectDiscovery	\N	\N	\N	t	1.0	2026-02-20 15:42:05.510815+00	2026-02-20 15:42:05.510815+00	\N	\N
c5ca4400-dca6-43d4-a13b-bf8b61ad1b13	technical_architecture	Technical Architecture	Comprehensive technical architecture including components, interfaces, data models, workflows, and quality attributes. Built after primary implementation plan, informs final planning.	architecture	landmark	{"type": "object", "required": ["architecture_summary", "components"], "properties": {"risks": {"type": "array"}, "workflows": {"type": "array"}, "components": {"type": "array", "items": {"type": "object", "required": ["name", "purpose"], "properties": {"name": {"type": "string"}, "purpose": {"type": "string"}, "interfaces": {"type": "array"}, "technology": {"type": "string"}}}}, "data_models": {"type": "array"}, "api_interfaces": {"type": "array"}, "quality_attributes": {"type": "object"}, "architecture_summary": {"type": "object", "properties": {"style": {"type": "string"}, "title": {"type": "string"}, "key_decisions": {"type": "array", "items": {"type": "string"}}}}}}	1.0	architect	technical_architecture	\N	technical_architecture	["project_discovery", "implementation_plan_primary"]	[]	{}	f	\N	single	\N	project	30	TechnicalArchitectureView	\N	\N	\N	t	1.0	2026-02-20 15:42:05.510815+00	2026-02-20 15:42:05.510815+00	\N	\N
d65626af-ab20-460d-b184-777953e1f9c2	implementation_plan_primary	Implementation Plan (Primary)	Preliminary implementation plan produced before technical architecture. Contains Work Package candidates that inform architectural decisions. WP candidates are not yet commitments - they become Work Packages after architecture review via IPF reconciliation.	planning	map	{"type": "object", "required": ["work_package_candidates"], "properties": {"risks_overview": {"type": "array"}, "epic_set_summary": {"type": "object", "properties": {"out_of_scope": {"type": "array", "items": {"type": "string"}}, "mvp_definition": {"type": "string"}, "overall_intent": {"type": "string"}, "key_constraints": {"type": "array", "items": {"type": "string"}}}}, "work_package_candidates": {"type": "array", "items": {"type": "object", "required": ["candidate_id", "title", "rationale", "scope_in", "scope_out", "dependencies", "definition_of_done"], "properties": {"title": {"type": "string"}, "scope_in": {"type": "array", "items": {"type": "string"}}, "rationale": {"type": "string"}, "scope_out": {"type": "array", "items": {"type": "string"}}, "candidate_id": {"type": "string"}, "dependencies": {"type": "array", "items": {"type": "string"}}, "governance_notes": {"type": "array", "items": {"type": "string"}}, "definition_of_done": {"type": "array", "items": {"type": "string"}}}}}, "recommendations_for_architecture": {"type": "array", "items": {"type": "string"}}}}	1.0	pm	preliminary_planning	\N	implementation_plan_primary	["project_discovery"]	[]	{}	f	\N	single	\N	project	25	ImplementationPlanPrimaryView	\N	\N	\N	t	1.0	2026-02-20 15:42:05.510815+00	2026-02-20 15:42:05.510815+00	\N	\N
075cb5f3-1c47-4936-8804-4c287ea45e2d	implementation_plan	Implementation Plan	Final implementation plan produced after technical architecture review. Reconciles WP candidates into committed Work Packages with governance pinning. Creating this document spawns individual Work Package documents.	planning	git-branch	{"type": "object", "required": ["plan_summary", "work_packages", "candidate_reconciliation"], "properties": {"plan_summary": {"type": "object", "properties": {"mvp_definition": {"type": "string"}, "overall_intent": {"type": "string"}, "key_constraints": {"type": "array", "items": {"type": "string"}}, "sequencing_rationale": {"type": "string"}}}, "risk_summary": {"type": "array"}, "work_packages": {"type": "array", "items": {"type": "object", "required": ["wp_id", "title", "rationale", "scope_in", "scope_out", "dependencies", "definition_of_done", "governance_pins"], "properties": {"title": {"type": "string"}, "wp_id": {"type": "string"}, "scope_in": {"type": "array", "items": {"type": "string"}}, "rationale": {"type": "string"}, "scope_out": {"type": "array", "items": {"type": "string"}}, "dependencies": {"type": "array"}, "transformation": {"enum": ["kept", "split", "merged", "added"], "type": "string"}, "governance_pins": {"type": "object", "properties": {"adr_refs": {"type": "array", "items": {"type": "string"}}, "policy_refs": {"type": "array", "items": {"type": "string"}}, "ta_version_id": {"type": "string"}}}, "definition_of_done": {"type": "array", "items": {"type": "string"}}, "source_candidate_ids": {"type": "array", "items": {"type": "string"}}, "transformation_notes": {"type": "string"}}}}, "cross_cutting_concerns": {"type": "array", "items": {"type": "string"}}, "candidate_reconciliation": {"type": "array", "items": {"type": "object", "required": ["candidate_id", "outcome", "resulting_wp_ids", "notes"], "properties": {"notes": {"type": "string"}, "outcome": {"enum": ["kept", "split", "merged", "dropped"], "type": "string"}, "candidate_id": {"type": "string"}, "resulting_wp_ids": {"type": "array", "items": {"type": "string"}}}}}}}	1.0	pm	implementation_planning	\N	implementation_plan	["implementation_plan_primary", "technical_architecture"]	[]	{}	f	\N	single	\N	project	35	ImplementationPlanView	\N	\N	\N	t	1.0	2026-02-20 15:42:05.510815+00	2026-02-20 15:42:05.510815+00	\N	\N
09316183-b19e-4009-9a0a-33f6410c85c3	work_package	Work Package	Unit of planned work replacing the Epic/Feature ontology. Created by IPF reconciliation. Tracks state, dependencies, governance pins, and child Work Statement references.	planning	package	{"type": "object", "required": ["wp_id", "title", "rationale", "scope_in", "scope_out", "dependencies", "definition_of_done", "state", "ws_child_refs", "governance_pins"], "properties": {"state": {"enum": ["PLANNED", "READY", "IN_PROGRESS", "AWAITING_GATE", "DONE"], "type": "string"}, "title": {"type": "string"}, "wp_id": {"type": "string"}, "scope_in": {"type": "array", "items": {"type": "string"}}, "rationale": {"type": "string"}, "scope_out": {"type": "array", "items": {"type": "string"}}, "dependencies": {"type": "array", "items": {"type": "object", "properties": {"wp_id": {"type": "string"}, "dependency_type": {"type": "string"}}}}, "ws_child_refs": {"type": "array", "items": {"type": "string"}}, "governance_pins": {"type": "object", "properties": {"adr_refs": {"type": "array", "items": {"type": "string"}}, "policy_refs": {"type": "array", "items": {"type": "string"}}}}, "definition_of_done": {"type": "array", "items": {"type": "string"}}}}	1.0	system	reconciliation	\N	work_package	[]	[]	{}	f	\N	multi	wp_id	project	38	WorkPackageView	\N	\N	\N	t	1.0	2026-02-20 15:42:05.510815+00	2026-02-20 15:42:05.510815+00	\N	\N
c2a9e502-93ef-4134-84f3-9ba2a5fd9835	work_statement	Work Statement	Unit of authorized execution within a Work Package. Defines objective, scope, procedure, verification criteria, and prohibited actions. Has its own lifecycle state machine.	planning	file-check	{"type": "object", "required": ["ws_id", "parent_wp_id", "title", "objective", "scope_in", "scope_out", "procedure", "verification_criteria", "prohibited_actions", "state", "governance_pins"], "properties": {"state": {"enum": ["DRAFT", "READY", "IN_PROGRESS", "ACCEPTED", "REJECTED", "BLOCKED"], "type": "string"}, "title": {"type": "string"}, "ws_id": {"type": "string"}, "scope_in": {"type": "array", "items": {"type": "string"}}, "objective": {"type": "string"}, "procedure": {"type": "array", "items": {"type": "string"}}, "scope_out": {"type": "array", "items": {"type": "string"}}, "parent_wp_id": {"type": "string"}, "governance_pins": {"type": "object", "properties": {"adr_refs": {"type": "array", "items": {"type": "string"}}, "policy_refs": {"type": "array", "items": {"type": "string"}}}}, "prohibited_actions": {"type": "array", "items": {"type": "string"}}, "verification_criteria": {"type": "array", "items": {"type": "string"}}}}	1.0	system	authoring	\N	work_statement	[]	[]	{}	f	\N	multi	ws_id	project	39	WorkStatementView	\N	\N	\N	t	1.0	2026-02-20 15:42:05.510815+00	2026-02-20 15:42:05.510815+00	\N	\N
db798e8f-0cf4-4e47-8fa5-b30857e2e0fe	project_logbook	Project Logbook	Append-only audit trail of Work Statement acceptances. Created lazily on first WS acceptance. Tracks mode-B rate and verification debt across the project.	governance	book-open	{"type": "object", "required": ["schema_version", "project_id", "mode_b_rate", "verification_debt_open", "entries"], "properties": {"entries": {"type": "array", "items": {"type": "object", "properties": {"ws_id": {"type": "string"}, "result": {"type": "string"}, "timestamp": {"type": "string"}, "tier0_json": {"type": "object"}, "mode_b_list": {"type": "array", "items": {"type": "string"}}, "parent_wp_id": {"type": "string"}}}}, "project_id": {"type": "string"}, "mode_b_rate": {"type": "number"}, "program_ref": {"type": "string"}, "schema_version": {"type": "string"}, "verification_debt_open": {"type": "integer"}}}	1.0	system	acceptance	\N	project_logbook	[]	[]	{}	f	\N	single	\N	project	40	ProjectLogbookView	\N	\N	\N	t	1.0	2026-02-20 15:42:05.510815+00	2026-02-20 15:42:05.510815+00	\N	\N
7f441857-9dac-444a-a53d-d1dcc0dc3a12	story_backlog	Story Backlog (Legacy)	Legacy: User stories decomposed from an epic. Being replaced by Feature documents with nested stories.	planning	list-checks	{"type": "object", "required": ["stories"], "properties": {"epic_id": {"type": "string"}, "stories": {"type": "array", "items": {"type": "object", "required": ["title", "description"], "properties": {"title": {"type": "string"}, "priority": {"type": "string"}, "story_id": {"type": "string"}, "description": {"type": "string"}, "story_points": {"type": "integer"}, "acceptance_criteria": {"type": "array"}}}}}}	1.0	ba	story_decomposition	\N	story_backlog	[]	["technical_architecture"]	{}	f	\N	single	\N	epic	50	StoryBacklogView	\N	\N	\N	t	1.0	2026-02-20 15:42:05.510815+00	2026-02-20 15:42:05.510815+00	\N	\N
807342c1-93b7-4e78-a5d9-24d5ddf28ed1	intent_packet	Intent Packet	Raw user intent persisted as immutable input to the Backlog Compilation Pipeline.	planning	lightbulb	\N	1.0.0	project_manager	intake	\N	intent_packet	[]	[]	{}	f	\N	single	\N	project	1	\N	\N	\N	\N	t	1.0.0	2026-02-20 15:42:32.196811+00	2026-02-20 15:42:32.196811+00	\N	\N
0c839046-e417-49c7-9035-7fd36214da67	backlog_item	Backlog Item	Unified backlog item (EPIC/FEATURE/STORY) generated by the Backlog Generator DCW.	planning	list	\N	1.0.0	project_manager	backlog_generator	\N	backlog_item	["intent_packet"]	[]	{}	f	\N	multi	id	project	2	\N	\N	\N	\N	t	1.0.0	2026-02-20 15:42:32.196811+00	2026-02-20 15:42:32.196811+00	\N	\N
0ecfa3ef-085c-4fd6-8557-d8a96466da1c	execution_plan	Execution Plan	Step-by-step execution plan for implementing a backlog item.	development	map	\N	1.0.0	developer	execution_planning	\N	execution_plan	["backlog_item"]	[]	{}	f	\N	multi	\N	project	3	\N	\N	\N	\N	t	1.0.0	2026-02-20 15:42:32.196811+00	2026-02-20 15:42:32.196811+00	\N	\N
ed28531f-f19e-4c66-8495-429759d251cb	plan_explanation	Plan Explanation	Human-readable explanation of an execution plan for review.	development	file-text	\N	1.0.0	developer	plan_explanation	\N	plan_explanation	["execution_plan"]	[]	{}	f	\N	multi	\N	project	4	\N	\N	\N	\N	t	1.0.0	2026-02-20 15:42:32.196811+00	2026-02-20 15:42:32.196811+00	\N	\N
0ecef170-4ce4-4779-b09b-16f9a1b88f88	pipeline_run	Pipeline Run	Audit record of a complete pipeline execution (intake through plan explanation).	governance	activity	\N	1.0.0	system	pipeline_tracking	\N	pipeline_run	[]	[]	{}	f	\N	multi	\N	project	5	\N	\N	\N	\N	t	1.0.0	2026-02-20 15:42:32.196811+00	2026-02-20 15:42:32.196811+00	\N	\N
2f34206b-16da-4acb-bc4d-5cea74f68d94	work_package_candidate	Work Package Candidate	\N	planning	\N	\N	1.0.0	system	import	\N	import	[]	[]	[]	f	\N	multi	wpc_id	project	0	\N	\N	\N	\N	t	1.0.0	2026-03-04 12:22:28.878774+00	2026-03-04 12:22:28.878774+00	\N	\N
\.


--
-- PostgreSQL database dump complete
--

\unrestrict pOdUTQpXZdoOzuF2M8CbZ3uIcZb3OihwlQoG734AT2xjlGEZB5QVxMBsBkIRlgH

