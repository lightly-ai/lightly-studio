import { expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { writable } from 'svelte/store';
import type { AnnotationView } from '$lib/api/lightly_studio_local';
import CopyAnnotationToSource from './CopyAnnotationToSource.svelte';

const mocks = vi.hoisted(() => ({
    copy: vi.fn(),
    sources: [{ collection_id: 'original', name: 'Model' }]
}));
vi.mock('$lib/hooks', () => ({
    useAnnotationCollections: () => ({ data: mocks.sources, isSuccess: true })
}));
vi.mock('./useCopyAnnotationToSource.svelte', () => ({
    useCopyAnnotationToSource: () => ({ copy: mocks.copy, pending })
}));
const pending = writable(false);
const annotation: AnnotationView = {
    sample_id: 'annotation',
    parent_sample_id: 'image',
    annotation_collection_id: 'original',
    annotation_type: 'classification',
    annotation_label: { annotation_label_name: 'car' },
    created_at: new Date()
};
const defaultProps = { collectionId: 'images', annotation, onCopied: vi.fn() };
it('creates a source without other destinations, validates names, and keeps the name on failure', async () => {
    const user = userEvent.setup();
    mocks.copy.mockResolvedValueOnce(false).mockResolvedValueOnce(true);
    render(CopyAnnotationToSource, { props: defaultProps });
    await user.click(
        screen.getByRole('button', { name: 'Duplicate to another annotation source' })
    );
    expect(screen.queryByRole('button', { name: 'Model' })).not.toBeInTheDocument();
    const input = screen.getByRole('textbox', { name: 'New annotation source' });
    await user.type(input, '{Enter} {Enter}');
    expect(mocks.copy).not.toHaveBeenCalled();
    await user.type(input, ' Model {Enter}');
    expect(input).toHaveAttribute('aria-invalid', 'true');
    expect(screen.getByText('This annotation source already exists.')).toBeInTheDocument();
    expect(mocks.copy).not.toHaveBeenCalled();
    await user.clear(input);
    await user.type(input, ' Human {Enter}');
    expect(mocks.copy).toHaveBeenLastCalledWith('Human');
    expect(input).toHaveValue(' Human ');
    pending.set(true);
    await waitFor(() => expect(input).toBeDisabled());
    pending.set(false);
    await waitFor(() => expect(input).toBeEnabled());
    await user.type(input, '{Enter}');
    await waitFor(() => expect(screen.queryByRole('textbox')).not.toBeInTheDocument());
});
