<script lang="ts">
    import type { GroupView } from '$lib/api/lightly_studio_local/types.gen';
    import { GroupGridItem } from './';

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

<GroupGridItem {sample} {width} {height} {sample_count} />
