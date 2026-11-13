import { describe, it, expect, vi, beforeAll } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';

import TrackSelect from './TrackSelect.svelte';
import type { TrackWithClassNameView } from '$lib/api/lightly_studio_local';

beforeAll(() => {
    Element.prototype.scrollIntoView = vi.fn();
});

const tracks: TrackWithClassNameView[] = [
    { object_track_id: 'track-2', object_track_number: 2, annotation_class_name: 'truck' },
    { object_track_id: 'track-1', object_track_number: 1, annotation_class_name: 'car' },
    { object_track_id: 'track-3', object_track_number: 3, annotation_class_name: null }
];

describe('TrackSelect', () => {
    it('renders with "No track" selected by default', () => {
        render(TrackSelect, { props: { tracks } });

        const trigger = screen.getByTestId('select-list-trigger');
        expect(trigger).toHaveTextContent('No track');
    });

    it('shows sorted track items when opened', async () => {
        const user = userEvent.setup();
        render(TrackSelect, { props: { tracks } });

        await user.click(screen.getByTestId('select-list-trigger'));

        const options = screen.getAllByRole('option');
        const labels = options.map((o) => o.textContent?.trim());
        expect(labels).toEqual(['No track', 'Track 3', 'car - 1', 'truck - 2', '+ New track']);
    });

    it('calls onValueChange with track id when an existing track is selected', async () => {
        const user = userEvent.setup();
        const onValueChange = vi.fn();
        render(TrackSelect, { props: { tracks, onValueChange } });

        await user.click(screen.getByTestId('select-list-trigger'));
        await user.click(screen.getByRole('option', { name: 'car - 1' }));

        expect(onValueChange).toHaveBeenCalledWith('track-1', false);
    });

    it('calls onValueChange with isNewTrack=true when "+ New track" is selected', async () => {
        const user = userEvent.setup();
        const onValueChange = vi.fn();
        render(TrackSelect, { props: { tracks, onValueChange } });

        await user.click(screen.getByTestId('select-list-trigger'));
        await user.click(screen.getByRole('option', { name: '+ New track' }));

        expect(onValueChange).toHaveBeenCalledWith(null, true);
    });

    it('calls onValueChange with null when "No track" is selected', async () => {
        const user = userEvent.setup();
        const onValueChange = vi.fn();
        render(TrackSelect, { props: { tracks, value: 'track-1', onValueChange } });

        await user.click(screen.getByTestId('select-list-trigger'));
        await user.click(screen.getByRole('option', { name: 'No track' }));

        expect(onValueChange).toHaveBeenCalledWith(null, false);
    });

    it('keeps "No track" and "+ New track" visible while filtering', async () => {
        const user = userEvent.setup();
        render(TrackSelect, { props: { tracks } });

        await user.click(screen.getByTestId('select-list-trigger'));
        await user.type(screen.getByTestId('select-list-input'), 'zzz');

        const options = screen.getAllByRole('option');
        const labels = options.map((o) => o.textContent?.trim());
        expect(labels.at(0)).toBe('No track');
        expect(labels.at(-1)).toBe('+ New track');
        expect(labels).not.toContain('car - 1');
        expect(labels).not.toContain('truck - 2');
    });
});
