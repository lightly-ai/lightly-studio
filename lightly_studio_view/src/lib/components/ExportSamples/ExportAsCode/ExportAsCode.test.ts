import { fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { writable } from 'svelte/store';
import { describe, expect, it, vi } from 'vitest';
import ExportAsCode from './ExportAsCode.svelte';
import { SCOPE_NOT_SUPPORTED_REASON } from './buildExportCode';

const imageFilter = writable<unknown>(null);
const tags = writable<Record<string, { tag_id: string; name: string }[]>>({});

vi.mock('$lib/hooks', () => ({
    useImageFilters: () => ({ imageFilter }),
    useGlobalStorage: () => ({ tags })
}));

const defaultProps = {
    collectionId: 'col-1',
    datasetName: 'caltech',
    exportType: 'object_detections_coco' as const,
    includeImages: true,
    annotationSources: [],
    selectedAnnotationSourceId: undefined
};

describe('ExportAsCode', () => {
    it('copies the code for a one-tag export', async () => {
        const writeText = vi.fn().mockResolvedValue(undefined);
        Object.assign(navigator, { clipboard: { writeText } });
        tags.set({ 'col-1': [{ tag_id: 'tag-1', name: 'train' }] });
        imageFilter.set({ filter_type: 'image', sample_filter: { tag_ids: ['tag-1'] } });
        render(ExportAsCode, { props: defaultProps });

        await fireEvent.click(screen.getByRole('button', { name: 'Copy as code' }));
        await fireEvent.click(screen.getByRole('button', { name: 'Copy code' }));

        const code = writeText.mock.calls[0][0] as string;
        expect(code).toContain('ImageSampleField.tags.contains("train")');
        expect(code).toContain('include_images=True');
        await waitFor(() => expect(screen.getByRole('button', { name: 'Copied' })).toBeVisible());
    });

    it('colors the code by token', async () => {
        imageFilter.set(null);
        render(ExportAsCode, { props: defaultProps });

        await fireEvent.click(screen.getByRole('button', { name: 'Copy as code' }));

        const keywords = document.querySelectorAll('[data-token="keyword"]');
        expect([...keywords].map((node) => node.textContent)).toContain('import');
        expect(document.querySelector('[data-token="comment"]')).not.toBeNull();
    });

    it('explains why there is no code for other filters', async () => {
        imageFilter.set({ filter_type: 'image', width: { min: 100 } });
        render(ExportAsCode, { props: defaultProps });

        await fireEvent.click(screen.getByRole('button', { name: 'Copy as code' }));

        expect(screen.getByText(SCOPE_NOT_SUPPORTED_REASON)).toBeInTheDocument();
        expect(screen.queryByRole('button', { name: 'Copy code' })).not.toBeInTheDocument();
    });
});
