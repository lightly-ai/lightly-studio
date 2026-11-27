import { describe, expect, it } from 'vitest';
import { DEFAULT_VISIBLE_TAG_COUNT, getDefaultTagIds, selectVisibleTags } from './visibleTags';

const tags = Array.from({ length: 5 }, (_, index) => ({
    tag_id: `tag-${index + 1}`,
    name: `tag ${index + 1}`,
    seq_numbers: [index]
}));

describe('visibleTags', () => {
    it('shows the first tags by default', () => {
        const visible = selectVisibleTags(tags, null);
        expect(visible).toHaveLength(DEFAULT_VISIBLE_TAG_COUNT);
        expect(visible.map((tag) => tag.tag_id)).toEqual(getDefaultTagIds(tags));
    });

    it('follows an explicit selection in list order and ignores ids of deleted tags', () => {
        const visible = selectVisibleTags(tags, ['tag-5', 'tag-2', 'gone']);
        expect(visible.map((tag) => tag.tag_id)).toEqual(['tag-2', 'tag-5']);
    });

    it('allows an empty selection', () => {
        expect(selectVisibleTags(tags, [])).toEqual([]);
    });
});
