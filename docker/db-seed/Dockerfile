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
# Seed data lives in openg2p-data. The platform image checks out openg2p-data at
# /openg2p-data; this one checks out the COSS repository at a pinned commit in its
# place. It is the source of the staff-portal theme (themes/oan_theme, rendered
# into the seed tree after the registry configuration, pointing it at oan_theme
# and setting the registry logo) and of the ETH-OAN pack's sample people and
# their crop records (samples/individuals.json, samples/crop_sown.json) for
# LOAD_SAMPLE_DATA=true.
ARG OPENG2P_DATA_REPO=https://github.com/Centre-for-Open-Societal-Systems/openg2p-data.git
ARG OPENG2P_DATA_REF=5a8291769a395c78ea5b6625513a7f951595a51f
RUN rm -rf /openg2p-data && mkdir -p /openg2p-data /seed/meta_data/zz-oan && cd /openg2p-data \
    && git init -q && git remote add origin ${OPENG2P_DATA_REPO} \
    && git fetch -q --depth 1 origin ${OPENG2P_DATA_REF} && git checkout -q FETCH_HEAD \
    && rm -rf .git \
    && python3 scripts/themes/build_theme_sql.py crop > /seed/meta_data/zz-oan/90_oan_theme.sql
COPY --chmod=755 docker/db-seed/load_sample_data.py /seed/
COPY docker/db-seed/build_list_words_sql.py /tmp/build_list_words_sql.py
COPY cropsown-extension/src/openg2p_registry_cropsown_extension/register_domain/services/plain_text.py /tmp/plain_text.py
# The commodity and season words of the lists are the pack's labels, rendered at build time;
# the build fails when a planning record name word differs from the pinned pack.
RUN python3 /tmp/build_list_words_sql.py /openg2p-data /tmp/plain_text.py     && python3 /tmp/build_list_words_sql.py /openg2p-data > /seed/meta_data/zz-oan/86b_list_words.sql     && rm /tmp/build_list_words_sql.py /tmp/plain_text.py
ENTRYPOINT ["/seed/entrypoint.sh"]
