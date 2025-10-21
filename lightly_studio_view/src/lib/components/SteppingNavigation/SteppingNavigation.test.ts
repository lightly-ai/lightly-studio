import { render, fireEvent, screen } from '@testing-library/svelte';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import SampleDetailsNavigation from './SteppingNavigation.svelte';

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
});
