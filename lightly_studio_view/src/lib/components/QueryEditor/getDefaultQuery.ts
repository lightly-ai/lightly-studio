const IMAGE_QUERY = `# Example query
width < 500
AND "reviewed" IN tags
AND object_detection(class_name = "person" AND x > 10)
`;

export function getDefaultQuery(sampleType?: 'image' | 'video'): string {
    return sampleType === 'video' ? 'duration_s > 10' : IMAGE_QUERY;
}
