<script lang="ts">
    import { Settings } from '@lucide/svelte';
    import { useSettingsDialog } from '$lib/hooks/useSettingsDialog/useSettingsDialog';

    interface Props {
        onClick?: () => void;
    }

    const { onClick }: Props = $props();
    const { openSettingsDialog } = useSettingsDialog();
</script>

<button
    type="button"
    class="flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-sm text-muted-foreground hover:bg-accent hover:text-foreground"
    onclick={() => {
        onClick?.();
        openSettingsDialog('annotation-classes');
    }}
>
    <Settings class="size-4" />
    Edit annotation classes
</button>
