import { get, writable } from 'svelte/store';

export interface ReversibleAction {
    id: string;
    description: string;
    execute: () => void | Promise<void>;
    timestamp: Date;
    groupId: string;
}

const reversibleActions = writable<ReversibleAction[]>([]);

export const useReversibleActions = () => {
    return {
        reversibleActions,
        addReversibleAction: (action: ReversibleAction) => {
            reversibleActions.update((actions) => [action, ...actions].slice(0, 50)); // Keep last 50 actions
        },
        executeReversibleAction: async (actionId: string) => {
            const actions = get(reversibleActions);
            const action = actions.find((a) => a.id === actionId);
            if (action) {
                await action.execute();
                // Remove this action and all actions added after it
                const actionIndex = actions.findIndex((a) => a.id === actionId);
                reversibleActions.update((actions) => actions.slice(actionIndex + 1));
            }
        },
        clearReversibleActions: () => {
            reversibleActions.set([]);
        },
        clearReversibleActionsByGroupId: (groupId: string) => {
            reversibleActions.update((actions) =>
                actions.filter((action) => action.groupId !== groupId)
            );
        },
        hasReversibleActions: () => {
            return get(reversibleActions).length > 0;
        }
    };
};
