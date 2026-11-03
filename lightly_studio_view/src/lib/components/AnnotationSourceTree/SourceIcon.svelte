<script lang="ts">
    import { Database } from '@lucide/svelte';
    import { useColorPicker } from '$lib/hooks';

    interface Props {
        sourceName: string;
    }

    let { sourceName }: Props = $props();

    const picker = useColorPicker(() => sourceName);
</script>

<span class="flex shrink-0" title="Annotation source">
    <Database class="size-4" style="color: {picker.borderColor}" aria-hidden="true" />
</span>
