import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/svelte';
import '@testing-library/jest-dom';
import AgentChatInput from './AgentChatInput.svelte';

const defaultProps = {
    isSending: false,
    text: 'Find tigers',
    selectedCount: 2,
    onTextChange: vi.fn(),
    onSend: vi.fn(),
    onStop: vi.fn()
};

describe('AgentChatInput', () => {
    it('sends on Enter and allows new lines and input composition', async () => {
        const onSend = vi.fn();
        render(AgentChatInput, { props: { ...defaultProps, onSend } });
        const input = screen.getByRole('textbox', { name: 'Message to the agent' });

        await fireEvent.keyDown(input, { key: 'Enter', shiftKey: true });
        await fireEvent.keyDown(input, { key: 'Enter', isComposing: true });
        expect(onSend).not.toHaveBeenCalled();

        await fireEvent.keyDown(input, { key: 'Enter' });
        expect(onSend).toHaveBeenCalledExactlyOnceWith('Find tigers');
        expect(screen.getByText('2 selected')).toBeVisible();
    });

    it('allows drafting and stopping while a reply runs', async () => {
        const onSend = vi.fn();
        const onTextChange = vi.fn();
        const onStop = vi.fn();
        render(AgentChatInput, {
            props: { ...defaultProps, isSending: true, onTextChange, onSend, onStop }
        });
        const input = screen.getByRole('textbox', { name: 'Message to the agent' });

        await fireEvent.input(input, { target: { value: 'Follow-up' } });
        await fireEvent.keyDown(input, { key: 'Enter' });

        expect(onTextChange).toHaveBeenCalledExactlyOnceWith('Follow-up');
        expect(onSend).not.toHaveBeenCalled();
        expect(screen.queryByRole('button', { name: 'Send message' })).not.toBeInTheDocument();

        await fireEvent.click(screen.getByRole('button', { name: 'Stop the reply' }));
        expect(onStop).toHaveBeenCalledOnce();
    });
});
