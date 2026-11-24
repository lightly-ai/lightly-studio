import { render, screen } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { writable } from 'svelte/store';
import * as hooks from '$lib/hooks';
import useAuth from '$lib/hooks/useAuth/useAuth';
import TagsEditor from './TagsEditor.svelte';

const { workflowContext } = vi.hoisted(() => ({
    workflowContext: { value: undefined as { canEdit: boolean } | undefined }
}));

vi.mock('$lib/hooks/useAuth/useAuth', () => ({ default: vi.fn() }));
vi.mock('$lib/contexts/WorkflowFile.svelte', async (importOriginal) => ({
    ...(await importOriginal<typeof import('$lib/contexts/WorkflowFile.svelte')>()),
    useWorkflowFileContext: () => workflowContext.value
}));
vi.mock('../AddTagPopover.svelte', async () => {
    const module = await import('../AddTagPopover.mock.svelte');
    return { default: module.default };
});

const asRole = (role: 'viewer' | 'labeler') =>
    vi.mocked(useAuth).mockReturnValue({
        user: { username: role, email: `${role}@example.com`, role },
        token: 'token',
        isAuthenticated: true
    });

const props = {
    tags: [{ tag_id: 'tag-occluded', name: 'occluded' }],
    collectionId: 'collection-1',
    sampleId: 'sample-1',
    class: 'tags-wrapper'
};

describe('TagsEditor', () => {
    beforeEach(() => {
        workflowContext.value = undefined;
        asRole('labeler');
        vi.spyOn(hooks, 'useRemoveTagFromSample').mockReturnValue({
            removeTagFromSample: vi.fn()
        } as ReturnType<typeof hooks.useRemoveTagFromSample>);
        vi.spyOn(hooks, 'useAddTagToSample').mockReturnValue({
            busy: writable(false),
            addExisting: vi.fn(),
            createAndAdd: vi.fn()
        } as ReturnType<typeof hooks.useAddTagToSample>);
        vi.spyOn(hooks, 'useTags').mockReturnValue({
            tags: writable([]),
            loadTags: vi.fn()
        } as unknown as ReturnType<typeof hooks.useTags>);
    });

    it('offers remove and add controls to labelers', () => {
        render(TagsEditor, props);

        expect(screen.getByRole('button', { name: 'Remove tag occluded' })).toBeInTheDocument();
        expect(screen.getByTestId('mock-add-existing')).toBeInTheDocument();
    });

    it('shows the tags without controls to viewers', () => {
        asRole('viewer');
        render(TagsEditor, props);

        expect(screen.getByTestId('segment-tag-name')).toHaveTextContent('occluded');
        expect(
            screen.queryByRole('button', { name: 'Remove tag occluded' })
        ).not.toBeInTheDocument();
        expect(screen.queryByTestId('mock-add-existing')).not.toBeInTheDocument();
    });

    it("shows the tags without controls when it is not the labeler's workflow turn", () => {
        workflowContext.value = { canEdit: false };
        render(TagsEditor, props);

        expect(screen.getByTestId('segment-tag-name')).toHaveTextContent('occluded');
        expect(
            screen.queryByRole('button', { name: 'Remove tag occluded' })
        ).not.toBeInTheDocument();
        expect(screen.queryByTestId('mock-add-existing')).not.toBeInTheDocument();
    });

    it('renders nothing when there are no tags and the user cannot tag', () => {
        asRole('viewer');
        const { container } = render(TagsEditor, { ...props, tags: [] });

        expect(container.querySelector('.tags-wrapper')).not.toBeInTheDocument();
    });
});
