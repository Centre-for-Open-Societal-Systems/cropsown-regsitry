import hashlib
import hmac

from fastapi import HTTPException

from . import verifier_registry


def verify_hmac_sha256(secret: str, body: bytes, headers: dict[str, str]) -> None:
    if not secret:
        raise HTTPException(503, "Webhook signing secret is not configured")
    values = {k.lower(): v for k, v in headers.items()}
    signatures = [values[k] for k in ("x-hub-signature", "x-hub-signature-256") if k in values]
    if not signatures:
        raise HTTPException(401, "Missing WebSub signature")
    expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    if any(not hmac.compare_digest(expected, signature) for signature in signatures):
        raise HTTPException(403, "Invalid webhook signature")


verifier_registry["hmac_sha256"] = verify_hmac_sha256
