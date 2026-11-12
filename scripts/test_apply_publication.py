"""Regression tests for manifest-driven, atomic calendar publication."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

import apply_publication
import check_data


class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        (self.root / "candidates" / "posters").mkdir(parents=True)
        (self.root / "img").mkdir()
        self.months = [(2026, 11), (2026, 12), (2027, 1)]
        self.movie = {
            "title": "旧电影", "sid": "100", "url": "https://movie.douban.com/subject/100/",
            "date": "2026-11-10", "year": 2026, "month": 11, "day": 10,
            "score": 7.0, "votes": 1000, "poster": "img/movie_100.jpg",
        }
        self.album = {
            "title": "Old Album", "artist": "Artist", "apple_id": "200",
            "apple_url": "https://music.apple.com/cn/album/old-album/200",
            "date": "2026-11-11", "year": 2026, "month": 11, "day": 11,
            "art": "https://is1-ssl.mzstatic.com/image.jpg",
        }
        self.game = {
            "title": "旧游戏", "date": "2026-11-12", "year": 2026, "month": 11, "day": 12,
            "mc": None, "plats": [{"key": "steam", "url": "https://store.steampowered.com/app/300/"}],
            "cover_img": "img/game_300.jpg",
        }
        self.data = {
            "movies": self.document("movies", [self.movie]),
            "albums": self.document("albums", [self.album]),
            "games": self.document("games", [self.game]),
        }
        for kind, document in self.data.items():
            self.write_data(kind, document)
        (self.root / "img" / "movie_100.jpg").write_bytes(b"\xff\xd8\xffold")
        (self.root / "img" / "game_300.jpg").write_bytes(b"\xff\xd8\xffgame")
        self.manifest = self.root / "candidates" / "publish.json"

    def tearDown(self):
        self.temporary.cleanup()

    def document(self, key, first_items):
        return {
            "fetched_at": "keep-me", "updated": "keep-me-too", "source": "unchanged",
            "groups": [
                {"year": year, "month": month, "label": f"{year}年{month}月",
                 key: copy.deepcopy(first_items) if (year, month) == self.months[0] else []}
                for year, month in self.months
            ],
        }

    def write_data(self, kind, document):
        (self.root / apply_publication.SPECS[kind]["file"]).write_text(
            json.dumps(document, ensure_ascii=False), encoding="utf-8"
        )

    def entry(self, kind, identity, title, day, month=11, year=2026):
        date = f"{year:04d}-{month:02d}-{day:02d}"
        common = {"title": title, "date": date, "year": year, "month": month, "day": day}
        if kind == "movies":
            return {**common, "sid": str(identity), "url": f"https://movie.douban.com/subject/{identity}/",
                    "score": None, "votes": 0, "poster": f"img/movie_{identity}.jpg"}
        if kind == "albums":
            return {**common, "artist": "New Artist", "apple_id": str(identity), "apple_url": None,
                    "art": "https://is1-ssl.mzstatic.com/new.jpg"}
        return {**common, "mc": 80,
                "plats": [{"key": "steam", "url": f"https://store.steampowered.com/app/{identity}/"}]}

    def publish(self, movies=None, albums=None, games=None, remove_movies=None, remove_albums=None, remove_games=None):
        manifest = {
            "version": 1,
            "movies": {"upsert": movies or [], "remove": remove_movies or []},
            "albums": {"upsert": albums or [], "remove": remove_albums or []},
            "games": {"upsert": games or [], "remove": remove_games or []},
        }
        self.manifest.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
        return apply_publication.apply(self.root)

    def snapshot(self):
        return {
            name: (self.root / name).read_bytes()
            for name in ("movies.json", "albums.json", "releases.json")
        }

    def assert_rejected(self, message, **operations):
        before = self.snapshot()
        with self.assertRaisesRegex(apply_publication.PublicationError, message):
            if operations:
                self.publish(**operations)
            else:
                apply_publication.apply(self.root)
        self.assertEqual(self.snapshot(), before)

    def items(self, kind):
        document = json.loads((self.root / apply_publication.SPECS[kind]["file"]).read_text(encoding="utf-8"))
        key = apply_publication.SPECS[kind]["key"]
        return [item for group in document["groups"] for item in group[key]]

    def test_three_kinds_upsert_update_remove_and_sort(self):
        movie = self.entry("movies", 101, "新电影", 2)
        (self.root / "candidates" / "posters" / "movie_101.jpg").write_bytes(b"\xff\xd8\xffnew")
        updated_album = {**self.album, "title": "Renamed Album", "date": "2026-12-01", "year": 2026, "month": 12, "day": 1}
        album = self.entry("albums", 201, "New Album", 3)
        game = self.entry("games", 301, "新游戏", 1)
        result = self.publish(movies=[movie], albums=[updated_album, album], games=[game], remove_games=["旧游戏"])
        self.assertEqual(result, apply_publication.Result(True, 3, 1))
        self.assertEqual([item["title"] for item in self.items("movies")], ["新电影", "旧电影"])
        self.assertEqual([item["title"] for item in self.items("albums")], ["New Album", "Renamed Album"])
        self.assertEqual([item["title"] for item in self.items("games")], ["新游戏"])
        self.assertFalse((self.root / "candidates" / "posters" / "movie_101.jpg").exists())
        self.assertTrue((self.root / "img" / "movie_101.jpg").is_file())
        self.assertEqual(check_data.validate(self.root, False), [])

    def test_existing_movie_update_does_not_need_candidate(self):
        updated = {**self.movie, "score": 8.2}
        result = self.publish(movies=[updated])
        self.assertEqual(result, apply_publication.Result(True, 1, 0))
        self.assertEqual(self.items("movies")[0]["score"], 8.2)

    def test_same_manifest_is_idempotent(self):
        movie = self.entry("movies", 101, "新电影", 2)
        (self.root / "candidates" / "posters" / "movie_101.jpg").write_bytes(b"\xff\xd8\xffnew")
        self.publish(movies=[movie])
        before = self.snapshot()
        result = apply_publication.apply(self.root)
        self.assertEqual(result, apply_publication.Result(False, 0, 0))
        self.assertEqual(self.snapshot(), before)

    def test_missing_poster_rejects_without_formal_writes(self):
        self.assert_rejected("missing candidate poster", movies=[self.entry("movies", 101, "新电影", 2)])
        self.assertEqual([item["sid"] for item in self.items("movies")], ["100"])

    def test_duplicate_id_rejected(self):
        self.assert_rejected(
            "duplicate IDs",
            movies=[self.entry("movies", 101, "A", 2), self.entry("movies", 101, "B", 3)],
        )

    def test_outside_window_rejected(self):
        self.assert_rejected(
            "outside the current three-month window",
            albums=[self.entry("albums", 201, "Outside", 2, month=2, year=2027)],
        )

    def test_illegal_poster_path_rejected(self):
        movie = {**self.entry("movies", 101, "Bad Path", 2), "poster": "../outside.jpg"}
        self.assert_rejected("poster must be img/movie_101.jpg", movies=[movie])

    def test_malformed_json_rejected(self):
        self.manifest.write_text("{not json", encoding="utf-8")
        self.assert_rejected("invalid JSON")

    def test_invalid_complete_entry_rejected_without_writes(self):
        album = {**self.entry("albums", 201, "Invalid", 2), "artist": ""}
        self.assert_rejected("result failed calendar validation", albums=[album])

    def test_untouched_entries_and_top_level_fields_stay_unchanged(self):
        before = copy.deepcopy(self.data["games"])
        self.publish(albums=[self.entry("albums", 201, "New Album", 2)])
        after = json.loads((self.root / "releases.json").read_text(encoding="utf-8"))
        self.assertEqual(after, before)
        albums = json.loads((self.root / "albums.json").read_text(encoding="utf-8"))
        self.assertEqual(albums["fetched_at"], "keep-me")
        self.assertEqual(albums["updated"], "keep-me-too")
        self.assertEqual(albums["source"], "unchanged")
        self.assertIn(self.album, self.items("albums"))

    def test_remove_is_idempotent_and_retains_images(self):
        result = self.publish(remove_movies=["100"])
        self.assertEqual(result, apply_publication.Result(True, 1, 0))
        self.assertTrue((self.root / "img" / "movie_100.jpg").exists())
        before = self.snapshot()
        self.assertEqual(apply_publication.apply(self.root), apply_publication.Result(False, 0, 0))
        self.assertEqual(self.snapshot(), before)

    def test_game_rename_uses_remove_and_upsert(self):
        renamed = self.entry("games", 301, "新名字", 12)
        self.publish(games=[renamed], remove_games=["旧游戏"])
        self.assertEqual([item["title"] for item in self.items("games")], ["新名字"])


if __name__ == "__main__":
    unittest.main()
