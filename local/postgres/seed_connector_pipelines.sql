-- Pre-configure Crop Sown Registry ODK Central pipelines in the connector database.
--
-- The ODK Central host, project and login come from psql variables, which
-- docker-compose fills from .env (ODK_CENTRAL_BASE_URL, ODK_PROJECT_ID,
-- ODK_CENTRAL_EMAIL, ODK_CENTRAL_PASSWORD). Nothing is seeded while they are
-- unset; create the pipelines in the connector UI instead.
\connect connector

CREATE TABLE IF NOT EXISTS connector_definitions (
    connector_id character varying NOT NULL PRIMARY KEY,
    name character varying(255) NOT NULL UNIQUE,
    platform character varying(64) NOT NULL,
    transport_type character varying(64) NOT NULL,
    enabled boolean DEFAULT true,
    paused boolean DEFAULT false,
    data_model_mnemonic character varying(128),
    mapper_expression text,
    mapper_version character varying(64),
    g2p_sender_id character varying(128),
    g2p_register_mnemonic character varying(128),
    source_config_json text,
    auth_type character varying(64) DEFAULT 'none' NOT NULL,
    auth_secret_json text,
    webhook_secret character varying(512),
    webhook_path_slug character varying(128),
    webhook_verifier character varying(64) DEFAULT 'hmac_sha256' NOT NULL,
    last_poll_at timestamp without time zone,
    last_poll_status character varying(32),
    last_poll_error text,
    last_poll_fetched integer,
    last_poll_duration_ms integer,
    max_in_flight integer,
    validation_schema_json text,
    poll_config_json text,
    poll_state_json text,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);

\if :{?odk_base_url} \else \set odk_base_url '' \endif
\if :{?odk_project_id} \else \set odk_project_id '' \endif
\if :{?odk_email} \else \set odk_email '' \endif
\if :{?odk_password} \else \set odk_password '' \endif
SELECT (:'odk_base_url' <> '' AND :'odk_project_id' <> '' AND :'odk_email' <> '' AND :'odk_password' <> '') AS odk_configured \gset
\if :odk_configured
INSERT INTO connector_definitions (
    connector_id, name, platform, transport_type, enabled, paused,
    data_model_mnemonic, g2p_sender_id, g2p_register_mnemonic,
    source_config_json, auth_type, auth_secret_json, webhook_verifier
)
SELECT
    p.connector_id, p.name, 'odk_central', 'odk_central', true, false,
    'CSR_DATA_MODEL', 'CropSown', 'CropSown',
    json_build_object(
        'base_url', rtrim(:'odk_base_url', '/'),
        'project_id', (:'odk_project_id')::int,
        'form_id', p.form_id,
        'resolve_nav_links', true,
        'embed_attachments', true,
        'strict_incremental', false,
        'target_url', 'http://partner-api:8000/partner/ingest_data',
        'target_headers', json_build_object('partner-id', 'crop-partner', 'Content-Type', 'application/json')
    )::text,
    'odk_session',
    json_build_object('email', :'odk_email', 'password', :'odk_password')::text,
    'hmac_sha256'
FROM (VALUES
    ('533b074b13544a8eb0a8fbd10c6f52ed', 'Crop Sown 1 - Planning', 'crop_sown_registry_plan'),
    ('24b12b2f3aac4ccdb5b876a604eb54aa', 'Crop Sown 2 - Cultivation & Land Prep', 'crop_sown_registry_prep'),
    ('54e73482cf304614a1f3db4982d907c5', 'Crop Sown 3 - Sowing', 'crop_sown_registry_sown'),
    ('2e6c255ec645430e8f8a8c5d3d94f707', 'Crop Sown 4 - Harvesting', 'crop_sown_registry_harvest')
) AS p(connector_id, name, form_id)
ON CONFLICT (name) DO NOTHING;
\else
\echo 'ODK_CENTRAL_BASE_URL / ODK_PROJECT_ID / ODK_CENTRAL_EMAIL / ODK_CENTRAL_PASSWORD not set: no connector pipelines seeded'
\endif
