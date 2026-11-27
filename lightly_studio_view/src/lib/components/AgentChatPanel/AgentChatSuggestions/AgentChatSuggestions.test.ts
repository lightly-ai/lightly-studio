import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/svelte';
import '@testing-library/jest-dom';
import AgentChatSuggestions from './AgentChatSuggestions.svelte';

describe('AgentChatSuggestions', () => {
    it('sends the prompt of the picked suggestion', async () => {
        const onPick = vi.fn();
        const suggestions = [
            { label: 'Tag these samples', prompt: 'Tag the 12 samples as clock.' },
            { label: 'Find similar', prompt: 'Find 20 samples similar to these.' }
        ];
        render(AgentChatSuggestions, { props: { suggestions, onPick } });

        await fireEvent.click(screen.getByRole('button', { name: 'Tag these samples' }));

        expect(onPick).toHaveBeenCalledWith('Tag the 12 samples as clock.');
        expect(screen.getByRole('button', { name: 'Find similar' })).toBeInTheDocument();
    });
});
