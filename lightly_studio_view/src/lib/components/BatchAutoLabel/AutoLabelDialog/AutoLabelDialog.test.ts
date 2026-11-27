import { render, screen } from '@testing-library/svelte';
import { writable } from 'svelte/store';
import { describe, expect, it, vi } from 'vitest';
import AutoLabelDialog from './AutoLabelDialog.svelte';

const mocks = vi.hoisted(() => ({ getDetector: vi.fn() }));

vi.mock('$lib/hooks', () => ({
    useBrowserModels: () => ({
        models: writable([
            { id: 'ltdetrv2-s-coco', task: 'object_detection', class_names: [], runsIn: 'browser' }
        ]),
        loadProgress: writable(null),
        getDetector: mocks.getDetector
    })
}));

describe('AutoLabelDialog', () => {
    it('shows why the model could not load instead of loading forever', async () => {
        mocks.getDetector.mockRejectedValue(new Error('HTTP 404'));

        render(AutoLabelDialog, { open: true, selectedCount: 3, onStart: vi.fn() });

        expect(await screen.findByText(/Could not load the model: HTTP 404/)).toBeInTheDocument();
        expect(screen.queryByText('Loading the model classes…')).not.toBeInTheDocument();
    });
});
