<script lang="ts">
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

<SettingsFieldRow {id} {label}>
    <button
        {id}
        type="button"
        {disabled}
        class="rounded-md border border-input bg-background p-2 text-left text-foreground"
        onclick={() => onStartRecording?.()}
    >
        {#if isRecording}
            <span class="italic opacity-70">Press a key...</span>
        {:else}
            <span>{value}</span>
        {/if}
    </button>
</SettingsFieldRow>
