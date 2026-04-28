<script lang="ts">
    import { page } from '$app/state';
    import EvaluationDashboard from '$lib/components/EvaluationDashboard/EvaluationDashboard.svelte';

    const datasetId = $derived(page.params.dataset_id!);
</script>

<EvaluationDashboard {datasetId} />
