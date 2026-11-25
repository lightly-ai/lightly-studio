export type Annotation = {
    label_name: string;
    total_count: number;
    current_count?: number;
    selected: boolean;
    /** The "No annotations" row, which selects the samples without annotations. */
    isNoAnnotationsRow?: boolean;
};

export type GridType = 'images' | 'annotations' | 'captions' | 'video_frames' | 'videos' | 'groups';
export type BoundingBox = {
    x: number;
    y: number;
    width: number;
    height: number;
};
