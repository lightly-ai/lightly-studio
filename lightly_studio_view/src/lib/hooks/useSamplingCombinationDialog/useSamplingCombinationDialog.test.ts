import { get, writable } from 'svelte/store';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useSamplingCombinationDialog } from './useSamplingCombinationDialog';

vi.mock('$lib/hooks/useTags/useTags', () => ({ useTags: vi.fn() }));
vi.mock('$lib/hooks/useImageFilters/useImageFilters', () => ({ useImageFilters: vi.fn() }));
vi.mock('$lib/hooks/useVideoFilters/useVideoFilters', () => ({ useVideoFilters: vi.fn() }));
vi.mock('$lib/hooks/useGlobalStorage', () => ({ useGlobalStorage: vi.fn() }));
vi.mock('$lib/hooks/useMetadataFilters/useMetadataFilters', () => ({
    useMetadataFilters: vi.fn()
}));
vi.mock('$lib/hooks/useStrategyBuilder', () => ({
    useStrategyBuilder: vi.fn(),
    isStrategyInstanceValid: vi.fn()
}));
vi.mock('$lib/hooks/useSamplingDialog/useSamplingDialog', () => ({ useSamplingDialog: vi.fn() }));
vi.mock('$lib/hooks/useSubmitCombinationSelection/useSubmitCombinationSelection', () => ({
    useSubmitCombinationSelection: vi.fn()
}));

const { useTags } = await import('$lib/hooks/useTags/useTags');
const { useImageFilters } = await import('$lib/hooks/useImageFilters/useImageFilters');
const { useVideoFilters } = await import('$lib/hooks/useVideoFilters/useVideoFilters');
const { useGlobalStorage } = await import('$lib/hooks/useGlobalStorage');
const { useMetadataFilters } = await import('$lib/hooks/useMetadataFilters/useMetadataFilters');
const { useStrategyBuilder, isStrategyInstanceValid } = await import(
    '$lib/hooks/useStrategyBuilder'
);
const { useSamplingDialog } = await import('$lib/hooks/useSamplingDialog/useSamplingDialog');
const { useSubmitCombinationSelection } = await import(
    '$lib/hooks/useSubmitCombinationSelection/useSubmitCombinationSelection'
);

describe('useSamplingCombinationDialog', () => {
    let filteredSampleCount: ReturnType<typeof writable<number>>;
    let metadataInfo: ReturnType<typeof writable<{ name: string; type: string }[]>>;
    let imageFilter: ReturnType<typeof writable>;
    let videoFilter: ReturnType<typeof writable>;
    let instances: ReturnType<typeof writable>;
    let isSubmitting: ReturnType<typeof writable<boolean>>;
    let submitFn: ReturnType<typeof vi.fn>;
    let resetStrategiesFn: ReturnType<typeof vi.fn>;

    const defaultParams = {
        getCollectionId: () => 'col-1',
        getIsVideoCollection: () => false
    };

    beforeEach(() => {
        vi.clearAllMocks();

        filteredSampleCount = writable(5);
        metadataInfo = writable([]);
        imageFilter = writable(null);
        videoFilter = writable(null);
        instances = writable([]);
        isSubmitting = writable(false);
        submitFn = vi.fn().mockResolvedValue(false);
        resetStrategiesFn = vi.fn();

        vi.mocked(useTags).mockReturnValue({
            tags: writable([]),
            loadTags: vi.fn().mockResolvedValue(undefined),
            setTagSelected: vi.fn()
        } as never);

        vi.mocked(useImageFilters).mockReturnValue({ imageFilter } as never);
        vi.mocked(useVideoFilters).mockReturnValue({ videoFilter } as never);
        vi.mocked(useGlobalStorage).mockReturnValue({ filteredSampleCount } as never);
        vi.mocked(useMetadataFilters).mockReturnValue({ metadataInfo } as never);

        vi.mocked(useStrategyBuilder).mockReturnValue({
            instances,
            addStrategy: vi.fn(),
            duplicateStrategy: vi.fn(),
            removeStrategy: vi.fn(),
            resetStrategies: resetStrategiesFn,
            toggleExpand: vi.fn(),
            updateParams: vi.fn()
        } as never);

        vi.mocked(useSamplingDialog).mockReturnValue({
            isSamplingDialogOpen: writable(false),
            openSamplingDialog: vi.fn(),
            closeSamplingDialog: vi.fn()
        });

        vi.mocked(useSubmitCombinationSelection).mockReturnValue({
            isSubmitting,
            loadingMessage: writable(''),
            submit: submitFn
        } as never);

        vi.mocked(isStrategyInstanceValid).mockReturnValue(true);
    });

    describe('metadataFieldNames', () => {
        it('returns only names of integer and float metadata fields', () => {
            metadataInfo.set([
                { name: 'score', type: 'float' },
                { name: 'count', type: 'integer' },
                { name: 'label', type: 'string' },
                { name: 'flag', type: 'boolean' }
            ]);

            const { metadataFieldNames } = useSamplingCombinationDialog(defaultParams);

            expect(get(metadataFieldNames)).toEqual(['score', 'count']);
        });

        it('returns empty array when metadataInfo has no numeric fields', () => {
            metadataInfo.set([{ name: 'label', type: 'string' }]);

            const { metadataFieldNames } = useSamplingCombinationDialog(defaultParams);

            expect(get(metadataFieldNames)).toEqual([]);
        });
    });

    describe('hasMetadataFields', () => {
        it('is true when metadataInfo contains numeric fields', () => {
            metadataInfo.set([{ name: 'score', type: 'float' }]);

            const { hasMetadataFields } = useSamplingCombinationDialog(defaultParams);

            expect(get(hasMetadataFields)).toBe(true);
        });

        it('is false when metadataInfo is empty', () => {
            metadataInfo.set([]);

            const { hasMetadataFields } = useSamplingCombinationDialog(defaultParams);

            expect(get(hasMetadataFields)).toBe(false);
        });
    });

    describe('noSamples', () => {
        it('is true when filteredSampleCount is 0', () => {
            filteredSampleCount.set(0);

            const { noSamples } = useSamplingCombinationDialog(defaultParams);

            expect(get(noSamples)).toBe(true);
        });

        it('is false when filteredSampleCount is greater than 0', () => {
            filteredSampleCount.set(10);

            const { noSamples } = useSamplingCombinationDialog(defaultParams);

            expect(get(noSamples)).toBe(false);
        });
    });

    describe('notEnoughSamples', () => {
        it('is true when nSamplesToSelect exceeds a positive filteredSampleCount', () => {
            filteredSampleCount.set(5);
            const { notEnoughSamples, nSamplesToSelect } = useSamplingCombinationDialog(defaultParams);
            nSamplesToSelect.set(10);

            expect(get(notEnoughSamples)).toBe(true);
        });

        it('is false when filteredSampleCount is 0', () => {
            filteredSampleCount.set(0);
            const { notEnoughSamples, nSamplesToSelect } = useSamplingCombinationDialog(defaultParams);
            nSamplesToSelect.set(10);

            expect(get(notEnoughSamples)).toBe(false);
        });

        it('is false when nSamplesToSelect does not exceed filteredSampleCount', () => {
            filteredSampleCount.set(20);
            const { notEnoughSamples, nSamplesToSelect } = useSamplingCombinationDialog(defaultParams);
            nSamplesToSelect.set(10);

            expect(get(notEnoughSamples)).toBe(false);
        });
    });

    describe('sampleCountLabel', () => {
        it('uses singular form for 1 sample', () => {
            filteredSampleCount.set(1);

            const { sampleCountLabel } = useSamplingCombinationDialog(defaultParams);

            expect(get(sampleCountLabel)).toBe('1 sample');
        });

        it('uses plural form for 0 samples', () => {
            filteredSampleCount.set(0);

            const { sampleCountLabel } = useSamplingCombinationDialog(defaultParams);

            expect(get(sampleCountLabel)).toBe('0 samples');
        });

        it('uses plural form for multiple samples', () => {
            filteredSampleCount.set(42);

            const { sampleCountLabel } = useSamplingCombinationDialog(defaultParams);

            expect(get(sampleCountLabel)).toBe('42 samples');
        });
    });

    describe('isFormValid', () => {
        it('is false when instances list is empty', () => {
            instances.set([]);

            const { isFormValid, nSamplesToSelect, selectionResultTagName } =
                useSamplingCombinationDialog(defaultParams);
            nSamplesToSelect.set(10);
            selectionResultTagName.set('my-tag');

            expect(get(isFormValid)).toBe(false);
        });

        it('is false when any strategy instance is invalid', () => {
            instances.set([{ id: 'a', type: 'diversity', params: {}, isExpanded: true }]);
            vi.mocked(isStrategyInstanceValid).mockReturnValue(false);

            const { isFormValid, nSamplesToSelect, selectionResultTagName } =
                useSamplingCombinationDialog(defaultParams);
            nSamplesToSelect.set(10);
            selectionResultTagName.set('my-tag');

            expect(get(isFormValid)).toBe(false);
        });

        it('is false when nSamplesToSelect is 0', () => {
            instances.set([{ id: 'a', type: 'diversity', params: {}, isExpanded: true }]);

            const { isFormValid, nSamplesToSelect, selectionResultTagName } =
                useSamplingCombinationDialog(defaultParams);
            nSamplesToSelect.set(0);
            selectionResultTagName.set('my-tag');

            expect(get(isFormValid)).toBe(false);
        });

        it('is false when selectionResultTagName is blank', () => {
            instances.set([{ id: 'a', type: 'diversity', params: {}, isExpanded: true }]);

            const { isFormValid, nSamplesToSelect, selectionResultTagName } =
                useSamplingCombinationDialog(defaultParams);
            nSamplesToSelect.set(10);
            selectionResultTagName.set('   ');

            expect(get(isFormValid)).toBe(false);
        });

        it('is true when instances are non-empty, all valid, count > 0, and tag name is set', () => {
            instances.set([{ id: 'a', type: 'diversity', params: {}, isExpanded: true }]);

            const { isFormValid, nSamplesToSelect, selectionResultTagName } =
                useSamplingCombinationDialog(defaultParams);
            nSamplesToSelect.set(10);
            selectionResultTagName.set('my-tag');

            expect(get(isFormValid)).toBe(true);
        });
    });

    describe('handleFormSubmit', () => {
        function makeValidForm(hook: ReturnType<typeof useSamplingCombinationDialog>) {
            instances.set([{ id: 'a', type: 'diversity', params: {}, isExpanded: true }]);
            filteredSampleCount.set(100);
            hook.nSamplesToSelect.set(10);
            hook.selectionResultTagName.set('my-tag');
        }

        it('always calls event.preventDefault()', () => {
            const { handleFormSubmit } = useSamplingCombinationDialog(defaultParams);
            const event = { preventDefault: vi.fn() } as unknown as Event;

            handleFormSubmit(event);

            expect(event.preventDefault).toHaveBeenCalled();
        });

        it('does not call submit when form is invalid', () => {
            instances.set([]);
            const { handleFormSubmit } = useSamplingCombinationDialog(defaultParams);
            const event = { preventDefault: vi.fn() } as unknown as Event;

            handleFormSubmit(event);

            expect(submitFn).not.toHaveBeenCalled();
        });

        it('does not call submit when noSamples', () => {
            filteredSampleCount.set(0);
            const hook = useSamplingCombinationDialog(defaultParams);
            makeValidForm(hook);
            filteredSampleCount.set(0);
            const event = { preventDefault: vi.fn() } as unknown as Event;

            hook.handleFormSubmit(event);

            expect(submitFn).not.toHaveBeenCalled();
        });

        it('does not call submit when notEnoughSamples', () => {
            const hook = useSamplingCombinationDialog(defaultParams);
            instances.set([{ id: 'a', type: 'diversity', params: {}, isExpanded: true }]);
            filteredSampleCount.set(5);
            hook.nSamplesToSelect.set(10);
            hook.selectionResultTagName.set('my-tag');
            const event = { preventDefault: vi.fn() } as unknown as Event;

            hook.handleFormSubmit(event);

            expect(submitFn).not.toHaveBeenCalled();
        });

        it('does not call submit when already submitting', () => {
            isSubmitting.set(true);
            const hook = useSamplingCombinationDialog(defaultParams);
            makeValidForm(hook);
            const event = { preventDefault: vi.fn() } as unknown as Event;

            hook.handleFormSubmit(event);

            expect(submitFn).not.toHaveBeenCalled();
        });

        it('calls submit with collectionId, instances, count, tag name, and filter', async () => {
            submitFn.mockResolvedValue(false);
            const hook = useSamplingCombinationDialog(defaultParams);
            makeValidForm(hook);
            imageFilter.set({ sample_filter: { tag_ids: ['t-1'] } });
            const event = { preventDefault: vi.fn() } as unknown as Event;

            hook.handleFormSubmit(event);
            await new Promise((r) => setTimeout(r, 0));

            expect(submitFn).toHaveBeenCalledWith(
                expect.objectContaining({
                    collectionId: 'col-1',
                    isVideoCollection: false,
                    nSamplesToSelect: 10,
                    selectionResultTagName: 'my-tag',
                    selectionFilter: {
                        sample_filter: { tag_ids: ['t-1'] },
                        filter_type: 'image'
                    }
                })
            );
        });
    });

    describe('buildSelectionFilter', () => {
        function makeValidForm(hook: ReturnType<typeof useSamplingCombinationDialog>) {
            instances.set([{ id: 'a', type: 'diversity', params: {}, isExpanded: true }]);
            filteredSampleCount.set(100);
            hook.nSamplesToSelect.set(10);
            hook.selectionResultTagName.set('my-tag');
        }

        it('appends filter_type "video" and uses videoFilter for video collections', async () => {
            submitFn.mockResolvedValue(false);
            const hook = useSamplingCombinationDialog({
                getCollectionId: () => 'col-1',
                getIsVideoCollection: () => true
            });
            makeValidForm(hook);
            videoFilter.set({ video_filter: { tag_ids: ['t-2'] } });
            const event = { preventDefault: vi.fn() } as unknown as Event;

            hook.handleFormSubmit(event);
            await new Promise((r) => setTimeout(r, 0));

            expect(submitFn).toHaveBeenCalledWith(
                expect.objectContaining({
                    selectionFilter: { video_filter: { tag_ids: ['t-2'] }, filter_type: 'video' }
                })
            );
        });

        it('passes null selectionFilter when imageFilter is null', async () => {
            submitFn.mockResolvedValue(false);
            imageFilter.set(null);
            const hook = useSamplingCombinationDialog(defaultParams);
            makeValidForm(hook);
            const event = { preventDefault: vi.fn() } as unknown as Event;

            hook.handleFormSubmit(event);
            await new Promise((r) => setTimeout(r, 0));

            expect(submitFn).toHaveBeenCalledWith(
                expect.objectContaining({ selectionFilter: null })
            );
        });
    });

    describe('resetForm', () => {
        it('resets strategies, nSamplesToSelect, and selectionResultTagName after successful submit', async () => {
            submitFn.mockResolvedValue(true);
            const hook = useSamplingCombinationDialog(defaultParams);
            instances.set([{ id: 'a', type: 'diversity', params: {}, isExpanded: true }]);
            filteredSampleCount.set(100);
            hook.nSamplesToSelect.set(50);
            hook.selectionResultTagName.set('result-tag');
            const event = { preventDefault: vi.fn() } as unknown as Event;

            hook.handleFormSubmit(event);
            await new Promise((r) => setTimeout(r, 0));

            expect(resetStrategiesFn).toHaveBeenCalled();
            expect(get(hook.nSamplesToSelect)).toBe(10);
            expect(get(hook.selectionResultTagName)).toBe('');
        });

        it('does not reset form when submit fails', async () => {
            submitFn.mockResolvedValue(false);
            const hook = useSamplingCombinationDialog(defaultParams);
            instances.set([{ id: 'a', type: 'diversity', params: {}, isExpanded: true }]);
            filteredSampleCount.set(100);
            hook.nSamplesToSelect.set(50);
            hook.selectionResultTagName.set('result-tag');
            const event = { preventDefault: vi.fn() } as unknown as Event;

            hook.handleFormSubmit(event);
            await new Promise((r) => setTimeout(r, 0));

            expect(resetStrategiesFn).not.toHaveBeenCalled();
            expect(get(hook.nSamplesToSelect)).toBe(50);
            expect(get(hook.selectionResultTagName)).toBe('result-tag');
        });
    });
});
