import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));

export const FRONTEND_DIR = 'lightly_studio_view';
// fast_track/src/guardrails/frontend -> fast_track/src/guardrails -> fast_track -> repo root -> lightly_studio_view
export const FRONTEND_ABS = resolve(__dirname, '../../../..', FRONTEND_DIR);
export const FRONTEND_PREFIX = FRONTEND_DIR + '/';
