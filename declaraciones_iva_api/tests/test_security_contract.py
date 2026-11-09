"""Static regression checks for high-risk API routes; no database or secrets required."""
import ast
import pathlib
import unittest

API = pathlib.Path(__file__).resolve().parents[1]
ROUTER = API / "app" / "routers" / "empresas.py"


def route_map(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    routes = {}
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute):
                if decorator.func.attr in {"get", "post", "put", "delete", "patch"} and decorator.args:
                    if isinstance(decorator.args[0], ast.Constant):
                        routes[(decorator.func.attr, decorator.args[0].value)] = node
    return routes


def has_auth_dependency(function):
    for arg, default in zip(function.args.args[-len(function.args.defaults):], function.args.defaults):
        if isinstance(default, ast.Call) and isinstance(default.func, ast.Name) and default.func.id == "Depends":
            if default.args and isinstance(default.args[0], ast.Name) and default.args[0].id == "usuario_actual":
                return True
    return False


class CompanySecurityContract(unittest.TestCase):
    def test_all_company_routes_require_authenticated_user(self):
        routes = route_map(ROUTER)
        self.assertGreaterEqual(len(routes), 6)
        for (method, path), function in routes.items():
            with self.subTest(method=method, path=path):
                self.assertTrue(has_auth_dependency(function), f"Missing auth dependency on {method} {path}")

    def test_no_public_database_wipe_route(self):
        routes = route_map(API / "main.py")
        self.assertNotIn(("delete", "/api/v1/debug/wipe_db"), routes)

    def test_archive_and_restore_endpoints_present(self):
        routes = route_map(ROUTER)
        self.assertIn(("delete", "/empresas/{empresa_id}/mi-vinculo"), routes)
        self.assertIn(("post", "/empresas/{empresa_id}/restaurar"), routes)


if __name__ == "__main__":
    unittest.main()
