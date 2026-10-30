<script lang="ts">
    import { cn } from '$lib/utils';
    import { SettingsFieldRow } from '../SettingsFieldRow';

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

<SettingsFieldRow {id} {label} isLabelClickable>
    <button
        {id}
        type="button"
        {disabled}
        class={cn(
            'inline-flex h-8 min-w-9 items-center justify-center whitespace-nowrap rounded-md border border-b-[3px] border-border bg-muted px-2.5 text-sm font-medium capitalize text-foreground transition-colors',
            'hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
            'disabled:cursor-default disabled:bg-transparent disabled:font-normal disabled:normal-case disabled:text-muted-foreground disabled:hover:bg-transparent',
            isRecording && 'border-primary text-primary ring-2 ring-primary/30'
        )}
        onclick={() => onStartRecording?.()}
    >
        {#if isRecording}
            <span class="normal-case">Press a key...</span>
        {:else}
            <span>{value}</span>
        {/if}
    </button>
</SettingsFieldRow>
