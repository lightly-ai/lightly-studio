import type { GitHub } from '@actions/github/lib/utils';

/**
 * A hydrated Octokit client, shared by the bot and the guardrails. Type-only
 * import — it erases at runtime, so referencing `Octokit` never pulls
 * `@actions/github` into a bundle. This keeps the guardrails' local git path
 * (which has no Actions runtime) free of the dependency; the bot always loads
 * it in CI regardless.
 */
export type Octokit = InstanceType<typeof GitHub>;
