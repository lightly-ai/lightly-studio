import { fireEvent, render, screen } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { writable } from 'svelte/store';
import { page } from '$app/state';
import type { AnnotationView } from '$lib/api/lightly_studio_local';
import * as hooks from '$lib/hooks';
import useAuth from '$lib/hooks/useAuth/useAuth';
import type { TagView } from '$lib/services/types';
import SampleDetailsSidePanelAnnotation from './SampleDetailsSidePanelAnnotation.svelte';

const { refetchAnnotationMock, workflowContext } = vi.hoisted(() => ({
    refetchAnnotationMock: vi.fn(),
    workflowContext: { value: undefined as { canEdit: boolean } | undefined }
}));

vi.mock('$lib/contexts/WorkflowFile.svelte', async (importOriginal) => ({
    ...(await importOriginal<typeof import('$lib/contexts/WorkflowFile.svelte')>()),
    useWorkflowFileContext: () => workflowContext.value
}));

vi.mock('$lib/hooks/useAuth/useAuth', () => ({ default: vi.fn() }));
vi.mock('$lib/components/SegmentTags/AddTagPopover.svelte', async () => {
    const module = await import('$lib/components/SegmentTags/AddTagPopover.mock.svelte');
    return { default: module.default };
});

vi.mock('$lib/hooks/useSaveAnnotationClassColor/useSaveAnnotationClassColor.svelte', () => ({
    useSaveAnnotationClassColor: () => ({ saveClassColor: vi.fn().mockResolvedValue(undefined) })
}));

vi.mock('$app/state', async () => {
    const { writable } = await import('svelte/store');
    return {
        page: {
            params: { collection_id: 'images' },
            data: { globalStorage: { isEditingMode: writable(true) } }
        }
    };
});
vi.mock('$lib/hooks/useAnnotationLabels/useAnnotationLabels', () => ({
    useAnnotationLabels: () => ({ data: [] })
}));
vi.mock('$lib/hooks/useAnnotation/useAnnotation', () => ({
    useAnnotation: () => ({
        annotation: {},
        updateAnnotation: vi.fn(),
        refetch: refetchAnnotationMock
    })
}));
vi.mock('$lib/hooks/useUpdateAnnotationsMutation/useUpdateAnnotationsMutation', () => ({
    useUpdateAnnotationsMutation: () => ({ updateAnnotations: vi.fn() })
}));
// The copy control mounts in editing mode; keep its data hooks isolated from the API.
vi.mock('$lib/hooks/useAnnotationCollections/useAnnotationCollections', () => ({
    useAnnotationCollections: () => ({ data: [], isSuccess: true })
}));
vi.mock('$lib/hooks/useCreateAnnotation/useCreateAnnotation', () => ({
    useCreateAnnotation: () => ({ createAnnotation: vi.fn() })
}));
vi.mock('$lib/hooks/useDeleteAnnotation/useDeleteAnnotation', () => ({
    useDeleteAnnotation: () => ({ deleteAnnotation: vi.fn() })
}));
const annotation: AnnotationView = {
    sample_id: 'annotation',
    parent_sample_id: 'image',
    annotation_collection_id: 'predictions',
    annotation_type: 'object_detection',
    annotation_label: { annotation_label_name: 'hole' },
    created_at: new Date()
};
const defaultProps = {
    annotation,
    isSelected: false,
    onClick: vi.fn(),
    onUpdate: vi.fn(),
    onToggleShowAnnotation: vi.fn(),
    onDeleteAnnotation: vi.fn()
};

const removeTagFromSampleMock = vi.fn();
const addExistingMock = vi.fn();
const createAndAddMock = vi.fn();

const collectionTag = (tag_id: string, name: string): TagView => ({
    tag_id,
    name,
    created_at: new Date(),
    updated_at: new Date()
});
// Each collection has its own tags, so picking one shows which collection the editor uses.
const tagsByCollection: Record<string, TagView[]> = {
    predictions: [collectionTag('tag-truncated', 'truncated')],
    images: [collectionTag('tag-image-only', 'image only')]
};

const asRole = (role: 'viewer' | 'labeler') =>
    vi.mocked(useAuth).mockReturnValue({
        user: { username: role, email: `${role}@example.com`, role },
        token: 'token',
        isAuthenticated: true
    });

const taggedAnnotation: AnnotationView = {
    ...annotation,
    tags: [
        { tag_id: 'tag-occluded', name: 'occluded' },
        { tag_id: 'tag-blurry', name: 'blurry' }
    ]
};

describe('SampleDetailsSidePanelAnnotation tags', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        workflowContext.value = undefined;
        page.data.globalStorage.isEditingMode.set(false);
        asRole('labeler');
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

    it('shows the tags of an unselected annotation as read-only chips', () => {
        render(SampleDetailsSidePanelAnnotation, {
            ...defaultProps,
            annotation: taggedAnnotation
        });

        const names = screen.getAllByTestId('segment-tag-name').map((el) => el.textContent);
        expect(names).toEqual(['occluded', 'blurry']);
        expect(screen.queryByTestId('remove-tag-occluded')).not.toBeInTheDocument();
        expect(screen.queryByTestId('mock-add-existing')).not.toBeInTheDocument();
    });

    it('shows nothing for tags on an annotation without tags', () => {
        render(SampleDetailsSidePanelAnnotation, defaultProps);

        expect(screen.queryByTestId('segment-tag-name')).not.toBeInTheDocument();
        expect(screen.queryByTestId('annotation-tags')).not.toBeInTheDocument();
    });

    it.each([false, true])(
        'shows tag controls for the selected annotation with editing=%s',
        (editing) => {
            page.data.globalStorage.isEditingMode.set(editing);
            render(SampleDetailsSidePanelAnnotation, {
                ...defaultProps,
                annotation: taggedAnnotation,
                isSelected: true
            });

            expect(screen.getByTestId('remove-tag-occluded')).toBeInTheDocument();
            expect(screen.getByTestId('mock-add-existing')).toBeInTheDocument();
        }
    );

    it('hides tag controls from viewers', () => {
        asRole('viewer');
        render(SampleDetailsSidePanelAnnotation, {
            ...defaultProps,
            annotation: taggedAnnotation,
            isSelected: true
        });

        expect(screen.getAllByTestId('segment-tag-name')).toHaveLength(2);
        expect(screen.queryByTestId('remove-tag-occluded')).not.toBeInTheDocument();
        expect(screen.queryByTestId('mock-add-existing')).not.toBeInTheDocument();
    });

    it("hides tag controls when it is not the labeler's workflow turn", () => {
        workflowContext.value = { canEdit: false };
        render(SampleDetailsSidePanelAnnotation, {
            ...defaultProps,
            annotation: taggedAnnotation,
            isSelected: true
        });

        expect(screen.getAllByTestId('segment-tag-name')).toHaveLength(2);
        expect(screen.queryByTestId('remove-tag-occluded')).not.toBeInTheDocument();
        expect(screen.queryByTestId('mock-add-existing')).not.toBeInTheDocument();
    });

    it('shows nothing for tags when the user cannot tag and there are none', () => {
        asRole('viewer');
        render(SampleDetailsSidePanelAnnotation, { ...defaultProps, isSelected: true });

        expect(screen.queryByTestId('annotation-tags')).not.toBeInTheDocument();
    });

    it('removes a tag from the annotation and refreshes the annotation and the sample', async () => {
        const onUpdate = vi.fn();
        render(SampleDetailsSidePanelAnnotation, {
            ...defaultProps,
            onUpdate,
            annotation: taggedAnnotation,
            isSelected: true
        });

        await fireEvent.click(screen.getByTestId('remove-tag-occluded'));

        expect(removeTagFromSampleMock).toHaveBeenCalledWith('annotation', 'tag-occluded');
        expect(refetchAnnotationMock).toHaveBeenCalled();
        expect(onUpdate).toHaveBeenCalled();
    });

    it('adds an existing tag of the annotation collection and refreshes', async () => {
        const onUpdate = vi.fn();
        render(SampleDetailsSidePanelAnnotation, { ...defaultProps, onUpdate, isSelected: true });

        await fireEvent.click(screen.getByTestId('mock-add-existing'));

        expect(addExistingMock).toHaveBeenCalledWith(
            'annotation',
            expect.objectContaining({ tag_id: 'tag-truncated' })
        );
        expect(refetchAnnotationMock).toHaveBeenCalled();
        expect(onUpdate).toHaveBeenCalled();
    });

    it('creates a new tag on the annotation and refreshes', async () => {
        const onUpdate = vi.fn();
        render(SampleDetailsSidePanelAnnotation, { ...defaultProps, onUpdate, isSelected: true });

        await fireEvent.click(screen.getByTestId('mock-add-new'));

        expect(createAndAddMock).toHaveBeenCalledWith('annotation', 'Fresh Tag');
        expect(refetchAnnotationMock).toHaveBeenCalled();
        expect(onUpdate).toHaveBeenCalled();
    });
});

describe('SampleDetailsSidePanelAnnotation', () => {
    it.each([false, true])('keeps confidence visible with editing=%s', async (editing) => {
        page.data.globalStorage.isEditingMode.set(editing);
        const props = { ...defaultProps, annotation: { ...annotation, confidence: 0.41 } };
        const { rerender } = render(SampleDetailsSidePanelAnnotation, props);
        expect(screen.getByText('Confidence: 0.41')).toBeInTheDocument();
        await rerender({ ...props, isHidden: true });
        expect(screen.getByText('Confidence: 0.41')).toBeInTheDocument();
        await rerender({ ...props, annotation: { ...annotation, confidence: 0 } });
        expect(screen.getByText('Confidence: 0')).toBeInTheDocument();
        await rerender({ ...props, annotation: { ...annotation, confidence: null } });
        expect(screen.queryByText(/Confidence:/)).not.toBeInTheDocument();
    });
});
