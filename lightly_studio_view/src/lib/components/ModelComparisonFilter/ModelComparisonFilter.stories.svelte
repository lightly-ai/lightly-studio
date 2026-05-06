<script module>
    import { defineMeta } from '@storybook/addon-svelte-csf';

    const { Story } = defineMeta({
        title: 'Prototypes/ModelComparisonFilter',
        tags: ['autodocs']
    });
</script>

<script lang="ts">
    import Grid from '$lib/components/Grid/Grid.svelte';
    import GridItem from '$lib/components/GridItem/GridItem.svelte';
    import Segment from '$lib/components/Segment/Segment.svelte';
    import { Checkbox } from '$lib/components/ui/checkbox/index.js';
    import { Label } from '$lib/components/ui/label/index.js';
    import { Tooltip } from '$lib/components/ui/tooltip';
    import { Slider } from '$lib/components/ui/slider';

    // ── Types ────────────────────────────────────────────────────────────────

    type ModelDef = { id: string; name: string; color: string; enabled: boolean };
    type LabelDef = { name: string; enabled: boolean };
    type BBox = { x: number; y: number; w: number; h: number; label: string; modelId: string; confidence: number };
    type ImageData = { index: number; width: number; height: number; bboxes: BBox[] };

    // ── Fake data ────────────────────────────────────────────────────────────

    const ALL_LABELS = ['cat', 'dog', 'car', 'person', 'bicycle'];
    const MODEL_DEFS: ModelDef[] = [
        { id: 'ground_truth', name: 'ground_truth', color: '#22c55e', enabled: true },
        { id: 'yolo_v8', name: 'yolo_v8', color: '#3b82f6', enabled: true },
        { id: 'predictions_a', name: 'predictions_a', color: '#f97316', enabled: false }
    ];

    function seededRand(seed: number): number {
        const x = Math.sin(seed + 1) * 10000;
        return x - Math.floor(x);
    }

    function generateImage(imageIndex: number): ImageData {
        let seed = imageIndex * 97;
        const width = Math.round(seededRand(seed++) * 3800 + 200);
        const height = Math.round(seededRand(seed++) * 3800 + 200);
        const bboxes: BBox[] = [];

        for (const modelId of MODEL_DEFS.map((m) => m.id)) {
            const boxCount = Math.floor(seededRand(seed++) * 3) + 1;
            for (let b = 0; b < boxCount; b++) {
                bboxes.push({
                    x: seededRand(seed++) * 0.5,
                    y: seededRand(seed++) * 0.5,
                    w: seededRand(seed++) * 0.35 + 0.1,
                    h: seededRand(seed++) * 0.35 + 0.1,
                    label: ALL_LABELS[Math.floor(seededRand(seed++) * ALL_LABELS.length)],
                    confidence: Math.round(seededRand(seed++) * 100) / 100,
                    modelId
                });
            }
        }

        return { index: imageIndex, width, height, bboxes };
    }

    const TOTAL_IMAGES = 48;
    const ALL_IMAGES: ImageData[] = Array.from({ length: TOTAL_IMAGES }, (_, i) => generateImage(i));

    // ── Reactive state ───────────────────────────────────────────────────────

    let models: ModelDef[] = $state(MODEL_DEFS.map((m) => ({ ...m })));
    let labelDefs: LabelDef[] = $state(ALL_LABELS.map((name) => ({ name, enabled: true })));

    let widthRange = $state([0, 4000]);
    let heightRange = $state([0, 4000]);

    let confidenceThresholds = $state<Record<string, number>>(
        Object.fromEntries(MODEL_DEFS.map((m) => [m.id, 0]))
    );

    const enabledModelIds = $derived(new Set(models.filter((m) => m.enabled).map((m) => m.id)));
    const enabledLabels = $derived(new Set(labelDefs.filter((l) => l.enabled).map((l) => l.name)));
    const modelColorMap = $derived(Object.fromEntries(models.map((m) => [m.id, m.color])));

    const colorByLabel = $derived(enabledModelIds.size === 1);

    const LABEL_COLORS: Record<string, string> = {
        cat: '#f43f5e',
        dog: '#f97316',
        car: '#eab308',
        person: '#22c55e',
        bicycle: '#6366f1'
    };

    function bboxColor(modelId: string, label: string): string {
        return colorByLabel ? (LABEL_COLORS[label] ?? '#ffffff') : (modelColorMap[modelId] ?? '#ffffff');
    }

    function toggleModel(id: string) {
        models = models.map((m) => (m.id === id ? { ...m, enabled: !m.enabled } : m));
    }

    function toggleLabel(name: string) {
        labelDefs = labelDefs.map((l) => (l.name === name ? { ...l, enabled: !l.enabled } : l));
    }

    const visibleImages = $derived(
        ALL_IMAGES.filter((img) => {
            if (img.width < widthRange[0] || img.width > widthRange[1]) return false;
            if (img.height < heightRange[0] || img.height > heightRange[1]) return false;
            return img.bboxes.some(
                (b) =>
                    enabledModelIds.has(b.modelId) &&
                    enabledLabels.has(b.label) &&
                    b.confidence >= (confidenceThresholds[b.modelId] ?? 0)
            );
        })
    );

    const visibleCount = $derived(visibleImages.length);

    // ── Helpers ──────────────────────────────────────────────────────────────

    function hexToRgba(hex: string, alpha: number): string {
        const r = parseInt(hex.slice(1, 3), 16);
        const g = parseInt(hex.slice(3, 5), 16);
        const b = parseInt(hex.slice(5, 7), 16);
        return `rgba(${r}, ${g}, ${b}, ${alpha})`;
    }

    function computeIoU(a: BBox, b: BBox): number {
        const ax2 = a.x + a.w, ay2 = a.y + a.h;
        const bx2 = b.x + b.w, by2 = b.y + b.h;
        const ix1 = Math.max(a.x, b.x), iy1 = Math.max(a.y, b.y);
        const ix2 = Math.min(ax2, bx2), iy2 = Math.min(ay2, by2);
        const iw = Math.max(0, ix2 - ix1), ih = Math.max(0, iy2 - iy1);
        const intersection = iw * ih;
        const union = a.w * a.h + b.w * b.h - intersection;
        return union > 0 ? intersection / union : 0;
    }

    const IOU_THRESHOLD = 0.5;

    // ── Aggregation stats ────────────────────────────────────────────────────

    type ClassStat = { count: number; confidenceSum: number };

    type ModelStats = {
        modelId: string;
        annotationCount: number;
        coverageCount: number;
        classStats: Record<string, ClassStat>;
        topLabel: string;
        avgConfidence: number;
        avgBoxArea: number;
        precision?: number;
        recall?: number;
        avgIoU?: number;
    };

    const GT_MODEL_ID = 'ground_truth';

    const modelStats = $derived(
        models
            .filter((m) => enabledModelIds.has(m.id))
            .map((m): ModelStats => {
                let annotationCount = 0;
                let coverageCount = 0;
                let confidenceSum = 0;
                let boxAreaSum = 0;
                const classStats: Record<string, ClassStat> = {};

                // For precision/recall vs ground truth
                let tp = 0, fp = 0, fn = 0, iouSum = 0;
                const computeVsGt = m.id !== GT_MODEL_ID && enabledModelIds.has(GT_MODEL_ID);

                for (const img of visibleImages) {
                    const threshold = confidenceThresholds[m.id] ?? 0;
                    const boxes = img.bboxes.filter(
                        (b) => b.modelId === m.id && enabledLabels.has(b.label) && b.confidence >= threshold
                    );

                    if (boxes.length > 0) {
                        coverageCount++;
                        annotationCount += boxes.length;
                        for (const b of boxes) {
                            confidenceSum += b.confidence;
                            boxAreaSum += b.w * b.h;
                            const cs = classStats[b.label] ?? { count: 0, confidenceSum: 0 };
                            cs.count++;
                            cs.confidenceSum += b.confidence;
                            classStats[b.label] = cs;
                        }
                    }

                    if (computeVsGt) {
                        const gtBoxes = img.bboxes.filter(
                            (b) => b.modelId === GT_MODEL_ID && enabledLabels.has(b.label)
                        );
                        const matched = new Set<number>();
                        for (const pred of boxes) {
                            let bestIoU = 0, bestIdx = -1;
                            gtBoxes.forEach((gt, i) => {
                                if (matched.has(i) || gt.label !== pred.label) return;
                                const iou = computeIoU(pred, gt);
                                if (iou > bestIoU) { bestIoU = iou; bestIdx = i; }
                            });
                            if (bestIoU >= IOU_THRESHOLD && bestIdx >= 0) {
                                tp++;
                                iouSum += bestIoU;
                                matched.add(bestIdx);
                            } else {
                                fp++;
                            }
                        }
                        fn += gtBoxes.length - matched.size;
                    }
                }

                const topLabel = Object.entries(classStats).sort((a, b) => b[1].count - a[1].count)[0]?.[0] ?? '—';
                const avgConfidence = annotationCount > 0 ? confidenceSum / annotationCount : 0;
                const avgBoxArea = annotationCount > 0 ? boxAreaSum / annotationCount : 0;

                return {
                    modelId: m.id,
                    annotationCount,
                    coverageCount,
                    classStats,
                    topLabel,
                    avgConfidence,
                    avgBoxArea,
                    ...(computeVsGt && {
                        precision: tp + fp > 0 ? tp / (tp + fp) : 0,
                        recall: tp + fn > 0 ? tp / (tp + fn) : 0,
                        avgIoU: tp > 0 ? iouSum / tp : 0
                    })
                };
            })
    );

    const DIM_MAX = 4000;
    const columnCount = 5;
</script>

<Story name="Comparison View" asChild>
    <div class="flex h-screen w-full overflow-hidden bg-background text-foreground">
        <!-- ── Sidebar ───────────────────────────────────────────────────── -->
        <aside
            class="flex w-60 shrink-0 flex-col gap-4 overflow-y-auto border-r border-border px-3 py-4"
        >
            <!-- Models -->
            <Segment title="Models">
                <div class="space-y-2">
                    {#each models as model (model.id)}
                        <div class="space-y-1" title={model.name}>
                            <div class="flex items-center space-x-2">
                                <Checkbox
                                    id={`model-${model.id}`}
                                    checked={model.enabled}
                                    aria-labelledby={`model-${model.id}-label`}
                                    onCheckedChange={() => toggleModel(model.id)}
                                />
                                <Label
                                    id={`model-${model.id}-label`}
                                    for={`model-${model.id}`}
                                    class="flex min-w-0 flex-1 cursor-pointer items-center space-x-2 text-nowrap"
                                >
                                    <span
                                        class="inline-block h-3 w-3 shrink-0 rounded-sm border"
                                        style="background-color: {hexToRgba(model.color, 0.35)}; border-color: {model.color};"
                                    ></span>
                                    <span class="flex-1 truncate text-sm font-normal">{model.name}</span>
                                </Label>
                            </div>
                            {#if model.enabled}
                                <div class="flex items-center gap-2 pl-6 text-xs text-muted-foreground">
                                    <Tooltip content="Only show annotations from this model with confidence ≥ this value" position="right">
                                        <span class="cursor-help underline decoration-dotted">Confidence</span>
                                    </Tooltip>
                                    <input
                                        type="range"
                                        min="0"
                                        max="1"
                                        step="0.05"
                                        value={confidenceThresholds[model.id]}
                                        oninput={(e) => {
                                            confidenceThresholds = {
                                                ...confidenceThresholds,
                                                [model.id]: parseFloat((e.target as HTMLInputElement).value)
                                            };
                                        }}
                                        class="min-w-0 flex-1 accent-primary"
                                        style="accent-color: {model.color};"
                                    />
                                    <span class="w-7 shrink-0 text-right tabular-nums">
                                        {confidenceThresholds[model.id].toFixed(2)}
                                    </span>
                                </div>
                            {/if}
                        </div>
                    {/each}
                </div>
            </Segment>

            <!-- Labels -->
            <Segment title="Labels">
                <div class="space-y-2">
                    {#each labelDefs as lbl (lbl.name)}
                        <div class="flex items-center space-x-2" title={lbl.name}>
                            <Checkbox
                                id={`label-${lbl.name}`}
                                checked={lbl.enabled}
                                aria-labelledby={`label-${lbl.name}-label`}
                                onCheckedChange={() => toggleLabel(lbl.name)}
                            />
                            <Label
                                id={`label-${lbl.name}-label`}
                                for={`label-${lbl.name}`}
                                class="flex min-w-0 flex-1 cursor-pointer items-center space-x-2 text-nowrap"
                            >
                                {#if colorByLabel}
                                    <span
                                        class="inline-block h-3 w-3 shrink-0 rounded-sm border transition-colors"
                                        style="background-color: {hexToRgba(LABEL_COLORS[lbl.name] ?? '#ffffff', 0.35)}; border-color: {LABEL_COLORS[lbl.name] ?? '#ffffff'};"
                                    ></span>
                                {/if}
                                <span class="flex-1 truncate text-sm font-normal">{lbl.name}</span>
                            </Label>
                        </div>
                    {/each}
                </div>
            </Segment>

            <!-- Dimensions filter -->
            <Segment title="Dimensions">
                <div class="space-y-3 text-xs">
                    <div class="space-y-2">
                        <div class="flex items-center justify-between text-muted-foreground">
                            <span>Width</span>
                            <span class="tabular-nums">{widthRange[0]} – {widthRange[1]} px</span>
                        </div>
                        <Slider
                            min={0}
                            max={DIM_MAX}
                            step={100}
                            bind:value={widthRange}
                        />
                    </div>
                    <div class="space-y-2">
                        <div class="flex items-center justify-between text-muted-foreground">
                            <span>Height</span>
                            <span class="tabular-nums">{heightRange[0]} – {heightRange[1]} px</span>
                        </div>
                        <Slider
                            min={0}
                            max={DIM_MAX}
                            step={100}
                            bind:value={heightRange}
                        />
                    </div>
                </div>
            </Segment>
        </aside>

        <!-- ── Main area ─────────────────────────────────────────────────── -->
        <div class="flex min-w-0 flex-1 flex-col">
            <!-- Header bar -->
            <div
                class="flex items-center gap-3 border-b border-border px-4 py-2 text-sm text-muted-foreground"
            >
                <span>{visibleCount} of {TOTAL_IMAGES} images</span>
            </div>

            <!-- Grid -->
            <div class="min-h-0 flex-1">
                {#if visibleCount === 0}
                    <div class="flex h-full items-center justify-center text-muted-foreground">
                        No images match the current filters.
                    </div>
                {:else}
                    <Grid itemCount={visibleCount} {columnCount}>
                        {#snippet gridItem({ index, style, width, height }: { index: number; style: string; width: number; height: number })}
                            {@const img = visibleImages[index]}
                            <GridItem {width} {height} {style} tag={false}>
                                <img
                                    src="https://picsum.photos/{Math.round(width)}/{Math.round(height)}?random={img.index}"
                                    alt="Sample {img.index + 1}"
                                    class="h-full w-full object-cover"
                                    loading="lazy"
                                />
                                <!-- Dimension badge -->
                                <span
                                    class="pointer-events-none absolute bottom-1 right-1 z-10 rounded bg-black/50 px-1 py-0.5 text-[9px] tabular-nums text-white"
                                >
                                    {img.width}×{img.height}
                                </span>

                                <!-- Bbox overlays -->
                                <div class="pointer-events-none absolute inset-0">
                                    {#each img.bboxes as bbox}
                                        {#if enabledModelIds.has(bbox.modelId) && enabledLabels.has(bbox.label) && bbox.confidence >= (confidenceThresholds[bbox.modelId] ?? 0)}
                                            {@const color = bboxColor(bbox.modelId, bbox.label)}
                                            <div
                                                class="absolute"
                                                style="
                                                    left: {bbox.x * 100}%;
                                                    top: {bbox.y * 100}%;
                                                    width: {bbox.w * 100}%;
                                                    height: {bbox.h * 100}%;
                                                    border: 2px solid {color};
                                                    box-shadow: inset 0 0 0 1px {hexToRgba(color, 0.25)};
                                                "
                                            >
                                                <span
                                                    class="absolute left-0 top-0 translate-y-[-100%] px-1 py-0.5 text-[9px] font-semibold leading-tight text-white"
                                                    style="background-color: {color};"
                                                >
                                                    {bbox.label} {bbox.confidence.toFixed(2)}
                                                </span>
                                            </div>
                                        {/if}
                                    {/each}
                                </div>
                            </GridItem>
                        {/snippet}
                    </Grid>
                {/if}
            </div>
        </div>

        <!-- ── Stats sidebar ─────────────────────────────────────────────── -->
        <aside
            class="flex w-52 shrink-0 flex-col gap-0 overflow-y-auto border-l border-border px-3 py-4"
        >
            <p class="mb-3 text-xs font-medium uppercase tracking-wider text-muted-foreground">
                Stats
            </p>
            {#each modelStats as stat}
                {@const model = models.find((m) => m.id === stat.modelId)!}
                {@const maxCount = Math.max(...modelStats.map((s) => s.annotationCount), 1)}
                <div class="mb-4 space-y-2">
                    <!-- Model name -->
                    <div class="flex items-center gap-1.5">
                        <span
                            class="inline-block h-2.5 w-2.5 shrink-0 rounded-sm"
                            style="background-color: {model.color};"
                        ></span>
                        <span class="truncate text-xs font-semibold">{model.name}</span>
                    </div>

                    <!-- Key numbers -->
                    <div class="grid grid-cols-2 gap-x-2 gap-y-0.5 text-xs">
                        <span class="text-muted-foreground">Annotations</span>
                        <span class="text-right tabular-nums font-medium">{stat.annotationCount}</span>

                        <Tooltip content="% of filtered images that have at least one annotation from this model" position="left">
                            <span class="cursor-help text-muted-foreground underline decoration-dotted">Coverage</span>
                        </Tooltip>
                        <span class="text-right tabular-nums font-medium">
                            {visibleCount > 0 ? Math.round((stat.coverageCount / visibleCount) * 100) : 0}%
                        </span>

                        <Tooltip content="The class this model annotates most often in the filtered image set" position="left">
                            <span class="cursor-help text-muted-foreground underline decoration-dotted">Top class</span>
                        </Tooltip>
                        <span class="text-right font-medium">{stat.topLabel}</span>

                        <Tooltip content="Mean confidence score across all visible annotations from this model" position="left">
                            <span class="cursor-help text-muted-foreground underline decoration-dotted">Avg conf.</span>
                        </Tooltip>
                        <span class="text-right tabular-nums font-medium">{stat.avgConfidence.toFixed(2)}</span>

                        <Tooltip content="Average bounding box area as % of image area — higher means larger predictions" position="left">
                            <span class="cursor-help text-muted-foreground underline decoration-dotted">Avg box</span>
                        </Tooltip>
                        <span class="text-right tabular-nums font-medium">{(stat.avgBoxArea * 100).toFixed(1)}%</span>
                    </div>

                    <!-- Overall annotation bar -->
                    <div class="h-1.5 w-full overflow-hidden rounded-full bg-muted">
                        <div
                            class="h-full rounded-full transition-all"
                            style="width: {(stat.annotationCount / maxCount) * 100}%; background-color: {model.color};"
                        ></div>
                    </div>

                    <!-- Precision / Recall / IoU vs ground_truth -->
                    {#if stat.precision !== undefined}
                        <div class="space-y-1">
                            <p class="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
                                vs ground_truth
                            </p>
                            <div class="grid grid-cols-2 gap-x-2 gap-y-0.5 text-xs">
                                <Tooltip content="TP / (TP + FP) — fraction of predictions that match a ground truth box (IoU ≥ 0.5, same class)" position="left">
                                    <span class="cursor-help text-muted-foreground underline decoration-dotted">Precision</span>
                                </Tooltip>
                                <span class="text-right tabular-nums font-medium">{stat.precision.toFixed(2)}</span>

                                <Tooltip content="TP / (TP + FN) — fraction of ground truth boxes that were found by this model" position="left">
                                    <span class="cursor-help text-muted-foreground underline decoration-dotted">Recall</span>
                                </Tooltip>
                                <span class="text-right tabular-nums font-medium">{stat.recall!.toFixed(2)}</span>

                                <Tooltip content="Average Intersection over Union for matched prediction–ground truth pairs" position="left">
                                    <span class="cursor-help text-muted-foreground underline decoration-dotted">Avg IoU</span>
                                </Tooltip>
                                <span class="text-right tabular-nums font-medium">{stat.avgIoU!.toFixed(2)}</span>
                            </div>
                        </div>
                    {/if}

                    <!-- Per-class breakdown with avg confidence -->
                    <div class="space-y-1">
                        <p class="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">By class</p>
                        {#each ALL_LABELS as lbl}
                            {@const cs = stat.classStats[lbl]}
                            {@const count = cs?.count ?? 0}
                            {@const avgConf = cs ? cs.confidenceSum / cs.count : 0}
                            {@const maxClassCount = Math.max(
                                ...modelStats.map((s) => s.classStats[lbl]?.count ?? 0),
                                1
                            )}
                            {#if count > 0}
                                <div class="space-y-0.5 text-xs">
                                    <div class="flex items-center justify-between">
                                        <span class="truncate text-muted-foreground">{lbl}</span>
                                        <Tooltip content="{count} annotation{count !== 1 ? 's' : ''} · avg confidence {avgConf.toFixed(2)}" position="left">
                                            <span class="cursor-help tabular-nums text-muted-foreground underline decoration-dotted">{count} · {avgConf.toFixed(2)}</span>
                                        </Tooltip>
                                    </div>
                                    <div class="h-1 w-full overflow-hidden rounded-full bg-muted">
                                        <div
                                            class="h-full rounded-full transition-all"
                                            style="width: {(count / maxClassCount) * 100}%; background-color: {hexToRgba(model.color, 0.7)};"
                                        ></div>
                                    </div>
                                </div>
                            {/if}
                        {/each}
                    </div>

                    <hr class="border-border" />
                </div>
            {/each}
            {#if modelStats.length === 0}
                <p class="text-xs text-muted-foreground">No models enabled.</p>
            {/if}
        </aside>
    </div>
</Story>
