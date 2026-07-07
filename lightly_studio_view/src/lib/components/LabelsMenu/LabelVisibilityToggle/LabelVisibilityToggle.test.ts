import { render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import LabelVisibilityToggle from './LabelVisibilityToggle.svelte';

describe('LabelVisibilityToggle', () => {
    it('renders a hide button when the class is visible', () => {
        render(LabelVisibilityToggle, {
            isHidden: false,
            labelName: 'car',
            toggleClassVisibility: vi.fn()
        });
        expect(screen.getByLabelText('Hide annotation class car')).toBeInTheDocument();
        expect(screen.queryByLabelText('Show annotation class car')).not.toBeInTheDocument();
    });

    it('renders a show button when the class is hidden', () => {
        render(LabelVisibilityToggle, {
            isHidden: true,
            labelName: 'car',
            toggleClassVisibility: vi.fn()
        });
        expect(screen.getByLabelText('Show annotation class car')).toBeInTheDocument();
        expect(screen.queryByLabelText('Hide annotation class car')).not.toBeInTheDocument();
    });

    it('calls toggleClassVisibility with the label name when clicked', async () => {
        const toggleClassVisibility = vi.fn();
        render(LabelVisibilityToggle, {
            isHidden: false,
            labelName: 'car',
            toggleClassVisibility
        });
        await userEvent.click(screen.getByLabelText('Hide annotation class car'));
        expect(toggleClassVisibility).toHaveBeenCalledWith('car');
    });
});
