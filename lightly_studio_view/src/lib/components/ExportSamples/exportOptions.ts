export type ExportType =
    | 'samples'
    | 'classifications'
    | 'object_detections_coco'
    | 'object_detections_yolo'
    | 'segmentation'
    | 'captions'
    | 'youtube_vis_segmentation'
    | 'semantic_segmentations';

interface ExportOption {
    value: ExportType;
    label: string;
}

const imageExportOptions: ExportOption[] = [
    { value: 'samples', label: 'Image Filenames' },
    { value: 'classifications', label: 'Image Classifications (CSV)' },
    { value: 'object_detections_coco', label: 'Image Object Detections (COCO)' },
    { value: 'object_detections_yolo', label: 'Image Object Detections (YOLO)' },
    { value: 'segmentation', label: 'Image Segmentation Mask (COCO)' },
    { value: 'semantic_segmentations', label: 'Image Segmentation Mask (PASCAL VOC)' },
    { value: 'captions', label: 'Image Captions' }
];

const youtubeVisOption: ExportOption = {
    value: 'youtube_vis_segmentation',
    label: 'YouTube-VIS Video Segmentation Masks'
};

export function getExportOptions(sampleType: string | undefined): ExportOption[] {
    if (sampleType === 'video') {
        return [
            { value: 'classifications', label: 'Video Classifications (CSV)' },
            youtubeVisOption
        ];
    }
    if (sampleType === 'video_frame') return [youtubeVisOption];
    return imageExportOptions;
}

export function getDefaultExportType(sampleType: string | undefined): ExportType {
    return sampleType === 'video' || sampleType === 'video_frame'
        ? 'youtube_vis_segmentation'
        : 'samples';
}
