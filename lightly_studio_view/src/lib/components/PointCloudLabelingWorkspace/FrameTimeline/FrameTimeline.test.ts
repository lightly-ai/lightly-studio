import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import FrameTimeline from './FrameTimeline.svelte';
import type { FrameNavigation } from '../types';

function navigation(overrides: Partial<FrameNavigation> = {}): FrameNavigation {
    return {
        position: 1,
        frameCount: 3,
        hasMore: true,
        isLoading: false,
        previous: vi.fn(),
        next: vi.fn(),
        ...overrides
    };
}

describe('FrameTimeline', () => {
    it('leaves its controls disabled without navigation', () => {
        render(FrameTimeline);

        expect(screen.getByTestId('workspace-frame-position')).toHaveTextContent('Frame — / —');
        expect(screen.getByLabelText('Previous frame')).toBeDisabled();
        expect(screen.getByLabelText('Next frame')).toBeDisabled();
    });

    it('reports the position, and that more frames follow', () => {
        render(FrameTimeline, { props: { navigation: navigation() } });

        expect(screen.getByTestId('workspace-frame-position')).toHaveTextContent('Frame 2 / 3+');
    });

    it('reports no continuation once the channel is exhausted', () => {
        render(FrameTimeline, { props: { navigation: navigation({ hasMore: false }) } });

        expect(screen.getByTestId('workspace-frame-position')).toHaveTextContent('Frame 2 / 3');
    });

    it('steps backwards and forwards', async () => {
        const nav = navigation();
        render(FrameTimeline, { props: { navigation: nav } });

        await userEvent.click(screen.getByLabelText('Previous frame'));
        await userEvent.click(screen.getByLabelText('Next frame'));

        expect(nav.previous).toHaveBeenCalledOnce();
        expect(nav.next).toHaveBeenCalledOnce();
    });

    it('cannot step back from the first frame', () => {
        render(FrameTimeline, { props: { navigation: navigation({ position: 0 }) } });

        expect(screen.getByLabelText('Previous frame')).toBeDisabled();
        expect(screen.getByLabelText('Next frame')).toBeEnabled();
    });

    it('stays steppable while the channel has more frames to list', () => {
        render(FrameTimeline, {
            props: { navigation: navigation({ position: 2, frameCount: 3, hasMore: true }) }
        });

        expect(screen.getByLabelText('Next frame')).toBeEnabled();
    });

    it('cannot step past the last frame of an exhausted channel', () => {
        render(FrameTimeline, {
            props: { navigation: navigation({ position: 2, frameCount: 3, hasMore: false }) }
        });

        expect(screen.getByLabelText('Next frame')).toBeDisabled();
    });

    it('shows that a frame is being read', () => {
        render(FrameTimeline, { props: { navigation: navigation({ isLoading: true }) } });

        expect(screen.getByText('loading…')).toBeInTheDocument();
    });
});
