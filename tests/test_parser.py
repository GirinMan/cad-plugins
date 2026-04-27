import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import ezdxf

from cad_parser.converters import detect_converters, prepare_analysis_input, validate_dxf_file
from cad_parser.models import BlockRecord, Bounds, GeometryRecord, Point, TextRecord
from cad_parser.parser import link_texts


class ParserTests(unittest.TestCase):
    def test_bounds_distance_is_zero_inside_box(self):
        bounds = Bounds(0, 0, 10, 10)

        self.assertEqual(bounds.distance_to(Point(5, 5)), 0)

    def test_link_texts_prefers_nearest_geometry(self):
        text = TextRecord(id="text:1", kind="TEXT", text="Road A", layer="labels", insert=Point(1, 1))
        near = GeometryRecord(id="geometry:1", kind="LINE", layer="roads", bounds=Bounds(0, 0, 2, 2))
        far = GeometryRecord(id="geometry:2", kind="LINE", layer="roads", bounds=Bounds(100, 100, 102, 102))

        links = link_texts([text], [far, near], [], max_links_per_text=1)

        self.assertEqual([link.target_id for link in links], ["geometry:1"])

    def test_link_texts_includes_blocks_as_candidates(self):
        text = TextRecord(id="text:1", kind="TEXT", text="Pump", layer="label", insert=Point(10, 10))
        block = BlockRecord(id="block:1", name="PUMP", layer="facility", insert=Point(11, 10))

        links = link_texts([text], [], [block], max_links_per_text=1)

        self.assertEqual(links[0].target_kind, "block")
        self.assertEqual(links[0].target_id, "block:1")

    def test_prepare_analysis_input_keeps_dxf_as_canonical_input(self):
        with TemporaryDirectory() as tmp:
            dxf = Path(tmp) / "sample.dxf"
            dxf.write_text("0\nEOF\n", encoding="utf-8")

            result = prepare_analysis_input(dxf, Path(tmp) / "intermediate")

            self.assertEqual(result.dxf_file, dxf)
            self.assertEqual(result.converter, "none")

    def test_detect_converters_accepts_explicit_paths(self):
        with TemporaryDirectory() as tmp:
            oda = Path(tmp) / "ODAFileConverter.exe"
            dwgread = Path(tmp) / "dwgread"
            oda.write_text("", encoding="utf-8")
            dwgread.write_text("", encoding="utf-8")

            results = detect_converters(oda_path=oda, dwgread_path=dwgread)

            self.assertTrue(all(item.available for item in results))
            self.assertEqual({item.name for item in results}, {"oda", "libredwg"})

    def test_validate_dxf_file_reports_core_counts(self):
        with TemporaryDirectory() as tmp:
            dxf = Path(tmp) / "valid.dxf"
            doc = ezdxf.new("R2010")
            msp = doc.modelspace()
            msp.add_line((0, 0), (1, 1), dxfattribs={"layer": "roads"})
            msp.add_text("Road", dxfattribs={"layer": "labels"}).set_placement((0, 0))
            doc.saveas(dxf)

            result = validate_dxf_file(dxf)

            self.assertTrue(result.readable)
            self.assertEqual(result.layer_count, 2)
            self.assertEqual(result.text_count, 1)
            self.assertEqual(result.geometry_count, 1)


if __name__ == "__main__":
    unittest.main()
