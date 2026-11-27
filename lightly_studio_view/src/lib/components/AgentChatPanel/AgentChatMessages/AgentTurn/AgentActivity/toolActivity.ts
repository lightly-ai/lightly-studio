const toolLabels: Record<string, [running: string, completed: string]> = {
    get_collection_overview: ['Reviewing the collection', 'Collection overview'],
    list_annotation_classes: ['Checking annotation classes', 'Annotation classes'],
    get_distribution: ['Analyzing the distribution', 'Distribution analysis'],
    find_samples: ['Finding matching samples', 'Sample search'],
    search_by_text: ['Finding matching images', 'Image search'],
    find_similar_samples: ['Finding similar samples', 'Similarity search'],
    compute_metadata: ['Computing sample metadata', 'Sample metadata'],
    run_selection: ['Selecting samples', 'Sample selection'],
    tag_samples: ['Applying tag', 'Tagging'],
    show_samples: ['Showing samples in the grid', 'Grid results'],
    search_docs: ['Searching the documentation', 'Documentation search'],
    list_operators: ['Checking available operators', 'Available operators'],
    run_operator: ['Running an operator', 'Operator run']
};

export function formatToolActivity(
    name: string,
    status: 'running' | 'done' | 'error' | 'interrupted'
) {
    const [running, completed] = Object.hasOwn(toolLabels, name)
        ? toolLabels[name]
        : ['Working with the collection', 'Collection activity'];
    if (status === 'running') return `${running}…`;
    if (status === 'interrupted') return `${completed} interrupted`;
    if (status === 'error') return `${completed} failed`;
    return completed;
}
