<script lang="ts">
    import ArrowUpRight from '@lucide/svelte/icons/arrow-up-right';
    import BookOpen from '@lucide/svelte/icons/book-open';
    import ChartNoAxesColumn from '@lucide/svelte/icons/chart-no-axes-column';
    import ScanLine from '@lucide/svelte/icons/scan-line';
    import Tag from '@lucide/svelte/icons/tag';
    import { Button } from '$lib/components/ui/button';
    import { COLLECTION_OVERVIEW } from '../AgentChatSuggestions/suggestions';

    interface Props {
        disabled: boolean;
        onPick: (prompt: string) => void;
    }

    const { disabled, onPick }: Props = $props();
    const tasks = [
        { icon: ChartNoAxesColumn, ...COLLECTION_OVERVIEW },
        { icon: ScanLine, label: 'Select samples', prompt: 'I want to select samples.' },
        {
            icon: Tag,
            label: 'Find and tag samples',
            prompt: 'I want to find samples and tag them.'
        },
        {
            icon: BookOpen,
            label: 'Ask about LightlyStudio',
            prompt: 'I have a question about LightlyStudio.'
        }
    ];
</script>

<div class="flex min-h-0 flex-1 overflow-y-auto px-4 py-6" data-testid="agent-chat-empty">
    <div class="mx-auto my-auto w-full max-w-lg">
        <h3 class="mb-2 text-xl font-semibold tracking-tight">What would you like to do?</h3>
        <p class="mb-5 text-sm leading-relaxed text-muted-foreground">
            Explore your collection or ask how to do something in LightlyStudio.
        </p>
        <div class="grid gap-2">
            {#each tasks as task (task.label)}
                <Button
                    variant="outline"
                    {disabled}
                    class="group h-auto justify-start gap-3 whitespace-normal rounded-xl bg-background/60 px-3 py-2.5 text-left text-sm"
                    onclick={() => onPick(task.prompt)}
                >
                    <span
                        class="grid size-7 shrink-0 place-items-center rounded-lg bg-primary/10 text-primary"
                    >
                        <task.icon class="size-3.5" />
                    </span>
                    <span class="flex-1">{task.label}</span>
                    <ArrowUpRight
                        class="size-3.5 shrink-0 text-muted-foreground group-hover:text-foreground"
                    />
                </Button>
            {/each}
        </div>
    </div>
</div>
