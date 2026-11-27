import { render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import ModelRunControls from './ModelRunControls.svelte';

const defaultProps = {
    predictionCount: 0,
    isGenerating: true,
    isEmptyResult: false,
    canGenerate: false,
    downloadProgress: null,
    onRun: vi.fn()
};

describe('ModelRunControls', () => {
    it('shows the download progress on the run button', () => {
        render(ModelRunControls, {
            ...defaultProps,
            downloadProgress: { loaded: 12e6, total: 20e6 }
        });

        expect(screen.getByText('Downloading model… 12 of 20 MB')).toBeInTheDocument();
    });

    it('shows that the model runs without a download', () => {
        render(ModelRunControls, defaultProps);

        expect(screen.getByText('Running…')).toBeInTheDocument();
    });
});
