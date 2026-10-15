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
    def validate(self,games,movies,albums=None):
        if albums is None:albums={'groups':[{'year':g['year'],'month':g['month'],'albums':[]} for g in games['groups']]}
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            for name,data in [('releases.json',games),('movies.json',movies),('albums.json',albums)]:
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

    def test_games_and_albums_months_match(self):
        games,movies=self.data([(2026,9),(2026,10),(2026,11)])
        albums={'groups':[{'year':2026,'month':m,'albums':[]} for m in (10,11,12)]}
        self.assertIn('game/album month groups disagree',self.validate(games,movies,albums))

    def test_album_fields_checked(self):
        games,movies=self.data([(2026,9),(2026,10),(2026,11)])
        bad={'title':'X','artist':'','date':'2026-10-09','year':2026,'month':10,'day':9,'mc':101,'mc_url':'https://example.com/'}
        albums={'groups':[{'year':2026,'month':m,'albums':[bad] if m==10 else []} for m in (9,10,11)]}
        errors=self.validate(games,movies,albums)
        for message in ('empty artist','invalid Metacritic score','invalid Metacritic album URL'):
            self.assertTrue(any(message in e for e in errors),message)

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

# Metacritic「New Releases」列表页的一行（2026-10-15 页面结构）
ROW=('<td class="clamp-summary-wrap"> <div class="clamp-score-wrap"> <a class="metascore_anchor" href="/music/{path}/critic-reviews">'
     ' <div class="metascore_w large release positive">{score}</div> </a> </div> <a href="/music/{path}" class="title"><h3>{title}</h3></a>'
     ' <div class="clamp-details"> <div class="artist"> by {artist} </div> <span>October 9, 2026</span> </div> </td>')

class AlbumScoreTests(unittest.TestCase):
    def page(self,*rows):
        return '<table>'+''.join(ROW.format(path=p,score=s,title=t,artist=a) for p,s,t,a in rows)+'</table>'

    def test_parse_list_row(self):
        rows=update_scores.parse_album_list(self.page(('shes-the-best/troye-sivan','81',"She&#039;s The Best",'Troye Sivan'),('x/y','tbd','X','Y')))
        self.assertEqual(rows[0],{'path':'/music/shes-the-best/troye-sivan','title':"She's The Best",'artist':'Troye Sivan','score':81})
        self.assertIsNone(rows[1]['score'])

    def test_match_by_url_then_name(self):
        rows=update_scores.parse_album_list(self.page(('heavy-is-the-crown/anderson-paak-cordae','77','Heavy Is The Crown','Anderson .Paak &amp; Cordae')))
        by_url={'title':'Other','artist':'Other','mc_url':'https://www.metacritic.com/music/heavy-is-the-crown/anderson-paak-cordae'}
        by_name={'title':'Heavy Is the Crown','artist':'Anderson .Paak & Cordae','mc_url':'https://www.metacritic.com/music/heavy-is-the-crown/anderson-paak-and-cordae'}
        miss={'title':'Heavy Is the Crown','artist':'Someone Else','mc_url':'https://www.metacritic.com/music/a/b'}
        self.assertIsNotNone(update_scores.match_album(by_url,rows))
        self.assertIsNotNone(update_scores.match_album(by_name,rows))
        self.assertIsNone(update_scores.match_album(miss,rows))

    def test_list_failure_reported(self):
        with patch.object(update_scores,'fetch',return_value='<html>Just a moment...</html>'):
            rows,errors=update_scores.album_list()
        self.assertEqual(rows,[]);self.assertEqual(len(errors),update_scores.ALBUM_LIST_PAGES)

if __name__=='__main__':unittest.main()
