print(" [+] Loading basics...")
import os
import json
import re
from pymongo import MongoClient
import bcrypt
import requests
from pathlib import Path
p = Path(__file__).parents[0]
if os.name == 'nt':
  os.system("color")

os.system("title Social Wars Server")

print(" [+] Loading game config...")
from get_game_config import get_game_config, patch_game_config

print (" [+] Loading players...")
from get_player_info import get_player_info, get_neighbor_info
from sessions import load_saves, load_static_villages, load_quests, all_saves_userid, all_saves_info, save_info, new_village
load_saves()

from dotenv import load_dotenv
load_dotenv()
#load_saved_villages()

#Nije u funkciji /Not in function.
#print (" [+] Loading static villages...")
#load_static_villages()
#print (" [+] Loading quests...")
#load_quests()

print(" [+] Loading server...")
from flask import Flask, render_template, send_from_directory, request, redirect, session, Response
from flask.debughelpers import attach_enctype_error_multidict
from command import command
from engine import timestamp_now
from version import version_name
from constants import Quests

from constants import Constant
from bundle import ASSETS_DIR, STUB_DIR, TEMPLATES_DIR, BASE_DIR, SAVES_DIR_BACKUP

host = '0.0.0.0'
site = ' ip here '
port = 5055

app = Flask(__name__, template_folder=TEMPLATES_DIR)

print(" [+] Connecting to database...")

def get_database():
   CONNECTION_STRING = f"mongodb://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_IP')}:{os.getenv('DB_PORT')}/?retryWrites=true&w=majority"
   client = MongoClient(CONNECTION_STRING)
   return client['socialworld']

db = get_database()
se = db["sw"]

print(" [+] Configuring server routes...")

##########
# ROUTES #
##########

__STATIC_ROOT = "/static/socialwars"
__DYNAMIC_ROOT = "/dynamic/menvswomen/srvsexwars"

## PAGES AND RESOURCES


@app.route("/", methods=['GET', 'POST'])
def login():
  # Log out previous session
  session.pop('USERID', default=None)
  session.pop('GAMEVERSION', default=None)
  # Reload saves. Allows saves modification without server reset DISABLED CUZ IT POSSIBLY CAUSES null SAVES
  load_saves()
  # If logging in, set session USERID, and go to play
  if request.method == 'POST':
    msg = ''
    password = request.form["password"]
    bytePassword = password.encode('utf-8')
    email = request.form["email"].lower()
    account = se.find_one({"email":email})
    print(account)
    print(email)
    #print(password)
    if account != None:
      db_hash = account["password"].encode('utf-8')
      if bcrypt.checkpw(bytePassword,db_hash):
        session['USERID'] = account["userid"]
        session['GAMEVERSION'] = "Basesec_1.5.4.swf"
        print("[LOGIN] USERID:", account["userid"])
        print("[LOGIN] GAMEVERSION:", "Basesec_1.5.4.swf")
        return redirect("/play.html")
      else:
        print("Wrong password")
        msg = "Wrong password!"
    else:
      print("Account not existing")
      msg = "Invalid e-mail/password entered!"
    return render_template("login.html", LOGmsg=msg)
  # Login page
  if request.method == 'GET':
    return render_template("login.html")



@app.route("/keeponline")
def keeponline():
  return "Online!"

@app.route("/play.html")
def play():
  print(session)

  if 'USERID' not in session:
    return redirect("/")
  if 'GAMEVERSION' not in session:
    return redirect("/")

  if session['USERID'] not in all_saves_userid():
    return redirect("/")

  USERID = session['USERID']
  GAMEVERSION = session['GAMEVERSION']
  print("[PLAY] USERID:", USERID)
  print("[PLAY] GAMEVERSION:", GAMEVERSION)
  return render_template("play.html",
                         save_info=save_info(USERID),
                         serverTime=timestamp_now(),
                         version=version_name,
                         GAMEVERSION=GAMEVERSION,
                         SERVERIP=site, ASSETSIP=ASSETS_DIR)


@app.route("/new.html", methods=["POST"])
def new():
  username = request.form["Regusername"]
  password = request.form["Regpassword"]
  bytePassword = password.encode('utf-8')
  mySalt = bcrypt.gensalt()
  pwd_hash = bcrypt.hashpw(bytePassword, mySalt)
  email = request.form["Regemail"].lower()
  msg = ''
  if not re.match(r'[^@]+@[^@]+\.[^@]+', email):
    msg = 'Invalid email address!'
  elif not re.match(r'[A-Za-z0-9]+', username):
    msg = 'Username may only contain characters and numbers!'
  elif not username or not password or not email:
    msg = 'Please fill in everything.'
  elif password == "5a93eccd2caa9166a9aa550ab4670e63ce637445a86081ffcc9b24ca317c99196b19df7b0f55238a5b27664ed95ba6f6bbe4b21ea975543fb063b4bd77cfced5":
    msg = 'Please fill in everything.'
  elif len(username) < 3 or len(username) > 20:
    msg = 'Your username should be between 3 and 20 characters!'
  else:
    account = se.find_one({"email":email})
    if account == None:
      session['USERID'] = new_village(username)
      session['GAMEVERSION'] = "Basesec_1.5.4.swf"
      se.insert_one({"userid":session['USERID'],"email":email,"password":pwd_hash.decode("utf-8")})
      return redirect("play.html")
    else:
      msg = 'An account with this e-mail already exists!'
  return render_template("login.html", REGmsg=msg)


@app.route("/crossdomain.xml")
def crossdomain():
  return send_from_directory(STUB_DIR, "crossdomain.xml")

@app.route("/saves/<path:path>")
def saves(path):
  return send_from_directory(SAVES_DIR_BACKUP, path)

@app.route("/img/<path:path>")
def images(path):
  return send_from_directory(TEMPLATES_DIR + "/img", path)


@app.route("/css/<path:path>")
def css(path):
  return send_from_directory(TEMPLATES_DIR + "/css", path)


## GAME STATIC

@app.route(__STATIC_ROOT + "/<path:path>")
def static_assets_loader(path):
    # LITE-WEIGHT BUILD: ASSETS FROM GITHUB
    if False:
        # cdn = "https://github.com/AcidCaos/socialwarriors/raw/main/assets/"
        cdn = "https://raw.githubusercontent.com/AcidCaos/socialwarriors/main/assets/"
        try:
            r = requests.get(cdn + path) # TODO timeout, retry
        except requests.exceptions:
            return ""
        m = io.BytesIO(r.content)
        m.seek(0)
        return send_file(m, download_name=path.split("/")[-1:][0])
    # OFFLINE BUILD
    return send_from_directory(ASSETS_DIR, path)

## GAME DYNAMIC

@app.route(__DYNAMIC_ROOT + "/track_game_status.php", methods=['POST'])
def track_game_status_response():
    status = request.values['status']
    installId = request.values['installId']
    user_id = request.values['user_id']

    # print(f"track_game_status: status={status}, installId={installId}, user_id={user_id}. --", request.values)
    print(f"[STATUS] USERID {user_id}: {status}")
    return ("", 200)

@app.route(__DYNAMIC_ROOT + "/get_game_config.php")
def get_game_config_response():
    USERID = request.values['USERID']
    user_key = request.values['user_key']
    language = request.values['language']

    # print(f"get_game_config: USERID: {USERID}. --", request.values)
    print(f"[CONFIG] USERID {USERID}.")
    return get_game_config()

@app.route(__DYNAMIC_ROOT + "/get_player_info.php", methods=['POST'])
def get_player_info_response():
    USERID = request.values['USERID']
    user_key = request.values['user_key']
    language = request.values['language']

    user = request.values['user'] if 'user' in request.values else None
    client_id = int(request.values['client_id']) if 'client_id' in request.values else None
    map = int(request.values['map']) if 'map' in request.values else None

    # print(f"get_player_info: USERID: {USERID}. --", request.values)

    # Current Player
    if user is None:
        print(f"[PLAYER INFO] USERID {USERID}.")
        return (get_player_info(USERID), 200)
    # General Mike
    elif user in ["100000030","100000031"]:
        print(f"[VISIT] USERID {USERID} visiting General Mike ({user}).")
        return (get_neighbor_info("100000030", map), 200)
    # Quest Maps
    elif user.startswith("100000"):
        print(f"[QUEST] USERID {USERID} loading", Quests.QUEST[user] if user in Quests.QUEST else "?", f"({user}).")
        return (get_neighbor_info(user, map), 200)
    # Static Neighbours
    else:
        print(f"[VISIT] USERID {USERID} visiting user: {user}.")
        return (get_neighbor_info(user, map), 200)
    
## AUCTION HOUSE

# @app.route(__DYNAMIC_ROOT + "/bets/get_bets_list.php", methods=['POST'])
# def get_bets_list():
#     USERID = request.values['USERID']
#     user_key = request.values['user_key']
#     language = request.values['language']
#     data = request.values['data']
# 
#     if not data.startswith("{"):
#         data = data[65:]
#     
#     data = json.loads(data)
#     user_id = data["user_id"]
#     level = data["level"]
# 
#     bets = auction_house.get_auctions(user_id, level)
#     for bet in bets:
#         bet["isPrivate"] =  0
#         bet["isWinning"] =  0
#         bet["won"] =  0
#         bet["finished"] =  0
# 
#     r = {}
#     r["result"] = "success"
#     r["data"] = {"bets": bets}
# 
#     response = json.dumps(r)
#     # print("RESPONSE:")
#     # print(response)
# 
#     return (response, 200)
# 
# @app.route(__DYNAMIC_ROOT + "/bets/get_bet_detail.php", methods=['POST'])
# def get_bet_detail():
#     USERID = request.values['USERID']
#     user_key = request.values['user_key']
#     language = request.values['language']
#     data = request.values['data']
#     
#     if not data.startswith("{"):
#         data = data[65:]
#     
#     data = json.loads(data)
#     uuid = data["uuid"]
#     checkFinish = 0
#     if "checkFinish" in data:
#         checkFinish = data["checkFinish"]
# 
#     bet = auction_house.get_auction_detail(USERID, uuid, checkFinish)
# 
#     print(f"Get bet details for BET UUID {uuid}")
#     print(json.dumps(data, indent="\t"))
# 
#     r = {}
#     r["result"] = "success"
#     r["data"] = bet
# 
#     response = json.dumps(r, indent="\t")
#     print("RESPONSE:")
#     print(response)
# 
#     return (response, 200)
# 
# @app.route(__DYNAMIC_ROOT + "/bets/set_bet.php", methods=['POST'])
# def set_bet():
#     USERID = request.values['USERID']
#     user_key = request.values['user_key']
#     language = request.values['language']
#     data = request.values['data']
# 
#     if not data.startswith("{"):
#         data = data[65:]
#     
#     data = json.loads(data)
#     uuid = data["uuid"]
#     bet_amount = data["bet"]
#     bet_round = data["round"]
# 
#     print(json.dumps(data, indent="\t"))
# 
#     auction_house.set_bet(USERID, uuid, bet_amount, bet_round)
# 
#     r = {}
#     r["result"] = "success"
#     r["data"] = {
#         "betResult": "OK"
#     }
# 
#     response = json.dumps(r)
#     # print("RESPONSE:")
#     # print(response)
# 
#     return (response, 200)

@app.route(__DYNAMIC_ROOT + "/sync_error_track.php", methods=['POST'])
def sync_error_track_response():
    USERID = request.values['USERID']
    user_key = request.values['user_key']
    language = request.values['language']

    # print(f"sync_error_track: USERID: {USERID}. --", request.values)
    return ("", 200)

@app.route("/null")
def flash_sync_error_response():
    sp_ref_cat = request.values['sp_ref_cat']

    if sp_ref_cat == "flash_sync_error":
        reason = "reload On Sync Error"
    elif sp_ref_cat == "flash_reload_quest":
        reason = "reload On End Quest"
    elif sp_ref_cat == "flash_reload_attack":
        reason = "reload On End Attack"

    print("flash_sync_error", reason, ". --", request.values)
    return redirect("/play.html")

@app.route(__DYNAMIC_ROOT + "/command.php", methods=['POST'])
def command_response():
    USERID = request.values['USERID']
    user_key = request.values['user_key']
    language = request.values['language']

    # print(f"command: USERID: {USERID}. --", request.values)

    data_str = request.values['data']
    data_hash = data_str[:64]
    assert data_str[64] == ';'
    data_payload = data_str[65:]
    data = json.loads(data_payload)

    command(USERID, data)
    
    return ({"result": "success"}, 200)


########
# MAIN #
########

print (" [+] Running server...")

if __name__ == '__main__':
    app.secret_key = 'SECRET_KEY'
    app.run(host=host, port=port, debug=False)
