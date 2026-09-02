import ast
from typing import Optional, Any
from dataclasses import dataclass
from collections import defaultdict
from enum import Enum

class FieldType(str, Enum):
    """Field types extracted from annotations"""
    INT = "int"
    STR = "str"
    FLOAT = "float"
    BOOL = "bool"
    DATETIME = "datetime"
    LIST = "list"
    DICT = "dict"
    UNKNOWN = "unknown"

@dataclass
class FieldFact:
    """Extracted field definition"""
    name: str
    type_annotation: str  # Raw annotation string
    type_enum: FieldType
    has_default: bool
    default_value: Optional[Any] = None
    line_number: int = 0

@dataclass
class MethodFact:
    """Extracted method definition"""
    name: str
    class_name: str  # parent class
    parameters: dict[str, str]  # name → type_annotation
    return_type: Optional[str]
    decorators: list[str]  # @property, @staticmethod, etc.
    is_async: bool
    line_number: int

@dataclass
class ClassFact:
    """Extracted class definition"""
    name: str
    fields: dict[str, FieldFact]
    methods: dict[str, MethodFact]
    base_classes: list[str]  # Parent classes
    decorators: list[str]  # @dataclass, @pydantic.BaseModel, etc.
    line_number: int

@dataclass
class ImportFact:
    """Extracted import statement"""
    module: str
    names: list[str]  # What was imported from module
    line_number: int

@dataclass
class ModuleFacts:
    """All code facts extracted from a module"""
    file_path: str
    classes: dict[str, ClassFact]
    functions: dict[str, MethodFact]  # module-level functions
    imports: dict[str, list[ImportFact]]  # module → [ImportFact]
    dependencies: set[str]  # External modules used

class ASTFactsExtractor(ast.NodeVisitor):
    """
    Extract CODE FACTS from Python source.
    Does NOT make decisions or inferences.
    Pure factual extraction.
    """

    def __init__(self, file_path: str, source: str):
        self.file_path = file_path
        self.source = source
        self.classes: dict[str, ClassFact] = {}
        self.functions: dict[str, MethodFact] = {}
        self.imports: dict[str, list[ImportFact]] = defaultdict(list)
        self.dependencies: set[str] = set()
        self.current_class: Optional[str] = None

    def visit_ClassDef(self, node: ast.ClassDef):
        """Extract class facts"""
        fields = {}
        methods = {}

        # Extract decorators as facts
        decorators = [self._extract_decorator_name(d) for d in node.decorator_list]

        # Extract base classes as facts
        base_classes = [ast.unparse(base) for base in node.bases]

        # Extract fields and methods
        for item in node.body:
            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                # Type-annotated field
                field_fact = self._extract_field_fact(item)
                fields[item.target.id] = field_fact

            elif isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Method
                method_fact = self._extract_method_fact(item, node.name)
                methods[item.name] = method_fact

        self.classes[node.name] = ClassFact(
            name=node.name,
            fields=fields,
            methods=methods,
            base_classes=base_classes,
            decorators=decorators,
            line_number=node.lineno,
        )

        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = None

    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Extract function facts (module-level only)"""
        if self.current_class is None:
            method_fact = self._extract_method_fact(node, class_name=None)
            self.functions[node.name] = method_fact
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        """Extract async function facts"""
        if self.current_class is None:
            method_fact = self._extract_method_fact(node, class_name=None, is_async=True)
            self.functions[node.name] = method_fact
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import):
        """Extract import facts"""
        for alias in node.names:
            import_fact = ImportFact(
                module=alias.name,
                names=[alias.asname or alias.name],
                line_number=node.lineno,
            )
            self.imports[alias.name].append(import_fact)
            self.dependencies.add(alias.name)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        """Extract from-import facts"""
        if node.module:
            names = [alias.name for alias in node.names]
            import_fact = ImportFact(
                module=node.module,
                names=names,
                line_number=node.lineno,
            )
            self.imports[node.module].append(import_fact)
            self.dependencies.add(node.module)

    def _extract_field_fact(self, node: ast.AnnAssign) -> FieldFact:
        """Extract field annotation facts"""
        type_str = ast.unparse(node.annotation)
        type_enum = self._infer_type(type_str)
        default_value = None
        has_default = node.value is not None

        if has_default:
            try:
                default_value = ast.literal_eval(node.value)
            except (ValueError, TypeError):
                default_value = None

        return FieldFact(
            name=node.target.id,
            type_annotation=type_str,
            type_enum=type_enum,
            has_default=has_default,
            default_value=default_value,
            line_number=node.lineno,
        )

    def _extract_method_fact(
        self,
        node,
        class_name: Optional[str] = None,
        is_async: bool = False
    ) -> MethodFact:
        """Extract method/function signature facts"""
        parameters = {}
        for arg in node.args.args:
            param_type = ast.unparse(arg.annotation) if arg.annotation else "Any"
            parameters[arg.arg] = param_type

        return_type = ast.unparse(node.returns) if node.returns else None
        decorators = [self._extract_decorator_name(d) for d in node.decorator_list]

        return MethodFact(
            name=node.name,
            class_name=class_name or "__module__",
            parameters=parameters,
            return_type=return_type,
            decorators=decorators,
            is_async=is_async or isinstance(node, ast.AsyncFunctionDef),
            line_number=node.lineno,
        )

    def _extract_decorator_name(self, node: ast.expr) -> str:
        """Extract decorator name as string fact"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return ast.unparse(node)
        else:
            return ast.unparse(node)

    def _infer_type(self, type_str: str) -> FieldType:
        """Infer FieldType from annotation string"""
        type_lower = type_str.lower()
        if "int" in type_lower:
            return FieldType.INT
        elif "str" in type_lower:
            return FieldType.STR
        elif "float" in type_lower:
            return FieldType.FLOAT
        elif "bool" in type_lower:
            return FieldType.BOOL
        elif "datetime" in type_lower or "date" in type_lower:
            return FieldType.DATETIME
        elif "list" in type_lower or type_lower.startswith("list"):
            return FieldType.LIST
        elif "dict" in type_lower:
            return FieldType.DICT
        return FieldType.UNKNOWN

    def analyze(self) -> ModuleFacts:
        """Parse source and extract all facts"""
        tree = ast.parse(self.source)
        self.visit(tree)
        return ModuleFacts(
            file_path=self.file_path,
            classes=self.classes,
            functions=self.functions,
            imports=self.imports,
            dependencies=self.dependencies,
        )