export type Annotation = {
    label_name: string;
    total_count: number;
    current_count?: number;
    selected: boolean;
};

export type GridType =
    | 'samples'
    | 'annotations'
    | 'captions'
    | 'video_frames'
    | 'videos'
    | 'groups';
export type BoundingBox = {
    x: number;
    y: number;
    width: number;
    height: number;
};
