<script lang="ts">
    import { Label } from '$lib/components/ui/label';

    interface Props {
        id: string;
        label: string;
        value: string;
        isRecording: boolean;
        disabled?: boolean;
        onStartRecording?: () => void;
    }

    const { id, label, value, isRecording, disabled = false, onStartRecording }: Props = $props();
</script>

<div class="grid grid-cols-2 items-center gap-4">
    <Label for={id} class="text-right text-foreground">
        {label}
    </Label>
    <button
        {id}
        type="button"
        {disabled}
        class="rounded-md border border-input bg-background p-2 text-left text-foreground"
        onclick={(e) => {
            e.preventDefault();
            onStartRecording?.();
        }}
    >
        {#if isRecording}
            <span class="italic opacity-70">Press a key...</span>
        {:else}
            <span>{value}</span>
        {/if}
    </button>
</div>
