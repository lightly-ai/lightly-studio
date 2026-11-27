const WIRE_TYPE_VARINT = 0;
const WIRE_TYPE_FIXED64 = 1;
const WIRE_TYPE_LENGTH_DELIMITED = 2;
const WIRE_TYPE_FIXED32 = 5;
const FIXED64_BYTES = 8;
const FIXED32_BYTES = 4;
const METADATA_PROPS_FIELD = 14;
const ENTRY_KEY_FIELD = 1;
const ENTRY_VALUE_FIELD = 2;
const VARINT_CONTINUATION_BIT = 0x80;
const VARINT_PAYLOAD_BITS = 0x7f;
const VARINT_BASE = 128;
const BITS_PER_WIRE_TYPE = 8;
// Matches `"key": "value"` pairs of a flat JSON object with string values.
const JSON_STRING_ENTRY = /"(?:[^"\\]|\\.)*"\s*:\s*("(?:[^"\\]|\\.)*")/g;

const textDecoder = new TextDecoder();

interface ProtobufField {
    field: number;
    // Set for length-delimited fields, the only ones the readers decode.
    bytes: Uint8Array | null;
}

// Reads the string metadata that LightlyTrain writes into an exported ONNX model, such as
// `classes` and `image_normalize`. onnxruntime-web does not expose it.
export const readOnnxMetadata = (bytes: Uint8Array): Record<string, string> => {
    const metadata: Record<string, string> = {};
    for (const { field, bytes: entryBytes } of readFields(bytes)) {
        if (field !== METADATA_PROPS_FIELD || entryBytes === null) continue;
        const entry = readEntry(entryBytes);
        if (entry) metadata[entry.key] = entry.value;
    }
    return metadata;
};

// Returns the class names in the order of the model's class indices. JSON.parse would sort
// integer keys, but LightlyTrain assigns the indices in insertion order.
export const parseClassNames = (classesJson: string): string[] =>
    [...classesJson.matchAll(JSON_STRING_ENTRY)].map(([, value]) => JSON.parse(value));

const readEntry = (bytes: Uint8Array): { key: string; value: string } | null => {
    let key: string | null = null;
    let value: string | null = null;
    for (const { field, bytes: fieldBytes } of readFields(bytes)) {
        if (fieldBytes === null) continue;
        if (field === ENTRY_KEY_FIELD) key = textDecoder.decode(fieldBytes);
        if (field === ENTRY_VALUE_FIELD) value = textDecoder.decode(fieldBytes);
    }
    return key === null || value === null ? null : { key, value };
};

function* readFields(bytes: Uint8Array): Generator<ProtobufField> {
    let offset = 0;
    while (offset < bytes.length) {
        const tag = readVarint(bytes, offset);
        offset = tag.offset;
        const field = Math.floor(tag.value / BITS_PER_WIRE_TYPE);
        const wireType = tag.value % BITS_PER_WIRE_TYPE;
        if (wireType === WIRE_TYPE_LENGTH_DELIMITED) {
            const length = readVarint(bytes, offset);
            const end = length.offset + length.value;
            yield { field, bytes: bytes.subarray(length.offset, end) };
            offset = end;
            continue;
        }
        yield { field, bytes: null };
        offset = skipScalar(bytes, offset, wireType);
    }
}

const skipScalar = (bytes: Uint8Array, offset: number, wireType: number): number => {
    if (wireType === WIRE_TYPE_VARINT) return readVarint(bytes, offset).offset;
    if (wireType === WIRE_TYPE_FIXED64) return offset + FIXED64_BYTES;
    if (wireType === WIRE_TYPE_FIXED32) return offset + FIXED32_BYTES;
    throw new Error(`Unsupported protobuf wire type ${wireType}.`);
};

// Decodes with arithmetic instead of bit operations, which would overflow at 2^31. The graph
// field of a large model can be longer than that.
const readVarint = (bytes: Uint8Array, start: number): { value: number; offset: number } => {
    let value = 0;
    let multiplier = 1;
    let offset = start;
    let byte: number;
    do {
        byte = bytes[offset];
        value += (byte & VARINT_PAYLOAD_BITS) * multiplier;
        multiplier *= VARINT_BASE;
        offset += 1;
    } while (byte & VARINT_CONTINUATION_BIT);
    return { value, offset };
};
