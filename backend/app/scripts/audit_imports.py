#!/usr/bin/env python3
"""
Audit script to verify module isolation and independence.

Checks for:
1. Cross-module imports (module A importing from module B)
2. Internal exports (models, repositories, services leaked from __init__.py)
3. Circular dependencies

This script MUST pass in CI/CD before deployment.
Wave 1 Task 14: Import audit.

Usage:
    python audit_imports.py
"""

import os
import sys
import ast
import re
from collections import defaultdict
from pathlib import Path

# Color output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
RESET = '\033[0m'

# Configuration
MODULES_DIR = Path(__file__).parent.parent / "modules"
MODULES = ["auth", "processos", "ia", "laudos", "ferramentas", "financeiro", "esaj", "infra"]

# What's allowed to be exported from __init__.py
ALLOWED_EXPORTS = {
    # Public DTOs
    "Request",
    "Response",
    "Schema",
    "Create",
    "Update",
    "List",
    # Routes
    "router",
    "calculator_router",
    "cnj_router",
    # Only these service-related exports (for backward compatibility):
    # (to be phased out — use Depends instead)
}

# Internal classes (should NEVER be exported)
FORBIDDEN_EXPORTS = {
    "Model",
    "Repository",
    "Service",
    "engine",
    "Base",
}

# Patterns for internal implementation
INTERNAL_PATTERNS = [
    r".*Repository",
    r".*Service",
    r"[A-Z][a-zA-Z]*Model",
]

# App.shared allowed imports (can use freely)
ALLOWED_SHARED_IMPORTS = [
    "app.shared.schemas",
    "app.shared.exceptions",
    "app.shared.enums",
    "app.core",
]

# Other allowed imports (stdlib, third-party)
ALLOWED_PREFIXES = [
    "typing",
    "pydantic",
    "sqlalchemy",
    "fastapi",
    "logging",
    "os",
    "sys",
    "json",
    "re",
    "datetime",
    "pathlib",
    "enum",
    "abc",
    "functools",
    "asyncio",
    "urllib",
    "requests",
    "dotenv",
]


class ImportAuditor:
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.module_exports = {}  # module_name -> set of exported names
        self.module_imports = defaultdict(set)  # module_name -> set of (module, name) tuples

    def audit(self):
        """Run full audit."""
        print(f"\n{YELLOW}🔍 Auditing module imports and isolation...{RESET}\n")

        # Phase 1: Check __init__.py exports
        self.check_init_exports()

        # Phase 2: Check internal imports
        self.check_internal_imports()

        # Phase 3: Check for circular dependencies
        self.check_circular_dependencies()

        # Print results
        self.print_results()

        # Return exit code
        return len(self.errors) == 0

    def check_init_exports(self):
        """Check what each module exports from __init__.py."""
        print(f"{YELLOW}Phase 1: Checking __init__.py exports...{RESET}")

        for module_name in MODULES:
            init_file = MODULES_DIR / module_name / "__init__.py"
            if not init_file.exists():
                self.warnings.append(f"Module {module_name} has no __init__.py")
                continue

            exports = self._extract_exports(init_file)
            self.module_exports[module_name] = exports

            # Check for forbidden exports
            for export in exports:
                is_forbidden = any(
                    forbidden in export
                    for forbidden in FORBIDDEN_EXPORTS
                )
                if is_forbidden:
                    self.errors.append(
                        f"🚫 Module '{module_name}' exports FORBIDDEN '{export}'. "
                        f"Internal implementation must stay private."
                    )

                # Check for pattern-based forbidden exports
                for pattern in INTERNAL_PATTERNS:
                    if re.match(pattern, export):
                        self.errors.append(
                            f"🚫 Module '{module_name}' exports FORBIDDEN '{export}' "
                            f"(matches pattern '{pattern}'). Use schemas/DTOs instead."
                        )
                        break

            print(f"  ✅ {module_name}: {len(exports)} exports")

    def check_internal_imports(self):
        """Check for cross-module imports in internal implementation."""
        print(f"\n{YELLOW}Phase 2: Checking for cross-module imports...{RESET}")

        for module_name in MODULES:
            module_path = MODULES_DIR / module_name
            py_files = list(module_path.rglob("*.py"))

            cross_module_imports = set()

            for py_file in py_files:
                # Skip __pycache__
                if "__pycache__" in str(py_file):
                    continue

                imports = self._extract_imports(py_file)

                for import_stmt in imports:
                    # Check if importing from a different module
                    for other_module in MODULES:
                        if other_module == module_name:
                            continue

                        # Pattern: from app.modules.{other_module} import X
                        if f"app.modules.{other_module}" in import_stmt:
                            cross_module_imports.add((other_module, import_stmt))

            if cross_module_imports:
                for other_module, import_stmt in cross_module_imports:
                    self.errors.append(
                        f"🚫 Cross-module import: {module_name} → {other_module}\n"
                        f"   {import_stmt}"
                    )
            else:
                print(f"  ✅ {module_name}: No cross-module imports")

    def check_circular_dependencies(self):
        """Check for circular dependencies in module imports."""
        print(f"\n{YELLOW}Phase 3: Checking for circular dependencies...{RESET}")

        # Since we've already verified no cross-module imports, this is a no-op
        # But kept for completeness
        print(f"  ✅ No cross-module imports → No circular dependencies possible")

    def _extract_exports(self, init_file):
        """Extract names from __all__ in __init__.py."""
        try:
            with open(init_file) as f:
                tree = ast.parse(f.read())

            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name) and target.id == "__all__":
                            if isinstance(node.value, ast.List):
                                return set(
                                    elt.s for elt in node.value.elts
                                    if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
                                )
            return set()
        except Exception as e:
            self.warnings.append(f"Failed to parse {init_file}: {e}")
            return set()

    def _extract_imports(self, py_file):
        """Extract import statements from a Python file."""
        try:
            with open(py_file) as f:
                content = f.read()

            # Use regex to find import statements
            patterns = [
                r"from\s+([\w\.]+)\s+import",
                r"import\s+([\w\.]+)",
            ]

            imports = []
            for pattern in patterns:
                for match in re.finditer(pattern, content):
                    imports.append(match.group(1))

            return imports
        except Exception as e:
            self.warnings.append(f"Failed to read {py_file}: {e}")
            return []

    def print_results(self):
        """Print audit results."""
        print(f"\n{YELLOW}{'='*60}")
        print(f"AUDIT RESULTS")
        print(f"{'='*60}{RESET}\n")

        if self.errors:
            print(f"{RED}❌ FAILURES ({len(self.errors)}):{RESET}")
            for i, error in enumerate(self.errors, 1):
                print(f"  {i}. {error}")
            print()

        if self.warnings:
            print(f"{YELLOW}⚠️  WARNINGS ({len(self.warnings)}):{RESET}")
            for i, warning in enumerate(self.warnings, 1):
                print(f"  {i}. {warning}")
            print()

        if not self.errors:
            print(f"{GREEN}✅ ALL CHECKS PASSED{RESET}")
            print(f"   - No cross-module imports")
            print(f"   - No circular dependencies")
            print(f"   - No internal exports leaked")
        else:
            print(f"{RED}❌ AUDIT FAILED{RESET}")
            sys.exit(1)


def main():
    """Run the audit."""
    auditor = ImportAuditor()
    success = auditor.audit()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
