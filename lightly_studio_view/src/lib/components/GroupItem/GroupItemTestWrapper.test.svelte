<script lang="ts">
    import type { GroupView } from '$lib/api/lightly_studio_local/types.gen';
    import GroupItem from './GroupItem.svelte';

    let {
        sample,
        width,
        height,
        sample_count
    }: {
        sample: GroupView['group_preview'];
        width: number;
        height: number;
        sample_count: number;
    } = $props();
</script>

<GroupItem {sample} {width} {height} {sample_count} />
