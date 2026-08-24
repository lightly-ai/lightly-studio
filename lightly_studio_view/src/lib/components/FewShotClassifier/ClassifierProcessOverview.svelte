<script lang="ts">
    interface Props {
        isTemporary: boolean;
    }

    const { isTemporary }: Props = $props();
</script>

<ol class="grid grid-cols-3 gap-2 rounded-lg border bg-muted/20 p-3 text-sm">
    <li><span class="font-medium">1. Choose examples</span></li>
    <li>
        <span class="font-medium">2. Review predictions</span>
        <span class="block text-xs text-muted-foreground">Repeat as useful</span>
    </li>
    <li>
        <span class="font-medium">3. Finish</span>
        <span class="block text-xs text-muted-foreground">
            {isTemporary ? 'Save classifier' : 'Done'}
        </span>
    </li>
</ol>
