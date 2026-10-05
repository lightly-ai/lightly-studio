import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/svelte';
import '@testing-library/jest-dom';
import AgentChatInput from './AgentChatInput.svelte';

describe('AgentChatInput', () => {
    it('sends on Enter and clears the input', async () => {
        const onSend = vi.fn();
        render(AgentChatInput, { props: { disabled: false, onSend } });
        const input = screen.getByTestId('agent-chat-input');

        await fireEvent.input(input, { target: { value: 'Find tigers' } });
        await fireEvent.keyDown(input, { key: 'Enter' });

        expect(onSend).toHaveBeenCalledWith('Find tigers');
        expect(input).toHaveValue('');
    });

    it('does not send while disabled', async () => {
        const onSend = vi.fn();
        render(AgentChatInput, { props: { disabled: true, onSend } });
        const input = screen.getByTestId('agent-chat-input');

        await fireEvent.input(input, { target: { value: 'Find tigers' } });
        await fireEvent.keyDown(input, { key: 'Enter' });

        expect(onSend).not.toHaveBeenCalled();
        expect(screen.getByTestId('agent-chat-send')).toBeDisabled();
    });
});
