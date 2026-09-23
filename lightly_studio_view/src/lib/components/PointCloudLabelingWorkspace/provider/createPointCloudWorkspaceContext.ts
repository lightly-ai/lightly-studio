import { setContext } from 'svelte';
import { POINT_CLOUD_WORKSPACE_CONTEXT_KEY } from './contextKey';
import { PointCloudWorkspace, type GetInputs } from './pointCloudWorkspace.svelte';
import type { PointCloudWorkspaceContext } from './types';

/**
 * Build the workspace context and register it for descendant panes via Svelte context.
 *
 * Call once at the workspace root; children read it with `usePointCloudWorkspaceContext`.
 */
export const createPointCloudWorkspaceContext = (
    getInputs: GetInputs
): PointCloudWorkspaceContext => {
    const context = new PointCloudWorkspace(getInputs);
    setContext(POINT_CLOUD_WORKSPACE_CONTEXT_KEY, context);
    return context;
};
