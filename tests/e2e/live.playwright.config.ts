import base from './playwright.config';
// Explicit LIVE-only runner owns its own server; never shares the offline19000 DB.
export default {...base,globalSetup:undefined,testMatch:'**/live-responsiveness.spec.ts'};
