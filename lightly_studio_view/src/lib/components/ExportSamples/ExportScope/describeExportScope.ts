interface DescribeExportScopeParams {
    /** Number of samples matching the current filters. */
    count: number;
    /** Sample type of the collection, e.g. 'image' or 'video'. */
    sampleType: string | undefined;
    /** Names of the tags in the active tag filter. Empty when no tag filter is active. */
    tagNames: string[];
}

interface DescribeExportScopeReturn {
    /** The sentence that states what the export contains. */
    summary: string;
    /** A hint on how to export a single tag, shown only when no tag filter is active. */
    hint: string | undefined;
}

/** Describes which samples an export contains, based on the active filters. */
export function describeExportScope({
    count,
    sampleType,
    tagNames
}: DescribeExportScopeParams): DescribeExportScopeReturn {
    const noun = getSampleNoun(sampleType, count);
    const base = `Exports the ${count} ${noun} matching your current filters`;
    if (tagNames.length === 0) {
        return { summary: `${base}.`, hint: 'To export one tag, filter by that tag first.' };
    }
    const tagWord = tagNames.length === 1 ? 'tag' : 'tags';
    return { summary: `${base} in ${tagWord} ${tagNames.join(' or ')}.`, hint: undefined };
}

function getSampleNoun(sampleType: string | undefined, count: number): string {
    const singular = sampleType === 'image' || sampleType === 'video' ? sampleType : 'sample';
    return count === 1 ? singular : `${singular}s`;
}
