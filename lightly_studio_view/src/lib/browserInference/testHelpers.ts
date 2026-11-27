const textEncoder = new TextEncoder();

const WIRE_TYPE_VARINT = 0;
const WIRE_TYPE_LENGTH_DELIMITED = 2;
const IR_VERSION_FIELD = 1;
const GRAPH_FIELD = 7;
const METADATA_PROPS_FIELD = 14;
const ENTRY_KEY_FIELD = 1;
const ENTRY_VALUE_FIELD = 2;
const IR_VERSION = 8;

const encodeVarint = (value: number): number[] => {
    const bytes: number[] = [];
    let rest = value;
    while (rest >= 0x80) {
        bytes.push((rest % 0x80) | 0x80);
        rest = Math.floor(rest / 0x80);
    }
    bytes.push(rest);
    return bytes;
};

const encodeTag = (field: number, wireType: number) => encodeVarint(field * 8 + wireType);

const encodeBytesField = (field: number, bytes: Uint8Array | number[]): number[] => [
    ...encodeTag(field, WIRE_TYPE_LENGTH_DELIMITED),
    ...encodeVarint(bytes.length),
    ...bytes
];

// Builds a minimal ONNX ModelProto: an IR version, a junk graph field that readers must skip,
// and one metadata_props entry per key.
export const encodeModel = (metadata: Record<string, string>): Uint8Array<ArrayBuffer> => {
    const entries = Object.entries(metadata).flatMap(([key, value]) =>
        encodeBytesField(METADATA_PROPS_FIELD, [
            ...encodeBytesField(ENTRY_KEY_FIELD, textEncoder.encode(key)),
            ...encodeBytesField(ENTRY_VALUE_FIELD, textEncoder.encode(value))
        ])
    );
    return new Uint8Array([
        ...encodeTag(IR_VERSION_FIELD, WIRE_TYPE_VARINT),
        ...encodeVarint(IR_VERSION),
        ...encodeBytesField(GRAPH_FIELD, [1, 2, 3, 0x72, 0x0a]),
        ...entries
    ]);
};
