"""TMDB poster matching, image validation and fallback tests."""
from io import BytesIO
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from PIL import Image

import monthly_prep


CANDIDATE = {"sid": "36915988", "title": "饥饿游戏：收获日出", "year": "2026",
             "original_title": "The Hunger Games: Sunrise on the Reaping"}
TMDB_MOVIE = {"id": 1300968, "title": "饥饿游戏: 收获日出",
              "original_title": CANDIDATE["original_title"], "release_date": "2026-11-18"}


def jpeg(width, height):
    source = BytesIO()
    Image.new("RGB", (width, height), "#806040").save(source, "JPEG")
    return source.getvalue()


def poster(path, language="zh", width=2000, height=3000):
    return {"file_path": path, "iso_639_1": language, "width": width, "height": height}


class MoviePosterTests(unittest.TestCase):
    def test_strict_ratio_rejects_near_misses(self):
        self.assertTrue(monthly_prep.strict_poster_ratio(2000, 3000))
        for size in ((2000, 2933), (1080, 1735), (540, 809), (0, 0), (600, 901), (True, True)):
            with self.subTest(size=size):
                self.assertFalse(monthly_prep.strict_poster_ratio(*size))

    def test_match_requires_unique_exact_title_and_original_year(self):
        older = {**TMDB_MOVIE, "id": 1, "release_date": "2025-12-28"}
        similar = {**TMDB_MOVIE, "id": 2, "title": "饥饿游戏", "original_title": "The Hunger Games"}
        with patch.object(monthly_prep, "tmdb_api", return_value={"results": [older, similar, TMDB_MOVIE]}) as api:
            self.assertEqual(monthly_prep.tmdb_movie_id(CANDIDATE, "test"), 1300968)
            self.assertEqual(api.call_args.kwargs["primary_release_year"], "2026")
        with patch.object(monthly_prep, "tmdb_api", return_value={"results": [older, similar]}):
            with self.assertRaisesRegex(ValueError, "No exact"):
                monthly_prep.tmdb_movie_id(CANDIDATE, "test")
        duplicate = {**TMDB_MOVIE, "id": 3}
        with patch.object(monthly_prep, "tmdb_api", return_value={"results": [TMDB_MOVIE, duplicate]}):
            with self.assertRaisesRegex(ValueError, "More than one exact"):
                monthly_prep.tmdb_movie_id(CANDIDATE, "test")

    def test_api_errors_do_not_expose_key(self):
        url = "https://api.themoviedb.org/3/search/movie?api_key=private-test-key"
        with patch.object(monthly_prep, "fetch_json", side_effect=HTTPError(url, 401, "unauthorized", {}, None)):
            with self.assertRaisesRegex(ValueError, "^TMDB API returned HTTP 401$"):
                monthly_prep.tmdb_api("search/movie", "private-test-key")
        with patch.object(monthly_prep, "fetch_json", side_effect=URLError(url)):
            with self.assertRaisesRegex(ValueError, "^TMDB API connection failed or returned invalid JSON$"):
                monthly_prep.tmdb_api("search/movie", "private-test-key")

    def test_filters_by_language_and_dimensions_and_resizes_without_cropping(self):
        images = [poster("/English.jpg", language="en"), poster("/Near.jpg", height=2933),
                  poster("/Failed.jpg"), poster("/WrongActual.jpg"), poster("/Exact.jpg")]
        responses = [URLError("unavailable"), jpeg(2000, 2933), jpeg(2000, 3000)]
        with patch.object(monthly_prep, "tmdb_movie_id", return_value=1300968), \
             patch.object(monthly_prep, "tmdb_api", return_value={"posters": images}), \
             patch.object(monthly_prep, "fetch", side_effect=responses) as fetch, \
             patch.object(Image.Image, "crop", side_effect=AssertionError("crop must not be used")), \
             tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "poster.jpg"
            result = monthly_prep.tmdb_candidate_poster(CANDIDATE, target, "test")
            with Image.open(target) as image:
                self.assertEqual(image.size, (600, 900))
                self.assertEqual(image.format, "JPEG")
        self.assertEqual([call.args[0].rsplit("/", 1)[1] for call in fetch.call_args_list],
                         ["Failed.jpg", "WrongActual.jpg", "Exact.jpg"])
        self.assertEqual(result["status"], "ready")
        self.assertTrue(result["image_url"].endswith("/Exact.jpg"))
        self.assertEqual((result["original_width"], result["original_height"]), (2000, 3000))
        self.assertEqual(len(result["download_failures"]), 2)

    def fake_douban(self, path):
        if path.startswith("subject_collection/movie_soon"):
            return {"subject_collection_items": [{
                "id": int(CANDIDATE["sid"]), "title": CANDIDATE["title"], "release_date": "11.20",
                "wish_count": 10754, "rating": {},
            }]}
        if path.startswith("subject_collection/movie_showing"):
            return {"subject_collection_items": []}
        return {
            "pubdate": ["2026-11-20(中国大陆)"], "year": CANDIDATE["year"],
            "original_title": CANDIDATE["original_title"],
            "pic": {"large": "https://example.invalid/main.jpg"},
        }

    def collect_with_tmdb(self, root, **tmdb_mock):
        with patch.object(monthly_prep, "ROOT", root), \
             patch.object(monthly_prep, "CAND", root / "candidates"), \
             patch.dict(monthly_prep.os.environ, {"TMDB_API_KEY": "test"}), \
             patch.object(monthly_prep, "douban", side_effect=self.fake_douban), \
             patch.object(monthly_prep, "tmdb_candidate_poster", **tmdb_mock) as tmdb, \
             patch.object(monthly_prep, "fetch", return_value=b"\xff\xd8\xffposter") as fetch:
            errors = []
            movies = monthly_prep.collect_movies([(2026, 11)], errors)
        return movies[0], errors, tmdb, fetch

    def test_tmdb_success_uses_candidate_file_without_douban_download(self):
        with tempfile.TemporaryDirectory() as folder:
            movie, errors, _, fetch = self.collect_with_tmdb(Path(folder), return_value={"status": "ready"})
        self.assertEqual(movie["poster_source"], "tmdb")
        self.assertEqual(movie["poster_file"], "candidates/posters/movie_36915988.jpg")
        self.assertEqual(errors, [])
        fetch.assert_not_called()

    def test_tmdb_unavailable_falls_back_to_original_douban_main(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            movie, errors, _, _ = self.collect_with_tmdb(root, side_effect=ValueError("TMDB API returned HTTP 401"))
            self.assertEqual((root / movie["poster_file"]).read_bytes(), b"\xff\xd8\xffposter")
        self.assertEqual(movie["poster_source"], "douban_main")
        self.assertEqual(movie["poster_gallery"]["reason"], "TMDB API returned HTTP 401")
        self.assertIn("HTTP 401", errors[0])

    def test_existing_formal_poster_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "img").mkdir()
            original = root / "img" / "movie_36915988.jpg"
            original.write_bytes(b"keep this poster")
            movie, _, tmdb, fetch = self.collect_with_tmdb(root)
            self.assertEqual(original.read_bytes(), b"keep this poster")
        tmdb.assert_not_called()
        fetch.assert_not_called()
        self.assertEqual(movie["poster_source"], "existing")


if __name__ == "__main__":
    unittest.main()
