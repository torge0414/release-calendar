"""Douban poster-gallery parsing, strict 2:3 selection and fallback tests."""
from io import BytesIO
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import URLError

from PIL import Image

import monthly_prep


HEADING = "<h1>饥饿游戏：收获日出 The Hunger Games: Sunrise on the Reaping的海报</h1>"


def gallery_item(photo_id, host="img3"):
    # Copied from the observed desktop type=R .cover structure.
    return f'''<li data-id="{photo_id}" class="">
            <div class="cover">
                <a href="https://movie.douban.com/photos/photo/{photo_id}/">
                    <img src="https://{host}.doubanio.com/view/photo/m/public/p{photo_id}.webp">
                </a>
            </div>
            <div class="name">正式海报 中国大陆 <a href="https://movie.douban.com/photos/photo/{photo_id}/#comments">1回应</a></div>
        </li>'''


GALLERY_PAGE = ("<html><body>" + HEADING + '<ul class="poster-col3 clearfix">'
                + gallery_item("2927298819") + gallery_item("2937430234", "img9")
                + "</ul>" + '<div class="paginator"><span class="thispage" data-total-page="3">1</span>'
                + '<a href="https://movie.douban.com/subject/36915988/photos?type=R&amp;start=30&amp;sortby=like&amp;size=a&amp;subtype=a">2</a>'
                + '<span class="count">(共74张)</span></div></body></html>')


def jpeg(width, height, color="#806040"):
    source = BytesIO()
    Image.new("RGB", (width, height), color).save(source, "JPEG")
    return source.getvalue()


class MoviePosterTests(unittest.TestCase):
    def candidate(self):
        return {"sid": "36915988", "title": "饥饿游戏：收获日出"}

    def fake_douban(self, path, retry=True):
        if path.startswith("subject_collection/movie_soon"):
            return {"subject_collection_items": [{
                "id": 36915988, "title": "饥饿游戏：收获日出", "release_date": "11.20",
                "wish_count": 10754, "rating": {},
            }]}
        if path.startswith("subject_collection/movie_showing"):
            return {"subject_collection_items": []}
        return {
            "pubdate": ["2026-11-20(中国大陆)"], "year": "2026",
            "original_title": "The Hunger Games: Sunrise on the Reaping", "aka": [],
            "genres": [], "countries": [], "directors": [], "actors": [], "rating": {},
            "pic": {"large": "https://example.invalid/main.jpg"},
        }

    def test_strict_ratio_rejects_near_misses(self):
        self.assertTrue(monthly_prep.strict_poster_ratio(2000, 3000))
        self.assertTrue(monthly_prep.strict_poster_ratio(900, 1350))
        for size in ((2000, 2933), (1080, 1735), (540, 809), (0, 0), (600, 901), (True, True)):
            with self.subTest(size=size):
                self.assertFalse(monthly_prep.strict_poster_ratio(*size))

    def test_parse_observed_gallery_markup(self):
        posters = monthly_prep.parse_douban_posters(GALLERY_PAGE)
        self.assertEqual([p["photo_id"] for p in posters], ["2927298819", "2937430234"])
        self.assertEqual(posters[0]["page_url"], "https://movie.douban.com/photos/photo/2927298819/")
        self.assertEqual(posters[0]["image_url"], "https://img3.doubanio.com/view/photo/l/public/p2927298819.jpg")
        self.assertEqual(posters[1]["image_url"], "https://img9.doubanio.com/view/photo/l/public/p2937430234.jpg")

    def test_verification_page_is_not_bypassed(self):
        page = '<html><form id="sec" action="/c"><input type="hidden" name="challenge"></form></html>'
        with self.assertRaisesRegex(ValueError, "requires verification; not bypassed"):
            monthly_prep.parse_douban_posters(page)

    def test_generic_stills_are_not_accepted_as_poster_gallery(self):
        page = "<h1>饥饿游戏：收获日出的剧照</h1>" + gallery_item("2927300520")
        with self.assertRaisesRegex(ValueError, "Unrecognized Douban poster gallery"):
            monthly_prep.parse_douban_posters(page)

    def test_gallery_request_is_poster_only_and_like_ordered(self):
        with patch.object(monthly_prep, "DOUBAN_DELAY", 0), \
             patch.object(monthly_prep, "fetch", return_value=GALLERY_PAGE) as fetch:
            monthly_prep.douban_poster_options("36915988")
        url = fetch.call_args.args[0]
        self.assertIn("type=R&start=0&sortby=like&size=a&subtype=a", url)
        self.assertNotIn("rexxar", url)

    def test_download_skips_near_ratio_and_resizes_without_cropping(self):
        options = [
            {"photo_id": "1", "page_url": "https://movie.douban.com/photos/photo/1/", "image_url": "https://img3.doubanio.com/view/photo/l/public/p1.jpg"},
            {"photo_id": "2", "page_url": "https://movie.douban.com/photos/photo/2/", "image_url": "https://img3.doubanio.com/view/photo/l/public/p2.jpg"},
        ]
        responses = [jpeg(2000, 2933), jpeg(2000, 3000)]
        with patch.object(monthly_prep, "douban_poster_options", return_value=options), \
             patch.object(monthly_prep, "fetch", side_effect=responses) as fetch, \
             patch.object(Image.Image, "crop", side_effect=AssertionError("crop must not be used")):
            with tempfile.TemporaryDirectory() as folder:
                target = Path(folder) / "poster.jpg"
                result = monthly_prep.douban_candidate_poster(self.candidate(), target)
                with Image.open(target) as image:
                    self.assertEqual(image.size, (600, 900))
                    self.assertEqual(image.format, "JPEG")
                    self.assertEqual(image.getpixel((0, 0)), image.getpixel((599, 899)))
        self.assertEqual(fetch.call_count, 2)
        self.assertTrue(all(call.kwargs["binary"] for call in fetch.call_args_list))
        self.assertEqual(result["status"], "ready")
        self.assertEqual(result["photo_id"], "2")
        self.assertEqual((result["original_width"], result["original_height"]), (2000, 3000))
        self.assertEqual((result["width"], result["height"]), (600, 900))
        self.assertEqual(result["checked_candidates"], 2)

    def test_candidate_download_limit_and_failure_reason(self):
        options = [{"photo_id": str(i), "page_url": f"https://movie.douban.com/photos/photo/{i}/",
                    "image_url": f"https://img3.doubanio.com/view/photo/l/public/p{i}.jpg"} for i in range(13)]
        with patch.object(monthly_prep, "DOUBAN_POSTER_LIMIT", 12), \
             patch.object(monthly_prep, "douban_poster_options", return_value=options), \
             patch.object(monthly_prep, "fetch", return_value=jpeg(1000, 1501)) as fetch:
            with tempfile.TemporaryDirectory() as folder:
                target = Path(folder) / "poster.jpg"
                result = monthly_prep.douban_candidate_poster(self.candidate(), target)
                self.assertFalse(target.exists())
        self.assertEqual(fetch.call_count, 12)
        self.assertEqual(result["status"], "no strict 2:3 poster")
        self.assertIn("first 12", result["reason"])
        self.assertEqual(result["checked_candidates"], 12)

    def test_failed_image_does_not_stop_later_candidate(self):
        options = [{"photo_id": str(i), "page_url": f"https://movie.douban.com/photos/photo/{i}/",
                    "image_url": f"https://img3.doubanio.com/view/photo/l/public/p{i}.jpg"} for i in (1, 2)]
        with patch.object(monthly_prep, "douban_poster_options", return_value=options), \
             patch.object(monthly_prep, "fetch", side_effect=[URLError("unavailable"), jpeg(600, 900)]):
            with tempfile.TemporaryDirectory() as folder:
                result = monthly_prep.douban_candidate_poster(self.candidate(), Path(folder) / "poster.jpg")
        self.assertEqual(result["status"], "ready")
        self.assertEqual(result["photo_id"], "2")
        self.assertEqual(len(result["download_failures"]), 1)

    def collect_with_gallery(self, root, **gallery_mock):
        with patch.object(monthly_prep, "ROOT", root), \
             patch.object(monthly_prep, "CAND", root / "candidates"), \
             patch.object(monthly_prep, "DOUBAN_DELAY", 0), \
             patch.object(monthly_prep, "douban", side_effect=self.fake_douban), \
             patch.object(monthly_prep, "douban_candidate_poster", **gallery_mock), \
             patch.object(monthly_prep, "fetch", return_value=b"\xff\xd8\xffposter"):
            errors = []
            movies = monthly_prep.collect_movies([(2026, 11)], errors)
        return movies, errors

    def test_gallery_failure_and_no_strict_poster_fall_back_to_main(self):
        cases = {
            "verification": {"side_effect": ValueError("Douban poster gallery requires verification; not bypassed")},
            "no strict": {"return_value": {"status": "no strict 2:3 poster", "reason": "No usable strict 2:3 poster"}},
        }
        for name, gallery_mock in cases.items():
            with self.subTest(case=name), tempfile.TemporaryDirectory() as folder:
                movies, errors = self.collect_with_gallery(Path(folder), **gallery_mock)
                self.assertEqual(movies[0]["poster_source"], "douban_main")
                self.assertEqual(movies[0]["poster_file"], "candidates/posters/movie_36915988.jpg")
                self.assertTrue(movies[0]["poster_gallery"]["reason"])
                self.assertTrue(any("main poster used" in error for error in errors))

    def test_existing_formal_poster_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "img").mkdir()
            original = root / "img" / "movie_36915988.jpg"
            original.write_bytes(b"keep this poster")
            with patch.object(monthly_prep, "douban_candidate_poster") as gallery:
                movies, _ = self.collect_with_gallery(root)
            gallery.assert_not_called()
            self.assertEqual(original.read_bytes(), b"keep this poster")
            self.assertEqual(movies[0]["poster_source"], "existing")


if __name__ == "__main__":
    unittest.main()
