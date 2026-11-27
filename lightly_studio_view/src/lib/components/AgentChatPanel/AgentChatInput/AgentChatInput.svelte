<script lang="ts">
    import SendHorizontal from '@lucide/svelte/icons/send-horizontal';
    import { Button } from '$lib/components';

    interface Props {
        disabled: boolean;
        onSend: (text: string) => void;
    }

    const { disabled, onSend }: Props = $props();

    let text = $state('');

    const submit = () => {
        if (disabled || !text.trim()) return;
        onSend(text);
        text = '';
    };

    // Enter sends, Shift+Enter adds a new line.
    const handleKeydown = (event: KeyboardEvent) => {
        if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) {
            event.preventDefault();
            submit();
        }
    };
</script>

<form
    class="flex items-end gap-2"
    onsubmit={(event) => {
        event.preventDefault();
        submit();
    }}
>
    <textarea
        bind:value={text}
        onkeydown={handleKeydown}
        rows="2"
        placeholder="Ask the agent…"
        aria-label="Message to the agent"
        data-testid="agent-chat-input"
        class="min-h-[2.5rem] flex-1 resize-none rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
    ></textarea>
    <Button
        icon={SendHorizontal}
        variant="default"
        ariaLabel="Send message"
        buttonProps={{
            type: 'submit',
            size: 'icon',
            disabled: disabled || !text.trim(),
            'data-testid': 'agent-chat-send'
        }}
    />
</form>
