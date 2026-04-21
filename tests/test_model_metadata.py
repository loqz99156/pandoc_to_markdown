import unittest

from pandoc_to_markdown.model_metadata import get_download_metadata


class ModelMetadataTests(unittest.TestCase):
    def test_marker_metadata_contains_models_with_link_and_size(self) -> None:
        metadata = get_download_metadata("marker")
        self.assertEqual(metadata["engine"], "marker")
        self.assertTrue(metadata["models"])
        self.assertIn("download_url", metadata["models"][0])
        self.assertIn("model_size", metadata["models"][0])

    def test_mineru_metadata_contains_models_with_link_and_size(self) -> None:
        metadata = get_download_metadata("mineru")
        self.assertEqual(metadata["engine"], "mineru")
        self.assertEqual(len(metadata["models"]), 2)
        self.assertTrue(all("download_url" in model for model in metadata["models"]))
        self.assertTrue(all("model_size" in model for model in metadata["models"]))


if __name__ == "__main__":
    unittest.main()
