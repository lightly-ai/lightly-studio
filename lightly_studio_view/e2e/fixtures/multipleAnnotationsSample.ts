import { SampleFixture } from './types';

export const multipleAnnotationsSample: SampleFixture = {
    name: '000000052016.jpg',
    annotations: [
        {
            label: 'person',
            coordinates: {
                x: 153,
                y: 30,
                width: 326,
                height: 596
            }
        },
        {
            label: 'donut',
            coordinates: {
                x: 178,
                y: 274,
                width: 88,
                height: 60
            }
        },
        {
            label: 'backpack',
            coordinates: {
                x: 258,
                y: 205,
                width: 169,
                height: 129
            }
        }
    ]
};
