import {
    getHiddenSourceMessage,
    LOADING_SOURCES_MESSAGE,
    PICK_SOURCE_MESSAGE,
    SOURCES_ERROR_MESSAGE
} from './messages';

/** The backend default source new annotations land in when no name is sent. */
export const DEFAULT_SOURCE_NAME = 'annotation';

interface ResolveTargetSourceParams {
    /** The source the user picked, remembered per collection. */
    pick: string | undefined;
    /** A new source name typed on this page. It may name a source that is not created yet. */
    typedSource: string | null | undefined;
    /** The names of the existing sources, undefined until they have loaded. */
    sourceNames: string[] | undefined;
    /** Whether the source list failed to load. */
    isError: boolean;
    /** The sources whose annotations are all hidden on this sample. */
    hiddenSources: string[];
}

interface ResolvedTargetSource {
    /** The source new annotations go to, or null while it is unknown or not picked. */
    targetSource: string | null;
    /** Why new annotations must not be created, or null when they may. */
    blockedReason: string | null;
}

/**
 * Returns the source new annotations go to, and why they must not be created, if so.
 *
 * Until the source list has loaded the target is unknown. A pick wins when its source exists or
 * it was typed on this page, so a pick of a source deleted elsewhere is dropped instead of
 * re-created. Then comes the only source. With several sources and no pick, the user must pick,
 * so nothing lands in a source by accident. With no source the
 * backend default is created on the first annotation. A hidden target blocks new annotations.
 */
export const resolveTargetSource = (params: ResolveTargetSourceParams): ResolvedTargetSource => {
    const { sourceNames } = params;
    if (!sourceNames) {
        const blockedReason = params.isError ? SOURCES_ERROR_MESSAGE : LOADING_SOURCES_MESSAGE;
        return { targetSource: null, blockedReason };
    }
    const targetSource = pickTargetSource({ ...params, sourceNames });
    if (targetSource === null) return { targetSource, blockedReason: PICK_SOURCE_MESSAGE };
    const isHidden = params.hiddenSources.includes(targetSource);
    return { targetSource, blockedReason: isHidden ? getHiddenSourceMessage(targetSource) : null };
};

/**
 * Whether the picked source left the source list between two loads of it. The source was
 * deleted or renamed elsewhere. From this page the two look the same: a rename on DuckDB also
 * gives the source a new ID. So the pick is not moved to a new name. A picked name that was not
 * in the previous list is a new source the user typed, and it was not removed.
 */
export const isPickRemoved = ({
    pick,
    previousNames,
    nextNames
}: {
    pick: string;
    previousNames: string[];
    nextNames: string[];
}): boolean => previousNames.includes(pick) && !nextNames.includes(pick);

const pickTargetSource = ({
    pick,
    typedSource,
    sourceNames
}: ResolveTargetSourceParams & { sourceNames: string[] }): string | null => {
    if (pick && (sourceNames.includes(pick) || pick === typedSource)) return pick;
    if (sourceNames.length === 0) return DEFAULT_SOURCE_NAME;
    return sourceNames.length === 1 ? sourceNames[0] : null;
};
