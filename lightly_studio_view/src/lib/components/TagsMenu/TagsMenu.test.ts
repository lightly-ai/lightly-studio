import { deleteTag, renameTag } from '$lib/api/lightly_studio_local';
import { fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { readable } from 'svelte/store';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import TagsMenu from './TagsMenu.svelte';
import type { TagView } from '$lib/services/types';
import { toast } from 'svelte-sonner';
import useAuth from '$lib/hooks/useAuth/useAuth';

const mocks = vi.hoisted(() => ({
    tags: [] as TagView[],
    tagsSelected: new Set<string>(),
    loadTags: vi.fn(),
    tagSelectionToggle: vi.fn(),
    clearTagSelected: vi.fn()
}));

vi.mock('$lib/api/lightly_studio_local', async () => {
    const actual = await vi.importActual('$lib/api/lightly_studio_local');
    return {
        ...actual,
        deleteTag: vi.fn(),
        renameTag: vi.fn()
    };
});

vi.mock('$lib/hooks/useTags/useTags.js', () => ({
    useTags: vi.fn(() => ({
        tags: readable(mocks.tags),
        tagsSelected: readable(mocks.tagsSelected),
        tagSelectionToggle: mocks.tagSelectionToggle,
        loadTags: mocks.loadTags,
        clearTagSelected: mocks.clearTagSelected
    }))
}));

vi.mock('svelte-sonner', () => ({
    toast: {
        error: vi.fn(),
        success: vi.fn()
    }
}));

vi.mock('$lib/hooks/useAuth/useAuth', () => ({
    default: vi.fn()
}));

const sampleTag: TagView = {
    tag_id: 'tag-1',
    name: 'Vehicle',
    created_at: new Date('2024-01-01T00:00:00.000Z'),
    updated_at: new Date('2024-01-01T00:00:00.000Z')
};

const mockRequest = new Request('http://localhost/api/test');
const mockResponse = new Response(null, { status: 200 });

describe('TagsMenu', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        vi.mocked(useAuth).mockReturnValue({
            user: undefined,
            token: undefined,
            isAuthenticated: false
        });
        mocks.tags = [sampleTag];
        mocks.tagsSelected = new Set<string>();
        vi.mocked(deleteTag).mockResolvedValue({
            data: {
                status: 'deleted'
            },
            error: undefined,
            request: mockRequest,
            response: mockResponse
        });
        vi.mocked(renameTag).mockResolvedValue({
            data: {
                ...sampleTag,
                name: 'Renamed Vehicle'
            },
            error: undefined,
            request: mockRequest,
            response: mockResponse
        });
    });

    it('shows the tag search even for a short tag list', () => {
        render(TagsMenu, { props: { collection_id: 'collection-1' } });

        expect(screen.getByPlaceholderText('Search tags…')).toBeInTheDocument();
    });

    it('keeps tag filters but hides tag mutations for viewers', () => {
        vi.mocked(useAuth).mockReturnValue({
            user: { username: 'viewer', email: 'viewer@example.com', role: 'viewer' },
            token: 'viewer-token',
            isAuthenticated: true
        });

        render(TagsMenu, {
            props: {
                collection_id: 'collection-1'
            }
        });

        expect(screen.getByText('Vehicle')).toBeVisible();
        expect(screen.queryByTestId('tag-actions-trigger-tag-1')).not.toBeInTheDocument();
    });

    it('shows tag mutations for labelers', () => {
        vi.mocked(useAuth).mockReturnValue({
            user: { username: 'labeler', email: 'labeler@example.com', role: 'labeler' },
            token: 'labeler-token',
            isAuthenticated: true
        });

        render(TagsMenu, {
            props: {
                collection_id: 'collection-1'
            }
        });

        expect(screen.getByTestId('tag-actions-trigger-tag-1')).toBeVisible();
    });

    it('deletes a tag from the sidebar actions menu', async () => {
        render(TagsMenu, {
            props: {
                collection_id: 'collection-1'
            }
        });

        await fireEvent.click(screen.getByTestId('tag-actions-trigger-tag-1'));
        await fireEvent.click(await screen.findByTestId('delete-tag-tag-1'));

        await waitFor(() => {
            expect(deleteTag).toHaveBeenCalledWith({
                path: {
                    collection_id: 'collection-1',
                    tag_id: 'tag-1'
                }
            });
        });

        expect(mocks.clearTagSelected).toHaveBeenCalledWith('tag-1');
        expect(mocks.loadTags).toHaveBeenCalled();
        expect(toast.success).toHaveBeenCalledWith('Tag deleted successfully');
    });

    it('shows a toast when deleting a tag fails', async () => {
        vi.mocked(deleteTag).mockRejectedValue(new Error('network error'));

        render(TagsMenu, {
            props: {
                collection_id: 'collection-1'
            }
        });

        await fireEvent.click(screen.getByTestId('tag-actions-trigger-tag-1'));
        await fireEvent.click(await screen.findByTestId('delete-tag-tag-1'));

        await waitFor(() => {
            expect(toast.error).toHaveBeenCalledWith('Failed to delete tag. Please try again.');
        });

        expect(mocks.clearTagSelected).not.toHaveBeenCalled();
        expect(mocks.loadTags).not.toHaveBeenCalled();
    });

    it('renames a tag from the inline row edit via tick button', async () => {
        render(TagsMenu, {
            props: {
                collection_id: 'collection-1'
            }
        });

        await fireEvent.click(screen.getByTestId('tag-actions-trigger-tag-1'));
        await fireEvent.click(await screen.findByTestId('rename-tag-tag-1'));

        expect(await screen.findByTestId('rename-tag-form-tag-1')).toBeVisible();
        const input = screen.getByTestId('rename-tag-input-tag-1') as HTMLInputElement;
        expect(input).toHaveValue('Vehicle');
        await waitFor(() => {
            expect(document.activeElement).toBe(input);
            expect(input.selectionStart).toBe(0);
            expect(input.selectionEnd).toBe('Vehicle'.length);
        });
        expect(screen.queryByTestId('rename-tag-tag-1')).not.toBeInTheDocument();

        await fireEvent.input(input, { target: { value: '  Renamed Vehicle  ' } });
        await fireEvent.click(screen.getByTestId('save-tag-rename-tag-1'));

        await waitFor(() => {
            expect(renameTag).toHaveBeenCalledWith({
                path: {
                    collection_id: 'collection-1',
                    tag_id: 'tag-1'
                },
                body: {
                    name: 'Renamed Vehicle'
                }
            });
            expect(mocks.loadTags).toHaveBeenCalled();
            expect(mocks.clearTagSelected).not.toHaveBeenCalled();
            expect(screen.queryByTestId('rename-tag-form-tag-1')).not.toBeInTheDocument();
            expect(toast.success).not.toHaveBeenCalled();
        });
    });

    it('shows a toast when renaming a tag fails', async () => {
        vi.mocked(renameTag).mockRejectedValue(new Error('network error'));

        render(TagsMenu, {
            props: {
                collection_id: 'collection-1'
            }
        });

        await fireEvent.click(screen.getByTestId('tag-actions-trigger-tag-1'));
        await fireEvent.click(await screen.findByTestId('rename-tag-tag-1'));

        const input = await screen.findByTestId('rename-tag-input-tag-1');
        await fireEvent.input(input, { target: { value: 'Renamed Vehicle' } });
        await fireEvent.click(screen.getByTestId('save-tag-rename-tag-1'));

        await waitFor(() => {
            expect(toast.error).toHaveBeenCalledWith('Failed to rename tag. Please try again.');
        });

        expect(screen.getByTestId('rename-tag-form-tag-1')).toBeVisible();
        expect(mocks.loadTags).not.toHaveBeenCalled();
    });

    it('does not toggle the checkbox when opening the tag actions menu', async () => {
        render(TagsMenu, {
            props: {
                collection_id: 'collection-1'
            }
        });

        await fireEvent.click(screen.getByTestId('tag-actions-trigger-tag-1'));

        expect(mocks.tagSelectionToggle).not.toHaveBeenCalled();
    });
});
