import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import '@testing-library/jest-dom';
import AgentReply from './AgentReply.svelte';

describe('AgentReply', () => {
    it('renders markdown, escapes raw HTML, and opens links in a new tab', () => {
        render(AgentReply, {
            props: {
                text: '**Done.** <img src=x onerror=alert(1)> See [docs](https://docs.lightly.ai) or [x](javascript:alert(1)).'
            }
        });
        const reply = screen.getByTestId('agent-chat-assistant');

        expect(reply.querySelector('strong')).toHaveTextContent('Done.');
        expect(reply.querySelector('img')).toBeNull();
        expect(reply).toHaveTextContent('<img src=x onerror=alert(1)>');
        expect(screen.getByRole('link', { name: 'docs' })).toHaveAttribute('target', '_blank');
        expect(screen.getByRole('link', { name: 'docs' })).toHaveAttribute(
            'rel',
            'noopener noreferrer'
        );
        expect(screen.getByText('x').closest('a')).not.toHaveAttribute('href');
    });
});
