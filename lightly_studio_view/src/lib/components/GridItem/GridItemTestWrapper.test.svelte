<script lang="ts">
    import GridItem from './GridItem.svelte';

    let {
        content = '',
        width,
        height,
        style,
        dataTestId = 'grid-item',
        ariaLabel = 'View item',
        isSelected = false,
        tag = true,
        caption,
        onSelect,
        ondblclick
    }: {
        content?: string;
        width?: string | number;
        height?: string | number;
        style?: string;
        dataTestId?: string;
        ariaLabel?: string;
        isSelected?: boolean;
        tag?: boolean;
        caption?: string;
        onSelect?: (event: MouseEvent | KeyboardEvent) => void;
        ondblclick?: (event: MouseEvent) => void;
    } = $props();
</script>

<GridItem
    {width}
    {height}
    {style}
    {dataTestId}
    {ariaLabel}
    {isSelected}
    {tag}
    {caption}
    {onSelect}
    {ondblclick}
>
    {content}
</GridItem>
