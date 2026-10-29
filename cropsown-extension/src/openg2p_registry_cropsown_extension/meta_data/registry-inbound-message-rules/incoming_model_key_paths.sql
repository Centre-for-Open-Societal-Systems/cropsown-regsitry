INSERT INTO "public"."incoming_model_key_paths" (
    "key_path_id",
    "data_model_id",
    "key_path_for_message_id",
    "key_path_for_sender",
    "key_path_for_signature",
    "key_path_for_signature_payload",
    "is_list",
    "key_path_for_list_elements"
) VALUES
(
    '4a5d9a8e-ffef-466a-9d00-d8bd39b0337c',
    'c331ba96-ac35-4014-9d13-4ef327f6b79b',
    '$.body.header.message_id',
    '$.body.header.sender_id',
    '$.body.signature',
    '$.body[''header'',''message'']',
    'FALSE',
    ''
)
ON CONFLICT ("data_model_id") DO NOTHING;

-- ODK_TO_CROP_INTAKE: ODK Central submissions carry the signature in the header.
INSERT INTO "public"."incoming_model_key_paths" (
    "key_path_id",
    "data_model_id",
    "key_path_for_message_id",
    "key_path_for_sender",
    "key_path_for_signature",
    "key_path_for_signature_payload",
    "is_list",
    "key_path_for_list_elements"
) VALUES (
    'odk_to_crop_intake_key_path',
    'odk_to_crop_intake',
    '$.body.header.message_id',
    '$.body.header.sender_id',
    '$.body.header.signature',
    '$.body.message',
    'FALSE',
    ''
)
ON CONFLICT ("key_path_id") DO UPDATE SET
    "data_model_id" = EXCLUDED."data_model_id",
    "key_path_for_message_id" = EXCLUDED."key_path_for_message_id",
    "key_path_for_sender" = EXCLUDED."key_path_for_sender",
    "key_path_for_signature" = EXCLUDED."key_path_for_signature",
    "key_path_for_signature_payload" = EXCLUDED."key_path_for_signature_payload",
    "is_list" = EXCLUDED."is_list",
    "key_path_for_list_elements" = EXCLUDED."key_path_for_list_elements";

-- FILE_IMPORT_TO_CROP_*_INTAKE: the import worker wraps every file row as
-- {"headers": {message_id, sender_id, signature}, "body": <flat row>}.
INSERT INTO "public"."incoming_model_key_paths" (
    "key_path_id",
    "data_model_id",
    "key_path_for_message_id",
    "key_path_for_sender",
    "key_path_for_signature",
    "key_path_for_signature_payload",
    "is_list",
    "key_path_for_list_elements"
) VALUES
('file_import_to_crop_planning_intake_key_path','file_import_to_crop_planning_intake','$.headers.message_id','$.headers.sender_id','$.headers.signature','$.body','FALSE',''),
('file_import_to_crop_cultivation_intake_key_path','file_import_to_crop_cultivation_intake','$.headers.message_id','$.headers.sender_id','$.headers.signature','$.body','FALSE',''),
('file_import_to_crop_sowing_intake_key_path','file_import_to_crop_sowing_intake','$.headers.message_id','$.headers.sender_id','$.headers.signature','$.body','FALSE',''),
('file_import_to_crop_harvesting_intake_key_path','file_import_to_crop_harvesting_intake','$.headers.message_id','$.headers.sender_id','$.headers.signature','$.body','FALSE','')
ON CONFLICT ("key_path_id") DO UPDATE SET
    "data_model_id" = EXCLUDED."data_model_id",
    "key_path_for_message_id" = EXCLUDED."key_path_for_message_id",
    "key_path_for_sender" = EXCLUDED."key_path_for_sender",
    "key_path_for_signature" = EXCLUDED."key_path_for_signature",
    "key_path_for_signature_payload" = EXCLUDED."key_path_for_signature_payload",
    "is_list" = EXCLUDED."is_list",
    "key_path_for_list_elements" = EXCLUDED."key_path_for_list_elements";
