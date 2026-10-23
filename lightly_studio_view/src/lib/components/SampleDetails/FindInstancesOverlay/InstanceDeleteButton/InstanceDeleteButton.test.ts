import { fireEvent, render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import InstanceDeleteButton from './InstanceDeleteButton.svelte';

const defaultProps = {
    bbox: { x: 10, y: 10, width: 90, height: 50 },
    index: 0,
    scale: 1,
    disabled: false,
    onDelete: vi.fn()
};

describe('InstanceDeleteButton', () => {
    it('deletes the instance on click', async () => {
        const onDelete = vi.fn();
        render(InstanceDeleteButton, { props: { ...defaultProps, onDelete } });

        await fireEvent.click(screen.getByRole('button', { name: 'Delete instance 1' }));

        expect(onDelete).toHaveBeenCalledOnce();
    });

    it('is disabled while the instances are saved', () => {
        render(InstanceDeleteButton, { props: { ...defaultProps, disabled: true } });
        expect(screen.getByRole('button')).toBeDisabled();
    });

    it('keeps its screen size at the top right of the box when zoomed out', () => {
        const { container } = render(InstanceDeleteButton, {
            props: { ...defaultProps, scale: 0.5 }
        });
        expect(container.querySelector('g')).toHaveAttribute(
            'transform',
            'translate(52 0) scale(2)'
        );
    });
});
