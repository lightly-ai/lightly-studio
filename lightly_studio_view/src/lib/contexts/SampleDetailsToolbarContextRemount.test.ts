import { fireEvent, render, screen } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';
import SampleDetailsToolbarContextRemountTestWrapper from './SampleDetailsToolbarContextRemountTestWrapper.svelte';

describe('SampleDetailsToolbarContext remount behavior', () => {
    it('keeps brush tool active when child remounts under same parent context', async () => {
        render(SampleDetailsToolbarContextRemountTestWrapper);

        await fireEvent.click(screen.getByRole('button', { name: 'Set brush' }));
        expect(screen.getByTestId('toolbar-status')).toHaveTextContent('brush');

        await fireEvent.click(screen.getByRole('button', { name: 'Toggle child' }));
        await fireEvent.click(screen.getByRole('button', { name: 'Toggle child' }));

        expect(screen.getByTestId('toolbar-status')).toHaveTextContent('brush');
    });
});
