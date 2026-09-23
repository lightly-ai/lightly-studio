import { getContext } from 'svelte';
import { POINT_CLOUD_WORKSPACE_CONTEXT_KEY } from './contextKey';
import type { PointCloudWorkspaceContext } from './types';

/**
 * Read the workspace context registered by `createPointCloudWorkspaceContext`.
 *
 * Throws when called outside a workspace subtree so misuse fails loudly instead of returning
 * `undefined`.
 */
export const usePointCloudWorkspaceContext = (): PointCloudWorkspaceContext => {
    const context = getContext<PointCloudWorkspaceContext>(POINT_CLOUD_WORKSPACE_CONTEXT_KEY);
    if (!context) {
        throw new Error('PointCloudWorkspaceContext not found');
    }
    return context;
};
