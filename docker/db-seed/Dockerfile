# Native seeding machinery; no database imports, worker or bundle patches.
# The image is the platform's db-seed with the Crop Sown extension's metadata,
# AWE policies and templates in place of the reference extension's. The native
# entrypoint applies the whole tree (meta_data, awe_meta_data, templates).
ARG RP_VERSION=1.2.2-rc.557
FROM openg2p/openg2p-registry-db-seed:${RP_VERSION}
RUN rm -rf /seed/meta_data/* /seed/awe_meta_data/* /seed/templates/* /seed/seed-data/*
COPY cropsown-extension/src/openg2p_registry_cropsown_extension/meta_data/ /seed/meta_data/
COPY cropsown-extension/src/openg2p_registry_cropsown_extension/templates/ /seed/templates/
COPY cropsown-extension/src/openg2p_registry_cropsown_extension/awe_meta_data/ /seed/awe_meta_data/
COPY docker/db-seed/reporting_views.sql /seed/reporting_views.sql
# OAN theme: the staff-portal theme (palette and background image) is data in
# openg2p-data (themes/oan_theme). Render this registry's entry into the seed
# tree; it runs after the registry configuration and points it at oan_theme.
# The ref is a commit SHA; move the repository to the COSS copy once merged there.
ARG OAN_THEME_DATA_REPO=https://github.com/asmitonweb/openg2p-data.git
ARG OAN_THEME_DATA_REF=bba20c3b7144f76cb99fae3522344bd31783d090
RUN mkdir -p /tmp/oan-theme-data /seed/meta_data/zz-oan \
 && cd /tmp/oan-theme-data \
 && git init -q \
 && git fetch -q --depth 1 "${OAN_THEME_DATA_REPO}" "${OAN_THEME_DATA_REF}" \
 && git checkout -q FETCH_HEAD \
 && python3 scripts/themes/build_theme_sql.py crop > /seed/meta_data/zz-oan/90_oan_theme.sql \
 && cd / && rm -rf /tmp/oan-theme-data
ENTRYPOINT ["/seed/entrypoint.sh"]
