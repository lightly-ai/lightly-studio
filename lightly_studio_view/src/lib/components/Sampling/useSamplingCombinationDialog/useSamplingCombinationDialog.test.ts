import { get, writable } from 'svelte/store';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { StrategyInstance } from '$lib/hooks/useStrategyBuilder';
import { useSamplingCombinationDialog } from './useSamplingCombinationDialog';

vi.mock('$lib/hooks/useTags/useTags', () => ({ useTags: vi.fn() }));
vi.mock('$lib/hooks/useGlobalStorage', () => ({ useGlobalStorage: vi.fn() }));
vi.mock('$lib/hooks/useStrategyBuilder', () => ({
    isStrategyInstanceValid: vi.fn()
}));
vi.mock('$lib/hooks/useSamplingDialog/useSamplingDialog', () => ({ useSamplingDialog: vi.fn() }));
vi.mock('$lib/hooks/useSubmitCombinationSelection/useSubmitCombinationSelection', () => ({
    useSubmitCombinationSelection: vi.fn()
}));
vi.mock('./useSelectionFilter', () => ({ useSelectionFilter: vi.fn() }));

const { useTags } = await import('$lib/hooks/useTags/useTags');
const { useGlobalStorage } = await import('$lib/hooks/useGlobalStorage');
const { isStrategyInstanceValid } = await import('$lib/hooks/useStrategyBuilder');
const { useSamplingDialog } = await import('$lib/hooks/useSamplingDialog/useSamplingDialog');
const { useSubmitCombinationSelection } =
    await import('$lib/hooks/useSubmitCombinationSelection/useSubmitCombinationSelection');
const { useSelectionFilter } = await import('./useSelectionFilter');

describe('useSamplingCombinationDialog', () => {
    let filteredSampleCount: ReturnType<typeof writable<number>>;
    let instances: ReturnType<typeof writable<StrategyInstance[]>>;
    let isSubmitting: ReturnType<typeof writable<boolean>>;
    let submitFn: ReturnType<typeof vi.fn>;
    let resetStrategiesFn: ReturnType<typeof vi.fn>;
    let buildSelectionFilterFn: ReturnType<typeof vi.fn>;
    let defaultParams: Parameters<typeof useSamplingCombinationDialog>[0];

    beforeEach(() => {
        vi.clearAllMocks();

        filteredSampleCount = writable(5);
        instances = writable([]);
        isSubmitting = writable(false);
        submitFn = vi.fn().mockResolvedValue(false);
        resetStrategiesFn = vi.fn();
        buildSelectionFilterFn = vi.fn().mockReturnValue(null);

        defaultParams = {
            getCollectionId: () => 'col-1',
            getIsVideoCollection: () => false,
            instances,
            onSubmitSuccess: resetStrategiesFn
        };

        vi.mocked(useTags).mockReturnValue({
            tags: writable([]),
            loadTags: vi.fn().mockResolvedValue(undefined),
            setTagSelected: vi.fn()
        } as never);

        vi.mocked(useGlobalStorage).mockReturnValue({ filteredSampleCount } as never);

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

        vi.mocked(useSelectionFilter).mockReturnValue({
            buildSelectionFilter: buildSelectionFilterFn
        });

        vi.mocked(isStrategyInstanceValid).mockReturnValue(true);
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
        it('is false when nSamplesToSelect is null', () => {
            filteredSampleCount.set(5);
            const { notEnoughSamples, nSamplesToSelect } =
                useSamplingCombinationDialog(defaultParams);
            nSamplesToSelect.set(null);

            expect(get(notEnoughSamples)).toBe(false);
        });

        it('is true when nSamplesToSelect exceeds a positive filteredSampleCount', () => {
            filteredSampleCount.set(5);
            const { notEnoughSamples, nSamplesToSelect } =
                useSamplingCombinationDialog(defaultParams);
            nSamplesToSelect.set(10);

            expect(get(notEnoughSamples)).toBe(true);
        });

        it('is false when filteredSampleCount is 0', () => {
            filteredSampleCount.set(0);
            const { notEnoughSamples, nSamplesToSelect } =
                useSamplingCombinationDialog(defaultParams);
            nSamplesToSelect.set(10);

            expect(get(notEnoughSamples)).toBe(false);
        });

        it('is false when nSamplesToSelect does not exceed filteredSampleCount', () => {
            filteredSampleCount.set(20);
            const { notEnoughSamples, nSamplesToSelect } =
                useSamplingCombinationDialog(defaultParams);
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
            instances.set([
                { id: 'a', type: 'diversity', params: { strength: 1 }, isExpanded: true }
            ]);
            vi.mocked(isStrategyInstanceValid).mockReturnValue(false);

            const { isFormValid, nSamplesToSelect, selectionResultTagName } =
                useSamplingCombinationDialog(defaultParams);
            nSamplesToSelect.set(10);
            selectionResultTagName.set('my-tag');

            expect(get(isFormValid)).toBe(false);
        });

        it('is false when nSamplesToSelect is 0', () => {
            instances.set([
                { id: 'a', type: 'diversity', params: { strength: 1 }, isExpanded: true }
            ]);

            const { isFormValid, nSamplesToSelect, selectionResultTagName } =
                useSamplingCombinationDialog(defaultParams);
            nSamplesToSelect.set(0);
            selectionResultTagName.set('my-tag');

            expect(get(isFormValid)).toBe(false);
        });

        it('is false when nSamplesToSelect is null', () => {
            instances.set([
                { id: 'a', type: 'diversity', params: { strength: 1 }, isExpanded: true }
            ]);

            const { isFormValid, nSamplesToSelect, selectionResultTagName } =
                useSamplingCombinationDialog(defaultParams);
            nSamplesToSelect.set(null);
            selectionResultTagName.set('my-tag');

            expect(get(isFormValid)).toBe(false);
        });

        it('is false when selectionResultTagName is blank', () => {
            instances.set([
                { id: 'a', type: 'diversity', params: { strength: 1 }, isExpanded: true }
            ]);

            const { isFormValid, nSamplesToSelect, selectionResultTagName } =
                useSamplingCombinationDialog(defaultParams);
            nSamplesToSelect.set(10);
            selectionResultTagName.set('   ');

            expect(get(isFormValid)).toBe(false);
        });

        it('is true when instances are non-empty, all valid, count > 0, and tag name is set', () => {
            instances.set([
                { id: 'a', type: 'diversity', params: { strength: 1 }, isExpanded: true }
            ]);

            const { isFormValid, nSamplesToSelect, selectionResultTagName } =
                useSamplingCombinationDialog(defaultParams);
            nSamplesToSelect.set(10);
            selectionResultTagName.set('my-tag');

            expect(get(isFormValid)).toBe(true);
        });
    });

    describe('createButtonTooltip', () => {
        it('returns message about adding a strategy when instances list is empty', () => {
            instances.set([]);
            const { createButtonTooltip, nSamplesToSelect, selectionResultTagName } =
                useSamplingCombinationDialog(defaultParams);
            nSamplesToSelect.set(10);
            selectionResultTagName.set('my-tag');

            expect(get(createButtonTooltip)).toBe('Add at least 1 strategy to create a selection.');
        });

        it('returns message about completing strategy fields when any instance is invalid', () => {
            instances.set([
                { id: 'a', type: 'diversity', params: { strength: 1 }, isExpanded: true }
            ]);
            vi.mocked(isStrategyInstanceValid).mockReturnValue(false);
            const { createButtonTooltip, nSamplesToSelect, selectionResultTagName } =
                useSamplingCombinationDialog(defaultParams);
            nSamplesToSelect.set(10);
            selectionResultTagName.set('my-tag');

            expect(get(createButtonTooltip)).toBe(
                'Complete the required fields in all strategies.'
            );
        });

        it('returns message about sample count when nSamplesToSelect is null', () => {
            instances.set([
                { id: 'a', type: 'diversity', params: { strength: 1 }, isExpanded: true }
            ]);
            const { createButtonTooltip, nSamplesToSelect, selectionResultTagName } =
                useSamplingCombinationDialog(defaultParams);
            nSamplesToSelect.set(null);
            selectionResultTagName.set('my-tag');

            expect(get(createButtonTooltip)).toBe('Enter a number of samples greater than 0.');
        });

        it('returns message about sample count when nSamplesToSelect is 0', () => {
            instances.set([
                { id: 'a', type: 'diversity', params: { strength: 1 }, isExpanded: true }
            ]);
            const { createButtonTooltip, nSamplesToSelect, selectionResultTagName } =
                useSamplingCombinationDialog(defaultParams);
            nSamplesToSelect.set(0);
            selectionResultTagName.set('my-tag');

            expect(get(createButtonTooltip)).toBe('Enter a number of samples greater than 0.');
        });

        it('returns message about tag name when selectionResultTagName is blank', () => {
            instances.set([
                { id: 'a', type: 'diversity', params: { strength: 1 }, isExpanded: true }
            ]);
            const { createButtonTooltip, nSamplesToSelect, selectionResultTagName } =
                useSamplingCombinationDialog(defaultParams);
            nSamplesToSelect.set(10);
            selectionResultTagName.set('   ');

            expect(get(createButtonTooltip)).toBe('Enter a tag name.');
        });

        it('returns empty string when form is valid', () => {
            instances.set([
                { id: 'a', type: 'diversity', params: { strength: 1 }, isExpanded: true }
            ]);
            const { createButtonTooltip, nSamplesToSelect, selectionResultTagName } =
                useSamplingCombinationDialog(defaultParams);
            nSamplesToSelect.set(10);
            selectionResultTagName.set('my-tag');

            expect(get(createButtonTooltip)).toBe('');
        });
    });

    describe('handleFormSubmit', () => {
        function makeValidForm(hook: ReturnType<typeof useSamplingCombinationDialog>) {
            instances.set([
                { id: 'a', type: 'diversity', params: { strength: 1 }, isExpanded: true }
            ]);
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
            instances.set([
                { id: 'a', type: 'diversity', params: { strength: 1 }, isExpanded: true }
            ]);
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
            buildSelectionFilterFn.mockReturnValue({
                sample_filter: { tag_ids: ['t-1'] },
                filter_type: 'image'
            });
            submitFn.mockResolvedValue(false);
            const hook = useSamplingCombinationDialog(defaultParams);
            makeValidForm(hook);
            const event = { preventDefault: vi.fn() } as unknown as Event;

            hook.handleFormSubmit(event);
            await new Promise((r) => setTimeout(r, 0));

            expect(submitFn).toHaveBeenCalledWith(
                expect.objectContaining({
                    collectionId: 'col-1',
                    isVideoCollection: false,
                    nSamplesToSelect: 10,
                    selectionResultTagName: 'my-tag',
                    selectionFilter: { sample_filter: { tag_ids: ['t-1'] }, filter_type: 'image' }
                })
            );
        });
    });

    describe('updateAbsolute', () => {
        it('updates nSamplesToSelect and derives percentageToSelect from filteredSampleCount', () => {
            filteredSampleCount.set(1000);
            const { updateAbsolute, nSamplesToSelect, percentageToSelect } =
                useSamplingCombinationDialog(defaultParams);

            updateAbsolute(100);

            expect(get(nSamplesToSelect)).toBe(100);
            expect(get(percentageToSelect)).toBe(10);
        });

        it('rounds percentageToSelect to the nearest integer', () => {
            filteredSampleCount.set(1000);
            const { updateAbsolute, percentageToSelect } =
                useSamplingCombinationDialog(defaultParams);

            updateAbsolute(333);

            expect(get(percentageToSelect)).toBe(33);
        });

        it('sets percentageToSelect to 0 when filteredSampleCount is 0', () => {
            filteredSampleCount.set(0);
            const { updateAbsolute, percentageToSelect } =
                useSamplingCombinationDialog(defaultParams);

            updateAbsolute(10);

            expect(get(percentageToSelect)).toBe(0);
        });

        it('sets nSamplesToSelect and percentageToSelect to null when input is cleared', () => {
            filteredSampleCount.set(1000);
            const { updateAbsolute, nSamplesToSelect, percentageToSelect } =
                useSamplingCombinationDialog(defaultParams);

            updateAbsolute(NaN);

            expect(get(nSamplesToSelect)).toBeNull();
            expect(get(percentageToSelect)).toBeNull();
        });

        it('updates percentageToSelect reactively when filteredSampleCount changes and user has not entered a percentage', () => {
            filteredSampleCount.set(0);
            const { percentageToSelect } = useSamplingCombinationDialog(defaultParams);

            filteredSampleCount.set(100);

            expect(get(percentageToSelect)).toBe(10); // default nSamplesToSelect=10, 10/100*100=10
        });
    });

    describe('updatePercentage', () => {
        it('updates percentageToSelect and derives nSamplesToSelect from filteredSampleCount', () => {
            filteredSampleCount.set(1000);
            const { updatePercentage, nSamplesToSelect, percentageToSelect } =
                useSamplingCombinationDialog(defaultParams);

            updatePercentage(10);

            expect(get(percentageToSelect)).toBe(10);
            expect(get(nSamplesToSelect)).toBe(100);
        });

        it('rounds nSamplesToSelect to the nearest integer', () => {
            filteredSampleCount.set(1000);
            const { updatePercentage, nSamplesToSelect } =
                useSamplingCombinationDialog(defaultParams);

            updatePercentage(33);

            expect(get(nSamplesToSelect)).toBe(330);
        });

        it('sets nSamplesToSelect to 0 when filteredSampleCount is 0', () => {
            filteredSampleCount.set(0);
            const { updatePercentage, nSamplesToSelect } =
                useSamplingCombinationDialog(defaultParams);

            updatePercentage(50);

            expect(get(nSamplesToSelect)).toBe(0);
        });

        it('allows percentage above 100 without clamping', () => {
            filteredSampleCount.set(100);
            const { updatePercentage, nSamplesToSelect, percentageToSelect } =
                useSamplingCombinationDialog(defaultParams);

            updatePercentage(150);

            expect(get(percentageToSelect)).toBe(150);
            expect(get(nSamplesToSelect)).toBe(150);
        });

        it('sets nSamplesToSelect and percentageToSelect to null when input is cleared', () => {
            filteredSampleCount.set(1000);
            const { updatePercentage, nSamplesToSelect, percentageToSelect } =
                useSamplingCombinationDialog(defaultParams);

            updatePercentage(NaN);

            expect(get(nSamplesToSelect)).toBeNull();
            expect(get(percentageToSelect)).toBeNull();
        });

        it('preserves the user-entered percentage when filteredSampleCount changes after entry', () => {
            filteredSampleCount.set(121);
            const { updatePercentage, nSamplesToSelect, percentageToSelect } =
                useSamplingCombinationDialog(defaultParams);

            updatePercentage(100);
            filteredSampleCount.set(116);

            expect(get(percentageToSelect)).toBe(100);
            expect(get(nSamplesToSelect)).toBe(121);
        });
    });

    describe('resetForm', () => {
        it('calls onSubmitSuccess, resets nSamplesToSelect, and selectionResultTagName after successful submit', async () => {
            submitFn.mockResolvedValue(true);
            const hook = useSamplingCombinationDialog(defaultParams);
            instances.set([
                { id: 'a', type: 'diversity', params: { strength: 1 }, isExpanded: true }
            ]);
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
            instances.set([
                { id: 'a', type: 'diversity', params: { strength: 1 }, isExpanded: true }
            ]);
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
