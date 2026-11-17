import { matchSources } from '../searchRanking';

interface ListSourceRowsParams {
    /** The annotation sources, undefined while they load. */
    sources: { collection_id: string; name: string }[] | undefined;
    query: string;
    excludeSourceId?: string;
    disabledSources?: { names: string[]; note: string };
    allowCreate: boolean;
    onPick: (sourceName: string) => void;
}

/**
 * The rows of the source search: the matching sources, then a create row for a typed name that
 * matches no source, when creating is allowed. The match ignores case, like the search, so
 * `gt` is not offered next to `GT`. Until the sources load, a typed name may already exist, so it
 * is not offered as new.
 */
export const listSourceRows = ({
    sources,
    query,
    excludeSourceId,
    disabledSources,
    allowCreate,
    onPick
}: ListSourceRowsParams) => {
    const listed = (sources ?? []).filter((source) => source.collection_id !== excludeSourceId);
    const sourceRows = matchSources({ sources: listed, query }).map((source) => {
        const isDisabled = disabledSources?.names.includes(source.name) ?? false;
        return {
            value: source.collection_id,
            label: source.name,
            disabled: isDisabled,
            note: isDisabled ? disabledSources?.note : undefined,
            onPick: () => onPick(source.name)
        };
    });
    const name = query.trim();
    const canCreate =
        allowCreate &&
        sources !== undefined &&
        name !== '' &&
        !sources.some((source) => source.name.toLowerCase() === name.toLowerCase());
    if (!canCreate) return sourceRows;
    const createRow = { value: 'create', label: name, isCreate: true, onPick: () => onPick(name) };
    return [...sourceRows, createRow];
};
