# Native seeding machinery; no database imports, worker or bundle patches.
# The image is the platform's db-seed with the Crop Sown extension's metadata,
# AWE policies and templates in place of the reference extension's. The native
# entrypoint applies the whole tree (meta_data, awe_meta_data, templates).
ARG RP_VERSION=1.2.2-rc.614
FROM openg2p/openg2p-registry-db-seed:${RP_VERSION}
RUN rm -rf /seed/meta_data/* /seed/awe_meta_data/* /seed/templates/* /seed/seed-data/*
COPY cropsown-extension/src/openg2p_registry_cropsown_extension/meta_data/ /seed/meta_data/
COPY cropsown-extension/src/openg2p_registry_cropsown_extension/templates/ /seed/templates/
COPY cropsown-extension/src/openg2p_registry_cropsown_extension/awe_meta_data/ /seed/awe_meta_data/
COPY docker/db-seed/reporting_views.sql /seed/reporting_views.sql
ENTRYPOINT ["/seed/entrypoint.sh"]
