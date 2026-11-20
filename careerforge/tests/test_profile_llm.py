import os
import unittest

from careerforge.llm import LLMError, MistralClient, extract_json
from careerforge.profile import default_profile, get_path, parse_value, profile_from_cv_text, set_path


class TestProfilePaths(unittest.TestCase):
    def test_set_and_get(self):
        p = default_profile()
        set_path(p, "work_preferences.remote", "hybrid")
        set_path(p, "skills.-", {"name": "Python", "level": "basic"})
        set_path(p, "skills.-", {"name": "SQL", "level": "none"})
        set_path(p, "skills.0.level", "intermediate")
        self.assertEqual(get_path(p, "work_preferences.remote"), "hybrid")
        self.assertEqual(get_path(p, "skills.1.name"), "SQL")
        self.assertEqual(get_path(p, "skills.0.level"), "intermediate")
        with self.assertRaises(KeyError):
            get_path(p, "nope.nope")

    def test_parse_value(self):
        self.assertEqual(parse_value('{"a": 1}'), {"a": 1})
        self.assertEqual(parse_value("[1, 2]"), [1, 2])
        self.assertEqual(parse_value("hybrid"), "hybrid")
        self.assertEqual(parse_value("true"), True)

    def test_profile_from_cv_text(self):
        cv = "JOHN DOE\njohn@example.com\n+421 900 000 111\n## SKILLS\nPython, Excel"
        p = profile_from_cv_text(cv, name="John Doe")
        self.assertEqual(p["name"], "John Doe")
        self.assertEqual(p["contact"]["email"], "john@example.com")
        self.assertIn("+421", p["contact"]["phone"])
        self.assertEqual(p["raw_cv"], cv)


class TestExtractJson(unittest.TestCase):
    def test_fenced(self):
        self.assertEqual(extract_json('```json\n{"a": 1}\n```'), {"a": 1})

    def test_raw_with_prose(self):
        text = 'Here you go: {"a": {"b": [1, 2, {"c": "}"}]}, "d": "x"} hope that helps'
        self.assertEqual(extract_json(text), {"a": {"b": [1, 2, {"c": "}"}]}, "d": "x"})

    def test_invalid(self):
        with self.assertRaises(LLMError):
            extract_json("no json here at all")


class TestMistralClient(unittest.TestCase):
    def test_unavailable_without_key(self):
        old = os.environ.pop("MISTRAL_API_KEY", None)
        try:
            c = MistralClient(api_key="")
            self.assertFalse(c.available)
            with self.assertRaises(LLMError):
                c.chat("s", "u")
        finally:
            if old is not None:
                os.environ["MISTRAL_API_KEY"] = old

    def test_available_with_key_and_model_override(self):
        c = MistralClient(api_key="k", model="mistral-small-latest")
        self.assertTrue(c.available)
        self.assertEqual(c.model, "mistral-small-latest")
        self.assertIn("api.mistral.ai", c.base_url)


if __name__ == "__main__":
    unittest.main()
