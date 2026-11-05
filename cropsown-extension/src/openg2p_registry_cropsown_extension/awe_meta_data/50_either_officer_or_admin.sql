-- Databases seeded before this change hold these six stages with mode 'all'
-- (the named officer alone). Set them in place to 'any-n' with one decision so
-- the named officer or admin completes the stage; stage and rule ids, policy
-- keys and bindings are unchanged, and the statement is a no-op once applied.
UPDATE public.approval_stage SET mode='any-n', mode_value=1, updated_at=NOW()
WHERE id IN (
    '8d585afa-4c07-5d3c-b2c6-250476b64f95',
    'cbe6cd87-08c3-519a-b857-6c37cb625d52',
    '7e7b6cd3-21ae-5fcf-9f39-aa8f8dd73264',
    '01e246a2-432c-51f0-8d0c-a3884cb02b16',
    'd06c1b3f-ee31-5b79-9f82-73333c701806',
    'b3cf7122-ecff-5338-a6d9-40ed4fe02614'
)
  AND (mode <> 'any-n' OR mode_value IS DISTINCT FROM 1);

-- Display name only: the stage ids, orders, modes and rules are untouched.
UPDATE public.approval_stage SET name='Stage 1 officers', updated_at=NOW()
WHERE id IN (
    '8d585afa-4c07-5d3c-b2c6-250476b64f95',
    '7e7b6cd3-21ae-5fcf-9f39-aa8f8dd73264',
    'd06c1b3f-ee31-5b79-9f82-73333c701806',
    'fb4ec737-a1c4-5a5b-a4a9-1b788c16cc68'
)
  AND name <> 'Stage 1 officers';
-- Display name only: the stage ids, orders, modes and rules are untouched.
UPDATE public.approval_stage SET name='Stage 2 officers', updated_at=NOW()
WHERE id IN (
    'cbe6cd87-08c3-519a-b857-6c37cb625d52',
    '01e246a2-432c-51f0-8d0c-a3884cb02b16',
    'b3cf7122-ecff-5338-a6d9-40ed4fe02614',
    '5cc7ff63-487e-5861-8a87-38454ee8466a'
)
  AND name <> 'Stage 2 officers';
