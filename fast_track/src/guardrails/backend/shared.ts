import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
// fast_track/src/guardrails/backend -> fast_track/src/guardrails -> fast_track -> repo root
export const REPO_ROOT = resolve(__dirname, '../../../..');
export const BACKEND_DIR = resolve(REPO_ROOT, 'lightly_studio');
