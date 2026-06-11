<script lang="ts">
    interface Props {
        maxCount: number;
    }

    const { maxCount }: Props = $props();

    const TP_ALPHAS = [0.15, 0.3, 0.5, 0.7, 0.95];
    const FP_FN_ALPHAS = [0.15, 0.3, 0.5, 0.7, 0.95];
</script>

<div
    class="flex flex-wrap items-center gap-x-8 gap-y-2 px-2 pt-4 text-xs text-muted-foreground"
    data-testid="confusion-matrix-legend"
>
    <div class="flex items-center gap-2">
        <span>True positive</span>
        <div class="flex gap-0.5">
            {#each TP_ALPHAS as alpha}
                <span
                    class="block h-3.5 w-5 rounded-sm"
                    style="background: rgba(34,197,94,{alpha});"
                ></span>
            {/each}
        </div>
        <span class="tabular-nums">1</span>
        <span aria-hidden="true">→</span>
        <span class="tabular-nums">{maxCount}</span>
    </div>

    <div class="flex items-center gap-2">
        <span>FP / FN</span>
        <div class="flex gap-0.5">
            {#each FP_FN_ALPHAS as alpha}
                <span
                    class="block h-3.5 w-5 rounded-sm"
                    style="background: rgba(239,68,68,{alpha});"
                ></span>
            {/each}
        </div>
        <span class="tabular-nums">1</span>
        <span aria-hidden="true">→</span>
        <span class="tabular-nums">{maxCount}</span>
    </div>

    <span class="text-muted-foreground/70">
        Color intensity scales logarithmically with cell count. Hover for breakdown.
    </span>
</div>
