<script lang="ts">
    import CollectionLayout from './CollectionLayout.svelte';

    type TestCase =
        | 'details-mode'
        | 'no-sidebar'
        | 'with-sidebar'
        | 'with-grid-header'
        | 'no-grid-header'
        | 'with-selection-pill'
        | 'with-all-snippets';

    let { testCase = 'no-sidebar' }: { testCase?: TestCase } = $props();

    const noop = () => {};
</script>

{#if testCase === 'details-mode'}
    <CollectionLayout
        showDetails={true}
        showLeftSidebar={false}
        showWithPlot={false}
        showGridHeader={false}
        showSelectionPill={false}
        selectedCount={0}
        onClearSelection={noop}
    >
        <div data-testid="details-children">Details content</div>
    </CollectionLayout>
{:else if testCase === 'no-sidebar'}
    <CollectionLayout
        showDetails={false}
        showLeftSidebar={false}
        showWithPlot={false}
        showGridHeader={false}
        showSelectionPill={false}
        selectedCount={0}
        onClearSelection={noop}
    >
        <div data-testid="main-children">Main content</div>
    </CollectionLayout>
{:else if testCase === 'with-sidebar'}
    <CollectionLayout
        showDetails={false}
        showLeftSidebar={true}
        showWithPlot={false}
        showGridHeader={false}
        showSelectionPill={false}
        selectedCount={0}
        onClearSelection={noop}
    >
        {#snippet sidebar()}
            <div data-testid="sidebar-content">Sidebar content</div>
        {/snippet}
        <div data-testid="main-children">Main content</div>
    </CollectionLayout>
{:else if testCase === 'with-grid-header'}
    <CollectionLayout
        showDetails={false}
        showLeftSidebar={false}
        showWithPlot={false}
        showGridHeader={true}
        showSelectionPill={false}
        selectedCount={0}
        onClearSelection={noop}
    >
        {#snippet searchBar()}
            <div data-testid="search-bar">Search bar</div>
        {/snippet}
        <div data-testid="main-children">Main content</div>
    </CollectionLayout>
{:else if testCase === 'no-grid-header'}
    <CollectionLayout
        showDetails={false}
        showLeftSidebar={false}
        showWithPlot={false}
        showGridHeader={false}
        showSelectionPill={false}
        selectedCount={0}
        onClearSelection={noop}
    >
        <div data-testid="main-children">Main content</div>
    </CollectionLayout>
{:else if testCase === 'with-selection-pill'}
    <CollectionLayout
        showDetails={false}
        showLeftSidebar={false}
        showWithPlot={false}
        showGridHeader={false}
        showSelectionPill={true}
        selectedCount={3}
        onClearSelection={noop}
    >
        <div data-testid="main-children">Main content</div>
    </CollectionLayout>
{:else if testCase === 'with-all-snippets'}
    <CollectionLayout
        showDetails={false}
        showLeftSidebar={true}
        showWithPlot={false}
        showGridHeader={true}
        showSelectionPill={false}
        selectedCount={0}
        onClearSelection={noop}
    >
        {#snippet header()}
            <div data-testid="header-content">Header</div>
        {/snippet}
        {#snippet sidebar()}
            <div data-testid="sidebar-content">Sidebar</div>
        {/snippet}
        {#snippet searchBar()}
            <div data-testid="search-bar">Search</div>
        {/snippet}
        {#snippet footer()}
            <div data-testid="footer-content">Footer</div>
        {/snippet}
        <div data-testid="main-children">Children</div>
    </CollectionLayout>
{/if}
