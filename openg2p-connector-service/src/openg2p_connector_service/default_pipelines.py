"""Automatic seed of default Crop Sown Registry integration pipelines.

Seeds one ODK Central pipeline per crop-sown stage form on a fresh connector
database, so a new environment comes up with working pipelines instead of an
empty UI.

Everything environment-specific is read from the environment. There are no
fallback credentials and no fallback ODK host: an unconfigured deployment logs
what is missing and seeds nothing, rather than pointing at someone's sandbox.
Configure:

    CONNECTOR_ODK_CENTRAL_BASE_URL   the ODK Central the forms live on
    CONNECTOR_ODK_PROJECT_ID         the project holding the four forms
    CONNECTOR_ODK_CENTRAL_EMAIL      an ODK Central account with access
    CONNECTOR_ODK_CENTRAL_PASSWORD   its password (mount from a secret)

The pipelines are seeded with ON CONFLICT (name) DO NOTHING, so a pipeline that
has since been edited in the UI is never overwritten.
"""

import json
import logging
import os

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from .config import get_settings

_logger = logging.getLogger("connector.pipelines.seed")

DEFAULT_CROPSOWN_PIPELINES = [
    {
        "connector_id": "533b074b13544a8eb0a8fbd10c6f52ed",
        "name": "Crop Sown 1 - Planning",
        "form_id": "crop_sown_registry_plan",
    },
    {
        "connector_id": "24b12b2f3aac4ccdb5b876a604eb54aa",
        "name": "Crop Sown 2 - Cultivation & Land Prep",
        "form_id": "crop_sown_registry_prep",
    },
    {
        "connector_id": "54e73482cf304614a1f3db4982d907c5",
        "name": "Crop Sown 3 - Sowing",
        "form_id": "crop_sown_registry_sown",
    },
    {
        "connector_id": "2e6c255ec645430e8f8a8c5d3d94f707",
        "name": "Crop Sown 4 - Harvesting",
        "form_id": "crop_sown_registry_harvest",
    },
]


def _setting(name: str, *env_names: str) -> str:
    """Read a setting from the connector settings or the environment."""
    value = getattr(get_settings(), name, "") or ""
    if not value:
        for env_name in env_names:
            value = os.environ.get(env_name) or ""
            if value:
                break
    return str(value).strip()


async def seed_default_pipelines(conn: AsyncConnection) -> None:
    """Ensure the standard Crop Sown pipelines exist in the connector database."""
    odk_base_url = _setting(
        "odk_central_base_url",
        "CONNECTOR_ODK_CENTRAL_BASE_URL", "ODK_CENTRAL_BASE_URL", "ODK_BASE_URL",
    ).rstrip("/")
    odk_project_id = _setting("odk_project_id", "CONNECTOR_ODK_PROJECT_ID", "ODK_PROJECT_ID")
    odk_email = _setting(
        "odk_central_email", "CONNECTOR_ODK_CENTRAL_EMAIL", "ODK_CENTRAL_EMAIL", "ODK_EMAIL"
    )
    odk_password = _setting(
        "odk_central_password",
        "CONNECTOR_ODK_CENTRAL_PASSWORD", "ODK_CENTRAL_PASSWORD", "ODK_PASSWORD",
    )

    missing = [
        name
        for name, value in (
            ("CONNECTOR_ODK_CENTRAL_BASE_URL", odk_base_url),
            ("CONNECTOR_ODK_PROJECT_ID", odk_project_id),
            ("CONNECTOR_ODK_CENTRAL_EMAIL", odk_email),
            ("CONNECTOR_ODK_CENTRAL_PASSWORD", odk_password),
        )
        if not value
    ]
    if missing:
        _logger.info(
            "Not seeding the default pipelines: %s not set. Create the pipelines "
            "in the connector UI, or set these and restart.",
            ", ".join(missing),
        )
        return

    partner_base = (
        getattr(get_settings(), "partner_ingest_base_url", None)
        or os.environ.get("CONNECTOR_PARTNER_INGEST_BASE_URL")
        or "http://partner-api:8000"
    ).strip().rstrip("/")
    target_url = f"{partner_base}/partner/ingest_data"

    auth_secret_json = json.dumps({"email": odk_email, "password": odk_password})

    insert_stmt = text(
        """
        INSERT INTO connector_definitions (
            connector_id, name, platform, transport_type, enabled, paused,
            data_model_mnemonic, g2p_sender_id, g2p_register_mnemonic,
            source_config_json, auth_type, auth_secret_json, webhook_verifier
        ) VALUES (
            :connector_id, :name, 'odk_central', 'odk_central', true, false,
            'CSR_DATA_MODEL', 'CropSown', 'CropSown',
            :source_config_json, 'odk_session', :auth_secret_json, 'hmac_sha256'
        )
        ON CONFLICT (name) DO NOTHING;
        """
    )

    for item in DEFAULT_CROPSOWN_PIPELINES:
        source_config = {
            "base_url": odk_base_url,
            "project_id": int(odk_project_id),
            "form_id": item["form_id"],
            "resolve_nav_links": True,
            # Photos (and any other ODK attachment) travel inline so the
            # registry stores them as documents; OData alone has the name only.
            "embed_attachments": True,
            "strict_incremental": False,
            "target_url": target_url,
            "target_headers": {
                "partner-id": "crop-partner",
                "Content-Type": "application/json",
            },
        }

        try:
            await conn.execute(
                insert_stmt,
                {
                    "connector_id": item["connector_id"],
                    "name": item["name"],
                    "source_config_json": json.dumps(source_config),
                    "auth_secret_json": auth_secret_json,
                },
            )
            _logger.info("Auto-seeded connector pipeline: %s", item["name"])
        except Exception as exc:
            _logger.warning("Could not auto-seed pipeline %s: %s", item["name"], exc)
