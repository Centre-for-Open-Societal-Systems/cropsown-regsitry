-- ODK_TO_CROP_INTAKE: retire the old ODK data model rows.
--
-- The four ODK Central forms used a data model whose mnemonic was CSR_DATA_MODEL, with
-- generated ids. The data model, key path, four semantic patterns, incoming template and
-- template document now have readable ids (odk_to_crop_intake and friends) and are seeded
-- by the files under data-models/, register-metadata/ and registry-inbound-message-rules/.
-- The old rows are not seeded any more, so databases that already hold them are cleaned
-- here, after the new rows exist (this folder sorts after all of those).
--
-- Order: move stored history and the import-file configurations to the new data model,
-- delete the old rows by explicit id (children first), then fail loudly if any trace of
-- the old data model is left. Idempotent: on a database without the old rows every
-- statement changes nothing.

-- 1. Stored submissions keep their history under the new data model.
DO $$
BEGIN
    IF to_regclass('public.incoming_raw_data') IS NOT NULL THEN
        UPDATE public.incoming_raw_data
           SET data_model_id = 'odk_to_crop_intake'
         WHERE data_model_id = 'e442ca96-ac35-4014-9d13-4ef327f6b79c';
    END IF;
    IF to_regclass('public.incoming_classified_data') IS NOT NULL THEN
        UPDATE public.incoming_classified_data
           SET data_model_id = 'odk_to_crop_intake'
         WHERE data_model_id = 'e442ca96-ac35-4014-9d13-4ef327f6b79c';
    END IF;
    IF to_regclass('public.g2p_registry_import_file_configurations') IS NOT NULL THEN
        UPDATE public.g2p_registry_import_file_configurations
           SET data_model_id = 'odk_to_crop_intake'
         WHERE data_model_id = 'e442ca96-ac35-4014-9d13-4ef327f6b79c';
    END IF;
END
$$;

-- 2. Delete the old rows by explicit id, children first.
DELETE FROM public.incoming_templates WHERE template_id = 'IN-TMPL-CSR';
DELETE FROM public.g2p_registry_documents WHERE document_id = '7a8b9c0d-1e2f-4a5b-8c9d-0e1f2a3b4c5d';
DELETE FROM public.incoming_model_semantic_patterns WHERE semantic_pattern_id = '11111111-ce19-46f8-874c-7147997f793b';
DELETE FROM public.incoming_model_semantic_patterns WHERE semantic_pattern_id = '22222222-0f1b-4c38-995f-395d52a1b17a';
DELETE FROM public.incoming_model_semantic_patterns WHERE semantic_pattern_id = '33333333-0ffb-41d8-8fea-f22349823675';
DELETE FROM public.incoming_model_semantic_patterns WHERE semantic_pattern_id = '44444444-153d-496d-9cd9-2a3815d6e13b';
DELETE FROM public.incoming_model_key_paths WHERE key_path_id = '5a5d9a8e-ffef-466a-9d00-d8bd39b0337d';
DELETE FROM public.data_models WHERE data_model_id = 'e442ca96-ac35-4014-9d13-4ef327f6b79c';

-- 3. Guard: nothing may still use the old mnemonic or id.
DO $$
DECLARE
    leftover integer := 0;
    found integer;
BEGIN
    SELECT count(*) INTO found FROM public.data_models
     WHERE data_model_mnemonic = 'CSR_DATA_MODEL' OR data_model_id = 'e442ca96-ac35-4014-9d13-4ef327f6b79c';
    leftover := leftover + found;
    IF to_regclass('public.incoming_raw_data') IS NOT NULL THEN
        SELECT count(*) INTO found FROM public.incoming_raw_data
         WHERE data_model_id = 'e442ca96-ac35-4014-9d13-4ef327f6b79c';
        leftover := leftover + found;
    END IF;
    IF to_regclass('public.incoming_classified_data') IS NOT NULL THEN
        SELECT count(*) INTO found FROM public.incoming_classified_data
         WHERE data_model_id = 'e442ca96-ac35-4014-9d13-4ef327f6b79c';
        leftover := leftover + found;
    END IF;
    IF to_regclass('public.g2p_registry_import_file_configurations') IS NOT NULL THEN
        SELECT count(*) INTO found FROM public.g2p_registry_import_file_configurations
         WHERE data_model_id = 'e442ca96-ac35-4014-9d13-4ef327f6b79c';
        leftover := leftover + found;
    END IF;
    IF leftover > 0 THEN
        RAISE EXCEPTION 'The old ODK data model (CSR_DATA_MODEL) is still referenced by % row(s)', leftover;
    END IF;
END
$$;
