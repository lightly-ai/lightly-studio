import { PUBLIC_LIGHTLY_STUDIO_API_URL } from '$env/static/public';
import type { CreateClientConfig } from './lightly_studio_local/client.gen';

// Called by the generated client on initialization. Reading the base URL from the app env,
// not at client generation, keeps the dev server URL out of the built GUI, so the GUI works
// on whichever port the backend serves it.
export const createClientConfig: CreateClientConfig = (config) => ({
    ...config,
    baseUrl: PUBLIC_LIGHTLY_STUDIO_API_URL
});
