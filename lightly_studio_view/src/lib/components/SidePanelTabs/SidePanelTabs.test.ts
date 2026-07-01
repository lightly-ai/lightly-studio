import { describe, it, expect, vi, beforeEach } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/svelte';
import { writable } from 'svelte/store';
import '@testing-library/jest-dom';

const activePanel = writable<string>('none');
const setActivePanel = vi.fn((panel: string) => activePanel.set(panel));

vi.mock('$lib/hooks/useGlobalStorage', () => ({
    useGlobalStorage: () => ({
        activePanel,
        setActivePanel
    })
}));

import SidePanelTabs from './SidePanelTabs.svelte';

describe('SidePanelTabs', () => {
    beforeEach(() => {
        activePanel.set('none');
        setActivePanel.mockClear();
    });

    it('renders the Query button only when isImages is true', () => {
        const { unmount } = render(SidePanelTabs, {
            props: {
                isImages: true,
                isEvaluationMatches: false,
                hasMediaWithEmbeddings: false,
                hasEvaluationRuns: false
            }
        });
        expect(screen.getByTestId('side-panel-tabs-query')).toBeInTheDocument();
        unmount();

        render(SidePanelTabs, {
            props: {
                isImages: false,
                isEvaluationMatches: false,
                hasMediaWithEmbeddings: false,
                hasEvaluationRuns: false
            }
        });
        expect(screen.queryByTestId('side-panel-tabs-query')).not.toBeInTheDocument();
    });

    it('renders the Embed button only when hasMediaWithEmbeddings is true', () => {
        const { unmount } = render(SidePanelTabs, {
            props: {
                isImages: false,
                isEvaluationMatches: false,
                hasMediaWithEmbeddings: true,
                hasEvaluationRuns: false
            }
        });
        expect(screen.getByTestId('side-panel-tabs-embed')).toBeInTheDocument();
        unmount();

        render(SidePanelTabs, {
            props: {
                isImages: false,
                isEvaluationMatches: false,
                hasMediaWithEmbeddings: false,
                hasEvaluationRuns: false
            }
        });
        expect(screen.queryByTestId('side-panel-tabs-embed')).not.toBeInTheDocument();
    });

    it('renders the Eval button when hasEvaluationRuns and on the images or matches view', () => {
        const { unmount } = render(SidePanelTabs, {
            props: {
                isImages: true,
                isEvaluationMatches: false,
                hasMediaWithEmbeddings: false,
                hasEvaluationRuns: true
            }
        });
        expect(screen.getByTestId('side-panel-tabs-eval')).toBeInTheDocument();
        unmount();

        const matchesView = render(SidePanelTabs, {
            props: {
                isImages: false,
                isEvaluationMatches: true,
                hasMediaWithEmbeddings: false,
                hasEvaluationRuns: true
            }
        });
        expect(screen.getByTestId('side-panel-tabs-eval')).toBeInTheDocument();
        matchesView.unmount();

        render(SidePanelTabs, {
            props: {
                isImages: false,
                isEvaluationMatches: false,
                hasMediaWithEmbeddings: false,
                hasEvaluationRuns: true
            }
        });
        expect(screen.queryByTestId('side-panel-tabs-eval')).not.toBeInTheDocument();
    });

    it('hides the Eval button on the matches view when there are no evaluation runs', () => {
        render(SidePanelTabs, {
            props: {
                isImages: false,
                isEvaluationMatches: true,
                hasMediaWithEmbeddings: false,
                hasEvaluationRuns: false
            }
        });
        expect(screen.queryByTestId('side-panel-tabs-eval')).not.toBeInTheDocument();
    });

    it('calls setActivePanel with queryEditor when Query button is clicked', async () => {
        render(SidePanelTabs, {
            props: {
                isImages: true,
                isEvaluationMatches: false,
                hasMediaWithEmbeddings: false,
                hasEvaluationRuns: false
            }
        });

        await fireEvent.click(screen.getByTestId('side-panel-tabs-query'));
        expect(setActivePanel).toHaveBeenCalledWith('queryEditor');
    });

    it('calls setActivePanel with none when the active Query button is clicked again', async () => {
        activePanel.set('queryEditor');
        render(SidePanelTabs, {
            props: {
                isImages: true,
                isEvaluationMatches: false,
                hasMediaWithEmbeddings: false,
                hasEvaluationRuns: false
            }
        });

        await fireEvent.click(screen.getByTestId('side-panel-tabs-query'));
        expect(setActivePanel).toHaveBeenCalledWith('none');
    });

    it('calls setActivePanel with embeddingPlot when Embed button is clicked', async () => {
        render(SidePanelTabs, {
            props: {
                isImages: false,
                isEvaluationMatches: false,
                hasMediaWithEmbeddings: true,
                hasEvaluationRuns: false
            }
        });

        await fireEvent.click(screen.getByTestId('side-panel-tabs-embed'));
        expect(setActivePanel).toHaveBeenCalledWith('embeddingPlot');
    });

    it('calls setActivePanel with evaluationRuns when Eval button is clicked', async () => {
        render(SidePanelTabs, {
            props: {
                isImages: true,
                isEvaluationMatches: false,
                hasMediaWithEmbeddings: false,
                hasEvaluationRuns: true
            }
        });

        await fireEvent.click(screen.getByTestId('side-panel-tabs-eval'));
        expect(setActivePanel).toHaveBeenCalledWith('evaluationRuns');
    });

    it('marks the active panel button with aria-pressed', async () => {
        activePanel.set('embeddingPlot');
        render(SidePanelTabs, {
            props: {
                isImages: true,
                isEvaluationMatches: false,
                hasMediaWithEmbeddings: true,
                hasEvaluationRuns: true
            }
        });

        expect(screen.getByTestId('side-panel-tabs-embed')).toHaveAttribute('aria-pressed', 'true');
        expect(screen.getByTestId('side-panel-tabs-query')).toHaveAttribute(
            'aria-pressed',
            'false'
        );
        expect(screen.getByTestId('side-panel-tabs-eval')).toHaveAttribute('aria-pressed', 'false');
    });
});
