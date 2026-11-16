import type { exportCollectionSceneUpdateOptions } from '$lib/api/lightly_studio_local';

type SceneUpdateScope = Parameters<typeof exportCollectionSceneUpdateOptions>[0]['body'];

/**
 * Scopes the SceneUpdate export to the sequence open in the point-cloud details view, falling
 * back to the grid's MCAP sequence filter everywhere else.
 */
export function getSceneUpdateExportScope(
    openSequenceId: string | undefined,
    mcapSequenceFilter: SceneUpdateScope['mcap_sequence_filter']
): SceneUpdateScope {
    return openSequenceId
        ? { sequence_id: openSequenceId }
        : { mcap_sequence_filter: mcapSequenceFilter };
}
