import type { InfiniteData } from '@tanstack/svelte-query';
import type { ImageView, ReadImagesResponse } from '$lib/api/lightly_studio_local';
import { describe, expect, it } from 'vitest';
import { patchSamplesTags } from './patchSamplesTags';

const trainTag = {
    tag_id: 'tag-train',
    name: 'train',
    kind: 'sample',
    created_at: new Date('2024-01-01'),
    updated_at: new Date('2024-01-01')
} satisfies ImageView['tags'][number];

function makeSample(sample_id: string, tags: ImageView['tags'] = []): ImageView {
    return { sample_id, file_name: `${sample_id}.png`, tags } as ImageView;
}

function makeData(pages: ImageView[][]): InfiniteData<ReadImagesResponse> {
    return {
        pages: pages.map((data) => ({ data, total_count: data.length }) as ReadImagesResponse),
        pageParams: pages.map((_, index) => index)
    };
}

function tagIdsOf(
    data: InfiniteData<ReadImagesResponse> | undefined,
    sampleId: string
): string[] | undefined {
    const sample = data?.pages.flatMap((page) => page.data).find((s) => s.sample_id === sampleId);
    return sample?.tags.map((tag) => tag.tag_id);
}

describe('patchSamplesTags', () => {
    it('adds the tag only to the targeted samples across pages', () => {
        const data = makeData([[makeSample('a'), makeSample('b')], [makeSample('c')]]);

        const patched = patchSamplesTags(data, {
            sampleIds: ['a', 'c'],
            tag: trainTag,
            action: 'add'
        });

        expect(tagIdsOf(patched, 'a')).toEqual(['tag-train']);
        expect(tagIdsOf(patched, 'c')).toEqual(['tag-train']);
        expect(tagIdsOf(patched, 'b')).toEqual([]);
        // Page structure and metadata survive the patch.
        expect(patched?.pages.map((page) => page.data.length)).toEqual([2, 1]);
        expect(patched?.pageParams).toEqual([0, 1]);
    });

    it('does not duplicate a tag the sample already has', () => {
        const data = makeData([[makeSample('a', [trainTag])]]);

        const patched = patchSamplesTags(data, {
            sampleIds: ['a'],
            tag: trainTag,
            action: 'add'
        });

        expect(tagIdsOf(patched, 'a')).toEqual(['tag-train']);
    });

    it('removes the tag and leaves the sample’s other tags in place', () => {
        const otherTag = { ...trainTag, tag_id: 'tag-other', name: 'other' };
        const data = makeData([
            [makeSample('a', [trainTag, otherTag]), makeSample('b', [trainTag])]
        ]);

        const patched = patchSamplesTags(data, {
            sampleIds: ['a'],
            tag: trainTag,
            action: 'remove'
        });

        expect(tagIdsOf(patched, 'a')).toEqual(['tag-other']);
        expect(tagIdsOf(patched, 'b')).toEqual(['tag-train']);
    });

    it('does not mutate the input data', () => {
        const sample = makeSample('a');
        const data = makeData([[sample]]);

        patchSamplesTags(data, { sampleIds: ['a'], tag: trainTag, action: 'add' });

        expect(sample.tags).toEqual([]);
    });

    it('returns undefined when nothing is cached', () => {
        expect(
            patchSamplesTags(undefined, { sampleIds: ['a'], tag: trainTag, action: 'add' })
        ).toBeUndefined();
    });
});
