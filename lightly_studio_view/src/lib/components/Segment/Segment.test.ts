import { render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { createRawSnippet } from 'svelte';
import { describe, expect, it } from 'vitest';
import Segment from './Segment.svelte';

const children = createRawSnippet(() => ({
    render: () => '<div data-testid="segment-content">content</div>'
}));

const actions = createRawSnippet(() => ({
    render: () => '<button type="button" data-testid="segment-action">action</button>'
}));

describe('Segment', () => {
    it('collapses and expands the content when clicking the title', async () => {
        const user = userEvent.setup();
        render(Segment, { props: { title: 'Annotations', children } });

        await user.click(screen.getByText('Annotations'));
        expect(screen.queryByTestId('segment-content')).not.toBeInTheDocument();

        await user.click(screen.getByText('Annotations'));
        expect(screen.getByTestId('segment-content')).toBeInTheDocument();
    });

    it('does not collapse when clicking an action', async () => {
        const user = userEvent.setup();
        render(Segment, { props: { title: 'Annotations', children, actions } });

        await user.click(screen.getByTestId('segment-action'));
        expect(screen.getByTestId('segment-content')).toBeInTheDocument();
    });
});
