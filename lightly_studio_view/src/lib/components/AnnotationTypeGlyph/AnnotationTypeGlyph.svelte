<script lang="ts">
    import type { AnnotationType } from '$lib/api/lightly_studio_local/types.gen';
    import { cn } from '$lib/utils';
    import { getAnnotationTypeGlyph } from './annotationTypeGlyph';

    interface Props {
        type: AnnotationType;
        /** Glyph size in px. 13 in side-panel rows, 14 in the sidebar filter. */
        size?: number;
        class?: string;
    }

    const { type, size = 13, class: className }: Props = $props();

    const glyph = $derived(getAnnotationTypeGlyph(type));
</script>

<!--
    Deliberately neutral: the colour chip next to it already carries the annotation's class
    colour, and two colour encodings in one row compete for the same meaning.
-->
{#snippet icon()}
    {@const Icon = glyph.icon}
    <Icon {size} class={cn('shrink-0 text-muted-foreground', className)} />
{/snippet}

<span
    class="inline-flex"
    title={glyph.label}
    aria-label={glyph.label}
    role="img"
    data-testid="annotation-type-glyph"
    data-annotation-type={type}
>
    {@render icon()}
</span>
