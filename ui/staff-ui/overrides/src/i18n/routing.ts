import { defineRouting } from 'next-intl/routing';

// The registry seeds Afaan Oromoo (om) and Tigrinya (ti) next to English and Amharic
// (registry_languages_am_om_ti.sql); the upstream list stops at am, so /om and /ti
// were routed as /en/om and /en/ti and showed the 404 page.
export const routing = defineRouting({
    locales: ['en', 'es', 'fr', 'am', 'ar', 'hi', 'om', 'ti'],
    defaultLocale: 'en'
});
