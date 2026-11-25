/** What to tell the user when the source of a new cuboid is not known. */
export const CUBOID_SOURCE_MESSAGES = {
    pick: 'Pick where new annotations go.',
    loading: 'Loading annotation sources…',
    error: 'Could not load the annotation sources. Reload the page to add annotations.'
} as const;

export interface CuboidTarget {
    /** The source the next cuboid goes to. Null while it is not known. */
    targetSource: string | null;
    /** Why a new cuboid must not be created now: the sources load or did not load. */
    blockedReason: string | null;
    /** No source is picked and there is not exactly one source, so the user must pick one. */
    needsPick: boolean;
}

interface ResolveCuboidTargetSourceParams {
    /** The source the user picked, remembered per collection. */
    pick: string | undefined;
    /** A new source name typed on this page. Its source is created with the first cuboid. */
    typedSource: string | null;
    /** The names of the existing sources, undefined until they have loaded. */
    sourceNames: string[] | undefined;
    /** Whether the source list failed to load. */
    isError: boolean;
}

const target = (targetSource: string): CuboidTarget => ({
    targetSource,
    blockedReason: null,
    needsPick: false
});

const blocked = (blockedReason: string): CuboidTarget => ({
    targetSource: null,
    blockedReason,
    needsPick: false
});

/** Resolves the annotation source that new cuboids go to. */
export function resolveCuboidTargetSource({
    pick,
    typedSource,
    sourceNames,
    isError
}: ResolveCuboidTargetSourceParams): CuboidTarget {
    if (isError) return blocked(CUBOID_SOURCE_MESSAGES.error);
    if (!sourceNames) return blocked(CUBOID_SOURCE_MESSAGES.loading);
    if (pick && (pick === typedSource || sourceNames.includes(pick))) return target(pick);
    if (sourceNames.length === 1) return target(sourceNames[0]);
    return { targetSource: null, blockedReason: null, needsPick: true };
}

interface IsCuboidPickRemovedParams {
    pick: string;
    previousNames: string[];
    nextNames: string[];
}

/**
 * Whether the picked source left the source list, for example because another tab renamed or
 * deleted it. A typed name that was never listed is not removed.
 */
export function isCuboidPickRemoved({
    pick,
    previousNames,
    nextNames
}: IsCuboidPickRemovedParams): boolean {
    return previousNames.includes(pick) && !nextNames.includes(pick);
}
