<script lang="ts">
    import ArrowUp from '@lucide/svelte/icons/arrow-up';
    import ScanLine from '@lucide/svelte/icons/scan-line';
    import Square from '@lucide/svelte/icons/square';
    import { Button } from '$lib/components/ui/button';

    interface Props {
        /** A reply is running. The user can draft the next message, but not send it. */
        isSending: boolean;
        text: string;
        selectedCount: number;
        onTextChange: (value: string) => void;
        onSend: (text: string) => void;
        onStop: () => void;
    }

    const { isSending, text, selectedCount, onTextChange, onSend, onStop }: Props = $props();
    let input: HTMLTextAreaElement | undefined = $state();

    export function focus() {
        input?.focus();
    }

    function submit() {
        if (isSending || !text.trim()) return;
        onSend(text);
    }

    function onKeydown(event: KeyboardEvent) {
        if (event.key !== 'Enter' || event.shiftKey || event.isComposing) return;
        event.preventDefault();
        submit();
    }

    $effect(() => {
        void text;
        if (!input) return;
        input.style.height = 'auto';
        input.style.height = `${input.scrollHeight}px`;
    });
</script>

<form
    class="shrink-0 border-t border-border/70 px-4 pb-4 pt-3"
    onsubmit={(event) => {
        event.preventDefault();
        submit();
    }}
>
    <div
        class="rounded-xl border border-input bg-background p-2 shadow-sm focus-within:border-ring"
    >
        <textarea
            bind:this={input}
            value={text}
            oninput={(event) => onTextChange(event.currentTarget.value)}
            onkeydown={onKeydown}
            rows="1"
            placeholder="Ask about this collection…"
            aria-label="Message to the agent"
            data-testid="agent-chat-input"
            class="block max-h-36 min-h-9 w-full resize-none border-0 bg-transparent px-2 py-1.5 text-sm leading-5 placeholder:text-muted-foreground focus:ring-0"
        ></textarea>
        <div class="flex min-h-8 items-center justify-end gap-2">
            {#if selectedCount}
                <span
                    class="mr-auto flex items-center gap-1 rounded-md bg-muted px-2 py-1 text-xs text-muted-foreground"
                >
                    <ScanLine class="size-3 shrink-0" aria-hidden="true" />
                    {selectedCount} selected
                </span>
            {/if}
            {#if isSending}
                <Button
                    type="button"
                    size="icon"
                    variant="secondary"
                    class="size-8 rounded-lg"
                    aria-label="Stop the reply"
                    title="Stop the reply"
                    data-testid="agent-chat-stop"
                    onclick={onStop}
                >
                    <Square class="size-3.5 fill-current" aria-hidden="true" />
                </Button>
            {:else}
                <Button
                    type="submit"
                    size="icon"
                    class="size-8 rounded-lg"
                    disabled={!text.trim()}
                    aria-label="Send message"
                    title="Send message"
                    data-testid="agent-chat-send"
                >
                    <ArrowUp class="size-4" aria-hidden="true" />
                </Button>
            {/if}
        </div>
    </div>
</form>
