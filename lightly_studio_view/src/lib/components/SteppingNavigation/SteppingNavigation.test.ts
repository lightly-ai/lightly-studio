import { render, fireEvent, screen } from '@testing-library/svelte';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import SampleDetailsNavigation from './SteppingNavigationTestWrapper.svelte';

describe('SampleDetailsNavigation', () => {
    const getNextButton = () => screen.queryByRole('button', { name: 'Next sample' });
    const getPreviousButton = () => screen.queryByRole('button', { name: 'Previous sample' });

    beforeEach(() => {
        vi.resetAllMocks();
    });

    it('renders navigation buttons when adjacent samples exist', () => {
        render(SampleDetailsNavigation, {
            hasPrevious: true,
            hasNext: true,
            onNext: vi.fn(),
            onPrevious: vi.fn()
        });

        expect(getNextButton()).toBeInTheDocument();
        expect(getPreviousButton()).toBeInTheDocument();
    });

    it('does not render navigation buttons when no adjacent samples exist', async () => {
        render(SampleDetailsNavigation, {
            hasPrevious: false,
            hasNext: false,
            onNext: vi.fn(),
            onPrevious: vi.fn()
        });

        expect(getNextButton()).not.toBeInTheDocument();
        expect(getPreviousButton()).not.toBeInTheDocument();
    });

    it('calls onNext when next button is clicked', async () => {
        const onNext = vi.fn();
        render(SampleDetailsNavigation, {
            hasPrevious: true,
            hasNext: true,
            onNext,
            onPrevious: vi.fn()
        });

        await fireEvent.click(getNextButton() as HTMLElement);

        expect(onNext).toHaveBeenCalled();
    });

    it('calls onPrevious when previous button is clicked', async () => {
        const onPrevious = vi.fn();
        render(SampleDetailsNavigation, {
            hasPrevious: true,
            hasNext: true,
            onNext: vi.fn(),
            onPrevious
        });

        await fireEvent.click(getPreviousButton() as HTMLElement);

        expect(onPrevious).toHaveBeenCalled();
    });

    it('does not navigate from a handled keyboard event', () => {
        const onNext = vi.fn();
        render(SampleDetailsNavigation, {
            hasPrevious: true,
            hasNext: true,
            onNext,
            onPrevious: vi.fn()
        });
        const event = new KeyboardEvent('keydown', { key: 'ArrowRight', cancelable: true });
        event.preventDefault();

        window.dispatchEvent(event);

        expect(onNext).not.toHaveBeenCalled();
    });

    it('does not navigate from text inputs or overlays', async () => {
        const onNext = vi.fn();
        const onPrevious = vi.fn();
        render(SampleDetailsNavigation, {
            hasPrevious: true,
            hasNext: true,
            onNext,
            onPrevious
        });
        const fixture = document.createElement('div');
        fixture.innerHTML = `<input><textarea></textarea><div contenteditable="true"></div>
            <div role="dialog"><button></button><div><button></button></div></div>
            <div role="menu"><button></button><div><button></button></div></div>
            <div role="listbox"><button></button><div><button></button></div></div>
            <div data-popover-content><button></button></div>`;
        document.body.append(fixture);
        (fixture.querySelector('[contenteditable]') as HTMLElement).contentEditable = 'true';

        try {
            for (const target of fixture.querySelectorAll(
                'input, textarea, [contenteditable], [role="dialog"] button, [role="menu"] button, [role="listbox"] button, [data-popover-content] button'
            )) {
                await fireEvent.keyDown(target, { key: 'ArrowLeft' });
                await fireEvent.keyDown(target, { key: 'ArrowRight' });
            }
        } finally {
            fixture.remove();
        }

        expect(onPrevious).not.toHaveBeenCalled();
        expect(onNext).not.toHaveBeenCalled();
    });
});
