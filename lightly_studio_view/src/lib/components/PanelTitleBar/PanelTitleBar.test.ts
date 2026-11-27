import { describe, it, expect } from 'vitest';
import { createRawSnippet } from 'svelte';
import { render, screen } from '@testing-library/svelte';
import PanelTitleBar from './PanelTitleBar.svelte';

const htmlSnippet = (html: string) => createRawSnippet(() => ({ render: () => html }));

describe('PanelTitleBar', () => {
    it('renders the title as a heading with the leading, inline, and action content', () => {
        render(PanelTitleBar, {
            props: {
                title: 'Evaluations',
                leading: htmlSnippet('<span>Back</span>'),
                children: htmlSnippet('<span>Axes</span>'),
                actions: htmlSnippet('<button>Close</button>')
            }
        });

        expect(screen.getByRole('heading', { level: 2, name: 'Evaluations' })).toBeInTheDocument();
        expect(screen.getByText('Back')).toBeInTheDocument();
        expect(screen.getByText('Axes')).toBeInTheDocument();
        expect(screen.getByRole('button', { name: 'Close' })).toBeInTheDocument();
    });
});
