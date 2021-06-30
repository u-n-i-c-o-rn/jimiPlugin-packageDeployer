from flask import Blueprint, render_template, redirect, send_from_directory
from flask import current_app as app
from pathlib import Path
import functools
import json

from flask.helpers import make_response

import jimi

from plugins.packageDeployer.models import packageDeployer
from plugins.asset.models import asset
from plugins.playbook.models import playbook

pluginPages = Blueprint('packageDeployerPages', __name__, template_folder="templates")

# SEC #
# * Cookie needs to be replaced with jwt
# * PUBLIC should be replaced with @publicEndpoint - need to build  

def authenticated(f):
    @functools.wraps(f)
    def wrap(*args, **kwargs):
        try:
            username = jimi.api.request.cookies["packageDeployer"]
            if username:
                return f(*args, **kwargs)
        except Exception as e:
            pass
        return "Authentication Required", 403
    return wrap

@pluginPages.route('/includes/<file>')
@authenticated
def __PUBLIC__custom_static(file):
    return send_from_directory(str(Path("plugins/packageDeployer/web/includes")), file)

@pluginPages.route("/",methods=["GET"])
def __PUBLIC__mainPage():
    return render_template("userLogin.html")

@pluginPages.route("/",methods=["POST"])
def __PUBLIC__doLogin():
    data = json.loads(jimi.api.request.data)
    response = make_response()
    response.set_cookie("packageDeployer", value=data["username"], max_age=1800, httponly=True)
    return response, 200

# jimi.api.request.cookies["jimiAuth"]

@pluginPages.route("/devices/",methods=["GET"])
@authenticated
def __PUBLIC__devices():
    username = jimi.api.request.cookies["packageDeployer"]
    devices = asset._asset().query(query={ "assetType" : "computer", "fields.user" : username },fields=["name"])["results"]
    result = []
    for device in devices:
        result.append({"_id" : device["_id"], "name" : device["name"]})
    return { "results" : result }, 200

@pluginPages.route("/device/<asset_id>/",methods=["GET"])
@authenticated
def __PUBLIC__manageDevicePage(asset_id):
    packages = packageDeployer._packageDeployer().query(query={})["results"]
    playbookIds = []
    for package in packages:
        playbookIds.append(jimi.db.ObjectId(package["playbook_id"]))
    playbooks = playbook._playbook().query(query={ "_id" : { "$in" : playbookIds }, "playbookData.asset_id" : asset_id },fields=["_id","playbookData","result"])["results"]
    playbookHash = {}
    for playbookItem in playbooks:
        playbookHash[playbookItem["_id"]] = playbookItem
    for package in packages:
        if package["playbook_id"] in playbookHash:
            if playbookHash[package["playbook_id"]]["result"]:
                package["status"] = "Installed"
            else:
                try:
                    package["status"] = playbookHash[package["playbook_id"]]["playbookData"]["status"]
                except KeyError:
                    package["status"] = "Unknown"
        else:
            package["status"] = "Available"
    return render_template("packages.html", packages=packages)