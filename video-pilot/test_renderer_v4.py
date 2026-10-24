"""Lightweight validation tests for Studio v4's pure helpers; run with python -m unittest."""
import importlib.util
import unittest
from pathlib import Path

MODULE = Path(__file__).with_name("renderer_v4.py")
spec = importlib.util.spec_from_file_location("renderer_v4", MODULE)
renderer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(renderer)

class StudioV4Tests(unittest.TestCase):
    def test_scene_split_preserves_script_words(self):
        script = "First point. Second point? Final point!"
        scenes = renderer.split_scenes(script)
        self.assertTrue(1 <= len(scenes) <= 8)
        self.assertEqual(" ".join(scenes), script)

    def test_scene_roles(self):
        self.assertEqual(renderer.visual_role(1, 3, "Intro")[0], "HOOK")
        self.assertEqual(renderer.visual_role(2, 3, "Ask this?")[0], "QUESTION")
        self.assertEqual(renderer.visual_role(3, 3, "Done.")[0], "TAKEAWAY")

    def test_validation_rejects_markup(self):
        with self.assertRaises(renderer.RenderError):
            renderer.validate({"schema":1,"title":"Title","description":"Desc","script":"<script>"})

    def test_stamp_format(self):
        self.assertEqual(renderer.caption_stamp(65.125), "00:01:05,125")

if __name__ == "__main__":
    unittest.main()
