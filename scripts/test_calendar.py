"""Regression checks for three-month data and app/package Steam prices."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import check_data
import update_scores

ROOT=Path(__file__).resolve().parents[1]

class CalendarTests(unittest.TestCase):
    def validate(self,games,movies):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            for name,data in [('releases.json',games),('movies.json',movies)]:
                (root/name).write_text(json.dumps(data),encoding='utf-8')
            return check_data.validate(root,False)

    def data(self,months):
        def groups(key):return {'groups':[{'year':y,'month':m,key:[]} for y,m in months]}
        return groups('games'),groups('movies')

    def test_three_months_across_year(self):
        self.assertEqual(self.validate(*self.data([(2026,12),(2027,1),(2027,2)])),[])

    def test_two_months_rejected(self):
        self.assertTrue(self.validate(*self.data([(2026,10),(2026,11)])))

    def test_third_month_gap_rejected(self):
        self.assertTrue(self.validate(*self.data([(2026,9),(2026,10),(2026,12)])))

    def test_games_and_movies_months_match(self):
        games,_=self.data([(2026,9),(2026,10),(2026,11)])
        _,movies=self.data([(2026,10),(2026,11),(2026,12)])
        self.assertIn('game/movie month groups disagree',self.validate(games,movies))

    def test_published_proposal(self):
        self.assertEqual(check_data.validate(ROOT,False),[])

class SteamPriceTests(unittest.TestCase):
    def package(self,apps=(2054970,2593290),currency='CNY',final=24800):
        return json.dumps({'1686522':{'success':True,'data':{'apps':[{'id':value} for value in apps],'price':{'currency':currency,'final':final}}}})

    def item(self):return {'steam_url':'https://store.steampowered.com/sub/1686522/','steam_package_apps':[2054970,2593290]}

    def test_valid_package(self):
        with patch.object(update_scores,'fetch',return_value=self.package()) as fetch:
            self.assertEqual(update_scores.steam_price(self.item()),('ok',248.0))
            self.assertIn('packageids=1686522',fetch.call_args.args[0])

    def test_missing_expected_expansion_rejected(self):
        with patch.object(update_scores,'fetch',return_value=self.package(apps=(2054970,))):
            status,value=update_scores.steam_price(self.item())
            self.assertTrue(status.startswith('error:'));self.assertIsNone(value)

    def test_wrong_currency_retains_price(self):
        with patch.object(update_scores,'fetch',return_value=self.package(currency='USD')):
            self.assertEqual(update_scores.steam_price(self.item()),('unavailable',None))

    def test_invalid_final_rejected(self):
        for final in (True,-1,248.0,None):
            with self.subTest(final=final),patch.object(update_scores,'fetch',return_value=self.package(final=final)):
                self.assertEqual(update_scores.steam_price(self.item()),('unavailable',None))

    def test_unverified_package_not_requested(self):
        with patch.object(update_scores,'fetch') as fetch:
            self.assertEqual(update_scores.steam_price({'steam_url':'https://store.steampowered.com/sub/1686522/'}),('unavailable',None))
            fetch.assert_not_called()

    def test_existing_app_unchanged(self):
        body=json.dumps({'2288340':{'success':True,'data':{'steam_appid':2288340,'type':'game','price_overview':{'currency':'CNY','final':29800}}}})
        with patch.object(update_scores,'fetch',return_value=body):
            self.assertEqual(update_scores.steam_price({'steam_url':'https://store.steampowered.com/app/2288340/'}),('ok',298.0))

if __name__=='__main__':unittest.main()
