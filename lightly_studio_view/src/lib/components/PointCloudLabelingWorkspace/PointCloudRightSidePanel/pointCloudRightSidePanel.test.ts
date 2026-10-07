import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import { writable } from 'svelte/store';
import * as hooks from '$lib/hooks';
import { createAnnotationFixture } from '$lib/components/PointCloudLabelingWorkspace/domain/fixtures';
import PointCloudRightSidePanel from './PointCloudRightSidePanel.svelte';

vi.mock('$lib/hooks/useAuth/useAuth', () => ({
    default: vi.fn(() => ({ user: undefined }))
}));

vi.spyOn(hooks, 'useGlobalStorage').mockReturnValue({
    collections: writable({})
} as unknown as ReturnType<typeof hooks.useGlobalStorage>);

vi.spyOn(hooks, 'useTags').mockReturnValue({
    tags: writable([]),
    loadTags: vi.fn()
} as unknown as ReturnType<typeof hooks.useTags>);

vi.spyOn(hooks, 'useAddTagToSample').mockReturnValue({
    busy: writable(false),
    addExisting: vi.fn(),
    createAndAdd: vi.fn()
} as ReturnType<typeof hooks.useAddTagToSample>);

vi.spyOn(hooks, 'useRemoveTagFromSample').mockReturnValue({
    removeTagFromSample: vi.fn()
} as ReturnType<typeof hooks.useRemoveTagFromSample>);

const defaultProps = {
    cuboids: [],
    annotationClasses: [{ id: 'vehicle', name: 'Vehicle', color: '#3b82f6' }],
    annotationSources: [{ id: 'ground-truth', name: 'Ground Truth' }],
    selectedCuboidId: null
};

describe('PointCloudRightSidePanel', () => {
    it('shows the empty message when there are no cuboids', () => {
        render(PointCloudRightSidePanel, { props: defaultProps });

        expect(screen.getByText('No annotations')).toBeInTheDocument();
    });

    it('renders a row for each cuboid', () => {
        const cuboid = createAnnotationFixture();
        render(PointCloudRightSidePanel, { props: { ...defaultProps, cuboids: [cuboid] } });

        expect(screen.getAllByTestId('point-cloud-annotation-list-row')).toHaveLength(1);
    });

    it('hides the tags segment until the tick loads', () => {
        render(PointCloudRightSidePanel, { props: defaultProps });

        expect(screen.queryByText('Tags')).not.toBeInTheDocument();
    });

    it('shows the tags of the tick above the annotations', () => {
        render(PointCloudRightSidePanel, {
            props: {
                ...defaultProps,
                tick: {
                    sampleId: 'tick-1',
                    collectionId: 'group-collection',
                    tags: [{ tag_id: 'tag-1', name: 'lidar_dropout' }]
                }
            }
        });

        expect(screen.getByTestId('segment-tag-name')).toHaveTextContent('lidar_dropout');
        const tagsTitle = screen.getByText('Tags');
        const annotationsTitle = screen.getByText('Annotations');
        expect(
            tagsTitle.compareDocumentPosition(annotationsTitle) & Node.DOCUMENT_POSITION_FOLLOWING
        ).toBeTruthy();
    });
});
