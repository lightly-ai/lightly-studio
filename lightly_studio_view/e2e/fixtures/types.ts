export type BoundingBox = {
    x: number;
    y: number;
    width: number;
    height: number;
};

export type Annotation = {
    label: string;
    coordinates: BoundingBox;
};

export type SampleFixture = {
    name: string;
    annotations: Annotation[];
};
