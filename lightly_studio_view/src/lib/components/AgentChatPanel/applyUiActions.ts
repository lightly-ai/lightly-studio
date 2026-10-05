import type { TurnDoneEvent } from '$lib/api/lightly_studio_local/types.gen';

type UiAction = TurnDoneEvent['ui_actions'][number];

interface UiActionHandlers {
    /** Filters the grid to one tag. */
    showTag: (tagId: string) => Promise<void>;
    /** Filters the grid to a list of samples. */
    showSamples: (sampleIds: string[]) => void;
    /** Reloads the tags and the samples, because a tool changed data. */
    refreshData: () => Promise<void>;
}

/**
 * Applies the GUI actions of an agent turn in their order. Each handler replaces the grid
 * filter of the one before, so the last action decides what the grid shows.
 */
export async function applyUiActions(
    actions: UiAction[],
    handlers: UiActionHandlers
): Promise<void> {
    for (const action of actions) {
        if (action.type === 'select_tag') {
            await handlers.showTag(action.tag_id);
        } else if (action.type === 'show_samples') {
            handlers.showSamples(action.sample_ids);
        } else {
            await handlers.refreshData();
        }
    }
}
