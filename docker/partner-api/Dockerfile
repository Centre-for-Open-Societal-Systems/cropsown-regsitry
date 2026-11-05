# Cropsown Registry — Partner API image.
#
# Thin extension of the registry-platform base image (see
# docker/staff-api/Dockerfile for the full rationale). Adds only the
# cropsown domain model; ENV defaults and the migrate+gunicorn CMD are inherited.
#
# Build context = repo root (so cropsown-extension/ is reachable).
ARG RP_VERSION=1.2.2-rc.614
FROM openg2p/openg2p-registry-partner-api:${RP_VERSION}

# Option C: select cropsown's domain model (coexists with the base image's
# reference extension; env picks cropsown, no uninstall needed).
ENV REGISTRY_EXTENSION_MODULE=openg2p_registry_cropsown_extension

COPY cropsown-extension/ /app/cropsown-extension/
RUN pip install --no-cache-dir /app/cropsown-extension
