import unittest

from cad_parser.visualize import render_html, render_svg


class VisualizeTests(unittest.TestCase):
    def test_render_svg_contains_geometry_and_label(self):
        analysis = {
            "source_file": "sample.dxf",
            "entity_counts": {"LINE": 1, "TEXT": 1},
            "layers": [{"name": "roads", "entity_count": 1}],
            "geometries": [
                {
                    "id": "geometry:1",
                    "kind": "LINE",
                    "layer": "roads",
                    "bounds": {"min_x": 0, "min_y": 0, "max_x": 10, "max_y": 0},
                    "points": [{"x": 0, "y": 0, "z": 0}, {"x": 10, "y": 0, "z": 0}],
                    "metadata": {},
                }
            ],
            "texts": [{"id": "text:1", "text": "Main Road", "layer": "labels", "insert": {"x": 5, "y": 1, "z": 0}}],
            "blocks": [],
            "links": [],
        }

        svg = render_svg(analysis, width=400, height=300)

        self.assertIn("<svg", svg)
        self.assertIn("Main Road", svg)
        self.assertIn("<polyline", svg)

    def test_render_html_embeds_svg(self):
        html = render_html({"source_file": "sample.dxf", "entity_counts": {}}, "<svg></svg>")

        self.assertIn("<!doctype html>", html)
        self.assertIn("<svg></svg>", html)


if __name__ == "__main__":
    unittest.main()
