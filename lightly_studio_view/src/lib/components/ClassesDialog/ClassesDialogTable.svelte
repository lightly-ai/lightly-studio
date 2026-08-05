<script lang="ts">
    import type { AnnotationLabelWithCountView } from '$lib/api/lightly_studio_local';
    import ClassesDialogRow from './ClassesDialogRow.svelte';

    let { labels }: { labels: AnnotationLabelWithCountView[] } = $props();
</script>

{#if labels.length}
    <div class="max-h-[50vh] overflow-y-auto dark:[color-scheme:dark]">
        <table class="w-full table-fixed text-sm">
            <thead class="sticky top-0 bg-background text-muted-foreground">
                <tr>
                    <th scope="col" class="w-16 py-2 text-left">Color</th>
                    <th scope="col" class="py-2 text-left">Class</th>
                    <th scope="col" class="w-20 py-2 text-center">Counts</th>
                </tr>
            </thead>
            <tbody>
                {#each labels as label (label.annotation_label_id)}
                    <ClassesDialogRow {label} />
                {/each}
            </tbody>
        </table>
    </div>
{:else}
    <p class="py-8 text-center text-sm text-muted-foreground">
        No classes yet. Add your first class above.
    </p>
{/if}
