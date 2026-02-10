import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

export type GroupComponent = {
    component_id: string;
    component_type: string;
    component_name: string;
    component_group?: string;
    thumbnail_url?: string;
};

export type Group = {
    group_id: string;
    group_name: string;
    components: GroupComponent[];
    created_at: string;
    thumbnail_url: string;
};

// Working image URLs
const images = [
    'https://images.unsplash.com/photo-1554224155-6726b3ff858f?w=400',
    'https://images.unsplash.com/photo-1436491865332-7a61a109cc05?w=400',
    'https://images.unsplash.com/photo-1472214103451-9374bd1c798e?w=400',
    'https://images.unsplash.com/photo-1576091160399-112ba8d25d1d?w=400',
    'https://images.unsplash.com/photo-1473186578172-c141e6798cf4?w=400'
];

const groupNames = [
    'ID Photo',
    'Passport Documents',
    'Driver License',
    'Medical Records',
    'Bank Statements',
    'Utility Bills',
    'Receipts',
    'Business Cards',
    'Invoices',
    'Contracts',
    'Certificates',
    'Tax Documents',
    'Insurance Documents',
    'Legal Papers',
    'Property Deeds',
    'Vehicle Registration',
    'Academic Transcripts',
    'Employment Records',
    'Financial Reports',
    'Travel Documents'
];

const componentGroups = ['front page', 'back page', 'signature page', 'attachment'];

// Generate 100 mock groups
const mockGroups: Group[] = Array.from({ length: 1000 }, (_, i) => {
    const groupIndex = i + 1;
    const numComponents = Math.floor(Math.random() * 4) + 2; // 2-5 components per group
    const baseDate = new Date('2024-01-01');
    baseDate.setHours(baseDate.getHours() + groupIndex * 3);

    return {
        group_id: String(groupIndex),
        group_name: `${groupNames[i % groupNames.length]} ${Math.floor(i / groupNames.length) + 1}`,
        components: Array.from({ length: numComponents }, (_, j) => ({
            component_id: `img_${groupIndex}_${j + 1}`,
            component_type: 'image',
            component_name: `Component ${j + 1}`,
            component_group: componentGroups[j % componentGroups.length],
            thumbnail_url: images[j % images.length]
        })),
        created_at: baseDate.toISOString(),
        thumbnail_url: images[Math.floor(Math.random() * images.length)]
    };
});

export const GET: RequestHandler = async ({ url }) => {
    // Simulate network delay
    await new Promise((resolve) => setTimeout(resolve, 500));

    // Get pagination parameters
    const offset = parseInt(url.searchParams.get('offset') || '0');
    const limit = parseInt(url.searchParams.get('limit') || '10');
    const filterName = url.searchParams.get('name');
    const componentType = url.searchParams.get('component_type');

    let groups = mockGroups;

    // Apply name filter if provided
    if (filterName) {
        groups = groups.filter((g) =>
            g.group_name.toLowerCase().includes(filterName.toLowerCase())
        );
    }

    // Apply component type filter if provided
    if (componentType) {
        groups = groups.filter((g) =>
            g.components.some((c) => c.component_group === componentType)
        );
    }

    // Apply pagination
    const total = groups.length;
    const paginatedGroups = groups.slice(offset, offset + limit);
    const hasMore = offset + limit < total;

    return json({
        groups: paginatedGroups,
        total,
        offset,
        limit,
        hasMore
    });
};
