interface TreeOpenParams {
    groupBy: string;
    /** The groups that can open: those with rows. */
    groupIds: string[];
    /** All groups, also empty ones; more than 3 start collapsed. */
    groupCount: number;
    searching: boolean;
}

/**
 * Which tree groups are open. More than 3 groups start collapsed. A search forces every group
 * open without changing the user's choice, which applies again once the search clears.
 */
export function useTreeOpenState(getParams: () => TreeOpenParams) {
    const userOpen = $state<Record<string, boolean>>({});
    const key = (id: string) => `${getParams().groupBy}:${id}`;
    const chosenOpen = (id: string) => userOpen[key(id)] ?? getParams().groupCount <= 3;
    const isOpen = (id: string) => getParams().searching || chosenOpen(id);

    return {
        isOpen,
        toggle: (id: string) => {
            userOpen[key(id)] = !isOpen(id);
        },
        /** Whether any group is open by the user's choice, ignoring the search. */
        get anyOpen() {
            return getParams().groupIds.some(chosenOpen);
        },
        setAll: (open: boolean) => {
            for (const id of getParams().groupIds) userOpen[key(id)] = open;
        }
    };
}
