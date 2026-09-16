<script lang="ts">
    import { version, git_sha, is_tagged_commit } from '$lib/version.json';
    import { BookOpen, Mail } from '@lucide/svelte';

    const linkClass =
        'flex h-[26px] items-center gap-1.5 rounded-md px-2 text-[12.5px] text-muted-foreground transition-colors hover:bg-sidebar-accent/60 hover:text-foreground';
</script>

<div
    class="flex items-center gap-0.5 border-t border-border-hard px-1.5 py-[7px]"
    data-testid="sidebar-footer"
>
    <a class={linkClass} href="https://docs.lightly.ai/studio/" target="_blank" rel="noreferrer">
        <BookOpen class="size-[13px] shrink-0" />
        <span>Docs</span>
    </a>
    <a class={linkClass} href="https://www.lightly.ai/contact" target="_blank" rel="noreferrer">
        <Mail class="size-[13px] shrink-0" />
        <span>Support</span>
    </a>
    <span class="flex-1"></span>
    <!-- The dev suffix would wrap the row, so it moves to the tooltip. -->
    <span
        class="shrink-0 pr-1.5 text-[10.5px] tabular-nums text-muted-foreground/70"
        title={is_tagged_commit ? `v${version}` : `v${version} (dev: ${git_sha})`}
    >
        v{version}
    </span>
</div>
