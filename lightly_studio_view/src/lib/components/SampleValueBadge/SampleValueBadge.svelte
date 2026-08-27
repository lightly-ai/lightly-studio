<script lang="ts">
    import { cn, getSimilarityColor } from '$lib/utils';
    import { formatOrderValue } from './SampleValueBadge.helpers';

    interface Props {
        /** Primary sort value for the active grid sort, when set. Takes precedence over `similarityScore`. */
        orderValue?: number | null;
        /** Similarity to a text/embedding query, when search is active. Shown with a color dot when there is no `orderValue`. */
        similarityScore?: number | null;
        /** Whether a caption/text overlay occupies the bottom edge; lifts the badge (`bottom-8` vs `bottom-1`) so they don't overlap. */
        hasBottomOverlay?: boolean;
    }

    let { orderValue = null, similarityScore = null, hasBottomOverlay = false }: Props = $props();

    const showOrderValue = $derived(orderValue != null);
    const orderValueLabel = $derived(orderValue != null ? formatOrderValue(orderValue) : '');
    const badgeClass = $derived(
        cn(
            'absolute right-1 z-10 box-border flex h-5 items-center rounded bg-black/60 px-1.5 text-xs font-medium text-white backdrop-blur-sm',
            hasBottomOverlay ? 'bottom-8' : 'bottom-1'
        )
    );
</script>

{#if showOrderValue}
    <div class={badgeClass}>
        {orderValueLabel}
    </div>
{:else if similarityScore != null}
    <div class={badgeClass}>
        <span
            class="mr-1.5 block h-2 w-2 rounded-full"
            style="background-color: {getSimilarityColor(similarityScore)}"
        ></span>
        {similarityScore.toFixed(2)}
    </div>
{/if}
