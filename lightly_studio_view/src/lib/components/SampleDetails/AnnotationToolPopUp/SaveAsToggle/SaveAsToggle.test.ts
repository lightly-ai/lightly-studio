import { render, screen, fireEvent } from '@testing-library/svelte';
import { describe, it, expect, vi } from 'vitest';
import SaveAsToggle from './SaveAsToggle.svelte';

describe('SaveAsToggle', () => {
    it('reports the chosen save as option', async () => {
        const onSaveAsChange = vi.fn();
        render(SaveAsToggle, { props: { saveAs: 'mask', onSaveAsChange } });

        await fireEvent.click(screen.getByRole('button', { name: 'Save as Box' }));

        expect(onSaveAsChange).toHaveBeenCalledWith('box');
    });
});
