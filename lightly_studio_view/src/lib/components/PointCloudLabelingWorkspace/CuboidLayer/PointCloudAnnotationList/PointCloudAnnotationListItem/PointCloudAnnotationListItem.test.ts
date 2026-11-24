import { render, screen, fireEvent } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi, type Mock } from 'vitest';
import { writable } from 'svelte/store';
import { createAnnotationFixture } from '$lib/components/PointCloudLabelingWorkspace/domain/fixtures';
import * as hooks from '$lib/hooks';
import useAuth from '$lib/hooks/useAuth/useAuth';
import type { TagView } from '$lib/services/types';
import PointCloudAnnotationListItem from './PointCloudAnnotationListItem.svelte';

vi.mock('$lib/hooks/useAuth/useAuth', () => ({ default: vi.fn() }));
vi.mock('$lib/components/SegmentTags/AddTagPopover.svelte', async () => {
    const module = await import('$lib/components/SegmentTags/AddTagPopover.mock.svelte');
    return { default: module.default };
});

vi.mock('$lib/hooks/useAnnotationLabels/useAnnotationLabels', () => ({
    useAnnotationLabels: vi.fn(() => ({ data: [] }))
}));

vi.mock(
    '$lib/components/PointCloudLabelingWorkspace/pointCloudWorkspaceLayoutContext.svelte',
    () => ({
        usePointCloudWorkspaceLayoutContext: () => () => ({ datasetId: 'dataset-1' })
    })
);
vi.mock('$lib/hooks/useTracks/useTracks.svelte', () => ({
    useTracks: () => ({ data: [], refetch: vi.fn() })
}));
vi.mock('$lib/hooks/useUpdateAnnotationsMutation/useUpdateAnnotationsMutation', () => ({
    useUpdateAnnotationsMutation: () => ({ updateAnnotations: vi.fn() })
}));
vi.mock('$lib/hooks/useUpdateTrackMutation/useUpdateTrackMutation.svelte', () => ({
    useUpdateTrackMutation: () => ({ updateParentTrack: vi.fn(), isPending: false })
}));

const cuboid = createAnnotationFixture();

const removeTagFromSampleMock = vi.fn();
const addExistingMock = vi.fn();
const createAndAddMock = vi.fn();

const collectionTag = (tag_id: string, name: string): TagView => ({
    tag_id,
    name,
    created_at: new Date(),
    updated_at: new Date()
});
// Each collection has its own tags, so picking one shows which collection the row uses.
const tagsByCollection: Record<string, TagView[]> = {
    'ground-truth': [collectionTag('tag-parked', 'parked')],
    'tick-collection': [collectionTag('tag-frame-only', 'frame only')]
};

const asLabeler = () =>
    vi.mocked(useAuth).mockReturnValue({
        user: { username: 'labeler', email: 'labeler@example.com', role: 'labeler' },
        token: 'token',
        isAuthenticated: true
    });

beforeEach(() => {
    vi.clearAllMocks();
    asLabeler();
    removeTagFromSampleMock.mockResolvedValue(undefined);
    vi.spyOn(hooks, 'useRemoveTagFromSample').mockReturnValue({
        removeTagFromSample: removeTagFromSampleMock
    } as ReturnType<typeof hooks.useRemoveTagFromSample>);
    vi.spyOn(hooks, 'useAddTagToSample').mockImplementation((params) => ({
        busy: writable(false),
        addExisting: async (tag) => {
            addExistingMock(params.getSampleId(), tag);
            params.onRefetch?.();
        },
        createAndAdd: async (name) => {
            createAndAddMock(params.getSampleId(), name);
            params.onRefetch?.();
        }
    }));
    vi.spyOn(hooks, 'useTags').mockImplementation(
        ({ collection_id }) =>
            ({
                tags: writable(tagsByCollection[collection_id] ?? []),
                loadTags: vi.fn()
            }) as unknown as ReturnType<typeof hooks.useTags>
    );
});

const defaultProps = {
    cuboid,
    color: '#3366ff',
    className: 'Vehicle',
    isSelected: false,
    onToggle: vi.fn()
};

describe('PointCloudAnnotationListItem', () => {
    it('renders the class name and toggle button', () => {
        render(PointCloudAnnotationListItem, { props: defaultProps });

        expect(screen.getByText('Vehicle')).toBeInTheDocument();
        expect(screen.getByTestId('point-cloud-annotation-list-row')).toBeInTheDocument();
    });

    it('calls onToggle with the cuboid id when the row is clicked', () => {
        const onToggle = vi.fn();
        render(PointCloudAnnotationListItem, { props: { ...defaultProps, onToggle } });

        fireEvent.click(screen.getByTestId('point-cloud-annotation-list-row'));

        expect(onToggle).toHaveBeenCalledWith(cuboid.id);
    });

    it('calls onToggle with the cuboid id when the row is clicked in edit mode', () => {
        const onToggle = vi.fn();
        render(PointCloudAnnotationListItem, {
            props: { ...defaultProps, editable: true, isSelected: true, onToggle }
        });

        const row = screen.getByTestId('point-cloud-annotation-list-row');
        expect(row).toHaveAttribute('aria-expanded', 'true');

        fireEvent.click(row);

        expect(onToggle).toHaveBeenCalledWith(cuboid.id);
    });

    it('does not show annotation details when not selected', () => {
        render(PointCloudAnnotationListItem, { props: defaultProps });

        expect(screen.queryByTestId('point-cloud-annotation-details')).not.toBeInTheDocument();
    });

    it('shows annotation details when selected', () => {
        render(PointCloudAnnotationListItem, {
            props: { ...defaultProps, isSelected: true }
        });

        expect(screen.getByTestId('point-cloud-annotation-details')).toBeInTheDocument();
    });

    it('calls onCuboidTransform with the geometry change when annotation is committed', async () => {
        const onCuboidTransform = vi.fn();
        render(PointCloudAnnotationListItem, {
            props: { ...defaultProps, isSelected: true, editable: true, onCuboidTransform }
        });

        const input = screen.getByRole('spinbutton', { name: 'location x' });
        fireEvent.focus(input);
        fireEvent.input(input, { target: { value: '99' } });
        fireEvent.blur(input);

        expect(onCuboidTransform).toHaveBeenCalledWith(
            expect.objectContaining({
                annotationId: cuboid.id,
                frameId: cuboid.frameId,
                center: [99, -2, 1]
            })
        );
    });

    it('uses the current annotation prop as base after a viewport drag updates the geometry', async () => {
        const onCuboidTransform: Mock = vi.fn();
        const { rerender } = render(PointCloudAnnotationListItem, {
            props: { ...defaultProps, isSelected: true, editable: true, onCuboidTransform }
        });

        // Panel sets X=99 and commits.
        const xInput = screen.getByRole('spinbutton', { name: 'location x' });
        fireEvent.focus(xInput);
        fireEvent.input(xInput, { target: { value: '99' } });
        fireEvent.blur(xInput);

        // Viewport drag updates the annotation prop (as $annotations would after transforms.commit).
        const draggedCuboid = { ...cuboid, center: [-20.69, 12.12, 0] as [number, number, number] };
        await rerender({
            ...defaultProps,
            cuboid: draggedCuboid,
            isSelected: true,
            editable: true,
            onCuboidTransform
        });

        // Second panel commit: L=12. Must build from drag geometry, not the first panel commit.
        const lInput = screen.getByRole('spinbutton', { name: 'dimension l' });
        fireEvent.focus(lInput);
        fireEvent.input(lInput, { target: { value: '12' } });
        fireEvent.blur(lInput);

        expect(onCuboidTransform).toHaveBeenLastCalledWith(
            expect.objectContaining({
                center: [-20.69, 12.12, 0],
                size: [12, cuboid.size[1], cuboid.size[2]]
            })
        );
    });
});

describe('PointCloudAnnotationListItem tags', () => {
    const taggedCuboid = {
        ...cuboid,
        tags: [
            { tag_id: 'tag-occluded', name: 'occluded' },
            { tag_id: 'tag-moving', name: 'moving' }
        ]
    };

    it('shows the tags of an unselected cuboid as read-only chips', () => {
        render(PointCloudAnnotationListItem, { props: { ...defaultProps, cuboid: taggedCuboid } });

        const names = screen.getAllByTestId('segment-tag-name').map((el) => el.textContent);
        expect(names).toEqual(['occluded', 'moving']);
        expect(screen.queryByTestId('remove-tag-occluded')).not.toBeInTheDocument();
        expect(screen.queryByTestId('mock-add-existing')).not.toBeInTheDocument();
    });

    it('shows nothing for tags on a cuboid without tags', () => {
        render(PointCloudAnnotationListItem, { props: defaultProps });

        expect(screen.queryByTestId('point-cloud-annotation-tags')).not.toBeInTheDocument();
    });

    it.each([false, true])(
        'shows tag controls for the selected cuboid with editable=%s',
        (editable) => {
            render(PointCloudAnnotationListItem, {
                props: { ...defaultProps, cuboid: taggedCuboid, isSelected: true, editable }
            });

            expect(screen.getByTestId('remove-tag-occluded')).toBeInTheDocument();
            expect(screen.getByTestId('mock-add-existing')).toBeInTheDocument();
        }
    );

    it('removes a tag from the cuboid and reloads the tags', async () => {
        const onTagsChange = vi.fn();
        render(PointCloudAnnotationListItem, {
            props: { ...defaultProps, cuboid: taggedCuboid, isSelected: true, onTagsChange }
        });

        await fireEvent.click(screen.getByTestId('remove-tag-occluded'));

        expect(removeTagFromSampleMock).toHaveBeenCalledWith(cuboid.id, 'tag-occluded');
        expect(onTagsChange).toHaveBeenCalled();
    });

    it('adds an existing tag of the cuboid source collection and reloads the tags', async () => {
        const onTagsChange = vi.fn();
        render(PointCloudAnnotationListItem, {
            props: { ...defaultProps, isSelected: true, onTagsChange }
        });

        await fireEvent.click(screen.getByTestId('mock-add-existing'));

        expect(addExistingMock).toHaveBeenCalledWith(
            cuboid.id,
            expect.objectContaining({ tag_id: 'tag-parked' })
        );
        expect(onTagsChange).toHaveBeenCalled();
    });

    it('creates a new tag on the cuboid and reloads the tags', async () => {
        const onTagsChange = vi.fn();
        render(PointCloudAnnotationListItem, {
            props: { ...defaultProps, isSelected: true, onTagsChange }
        });

        await fireEvent.click(screen.getByTestId('mock-add-new'));

        expect(createAndAddMock).toHaveBeenCalledWith(cuboid.id, 'Fresh Tag');
        expect(onTagsChange).toHaveBeenCalled();
    });
});
