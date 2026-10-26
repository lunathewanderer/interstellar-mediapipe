"""Cross-check shader texture indexes against the actual TD network topology."""
import ast
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class RenderContractTests(unittest.TestCase):
    def test_shader_bindings_fit_wires_and_operator_capacity(self):
        tree = ast.parse((ROOT/'touchdesigner'/'build_network.py').read_text(encoding='utf-8'))
        operator_types = {}
        input_counts = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
                call = node.value
                if isinstance(call.func, ast.Attribute) and call.func.attr == 'create' and call.args:
                    if isinstance(call.args[0], ast.Name) and isinstance(node.targets[0], ast.Name):
                        operator_types[node.targets[0].id] = call.args[0].id
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr == 'setInputs' and isinstance(node.func.value, ast.Name):
                    if node.args and isinstance(node.args[0], ast.List):
                        input_counts[node.func.value.id] = len(node.args[0].elts)
        for operator, shader in (('raw','galaxy'),('trails','trail'),('glow','glow_h'),('final','composite')):
            source = (ROOT/'shaders'/f'{shader}.frag').read_text(encoding='utf-8')
            indexes = [int(x) for x in re.findall(r'sTD2DInputs\[(\d+)\]', source)]
            required = max(indexes) + 1
            self.assertGreaterEqual(input_counts[operator], required, f'{operator}: shader input missing')
            if operator_types[operator] == 'glslTOP':
                self.assertLessEqual(input_counts[operator], 3, f'{operator}: use GLSL Multi TOP for four or more inputs')
            else:
                self.assertEqual(operator_types[operator], 'glslmultiTOP')


if __name__ == '__main__':
    unittest.main()
