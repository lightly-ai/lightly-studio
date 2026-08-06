import { describe, expect, it, vi, beforeEach } from 'vitest';
import { writable } from 'svelte/store';
import type { AnnotationWithPayloadView, AnnotationView } from '$lib/api/lightly_studio_local';
import { useAnnotationTileSelection } from './useAnnotationTileSelection';

const mocks = vi.hoisted(() => ({
    selectRangeByAnchor: vi.fn()
}));

vi.mock('$lib/utils/selectRangeByAnchor', () => ({
    selectRangeByAnchor: mocks.selectRangeByAnchor
}));

function buildAnnotation(sampleId: string): AnnotationWithPayloadView {
    return {
        annotation: { sample_id: sampleId } as unknown as AnnotationView
    } as unknown as AnnotationWithPayloadView;
}

describe('useAnnotationTileSelection', () => {
    let pickedAnnotationIds: ReturnType<typeof writable<Record<string, Set<string>>>>;
    let toggleSelection: ReturnType<typeof vi.fn>;
    let annotations: AnnotationWithPayloadView[];

    beforeEach(() => {
        vi.clearAllMocks();
        pickedAnnotationIds = writable({ 'col-1': new Set(['ann-1']) });
        toggleSelection = vi.fn();
        annotations = [buildAnnotation('ann-1'), buildAnnotation('ann-2')];
    });

    function build() {
        return useAnnotationTileSelection({
            getCollectionId: () => 'col-1',
            getAnnotations: () => annotations,
            pickedAnnotationIds,
            toggleSelection
        });
    }

    it('toggles the picked selection for the current collection', () => {
        const selection = build();

        selection.handleToggleSelection('ann-2');

        expect(toggleSelection).toHaveBeenCalledWith('col-1', 'ann-2');
    });

    it('does not toggle when annotationId is empty', () => {
        const selection = build();

        selection.handleToggleSelection('');

        expect(toggleSelection).not.toHaveBeenCalled();
    });

    it('forwards the current selection state and anchor to selectRangeByAnchor', () => {
        const selection = build();

        selection.handleAnnotationSelect('ann-2', 1, true);

        expect(mocks.selectRangeByAnchor).toHaveBeenCalledWith(
            expect.objectContaining({
                sampleIdsInOrder: ['ann-1', 'ann-2'],
                selectedSampleIds: new Set(['ann-1']),
                clickedSampleId: 'ann-2',
                clickedIndex: 1,
                shiftKey: true,
                anchorSampleId: null
            })
        );
    });

    it('remembers the anchor returned by selectRangeByAnchor for the next call', () => {
        mocks.selectRangeByAnchor.mockReturnValue('ann-1');
        const selection = build();

        selection.handleAnnotationSelect('ann-1', 0, false);
        selection.handleAnnotationSelect('ann-2', 1, true);

        expect(mocks.selectRangeByAnchor).toHaveBeenLastCalledWith(
            expect.objectContaining({ anchorSampleId: 'ann-1' })
        );
    });

    it('calls onSelectSample through to toggleSelection', () => {
        mocks.selectRangeByAnchor.mockImplementation(({ onSelectSample }) => {
            onSelectSample('ann-2');
            return 'ann-2';
        });
        const selection = build();

        selection.handleAnnotationSelect('ann-2', 1, false);

        expect(toggleSelection).toHaveBeenCalledWith('col-1', 'ann-2');
    });

    it('derives shiftKey from the event in handleGridItemSelect', () => {
        const selection = build();
        const event = new MouseEvent('click', { shiftKey: true });

        selection.handleGridItemSelect(event, 'ann-2', 1);

        expect(mocks.selectRangeByAnchor).toHaveBeenCalledWith(
            expect.objectContaining({ shiftKey: true })
        );
    });
});
