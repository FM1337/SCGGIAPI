import requests
import os
from dateutil.relativedelta import relativedelta
import json
import time
import re


dbname = 'games.db'

template = """
<div class="col-lg-2 col-md-2 col-sm-12" style="font-size: 18px;color: green;height: 200px;"><center>
    <a href="http://store.steampowered.com/app/{appid}">
        <span data-toggle="tooltip" data-placement="bottom" title="Rating: <span class='badge'>{rating}</span><br>Description:<br>{disc}">
             <img class="img img-responsive" src="http://media.steampowered.com/steamcommunity/public/images/apps/{appid}/{logo}.jpg">
        </span>
    </a>
    <br>
    <a href="http://store.steampowered.com/app/{appid}">{appname}</a>
    <br>
    <span class="label label-danger">{playtime}</span>
</center></div>
"""

template2 = """
    <img src="{avatar}"><br>
    <h1><a href="{profileurl}">{profilename}</a></h1><br>
    is currently playing<br>
    <img src="http://media.steampowered.com/steamcommunity/public/images/apps/{gameid}/{logo}.jpg" width="200 hight="200"><br>
    <h2>
        <a href="http://store.steampowered.com/app/{gameid}/">{game}</a><br>
        <span class="label label-danger">{playtime} played</span>
    </h2>
"""

htmlerror = """
<img src="{avatar}"><br>
<h1><a href="{profileurl}">{profilename}</a></h1>
<br>
is currently playing
<br>
<h1><font color=red>NOTHING <i class="icon-frown"></i></font></h1>
"""

attrs = ['years', 'months', 'days', 'hours', 'minutes', 'seconds']
date = lambda delta: [
    '%d %s' % (
        getattr(delta, attr), getattr(delta, attr) > 1 and
        attr or attr[:-1]
    ) for attr in attrs if getattr(delta, attr)]


def relative(**kwargs):
    return date(relativedelta(**kwargs))


def hrt(tmp_time):
    return relative(seconds=int(tmp_time))


def striptags(string):
    return re.compile(r'(?ims)<[^>]+>').sub('', string).strip()


def get_games(steamid):
    """ give this function a steamid, it'll give you the current game """
    params = {
        'key': 'steamapikeyhere',
        'steamid': steamid,
        'include_appinfo': 1,
        'include_played_free_games': 1
    }
    print("Fetching all owned games...")
    try:
        data = requests.get("https://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/", params=params).json()
    except:
        print("Failed to fetch all games...")
        return False

    if data['response']['games']:
        games = data['response']['games']
        print("Done.")
        return games
    else:
        print("Failed to fetch all games...")
        return False


def get_current(steamids):
    """ give this function a steamid, it'll give you the current game """
    params = {
        'key': 'steamapikeyhere',
        'steamids': steamids,
    }
    print("Fetching any games being currently played...")
    try:
        data = requests.get("http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/", params=params).json()
    except:
        print("Failed to fetch current games. Not playing any?")
        return False

    if data['response']['players']:
        players = data['response']['players'][0]
        print("Done.")
        return players
    else:
        print("Failed to fetch current games. Not playing any?")
        return False


def check_for_updates(dbname, games):
    """ Function that will check for updates for any games """

    print("Checking for any updates now...")

    def fetch(appid):
        print("Fetching data for %s..." % appid)
        # Sleep prior to pulling the data that way we don't send 100 requests within 10s
        time.sleep(1)
        uri = 'http://store.steampowered.com/api/appdetails/?appids=%s'
        try:
            data = requests.get(uri % appid, timeout=4).json()[appid]
            if not data['success']:
                return False

            return data
        except:
            print("Failed to fetch data for %s..." % appid)
            return False

    try:
        with open(dbname, 'r') as f:
            db = json.loads(f.read())

    except Exception as e:
        print("Error reading %s file... (%s)" % (dbname, str(e)))
        print("Regenerating...")
        with open(dbname, 'w') as f:
            f.write(json.dumps({}))
        db = {}

    for game in games:
        appid = str(game['appid'])
        if appid not in db:
            # We need to fetch the data and save it!
            tmp = fetch(appid)
            if tmp:
                db[appid] = tmp
                db[appid]['checked'] = int(time.time())
        else:
            if int(time.time()) - int(db[appid]['checked']) >= 1296000:
                # Assume it's older than one month
                print "herp"
                os._exit(1)
                tmp = fetch(appid)
                if tmp:
                    db[appid] = tmp
                    db[appid]['checked'] = int(time.time())

    with open(dbname, 'w') as f:
        f.write(json.dumps(db))

    return db


def main():
    """ Main function, do stuffz """

    games = get_games(steamidhere)
    players = get_current(steamidhere)
    db = check_for_updates(dbname, games)
    if not games:
        print("Error while fetching games.")
        os._exit(1)

    if 'gameid' not in players:
        with open('location/file', 'w') as f:
            f.write(htmlerror.format(profilename=players['personaname'], avatar=players['avatarfull'], profileurl=players['profileurl']).encode('ascii', 'xmlcharrefreplace'))
    else:
        playtime = False
        logo = ""
        for game in games:
            if int(game['appid']) == int(players['gameid']):
                playtime = hrt(int(game['playtime_forever']) * 60)[0]
                logo = game['img_logo_url']

                break
        if not playtime:
            playtime = "N/A"
        html2 = template2.format(logo=logo, playtime=playtime, game=players['gameextrainfo'], gameid=players['gameid'], profilename=players['personaname'], avatar=players['avatarfull'], profileurl=players['profileurl'].encode('ascii', 'xmlcharrefreplace'))
        with open('location/file', 'w') as f:
            f.write(html2)

    output = []  # We'll output a list of things to output, then combine them with join()
    games = list(reversed(sorted(games, key=lambda k: k['playtime_forever'])))

    for game in games:
        rating = False
        disc = False
        if str(game['appid']) in db:
            game_data = db[str(game['appid'])]
            if 'metacritic' in game_data:
                rating = str(game_data['metacritic']['score']) + '%'
            if 'about_the_game' in game_data:
                disc = striptags(game_data['about_the_game'].encode('ascii', 'xmlcharrefreplace')).replace('"', '')
                if len(disc) > 200:
                    disc = disc[0:199] + '... <p style=\'color: orange;font-size: 12px\'>Click the image to learn more</p>'
            if not rating:
                rating = 'N/A'
            if not disc:
                disc = 'None'
        # game is a dictionary, that looks like the below:
        # {
        #    u'appid': 70,
        #    u'has_community_visible_stats': True,
        #    u'img_icon_url': u'95be6d131fc61f145797317ca437c9765f24b41c',
        #    u'img_logo_url': u'6bd76ff700a8c7a5460fbae3cf60cb930279897d',
        #    u'name': u'Half-Life',
        #    u'playtime_forever': 158
        # }
        ptime = hrt(int(game['playtime_forever']) * 60)
        # ptimeweeks = hrt(int(game['playtime_2weeks']) * 60)
        # if not ptimeweeks:
        #    ptimeweeks = 'Have not played in the last 2 weeks'
        # else:
        #    ptimeweeks = ptimeweeks[0] + ' played in the last two weeks'
        # Was not working will fix later#
        if not ptime:
            ptime = 'N/A'
        else:
            ptime = ptime[0] + ' played'
        html = template.format(rating=rating, disc=disc, logo=game['img_logo_url'], appid=str(game['appid']), playtime=ptime, appname=game['name'].encode('ascii', 'xmlcharrefreplace'))
        output.append(html)

    # Now, output is a list we need to join.
    content = ''.join(output)

    # Will be something like this http://paste.ml/xava.xml
    # It's complete now dump it:
    with open('location/file', 'w') as f:
        f.write(content)

if __name__ == "__main__":
    main()
