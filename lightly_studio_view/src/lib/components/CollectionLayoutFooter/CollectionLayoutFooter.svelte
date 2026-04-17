<script lang="ts">
    import { Footer } from '$lib/components';

    const {
        totalSamples,
        filteredSamples,
        totalAnnotations,
        filteredAnnotations
    }: {
        totalSamples: number | undefined;
        filteredSamples: number | undefined;
        totalAnnotations: number;
        filteredAnnotations: number | undefined;
    } = $props();
</script>

<Footer {totalSamples} {filteredSamples} {totalAnnotations} {filteredAnnotations} />
