import { render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import AnnotationLockToggle from './AnnotationLockToggle.svelte';

const defaultProps = { locked: false, scope: 'all' as const, onToggle: vi.fn() };

describe('AnnotationLockToggle', () => {
    it('offers to lock all annotations when not all are locked', async () => {
        const user = userEvent.setup();
        render(AnnotationLockToggle, { props: defaultProps });

        await user.hover(screen.getByRole('button', { name: 'Lock all annotations' }));
        expect(screen.getByRole('tooltip')).toHaveTextContent(
            "Lock all annotations. Locked masks are protected: new brush strokes won't paint over or modify them."
        );
    });

    it('offers to unlock all annotations when all are locked', async () => {
        const user = userEvent.setup();
        render(AnnotationLockToggle, { props: { ...defaultProps, locked: true } });

        await user.hover(screen.getByRole('button', { name: 'Unlock all annotations' }));
        expect(screen.getByRole('tooltip')).toHaveTextContent(
            'Unlock all annotations. Allows new brush strokes to paint over these masks again.'
        );
    });

    it('names the source scope in the label and the tooltip', async () => {
        const user = userEvent.setup();
        render(AnnotationLockToggle, { props: { ...defaultProps, scope: 'source' } });

        await user.hover(
            screen.getByRole('button', { name: 'Lock all annotations in this source' })
        );
        expect(screen.getByRole('tooltip')).toHaveTextContent(
            "Lock all annotations in this source. Locked masks are protected: new brush strokes won't paint over or modify them."
        );
    });

    it('names the source scope when all annotations of the source are locked', () => {
        render(AnnotationLockToggle, {
            props: { ...defaultProps, scope: 'source', locked: true }
        });

        expect(
            screen.getByRole('button', { name: 'Unlock all annotations in this source' })
        ).toBeInTheDocument();
    });

    it('calls onToggle on click', async () => {
        const user = userEvent.setup();
        const onToggle = vi.fn();
        render(AnnotationLockToggle, { props: { ...defaultProps, onToggle } });

        await user.click(screen.getByRole('button', { name: 'Lock all annotations' }));
        expect(onToggle).toHaveBeenCalledOnce();
    });
});
