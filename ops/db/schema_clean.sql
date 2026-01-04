--
-- PostgreSQL database dump
--

\restrict bg2dQfYnRBclfYKPi5wsbhca9h15aP6X8yxr1FmytknW9iPe3GAZfBfC1bFPXkl

-- Dumped from database version 18.1
-- Dumped by pg_dump version 18.1

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
-- Name: btree_gin; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS btree_gin WITH SCHEMA public;


--
-- Name: EXTENSION btree_gin; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION btree_gin IS 'support for indexing common datatypes in GIN';


--
-- Name: uuid-ossp; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA public;


--
-- Name: EXTENSION "uuid-ossp"; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION "uuid-ossp" IS 'generate universally unique identifiers (UUIDs)';


--
-- Name: get_artifact_with_ancestry(character varying); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.get_artifact_with_ancestry(path character varying) RETURNS TABLE(artifact_path character varying, artifact_type character varying, title character varying, content jsonb, depth integer)
    LANGUAGE plpgsql
    AS $$
BEGIN
    RETURN QUERY
    WITH RECURSIVE ancestry AS (
        -- Base case: the requested artifact
        SELECT 
            a.artifact_path,
            a.artifact_type,
            a.title,
            a.content,
            0 as depth
        FROM artifacts a
        WHERE a.artifact_path = path
        
        UNION ALL
        
        -- Recursive case: parent artifacts
        SELECT 
            a.artifact_path,
            a.artifact_type,
            a.title,
            a.content,
            anc.depth + 1
        FROM artifacts a
        INNER JOIN ancestry anc ON a.artifact_path = anc.parent_path
    )
    SELECT * FROM ancestry ORDER BY depth DESC;
END;
$$;


ALTER FUNCTION public.get_artifact_with_ancestry(path character varying) OWNER TO postgres;

--
-- Name: FUNCTION get_artifact_with_ancestry(path character varying); Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON FUNCTION public.get_artifact_with_ancestry(path character varying) IS 'Returns artifact with complete parent chain';


--
-- Name: parse_artifact_path(character varying); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.parse_artifact_path(path character varying) RETURNS TABLE(project_id character varying, epic_id character varying, feature_id character varying, story_id character varying)
    LANGUAGE plpgsql IMMUTABLE
    AS $$
DECLARE
    parts TEXT[];
BEGIN
    parts := string_to_array(path, '/');
    
    RETURN QUERY SELECT
        parts[1],
        CASE WHEN array_length(parts, 1) >= 2 THEN parts[2] ELSE NULL END,
        CASE WHEN array_length(parts, 1) >= 3 THEN parts[3] ELSE NULL END,
        CASE WHEN array_length(parts, 1) >= 4 THEN parts[4] ELSE NULL END;
END;
$$;


ALTER FUNCTION public.parse_artifact_path(path character varying) OWNER TO postgres;

--
-- Name: FUNCTION parse_artifact_path(path character varying); Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON FUNCTION public.parse_artifact_path(path character varying) IS 'Parses RSP-1 path into components';


--
-- Name: update_updated_at(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.update_updated_at() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.update_updated_at() OWNER TO postgres;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: combine_user
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


ALTER TABLE public.alembic_version OWNER TO combine_user;

--
-- Name: auth_audit_log; Type: TABLE; Schema: public; Owner: combine_user
--

CREATE TABLE public.auth_audit_log (
    log_id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid,
    event_type character varying(50) NOT NULL,
    provider_id character varying(50),
    ip_address inet,
    user_agent text,
    metadata jsonb,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE public.auth_audit_log OWNER TO combine_user;

--
-- Name: document_relations; Type: TABLE; Schema: public; Owner: combine_user
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


ALTER TABLE public.document_relations OWNER TO combine_user;

--
-- Name: document_types; Type: TABLE; Schema: public; Owner: combine_user
--

CREATE TABLE public.document_types (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    doc_type_id character varying(100) NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    category character varying(100) NOT NULL,
    icon character varying(50),
    schema_definition jsonb,
    schema_version character varying(20) DEFAULT '1.0'::character varying NOT NULL,
    builder_role character varying(50) NOT NULL,
    builder_task character varying(100) NOT NULL,
    system_prompt_id uuid,
    handler_id character varying(100) NOT NULL,
    required_inputs jsonb DEFAULT '[]'::jsonb NOT NULL,
    optional_inputs jsonb DEFAULT '[]'::jsonb NOT NULL,
    gating_rules jsonb DEFAULT '{}'::jsonb NOT NULL,
    scope character varying(50) DEFAULT 'project'::character varying NOT NULL,
    display_order integer DEFAULT 0 NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    version character varying(20) DEFAULT '1.0'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by character varying(200),
    notes text,
    acceptance_required boolean DEFAULT false NOT NULL,
    accepted_by_role character varying(64)
);


ALTER TABLE public.document_types OWNER TO combine_user;

--
-- Name: COLUMN document_types.acceptance_required; Type: COMMENT; Schema: public; Owner: combine_user
--

COMMENT ON COLUMN public.document_types.acceptance_required IS 'Whether this document type requires human acceptance before downstream use';


--
-- Name: COLUMN document_types.accepted_by_role; Type: COMMENT; Schema: public; Owner: combine_user
--

COMMENT ON COLUMN public.document_types.accepted_by_role IS 'Role that must accept this document type (pm, architect, etc.)';


--
-- Name: documents; Type: TABLE; Schema: public; Owner: combine_user
--

CREATE TABLE public.documents (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    space_type character varying(50) NOT NULL,
    space_id uuid NOT NULL,
    doc_type_id character varying(100) NOT NULL,
    version integer DEFAULT 1 NOT NULL,
    revision_hash character varying(64),
    is_latest boolean DEFAULT true NOT NULL,
    title character varying(500) NOT NULL,
    summary text,
    content jsonb NOT NULL,
    status character varying(50) DEFAULT 'draft'::character varying NOT NULL,
    is_stale boolean DEFAULT false NOT NULL,
    created_by character varying(200),
    created_by_type character varying(50),
    builder_metadata jsonb,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    search_vector tsvector,
    accepted_at timestamp with time zone,
    accepted_by character varying(200),
    rejected_at timestamp with time zone,
    rejected_by character varying(200),
    rejection_reason text
);


ALTER TABLE public.documents OWNER TO combine_user;

--
-- Name: COLUMN documents.accepted_at; Type: COMMENT; Schema: public; Owner: combine_user
--

COMMENT ON COLUMN public.documents.accepted_at IS 'Timestamp when document was accepted';


--
-- Name: COLUMN documents.accepted_by; Type: COMMENT; Schema: public; Owner: combine_user
--

COMMENT ON COLUMN public.documents.accepted_by IS 'User ID or identifier who accepted the document';


--
-- Name: COLUMN documents.rejected_at; Type: COMMENT; Schema: public; Owner: combine_user
--

COMMENT ON COLUMN public.documents.rejected_at IS 'Timestamp when document was rejected (most recent rejection)';


--
-- Name: COLUMN documents.rejected_by; Type: COMMENT; Schema: public; Owner: combine_user
--

COMMENT ON COLUMN public.documents.rejected_by IS 'User ID or identifier who rejected the document';


--
-- Name: COLUMN documents.rejection_reason; Type: COMMENT; Schema: public; Owner: combine_user
--

COMMENT ON COLUMN public.documents.rejection_reason IS 'Human-provided reason for rejection';


--
-- Name: files; Type: TABLE; Schema: public; Owner: combine_user
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


ALTER TABLE public.files OWNER TO combine_user;

--
-- Name: link_intent_nonces; Type: TABLE; Schema: public; Owner: combine_user
--

CREATE TABLE public.link_intent_nonces (
    nonce character varying(64) NOT NULL,
    user_id uuid NOT NULL,
    provider_id character varying(50) NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    expires_at timestamp with time zone NOT NULL
);


ALTER TABLE public.link_intent_nonces OWNER TO combine_user;

--
-- Name: personal_access_tokens; Type: TABLE; Schema: public; Owner: combine_user
--

CREATE TABLE public.personal_access_tokens (
    token_id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    token_name character varying(100) NOT NULL,
    token_display character varying(50) NOT NULL,
    key_id character varying(20) NOT NULL,
    secret_hash character varying(64) NOT NULL,
    last_used_at timestamp with time zone,
    expires_at timestamp with time zone,
    token_created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    is_active boolean DEFAULT true NOT NULL
);


ALTER TABLE public.personal_access_tokens OWNER TO combine_user;

--
-- Name: projects; Type: TABLE; Schema: public; Owner: combine_user
--

CREATE TABLE public.projects (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    project_id character varying(50) NOT NULL,
    name character varying(200) NOT NULL,
    description text,
    status character varying(50) DEFAULT 'active'::character varying,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by character varying(100),
    metadata jsonb DEFAULT '{}'::jsonb,
    icon character varying(32) DEFAULT 'folder'::character varying,
    owner_id uuid,
    organization_id uuid,
    CONSTRAINT projects_project_id_format CHECK (((project_id)::text ~ '^[A-Z]{2,8}$'::text))
);


ALTER TABLE public.projects OWNER TO combine_user;

--
-- Name: TABLE projects; Type: COMMENT; Schema: public; Owner: combine_user
--

COMMENT ON TABLE public.projects IS 'Top-level project container (e.g., Healthcare Marketplace Project)';


--
-- Name: COLUMN projects.project_id; Type: COMMENT; Schema: public; Owner: combine_user
--

COMMENT ON COLUMN public.projects.project_id IS 'Short project identifier like HMP, GARDEN, APB';


--
-- Name: COLUMN projects.metadata; Type: COMMENT; Schema: public; Owner: combine_user
--

COMMENT ON COLUMN public.projects.metadata IS 'Flexible storage for project-level config, tags, etc.';


--
-- Name: COLUMN projects.icon; Type: COMMENT; Schema: public; Owner: combine_user
--

COMMENT ON COLUMN public.projects.icon IS 'Lucide icon name for project display';


--
-- Name: role_prompts; Type: TABLE; Schema: public; Owner: combine_user
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


ALTER TABLE public.role_prompts OWNER TO combine_user;

--
-- Name: role_tasks; Type: TABLE; Schema: public; Owner: combine_user
--

CREATE TABLE public.role_tasks (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    role_id uuid NOT NULL,
    task_name character varying(100) NOT NULL,
    task_prompt text NOT NULL,
    expected_schema jsonb,
    progress_steps jsonb,
    is_active boolean DEFAULT true NOT NULL,
    version character varying(16) DEFAULT '1'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by character varying(128),
    notes text
);


ALTER TABLE public.role_tasks OWNER TO combine_user;

--
-- Name: TABLE role_tasks; Type: COMMENT; Schema: public; Owner: combine_user
--

COMMENT ON TABLE public.role_tasks IS 'Task-specific prompts and schemas for each role';


--
-- Name: COLUMN role_tasks.task_name; Type: COMMENT; Schema: public; Owner: combine_user
--

COMMENT ON COLUMN public.role_tasks.task_name IS 'Task identifier: preliminary, final, epic_creation, story_breakdown, etc.';


--
-- Name: COLUMN role_tasks.task_prompt; Type: COMMENT; Schema: public; Owner: combine_user
--

COMMENT ON COLUMN public.role_tasks.task_prompt IS 'The "what you are doing" prompt portion for this specific task';


--
-- Name: COLUMN role_tasks.expected_schema; Type: COMMENT; Schema: public; Owner: combine_user
--

COMMENT ON COLUMN public.role_tasks.expected_schema IS 'JSON schema defining expected output structure';


--
-- Name: roles; Type: TABLE; Schema: public; Owner: combine_user
--

CREATE TABLE public.roles (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    name character varying(50) NOT NULL,
    identity_prompt text NOT NULL,
    description text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.roles OWNER TO combine_user;

--
-- Name: TABLE roles; Type: COMMENT; Schema: public; Owner: combine_user
--

COMMENT ON TABLE public.roles IS 'Defines mentor role identities (Architect, PM, BA, Developer, QA)';


--
-- Name: COLUMN roles.name; Type: COMMENT; Schema: public; Owner: combine_user
--

COMMENT ON COLUMN public.roles.name IS 'Role identifier: architect, pm, ba, developer, qa';


--
-- Name: COLUMN roles.identity_prompt; Type: COMMENT; Schema: public; Owner: combine_user
--

COMMENT ON COLUMN public.roles.identity_prompt IS 'The "who you are" prompt portion shared across all tasks';


--
-- Name: user_oauth_identities; Type: TABLE; Schema: public; Owner: combine_user
--

CREATE TABLE public.user_oauth_identities (
    identity_id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    provider_id character varying(50) NOT NULL,
    provider_user_id character varying(255) NOT NULL,
    provider_email character varying(255),
    email_verified boolean DEFAULT false NOT NULL,
    provider_metadata jsonb,
    identity_created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    last_used_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE public.user_oauth_identities OWNER TO combine_user;

--
-- Name: user_sessions; Type: TABLE; Schema: public; Owner: combine_user
--

CREATE TABLE public.user_sessions (
    session_id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    session_token character varying(255) NOT NULL,
    csrf_token character varying(255) NOT NULL,
    ip_address inet,
    user_agent text,
    session_created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    last_activity_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    expires_at timestamp with time zone NOT NULL
);


ALTER TABLE public.user_sessions OWNER TO combine_user;

--
-- Name: users; Type: TABLE; Schema: public; Owner: combine_user
--

CREATE TABLE public.users (
    user_id uuid DEFAULT gen_random_uuid() NOT NULL,
    email character varying(255) NOT NULL,
    email_verified boolean DEFAULT false NOT NULL,
    name character varying(255) NOT NULL,
    avatar_url text,
    is_active boolean DEFAULT true NOT NULL,
    user_created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    user_updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    last_login_at timestamp with time zone
);


ALTER TABLE public.users OWNER TO combine_user;

--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: combine_user
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: auth_audit_log auth_audit_log_pkey; Type: CONSTRAINT; Schema: public; Owner: combine_user
--

ALTER TABLE ONLY public.auth_audit_log
    ADD CONSTRAINT auth_audit_log_pkey PRIMARY KEY (log_id);


--
-- Name: document_relations document_relations_pkey; Type: CONSTRAINT; Schema: public; Owner: combine_user
--

ALTER TABLE ONLY public.document_relations
    ADD CONSTRAINT document_relations_pkey PRIMARY KEY (id);


--
-- Name: document_types document_types_pkey; Type: CONSTRAINT; Schema: public; Owner: combine_user
--

ALTER TABLE ONLY public.document_types
    ADD CONSTRAINT document_types_pkey PRIMARY KEY (id);


--
-- Name: documents documents_pkey; Type: CONSTRAINT; Schema: public; Owner: combine_user
--

ALTER TABLE ONLY public.documents
    ADD CONSTRAINT documents_pkey PRIMARY KEY (id);


--
-- Name: files files_pkey; Type: CONSTRAINT; Schema: public; Owner: combine_user
--

ALTER TABLE ONLY public.files
    ADD CONSTRAINT files_pkey PRIMARY KEY (id);


--
-- Name: link_intent_nonces link_intent_nonces_pkey; Type: CONSTRAINT; Schema: public; Owner: combine_user
--

ALTER TABLE ONLY public.link_intent_nonces
    ADD CONSTRAINT link_intent_nonces_pkey PRIMARY KEY (nonce);


--
-- Name: user_oauth_identities oauth_provider_user_unique; Type: CONSTRAINT; Schema: public; Owner: combine_user
--

ALTER TABLE ONLY public.user_oauth_identities
    ADD CONSTRAINT oauth_provider_user_unique UNIQUE (provider_id, provider_user_id);


--
-- Name: personal_access_tokens personal_access_tokens_pkey; Type: CONSTRAINT; Schema: public; Owner: combine_user
--

ALTER TABLE ONLY public.personal_access_tokens
    ADD CONSTRAINT personal_access_tokens_pkey PRIMARY KEY (token_id);


--
-- Name: projects projects_pkey; Type: CONSTRAINT; Schema: public; Owner: combine_user
--

ALTER TABLE ONLY public.projects
    ADD CONSTRAINT projects_pkey PRIMARY KEY (id);


--
-- Name: projects projects_project_id_key; Type: CONSTRAINT; Schema: public; Owner: combine_user
--

ALTER TABLE ONLY public.projects
    ADD CONSTRAINT projects_project_id_key UNIQUE (project_id);


--
-- Name: role_prompts role_prompts_pkey; Type: CONSTRAINT; Schema: public; Owner: combine_user
--

ALTER TABLE ONLY public.role_prompts
    ADD CONSTRAINT role_prompts_pkey PRIMARY KEY (id);


--
-- Name: role_tasks role_tasks_pkey; Type: CONSTRAINT; Schema: public; Owner: combine_user
--

ALTER TABLE ONLY public.role_tasks
    ADD CONSTRAINT role_tasks_pkey PRIMARY KEY (id);


--
-- Name: roles roles_name_key; Type: CONSTRAINT; Schema: public; Owner: combine_user
--

ALTER TABLE ONLY public.roles
    ADD CONSTRAINT roles_name_key UNIQUE (name);


--
-- Name: roles roles_pkey; Type: CONSTRAINT; Schema: public; Owner: combine_user
--

ALTER TABLE ONLY public.roles
    ADD CONSTRAINT roles_pkey PRIMARY KEY (id);


--
-- Name: document_relations unique_relation; Type: CONSTRAINT; Schema: public; Owner: combine_user
--

ALTER TABLE ONLY public.document_relations
    ADD CONSTRAINT unique_relation UNIQUE (from_document_id, to_document_id, relation_type);


--
-- Name: role_tasks uq_role_task; Type: CONSTRAINT; Schema: public; Owner: combine_user
--

ALTER TABLE ONLY public.role_tasks
    ADD CONSTRAINT uq_role_task UNIQUE (role_id, task_name, version);


--
-- Name: user_oauth_identities user_oauth_identities_pkey; Type: CONSTRAINT; Schema: public; Owner: combine_user
--

ALTER TABLE ONLY public.user_oauth_identities
    ADD CONSTRAINT user_oauth_identities_pkey PRIMARY KEY (identity_id);


--
-- Name: user_sessions user_sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: combine_user
--

ALTER TABLE ONLY public.user_sessions
    ADD CONSTRAINT user_sessions_pkey PRIMARY KEY (session_id);


--
-- Name: user_sessions user_sessions_session_token_unique; Type: CONSTRAINT; Schema: public; Owner: combine_user
--

ALTER TABLE ONLY public.user_sessions
    ADD CONSTRAINT user_sessions_session_token_unique UNIQUE (session_token);


--
-- Name: users users_email_unique; Type: CONSTRAINT; Schema: public; Owner: combine_user
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_email_unique UNIQUE (email);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: combine_user
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (user_id);


--
-- Name: idx_auth_log_created; Type: INDEX; Schema: public; Owner: combine_user
--

CREATE INDEX idx_auth_log_created ON public.auth_audit_log USING btree (created_at DESC);


--
-- Name: idx_auth_log_event; Type: INDEX; Schema: public; Owner: combine_user
--

CREATE INDEX idx_auth_log_event ON public.auth_audit_log USING btree (event_type);


--
-- Name: idx_auth_log_user; Type: INDEX; Schema: public; Owner: combine_user
--

CREATE INDEX idx_auth_log_user ON public.auth_audit_log USING btree (user_id);


--
-- Name: idx_document_types_acceptance_required; Type: INDEX; Schema: public; Owner: combine_user
--

CREATE INDEX idx_document_types_acceptance_required ON public.document_types USING btree (acceptance_required) WHERE (acceptance_required = true);


--
-- Name: idx_document_types_active; Type: INDEX; Schema: public; Owner: combine_user
--

CREATE INDEX idx_document_types_active ON public.document_types USING btree (is_active);


--
-- Name: idx_document_types_builder; Type: INDEX; Schema: public; Owner: combine_user
--

CREATE INDEX idx_document_types_builder ON public.document_types USING btree (builder_role, builder_task);


--
-- Name: idx_document_types_category; Type: INDEX; Schema: public; Owner: combine_user
--

CREATE INDEX idx_document_types_category ON public.document_types USING btree (category);


--
-- Name: idx_document_types_required_inputs; Type: INDEX; Schema: public; Owner: combine_user
--

CREATE INDEX idx_document_types_required_inputs ON public.document_types USING gin (required_inputs);


--
-- Name: idx_document_types_scope; Type: INDEX; Schema: public; Owner: combine_user
--

CREATE INDEX idx_document_types_scope ON public.document_types USING btree (scope);


--
-- Name: idx_documents_acceptance; Type: INDEX; Schema: public; Owner: combine_user
--

CREATE INDEX idx_documents_acceptance ON public.documents USING btree (accepted_at, rejected_at) WHERE (is_latest = true);


--
-- Name: idx_documents_search; Type: INDEX; Schema: public; Owner: combine_user
--

CREATE INDEX idx_documents_search ON public.documents USING gin (search_vector);


--
-- Name: idx_documents_space; Type: INDEX; Schema: public; Owner: combine_user
--

CREATE INDEX idx_documents_space ON public.documents USING btree (space_type, space_id);


--
-- Name: idx_documents_status; Type: INDEX; Schema: public; Owner: combine_user
--

CREATE INDEX idx_documents_status ON public.documents USING btree (status);


--
-- Name: idx_documents_type; Type: INDEX; Schema: public; Owner: combine_user
--

CREATE INDEX idx_documents_type ON public.documents USING btree (doc_type_id);


--
-- Name: idx_documents_unique_latest; Type: INDEX; Schema: public; Owner: combine_user
--

CREATE UNIQUE INDEX idx_documents_unique_latest ON public.documents USING btree (space_type, space_id, doc_type_id) WHERE (is_latest = true);


--
-- Name: idx_files_hash; Type: INDEX; Schema: public; Owner: combine_user
--

CREATE INDEX idx_files_hash ON public.files USING btree (content_hash);


--
-- Name: idx_files_path; Type: INDEX; Schema: public; Owner: combine_user
--

CREATE INDEX idx_files_path ON public.files USING btree (file_path);


--
-- Name: idx_files_search; Type: INDEX; Schema: public; Owner: combine_user
--

CREATE INDEX idx_files_search ON public.files USING gin (search_vector);


--
-- Name: idx_files_type; Type: INDEX; Schema: public; Owner: combine_user
--

CREATE INDEX idx_files_type ON public.files USING btree (file_type);


--
-- Name: idx_link_nonces_expires; Type: INDEX; Schema: public; Owner: combine_user
--

CREATE INDEX idx_link_nonces_expires ON public.link_intent_nonces USING btree (expires_at);


--
-- Name: idx_link_nonces_user; Type: INDEX; Schema: public; Owner: combine_user
--

CREATE INDEX idx_link_nonces_user ON public.link_intent_nonces USING btree (user_id);


--
-- Name: idx_oauth_provider; Type: INDEX; Schema: public; Owner: combine_user
--

CREATE INDEX idx_oauth_provider ON public.user_oauth_identities USING btree (provider_id);


--
-- Name: idx_oauth_user_id; Type: INDEX; Schema: public; Owner: combine_user
--

CREATE INDEX idx_oauth_user_id ON public.user_oauth_identities USING btree (user_id);


--
-- Name: idx_pat_active; Type: INDEX; Schema: public; Owner: combine_user
--

CREATE INDEX idx_pat_active ON public.personal_access_tokens USING btree (is_active) WHERE (is_active = true);


--
-- Name: idx_pat_token_id; Type: INDEX; Schema: public; Owner: combine_user
--

CREATE INDEX idx_pat_token_id ON public.personal_access_tokens USING btree (token_id);


--
-- Name: idx_pat_user; Type: INDEX; Schema: public; Owner: combine_user
--

CREATE INDEX idx_pat_user ON public.personal_access_tokens USING btree (user_id);


--
-- Name: idx_projects_created_at; Type: INDEX; Schema: public; Owner: combine_user
--

CREATE INDEX idx_projects_created_at ON public.projects USING btree (created_at DESC);


--
-- Name: idx_projects_project_id; Type: INDEX; Schema: public; Owner: combine_user
--

CREATE INDEX idx_projects_project_id ON public.projects USING btree (project_id);


--
-- Name: idx_projects_status; Type: INDEX; Schema: public; Owner: combine_user
--

CREATE INDEX idx_projects_status ON public.projects USING btree (status);


--
-- Name: idx_relations_from; Type: INDEX; Schema: public; Owner: combine_user
--

CREATE INDEX idx_relations_from ON public.document_relations USING btree (from_document_id);


--
-- Name: idx_relations_to; Type: INDEX; Schema: public; Owner: combine_user
--

CREATE INDEX idx_relations_to ON public.document_relations USING btree (to_document_id);


--
-- Name: idx_relations_type; Type: INDEX; Schema: public; Owner: combine_user
--

CREATE INDEX idx_relations_type ON public.document_relations USING btree (relation_type);


--
-- Name: idx_role_prompts_active; Type: INDEX; Schema: public; Owner: combine_user
--

CREATE INDEX idx_role_prompts_active ON public.role_prompts USING btree (is_active);


--
-- Name: idx_role_prompts_role_name; Type: INDEX; Schema: public; Owner: combine_user
--

CREATE INDEX idx_role_prompts_role_name ON public.role_prompts USING btree (role_name);


--
-- Name: idx_role_prompts_version; Type: INDEX; Schema: public; Owner: combine_user
--

CREATE INDEX idx_role_prompts_version ON public.role_prompts USING btree (role_name, version);


--
-- Name: idx_role_tasks_active; Type: INDEX; Schema: public; Owner: combine_user
--

CREATE INDEX idx_role_tasks_active ON public.role_tasks USING btree (role_id, is_active) WHERE (is_active = true);


--
-- Name: idx_role_tasks_lookup; Type: INDEX; Schema: public; Owner: combine_user
--

CREATE INDEX idx_role_tasks_lookup ON public.role_tasks USING btree (role_id, task_name, is_active);


--
-- Name: idx_role_tasks_role_id; Type: INDEX; Schema: public; Owner: combine_user
--

CREATE INDEX idx_role_tasks_role_id ON public.role_tasks USING btree (role_id);


--
-- Name: idx_roles_name; Type: INDEX; Schema: public; Owner: combine_user
--

CREATE INDEX idx_roles_name ON public.roles USING btree (name);


--
-- Name: idx_session_expires; Type: INDEX; Schema: public; Owner: combine_user
--

CREATE INDEX idx_session_expires ON public.user_sessions USING btree (expires_at);


--
-- Name: idx_session_token; Type: INDEX; Schema: public; Owner: combine_user
--

CREATE UNIQUE INDEX idx_session_token ON public.user_sessions USING btree (session_token);


--
-- Name: idx_session_user_id; Type: INDEX; Schema: public; Owner: combine_user
--

CREATE INDEX idx_session_user_id ON public.user_sessions USING btree (user_id);


--
-- Name: idx_users_active; Type: INDEX; Schema: public; Owner: combine_user
--

CREATE INDEX idx_users_active ON public.users USING btree (is_active) WHERE (is_active = true);


--
-- Name: idx_users_email; Type: INDEX; Schema: public; Owner: combine_user
--

CREATE INDEX idx_users_email ON public.users USING btree (email);


--
-- Name: ix_document_types_category; Type: INDEX; Schema: public; Owner: combine_user
--

CREATE INDEX ix_document_types_category ON public.document_types USING btree (category);


--
-- Name: ix_document_types_doc_type_id; Type: INDEX; Schema: public; Owner: combine_user
--

CREATE UNIQUE INDEX ix_document_types_doc_type_id ON public.document_types USING btree (doc_type_id);


--
-- Name: ix_files_content_hash; Type: INDEX; Schema: public; Owner: combine_user
--

CREATE INDEX ix_files_content_hash ON public.files USING btree (content_hash);


--
-- Name: ix_files_file_path; Type: INDEX; Schema: public; Owner: combine_user
--

CREATE UNIQUE INDEX ix_files_file_path ON public.files USING btree (file_path);


--
-- Name: ix_files_file_type; Type: INDEX; Schema: public; Owner: combine_user
--

CREATE INDEX ix_files_file_type ON public.files USING btree (file_type);


--
-- Name: ix_projects_organization_id; Type: INDEX; Schema: public; Owner: combine_user
--

CREATE INDEX ix_projects_organization_id ON public.projects USING btree (organization_id);


--
-- Name: ix_projects_owner_id; Type: INDEX; Schema: public; Owner: combine_user
--

CREATE INDEX ix_projects_owner_id ON public.projects USING btree (owner_id);


--
-- Name: ix_role_prompts_is_active; Type: INDEX; Schema: public; Owner: combine_user
--

CREATE INDEX ix_role_prompts_is_active ON public.role_prompts USING btree (is_active);


--
-- Name: ix_role_prompts_role_name; Type: INDEX; Schema: public; Owner: combine_user
--

CREATE INDEX ix_role_prompts_role_name ON public.role_prompts USING btree (role_name);


--
-- Name: projects projects_updated_at; Type: TRIGGER; Schema: public; Owner: combine_user
--

CREATE TRIGGER projects_updated_at BEFORE UPDATE ON public.projects FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();


--
-- Name: auth_audit_log auth_audit_log_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: combine_user
--

ALTER TABLE ONLY public.auth_audit_log
    ADD CONSTRAINT auth_audit_log_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE SET NULL;


--
-- Name: documents fk_documents_doc_type; Type: FK CONSTRAINT; Schema: public; Owner: combine_user
--

ALTER TABLE ONLY public.documents
    ADD CONSTRAINT fk_documents_doc_type FOREIGN KEY (doc_type_id) REFERENCES public.document_types(doc_type_id) ON DELETE RESTRICT;


--
-- Name: document_relations fk_relations_from_doc; Type: FK CONSTRAINT; Schema: public; Owner: combine_user
--

ALTER TABLE ONLY public.document_relations
    ADD CONSTRAINT fk_relations_from_doc FOREIGN KEY (from_document_id) REFERENCES public.documents(id) ON DELETE CASCADE;


--
-- Name: document_relations fk_relations_to_doc; Type: FK CONSTRAINT; Schema: public; Owner: combine_user
--

ALTER TABLE ONLY public.document_relations
    ADD CONSTRAINT fk_relations_to_doc FOREIGN KEY (to_document_id) REFERENCES public.documents(id) ON DELETE CASCADE;


--
-- Name: link_intent_nonces link_intent_nonces_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: combine_user
--

ALTER TABLE ONLY public.link_intent_nonces
    ADD CONSTRAINT link_intent_nonces_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- Name: personal_access_tokens personal_access_tokens_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: combine_user
--

ALTER TABLE ONLY public.personal_access_tokens
    ADD CONSTRAINT personal_access_tokens_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- Name: role_tasks role_tasks_role_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: combine_user
--

ALTER TABLE ONLY public.role_tasks
    ADD CONSTRAINT role_tasks_role_id_fkey FOREIGN KEY (role_id) REFERENCES public.roles(id) ON DELETE CASCADE;


--
-- Name: user_oauth_identities user_oauth_identities_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: combine_user
--

ALTER TABLE ONLY public.user_oauth_identities
    ADD CONSTRAINT user_oauth_identities_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- Name: user_sessions user_sessions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: combine_user
--

ALTER TABLE ONLY public.user_sessions
    ADD CONSTRAINT user_sessions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- Name: SCHEMA public; Type: ACL; Schema: -; Owner: pg_database_owner
--

GRANT ALL ON SCHEMA public TO combine_user;


--
-- Name: DEFAULT PRIVILEGES FOR SEQUENCES; Type: DEFAULT ACL; Schema: public; Owner: postgres
--

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON SEQUENCES TO combine_user;


--
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: public; Owner: postgres
--

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON TABLES TO combine_user;


--
-- PostgreSQL database dump complete
--

\unrestrict bg2dQfYnRBclfYKPi5wsbhca9h15aP6X8yxr1FmytknW9iPe3GAZfBfC1bFPXkl

