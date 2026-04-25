--
-- PostgreSQL database dump
--

-- Dumped from database version 17.5
-- Dumped by pg_dump version 17.5 (Ubuntu 17.5-1.pgdg24.04+1)

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
-- Name: uuid-ossp; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA public;


--
-- Name: EXTENSION "uuid-ossp"; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION "uuid-ossp" IS 'generate universally unique identifiers (UUIDs)';


--
-- Name: vector; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public;


--
-- Name: EXTENSION vector; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION vector IS 'vector data type and ivfflat and hnsw access methods';


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: analytics_events; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.analytics_events (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    schema_version text NOT NULL,
    event text NOT NULL,
    "timestamp" timestamp with time zone NOT NULL,
    source_product text NOT NULL,
    source_version text NOT NULL,
    source_environment text NOT NULL,
    user_id text,
    anonymous_id text,
    account_id text,
    locale text,
    timezone text,
    session_id text NOT NULL,
    ip text,
    user_agent text,
    network text,
    device_id text NOT NULL,
    device_type text NOT NULL,
    os text,
    os_version text,
    properties jsonb,
    debug boolean DEFAULT false,
    parent_event_id text,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.analytics_events OWNER TO postgres;

--
-- Name: chat_history; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.chat_history (
    id integer NOT NULL,
    user_id character varying(64) NOT NULL,
    session_id character varying(64) NOT NULL,
    message_history jsonb NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.chat_history OWNER TO postgres;

--
-- Name: chat_history_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.chat_history_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.chat_history_id_seq OWNER TO postgres;

--
-- Name: chat_history_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.chat_history_id_seq OWNED BY public.chat_history.id;


--
-- Name: chat_history_summary; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.chat_history_summary (
    id integer NOT NULL,
    user_id character varying(64) NOT NULL,
    session_id character varying(64) NOT NULL,
    summary text NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.chat_history_summary OWNER TO postgres;

--
-- Name: chat_history_summary_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.chat_history_summary_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.chat_history_summary_id_seq OWNER TO postgres;

--
-- Name: chat_history_summary_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.chat_history_summary_id_seq OWNED BY public.chat_history_summary.id;


--
-- Name: cocktail_mixlist_items; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.cocktail_mixlist_items (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    mixlist_id uuid NOT NULL,
    cocktail_id uuid NOT NULL,
    "position" integer,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.cocktail_mixlist_items OWNER TO postgres;

--
-- Name: cocktail_mixlists; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.cocktail_mixlists (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    author jsonb,
    tags jsonb,
    image jsonb,
    deprecated_id integer,
    chatbot_360_compatible boolean DEFAULT true,
    is_deleted boolean DEFAULT false NOT NULL,
    deleted_at timestamp without time zone,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    user_id text
);


ALTER TABLE public.cocktail_mixlists OWNER TO postgres;

--
-- Name: cocktail_recipes; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.cocktail_recipes (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    image jsonb,
    ice character varying(50),
    ingredients jsonb NOT NULL,
    instructions jsonb NOT NULL,
    mixing_technique character varying(50),
    glassware jsonb,
    tags jsonb,
    author jsonb,
    variations jsonb,
    deprecated_id integer,
    chatbot_360_compatible boolean DEFAULT true,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    user_id text,
    origin text,
    is_deleted boolean DEFAULT false NOT NULL,
    deleted_at timestamp with time zone
);


ALTER TABLE public.cocktail_recipes OWNER TO postgres;

--
-- Name: device_docs; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.device_docs (
    id uuid NOT NULL,
    source text,
    chunk_index integer NOT NULL,
    text text NOT NULL,
    embedding public.vector(1536) NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.device_docs OWNER TO postgres;

--
-- Name: device_types; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.device_types (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    title text NOT NULL,
    slug text NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.device_types OWNER TO postgres;

--
-- Name: devices; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.devices (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    device_number text NOT NULL,
    device_type_id uuid,
    configuration jsonb,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.devices OWNER TO postgres;

--
-- Name: home_cards; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.home_cards (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    title text NOT NULL,
    prompt text NOT NULL,
    status boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.home_cards OWNER TO postgres;

--
-- Name: image_cache; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.image_cache (
    id integer NOT NULL,
    perceptual_hash character varying(64) NOT NULL,
    image_size character varying(20) NOT NULL,
    image_format character varying(10) NOT NULL,
    file_size integer NOT NULL,
    ingredients json,
    analysis_confidence double precision,
    created_at timestamp without time zone,
    last_accessed timestamp without time zone,
    access_count integer
);


ALTER TABLE public.image_cache OWNER TO postgres;

--
-- Name: image_cache_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.image_cache_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.image_cache_id_seq OWNER TO postgres;

--
-- Name: image_cache_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.image_cache_id_seq OWNED BY public.image_cache.id;


--
-- Name: mixlist_embeddings; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.mixlist_embeddings (
    id uuid NOT NULL,
    mixlist_id text NOT NULL,
    mixlist_summary text NOT NULL,
    embedding public.vector(768) NOT NULL,
    created_at timestamp without time zone,
    updated_at timestamp without time zone
);


ALTER TABLE public.mixlist_embeddings OWNER TO postgres;

--
-- Name: ory_token_cache; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.ory_token_cache (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    token text NOT NULL,
    token_data jsonb NOT NULL,
    expires_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.ory_token_cache OWNER TO postgres;

--
-- Name: recipe_embeddings; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.recipe_embeddings (
    id uuid NOT NULL,
    recipe_id text NOT NULL,
    recipe_summary text NOT NULL,
    embedding public.vector(768) NOT NULL,
    created_at timestamp without time zone,
    updated_at timestamp without time zone
);


ALTER TABLE public.recipe_embeddings OWNER TO postgres;

--
-- Name: schema_migrations; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.schema_migrations (
    version bigint NOT NULL,
    dirty boolean NOT NULL
);


ALTER TABLE public.schema_migrations OWNER TO postgres;

--
-- Name: chat_history id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chat_history ALTER COLUMN id SET DEFAULT nextval('public.chat_history_id_seq'::regclass);


--
-- Name: chat_history_summary id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chat_history_summary ALTER COLUMN id SET DEFAULT nextval('public.chat_history_summary_id_seq'::regclass);


--
-- Name: image_cache id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.image_cache ALTER COLUMN id SET DEFAULT nextval('public.image_cache_id_seq'::regclass);


--
-- Name: analytics_events analytics_events_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.analytics_events
    ADD CONSTRAINT analytics_events_pkey PRIMARY KEY (id);


--
-- Name: chat_history chat_history_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chat_history
    ADD CONSTRAINT chat_history_pkey PRIMARY KEY (id);


--
-- Name: chat_history_summary chat_history_summary_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chat_history_summary
    ADD CONSTRAINT chat_history_summary_pkey PRIMARY KEY (id);


--
-- Name: cocktail_mixlist_items cocktail_mixlist_items_mixlist_id_cocktail_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.cocktail_mixlist_items
    ADD CONSTRAINT cocktail_mixlist_items_mixlist_id_cocktail_id_key UNIQUE (mixlist_id, cocktail_id);


--
-- Name: cocktail_mixlist_items cocktail_mixlist_items_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.cocktail_mixlist_items
    ADD CONSTRAINT cocktail_mixlist_items_pkey PRIMARY KEY (id);


--
-- Name: cocktail_mixlists cocktail_mixlists_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.cocktail_mixlists
    ADD CONSTRAINT cocktail_mixlists_pkey PRIMARY KEY (id);


--
-- Name: cocktail_recipes cocktail_recipes_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.cocktail_recipes
    ADD CONSTRAINT cocktail_recipes_pkey PRIMARY KEY (id);


--
-- Name: device_docs device_docs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.device_docs
    ADD CONSTRAINT device_docs_pkey PRIMARY KEY (id);


--
-- Name: device_types device_types_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.device_types
    ADD CONSTRAINT device_types_pkey PRIMARY KEY (id);


--
-- Name: devices devices_device_number_unique; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.devices
    ADD CONSTRAINT devices_device_number_unique UNIQUE (device_number);


--
-- Name: devices devices_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.devices
    ADD CONSTRAINT devices_pkey PRIMARY KEY (id);


--
-- Name: home_cards home_cards_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.home_cards
    ADD CONSTRAINT home_cards_pkey PRIMARY KEY (id);


--
-- Name: image_cache image_cache_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.image_cache
    ADD CONSTRAINT image_cache_pkey PRIMARY KEY (id);


--
-- Name: mixlist_embeddings mixlist_embeddings_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.mixlist_embeddings
    ADD CONSTRAINT mixlist_embeddings_pkey PRIMARY KEY (id);


--
-- Name: ory_token_cache ory_token_cache_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ory_token_cache
    ADD CONSTRAINT ory_token_cache_pkey PRIMARY KEY (id);


--
-- Name: ory_token_cache ory_token_cache_token_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ory_token_cache
    ADD CONSTRAINT ory_token_cache_token_key UNIQUE (token);


--
-- Name: recipe_embeddings recipe_embeddings_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.recipe_embeddings
    ADD CONSTRAINT recipe_embeddings_pkey PRIMARY KEY (id);


--
-- Name: schema_migrations schema_migrations_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.schema_migrations
    ADD CONSTRAINT schema_migrations_pkey PRIMARY KEY (version);


--
-- Name: idx_analytics_events_created_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_analytics_events_created_at ON public.analytics_events USING btree (created_at);


--
-- Name: idx_analytics_events_device_event; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_analytics_events_device_event ON public.analytics_events USING btree (device_id, event);


--
-- Name: idx_analytics_events_device_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_analytics_events_device_id ON public.analytics_events USING btree (device_id);


--
-- Name: idx_analytics_events_device_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_analytics_events_device_type ON public.analytics_events USING btree (device_type);


--
-- Name: idx_analytics_events_event; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_analytics_events_event ON public.analytics_events USING btree (event);


--
-- Name: idx_analytics_events_event_timestamp; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_analytics_events_event_timestamp ON public.analytics_events USING btree (event, "timestamp");


--
-- Name: idx_analytics_events_properties; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_analytics_events_properties ON public.analytics_events USING gin (properties);


--
-- Name: idx_analytics_events_schema_version; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_analytics_events_schema_version ON public.analytics_events USING btree (schema_version);


--
-- Name: idx_analytics_events_session_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_analytics_events_session_id ON public.analytics_events USING btree (session_id);


--
-- Name: idx_analytics_events_source_product; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_analytics_events_source_product ON public.analytics_events USING btree (source_product);


--
-- Name: idx_analytics_events_timestamp; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_analytics_events_timestamp ON public.analytics_events USING btree ("timestamp");


--
-- Name: idx_analytics_events_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_analytics_events_user_id ON public.analytics_events USING btree (user_id);


--
-- Name: idx_analytics_events_user_session; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_analytics_events_user_session ON public.analytics_events USING btree (user_id, session_id);


--
-- Name: idx_chat_history_created_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_chat_history_created_at ON public.chat_history USING btree (created_at);


--
-- Name: idx_chat_history_session_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_chat_history_session_id ON public.chat_history USING btree (session_id);


--
-- Name: idx_chat_history_summary_created_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_chat_history_summary_created_at ON public.chat_history_summary USING btree (created_at);


--
-- Name: idx_chat_history_summary_session_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_chat_history_summary_session_id ON public.chat_history_summary USING btree (session_id);


--
-- Name: idx_chat_history_summary_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_chat_history_summary_user_id ON public.chat_history_summary USING btree (user_id);


--
-- Name: idx_chat_history_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_chat_history_user_id ON public.chat_history USING btree (user_id);


--
-- Name: idx_cocktail_author; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_cocktail_author ON public.cocktail_recipes USING gin (author);


--
-- Name: idx_cocktail_deprecated_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_cocktail_deprecated_id ON public.cocktail_recipes USING btree (deprecated_id);


--
-- Name: idx_cocktail_glassware; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_cocktail_glassware ON public.cocktail_recipes USING gin (glassware);


--
-- Name: idx_cocktail_ice; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_cocktail_ice ON public.cocktail_recipes USING btree (ice);


--
-- Name: idx_cocktail_ingredients; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_cocktail_ingredients ON public.cocktail_recipes USING gin (ingredients);


--
-- Name: idx_cocktail_mixing_technique; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_cocktail_mixing_technique ON public.cocktail_recipes USING btree (mixing_technique);


--
-- Name: idx_cocktail_mixlist_items_cocktail_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_cocktail_mixlist_items_cocktail_id ON public.cocktail_mixlist_items USING btree (cocktail_id);


--
-- Name: idx_cocktail_mixlist_items_mixlist_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_cocktail_mixlist_items_mixlist_id ON public.cocktail_mixlist_items USING btree (mixlist_id);


--
-- Name: idx_cocktail_mixlist_items_position; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_cocktail_mixlist_items_position ON public.cocktail_mixlist_items USING btree (mixlist_id, "position");


--
-- Name: idx_cocktail_mixlists_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_cocktail_mixlists_user_id ON public.cocktail_mixlists USING btree (user_id);


--
-- Name: idx_cocktail_name; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_cocktail_name ON public.cocktail_recipes USING btree (name);


--
-- Name: idx_cocktail_recipes_is_deleted; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_cocktail_recipes_is_deleted ON public.cocktail_recipes USING btree (is_deleted);


--
-- Name: idx_cocktail_recipes_origin; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_cocktail_recipes_origin ON public.cocktail_recipes USING btree (origin);


--
-- Name: idx_cocktail_recipes_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_cocktail_recipes_user_id ON public.cocktail_recipes USING btree (user_id);


--
-- Name: idx_cocktail_recipes_user_id_is_deleted; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_cocktail_recipes_user_id_is_deleted ON public.cocktail_recipes USING btree (user_id, is_deleted) WHERE (user_id IS NOT NULL);


--
-- Name: idx_cocktail_tags; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_cocktail_tags ON public.cocktail_recipes USING gin (tags);


--
-- Name: idx_created_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_created_at ON public.image_cache USING btree (created_at);


--
-- Name: idx_device_types_slug; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_device_types_slug ON public.device_types USING btree (slug);


--
-- Name: idx_device_types_title; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_device_types_title ON public.device_types USING btree (title);


--
-- Name: idx_devices_device_number; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_devices_device_number ON public.devices USING btree (device_number);


--
-- Name: idx_home_cards_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_home_cards_id ON public.home_cards USING btree (id);


--
-- Name: idx_home_cards_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_home_cards_status ON public.home_cards USING btree (status);


--
-- Name: idx_last_accessed; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_last_accessed ON public.image_cache USING btree (last_accessed);


--
-- Name: idx_mixlist_active; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_mixlist_active ON public.cocktail_mixlists USING btree (created_at, updated_at) WHERE (is_deleted = false);


--
-- Name: idx_mixlist_author; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_mixlist_author ON public.cocktail_mixlists USING gin (author);


--
-- Name: idx_mixlist_deprecated_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_mixlist_deprecated_id ON public.cocktail_mixlists USING btree (deprecated_id);


--
-- Name: idx_mixlist_is_deleted; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_mixlist_is_deleted ON public.cocktail_mixlists USING btree (is_deleted);


--
-- Name: idx_mixlist_name; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_mixlist_name ON public.cocktail_mixlists USING btree (name);


--
-- Name: idx_mixlist_tags; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_mixlist_tags ON public.cocktail_mixlists USING gin (tags);


--
-- Name: idx_ory_token_cache_created_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_ory_token_cache_created_at ON public.ory_token_cache USING btree (created_at);


--
-- Name: idx_ory_token_cache_expires_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_ory_token_cache_expires_at ON public.ory_token_cache USING btree (expires_at);


--
-- Name: idx_ory_token_cache_token; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_ory_token_cache_token ON public.ory_token_cache USING btree (token);


--
-- Name: idx_ory_token_cache_token_data; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_ory_token_cache_token_data ON public.ory_token_cache USING gin (token_data);


--
-- Name: idx_ory_token_cache_token_expires; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_ory_token_cache_token_expires ON public.ory_token_cache USING btree (token, expires_at);


--
-- Name: idx_perceptual_hash; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_perceptual_hash ON public.image_cache USING btree (perceptual_hash);


--
-- Name: ix_cocktails_embedding; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_cocktails_embedding ON public.recipe_embeddings USING hnsw (embedding public.vector_cosine_ops);


--
-- Name: ix_image_cache_perceptual_hash; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_image_cache_perceptual_hash ON public.image_cache USING btree (perceptual_hash);


--
-- Name: ix_mixlist_embeddings_embedding; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_mixlist_embeddings_embedding ON public.mixlist_embeddings USING hnsw (embedding public.vector_cosine_ops);


--
-- Name: cocktail_mixlist_items cocktail_mixlist_items_cocktail_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.cocktail_mixlist_items
    ADD CONSTRAINT cocktail_mixlist_items_cocktail_id_fkey FOREIGN KEY (cocktail_id) REFERENCES public.cocktail_recipes(id) ON DELETE CASCADE;


--
-- Name: cocktail_mixlist_items cocktail_mixlist_items_mixlist_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.cocktail_mixlist_items
    ADD CONSTRAINT cocktail_mixlist_items_mixlist_id_fkey FOREIGN KEY (mixlist_id) REFERENCES public.cocktail_mixlists(id) ON DELETE CASCADE;


--
-- Name: devices devices_device_type_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.devices
    ADD CONSTRAINT devices_device_type_id_fkey FOREIGN KEY (device_type_id) REFERENCES public.device_types(id) ON DELETE CASCADE;


--
-- Name: SCHEMA public; Type: ACL; Schema: -; Owner: pg_database_owner
--

GRANT ALL ON SCHEMA public TO cloudsqlsuperuser;
GRANT USAGE ON SCHEMA public TO ai_backend;


--
-- Name: TABLE analytics_events; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE public.analytics_events TO ai_backend;


--
-- Name: TABLE chat_history; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE public.chat_history TO ai_backend;


--
-- Name: SEQUENCE chat_history_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT USAGE ON SEQUENCE public.chat_history_id_seq TO ai_backend;


--
-- Name: TABLE chat_history_summary; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE public.chat_history_summary TO ai_backend;


--
-- Name: SEQUENCE chat_history_summary_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT USAGE ON SEQUENCE public.chat_history_summary_id_seq TO ai_backend;


--
-- Name: TABLE cocktail_mixlist_items; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE public.cocktail_mixlist_items TO ai_backend;


--
-- Name: TABLE cocktail_mixlists; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE public.cocktail_mixlists TO ai_backend;


--
-- Name: TABLE cocktail_recipes; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE public.cocktail_recipes TO ai_backend;


--
-- Name: TABLE device_docs; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE public.device_docs TO ai_backend;


--
-- Name: TABLE device_types; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE public.device_types TO ai_backend;


--
-- Name: TABLE devices; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE public.devices TO ai_backend;


--
-- Name: TABLE home_cards; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE public.home_cards TO ai_backend;


--
-- Name: TABLE image_cache; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE public.image_cache TO ai_backend;


--
-- Name: SEQUENCE image_cache_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT USAGE ON SEQUENCE public.image_cache_id_seq TO ai_backend;


--
-- Name: TABLE mixlist_embeddings; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE public.mixlist_embeddings TO ai_backend;


--
-- Name: TABLE ory_token_cache; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE public.ory_token_cache TO ai_backend;


--
-- Name: TABLE recipe_embeddings; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE public.recipe_embeddings TO ai_backend;


--
-- Name: TABLE schema_migrations; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE public.schema_migrations TO ai_backend;


--
-- PostgreSQL database dump complete
--

