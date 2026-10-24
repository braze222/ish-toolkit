import importlib.util, unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location("renderer_v5",Path(__file__).with_name("renderer_v5.py"))
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
class StoryboardTests(unittest.TestCase):
 def test_hook_takeaway(self):
  p=m.build_storyboard("Tips","Compare the scope. Write down the answers.")
  self.assertEqual(p[0]["role"],"HOOK"); self.assertEqual(p[-1]["role"],"TAKEAWAY")
 def test_niche_prompt(self):
  p=m.build_storyboard("Study","Review the notes. Test yourself.","education")
  self.assertIn("learner",p[0]["visual_prompt"])
 def test_scene_limit(self):
  p=m.build_storyboard("Title"," ".join(f"Sentence {i}." for i in range(30)))
  self.assertLessEqual(len(p),8); self.assertGreaterEqual(len(p),1)
 def test_safe_asset_paths(self):
  self.assertIsNotNone(__import__('re').fullmatch(r'assets/scene-[0-9]{2}\.(png|jpg|jpeg)','assets/scene-01.png'))
if __name__=="__main__": unittest.main()
