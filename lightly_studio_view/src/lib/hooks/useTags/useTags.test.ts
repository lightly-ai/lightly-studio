import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useTags } from './useTags';
import { get } from 'svelte/store';
import type { TagView } from '$lib/services/types';
import * as lightly_studio_local from '$lib/api/lightly_studio_local';
import { waitFor } from '@testing-library/svelte';
import { useGlobalStorage } from '../useGlobalStorage';

type QueryResult = {
    data: TagView[] | null;
    isLoading: boolean;
    error: Error | null;
};

const mockTags: TagView[] = [
    { tag_id: '1', name: 'Tag 1', description: 'Description 1', kind: 'sample' },
    { tag_id: '2', name: 'Tag 2', description: 'Description 2', kind: 'annotation' },
    { tag_id: '3', name: 'Tag 3', description: 'Description 3', kind: 'sample' }
];

describe('useTags Hook', () => {
    const setup = (
        result: QueryResult = {
            data: mockTags,
            isLoading: false,
            error: null
        }
    ) => {
        return vi.spyOn(lightly_studio_local, 'readTags').mockResolvedValue({
            ...result,
            error: undefined
        });
    };

    beforeEach(() => {
        // Reset all mocks before each test
        vi.clearAllMocks();
        vi.resetAllMocks();
        setup();

        const { tags } = useGlobalStorage();
        tags.set([]);
    });

    it('should initialize with empty selected tags', () => {
        const { tagsSelected } = useTags({ dataset_id: '123' });
        expect(get(tagsSelected).size).toBe(0);
    });

    it('should return all tags when no kind filter is provided', async () => {
        const { tags } = useTags({ dataset_id: '123' });

        await waitFor(() => expect(get(tags)).toEqual(mockTags));
    });

    it('should filter tags by kind', async () => {
        const { tags } = useTags({
            dataset_id: '123',
            kind: ['sample']
        });

        await waitFor(() => expect(get(tags)).toHaveLength(2));
        await waitFor(() => expect(get(tags).every((tag) => tag.kind === 'sample')).toBe(true));
    });

    it('should toggle tag selection', () => {
        const { tagsSelected, tagSelectionToggle } = useTags({ dataset_id: '123' });

        // Toggle tag on
        tagSelectionToggle('1');
        expect(get(tagsSelected).has('1')).toBe(true);

        // Toggle same tag off
        tagSelectionToggle('1');
        expect(get(tagsSelected).has('1')).toBe(false);
    });

    it('should handle loading state', () => {
        // Mock loading state
        setup({ data: null, isLoading: true, error: null });

        const { isLoading, tags } = useTags({ dataset_id: '123' });

        expect(get(isLoading)).toBe(true);
        expect(get(tags)).toEqual([]);
    });

    it('should handle error state', async () => {
        const testError = new Error('Test error');

        // Mock error state
        vi.spyOn(lightly_studio_local, 'readTags').mockRejectedValueOnce(testError);

        const { error, tags } = useTags({ dataset_id: '123' });

        expect(get(tags)).toEqual([]);

        await waitFor(() => {
            expect(get(error)).toEqual(testError);
        });
    });

    it('should call createQuery with correct parameters', () => {
        const dataset_id = '123';
        const createQuery = setup();
        useTags({ dataset_id });

        expect(createQuery).toHaveBeenCalledWith({
            path: {
                dataset_id
            }
        });
    });

    it('should handle multiple tag selections', () => {
        const { tagsSelected, tagSelectionToggle, clearTagsSelected } = useTags({
            dataset_id: '123'
        });
        clearTagsSelected();
        tagSelectionToggle('1');
        tagSelectionToggle('2');

        const selected = get(tagsSelected);
        expect(selected.size).toBe(2);
        expect(selected.has('1')).toBe(true);
        expect(selected.has('2')).toBe(true);
    });

    it('should maintain selected tags when filter changes', async () => {
        const { tagsSelected, tagSelectionToggle, tags, clearTagsSelected } = useTags({
            dataset_id: '123',
            kind: ['sample']
        });
        clearTagsSelected();
        tagSelectionToggle('1');

        await waitFor(() => expect(get(tagsSelected).has('1')).toBe(true));
        await waitFor(() => expect(get(tags).length).toBe(2)); // Only sample tags
    });

    it('should maintain separate tag selections for different datasets', () => {
        const { tagsSelected: tags1Selected, tagSelectionToggle: toggle1, clearTagsSelected: clear1 } = useTags({
            dataset_id: 'dataset1'
        });
        const { tagsSelected: tags2Selected, tagSelectionToggle: toggle2, clearTagsSelected: clear2 } = useTags({
            dataset_id: 'dataset2'
        });

        clear1();
        clear2();

        // Select tag '1' in dataset1
        toggle1('1');
        expect(get(tags1Selected).has('1')).toBe(true);
        expect(get(tags2Selected).has('1')).toBe(false);

        // Select tag '2' in dataset2
        toggle2('2');
        expect(get(tags1Selected).has('1')).toBe(true);
        expect(get(tags1Selected).has('2')).toBe(false);
        expect(get(tags2Selected).has('2')).toBe(true);
        expect(get(tags2Selected).has('1')).toBe(false);
    });

    it('should clear tags selected for specific dataset only', () => {
        const { tagsSelected: tags1Selected, tagSelectionToggle: toggle1, clearTagsSelected: clear1 } = useTags({
            dataset_id: 'dataset1'
        });
        const { tagsSelected: tags2Selected, tagSelectionToggle: toggle2, clearTagsSelected: clear2 } = useTags({
            dataset_id: 'dataset2'
        });

        toggle1('1');
        toggle1('2');
        toggle2('3');

        clear1();

        expect(get(tags1Selected).size).toBe(0);
        expect(get(tags2Selected).has('3')).toBe(true);
    });

    it('should toggle tags independently across datasets', () => {
        const { tagsSelected: tags1Selected, tagSelectionToggle: toggle1 } = useTags({
            dataset_id: 'dataset1'
        });
        const { tagsSelected: tags2Selected, tagSelectionToggle: toggle2 } = useTags({
            dataset_id: 'dataset2'
        });

        // Toggle same tag ID in different datasets
        toggle1('1');
        toggle2('1');

        expect(get(tags1Selected).has('1')).toBe(true);
        expect(get(tags2Selected).has('1')).toBe(true);

        // Toggle off in dataset1 only
        toggle1('1');

        expect(get(tags1Selected).has('1')).toBe(false);
        expect(get(tags2Selected).has('1')).toBe(true);
    });

    it('should persist selections when creating multiple instances for same dataset', () => {
        const { tagsSelected: tags1Selected, tagSelectionToggle: toggle1 } = useTags({
            dataset_id: 'dataset1'
        });
        const { tagsSelected: tags1SelectedAgain } = useTags({
            dataset_id: 'dataset1'
        });

        toggle1('1');
        toggle1('2');

        expect(get(tags1SelectedAgain).has('1')).toBe(true);
        expect(get(tags1SelectedAgain).has('2')).toBe(true);
        expect(get(tags1SelectedAgain).size).toBe(2);
    });
});
