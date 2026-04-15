import {
  createDefaultCoreModule,
  createDefaultSharedCoreModule,
  inject,
  type DefaultCoreModuleContext,
  type LangiumCoreServices,
  type LangiumSharedCoreServices,
  type Module,
  EmptyFileSystem,
  type FileSystemProvider,
} from "langium";
import {
  LightlyQueryGeneratedModule,
  LightlyQueryGeneratedSharedModule,
} from "./generated/module.ts";
import {
  type Query,
  isBinaryExpression,
  isComparisonExpression,
  isFunctionCall,
  isMemberCall,
  isNumberLiteral,
  isStringLiteral,
  isBooleanLiteral,
  isNotExpression,
} from "./generated/ast.ts";

export type LightlyQueryServices = LangiumCoreServices;

export function createLightlyQueryServices(context: DefaultCoreModuleContext): {
  shared: LangiumSharedCoreServices;
  LightlyQuery: LightlyQueryServices;
} {
  const shared = inject(
    createDefaultSharedCoreModule(context),
    LightlyQueryGeneratedSharedModule,
  );
  const LightlyQuery = inject(
    createDefaultCoreModule({ shared }),
    LightlyQueryGeneratedModule,
  );
  shared.ServiceRegistry.register(LightlyQuery);
  return { shared, LightlyQuery };
};

function transformToDSLJson(node: any): any {
  if (isBinaryExpression(node)) {
    return {
      kind: node.operator.toUpperCase(),
      terms: [transformToDSLJson(node.left), transformToDSLJson(node.right)],
    };
  }
  if (isNotExpression(node)) {
    return {
      kind: "NOT",
      term: transformToDSLJson(node.expression),
    };
  }
  if (isComparisonExpression(node)) {
    const left = node.left;
    let field = "";
    if (isMemberCall(left)) {
      if (left.receiver === "ImageSampleField" && left.member.length === 1) {
        field = left.member[0];
      } else if (
        left.receiver === "ObjectDetectionField" &&
        left.member.length === 1
      ) {
        field = left.member[0];
      } else {
        field = left.receiver || (left as any).name || "unknown_field";
      }
    } else {
      field = (left as any).name || "unknown_field";
    }
    0;
    return {
      kind: "COMPARISON",
      field: field,
      operator: node.operator,
      value: transformToDSLJson(node.right),
    };
  }
  if (isFunctionCall(node)) {
    return {
      kind: "ANNOTATION_QUERY",
      annotation_type: node.name,
      criterion: node.args.length > 0 ? transformToDSLJson(node.args[0]) : null,
    };
  }
  if (isMemberCall(node)) {
    if (node.receiver === "tags" && node.member.includes("contains")) {
      const containsArg = node.args?.[0];
      if (containsArg) {
        return {
          kind: "TAGS_CONTAINS",
          tag_name: transformToDSLJson(containsArg),
        };
      }
    }
  }
  if (isNumberLiteral(node)) return node.value;
  if (isStringLiteral(node)) return node.value;
  if (isBooleanLiteral(node)) return node.value === "true";

  if (node.expression) return transformToDSLJson(node.expression);

  console.warn("transformToDSLJson: Unhandled node type", node);
  return null;
}

// Mock FileSystemProvider to satisfy Langium's requirements
// This mock provides a function that returns an EmptyFileSystem
const mockFileSystemProviderFunction: () => FileSystemProvider = () => ({
  createFileSystem: () => EmptyFileSystem,
  statSync: (path: string) => ({
    isDirectory: () => false,
    isFile: () => true,
  }),
  readdirSync: (path: string) => [],
});

// Mock other required context properties
const mockContext: DefaultCoreModuleContext = {
  fileSystem: EmptyFileSystem, // Still provide EmptyFileSystem for the fileSystem property
  fileSystemProvider: mockFileSystemProviderFunction, // Correctly provide the function
  documentFactory: {} as any, // Mock
  textDocumentConnection: {} as any, // Mock
  serviceRegistry: {} as any, // Mock
  workspaceProvider: {} as any, // Mock
  undoProvider: {} as any, // Mock
  validationProvider: {} as any, // Mock
};

const services = createLightlyQueryServices(mockContext).LightlyQuery;

const parser = services.parser.LangiumParser;

const queries = [
  "(width > 100 OR height > 100) AND object_detection(label == 'car')",
  "tags.contains('dog') or tags.contains('cat')",
  "NOT (width < 50 AND NOT tags.contains('low_res'))",
];

console.log("=== Langium-Powered LightlyQuery DSL Showcase ===");
console.log("");

queries.forEach((q, i) => {
  console.log("Query " + (i + 1) + ": " + q);
  const parseResult = parser.parse<Query>(q);

  if (
    parseResult.lexerErrors.length > 0 ||
    parseResult.parserErrors.length > 0
  ) {
    console.error("Errors encountered during parsing:");
    parseResult.lexerErrors.forEach((err) =>
      console.error("Lexer Error: " + err.message),
    );
    parseResult.parserErrors.forEach((err) =>
      console.error("Parser Error: " + err.message),
    );
  } else {
    const json = transformToDSLJson(parseResult.value);
    console.log("Emitted JSON for Backend:");
    console.log(JSON.stringify(json, null, 2));
  }
  console.log("\n-----------------------------------\n");
});
