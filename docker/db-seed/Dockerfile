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

# Sample data (LOAD_SAMPLE_DATA=true). The platform image checks out openg2p-data
# at /openg2p-data; this one checks out the COSS repository at a pinned commit in
# its place, the source of the ETH-OAN pack's sample farmers and their crop
# records (samples/farmer_ids.json, samples/crop_sown.json).
ARG OPENG2P_DATA_REPO=https://github.com/Centre-for-Open-Societal-Systems/openg2p-data.git
ARG OPENG2P_DATA_REF=5aa26d65aabd979ad96a2fc4a293c8f12de18bf7
RUN rm -rf /openg2p-data && mkdir -p /openg2p-data && cd /openg2p-data \
    && git init -q && git remote add origin ${OPENG2P_DATA_REPO} \
    && git fetch -q --depth 1 origin ${OPENG2P_DATA_REF} && git checkout -q FETCH_HEAD \
    && rm -rf .git
COPY --chmod=755 docker/db-seed/load_sample_data.py /seed/
ENTRYPOINT ["/seed/entrypoint.sh"]
