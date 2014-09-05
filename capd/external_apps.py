#! /usr/bin/env python

import ConfigParser
import json
import logging
import os
import plistlib
import re
import requests
import sys
import time
import xml.etree.ElementTree as ET
from subprocess import check_call, call
from twython import Twython, TwythonError

# Global Variables
Software_Repo = os.environ['HOME']+"/Documents/capd"
twitter_applist = {}
client_prototype_dict = {}
client_prototype_file = Software_Repo+"/conf/client_prototype_file.json"
autopkg_pkg_path_plist_file = os.environ["HOME"]+"/Library/AutoPkg/Cache/autopkg_results.plist"
autopkg_git_repo = "http://github.com/autopkg/recipes.git"

def add_pkg_prefix():
	logger = logging.getLogger('capd')
	logger.debug("add_pkg_prefix")
	pkg_prefix = time.strftime("%y%m%d%H%M")+"_"
	pkgs = os.listdir(Software_Repo+"/apps/")
	client_prototype_dict = json.loads(open(client_prototype_file).read())
	for pkg in pkgs:
		pkg_name = pkg.split('.')[0]
		pkg_ext = pkg.split('.')[1]
		if not pkg.startswith('.') and not pkg.startswith(pkg_prefix):
			if client_prototype_dict:
				os.rename(Software_Repo+"/apps/"+pkg, Software_Repo+"/apps/"+pkg_prefix+pkg_name+'_'+client_prototype_dict[pkg_name]+'.'+pkg_ext)
			else:
				os.rename(Software_Repo+"/apps/"+pkg, Software_Repo+"/apps/"+pkg_prefix+pkg_name+'.'+pkg_ext)
		logger.info("[+] Package %s renamed", pkg)

def create_twitter_applist():
	global twitter_applist
	logger = logging.getLogger('capd')
	logger.debug("create_twitter_applist")
	config = ConfigParser.ConfigParser()
	config.read(Software_Repo+'/conf/JSS_Server.conf')
	app_key = config.get('Twitter_Auth', 'twitter_app_key', 0)
	app_secret = config.get('Twitter_Auth', 'twitter_app_secret', 0)
	oauth_token = config.get('Twitter_Auth', 'twitter_oauth_token', 0)
	oauth_token_secret = config.get('Twitter_Auth', 'twitter_oauth_token_secret', 0)
	external_apps_list = (config.get('External_Apps', 'external_apps_list')).split(',')
	if not app_key:
		logger.info("[+] No Twitter app_key. Will not create twitter applist!")
		return
	twitter = Twython(app_key, app_secret, oauth_token, oauth_token_secret)
	n = 0
	tweet_object = twitter.get_user_timeline(screen_name='current_version', count=12)
	for n in range(len(tweet_object)):
		pkg_info = tweet_object[n]['text']
		pkg_list = re.findall(r"\[(.*?)\]", pkg_info)
		if pkg_list[0] == "Mac":
			twitter_applist[pkg_list[1]] = pkg_list[2]
		n += 1

def compare_lists():
	global client_prototype_dict
	logger = logging.getLogger('capd')
	logger.debug("compare_lists")
	config = ConfigParser.ConfigParser()
	config.read(Software_Repo+'/conf/JSS_Server.conf')
	external_apps_list = (config.get('External_Apps', 'external_apps_list')).split(',')
	if not twitter_applist:
		logger.info("[+] No twitter credentials provided, so no lists to compare")
		return	
	if not os.path.isfile(client_prototype_file):
		logger.info("[+] No external apps json file found. Using external apps list to download ...")
		for app in external_apps_list:
			if app in twitter_applist:
				client_prototype_dict[app] = twitter_applist[app]
				xcall_autopkg(app)
		json.dump(client_prototype_dict, open(client_prototype_file, 'wb'))
	elif os.path.isfile(client_prototype_file):
		client_prototype_dict = json.loads(open(client_prototype_file).read())
		logger.debug("Client Prototype AppList: %s", client_prototype_dict)
		logger.debug("Twitter AppList: %s", twitter_applist)
		dict_intersection = client_prototype_dict.viewkeys() & twitter_applist.viewkeys()
		for key in set(client_prototype_dict) & set(twitter_applist):
			if client_prototype_dict[key] == twitter_applist[key]:
				logger.info("[+] App installed is up-to-date: %s %s", key, client_prototype_dict[key])
			elif client_prototype_dict[key] > twitter_applist[key]:
				logger.info("[+] App installed %s is a newer version %s", key, client_prototype_dict[key])
			else:
				logger.info("[+] Installed app: %s %s -------- new version: %s", key, client_prototype_dict[key], twitter_applist[key])
				client_prototype_dict[key] = twitter_applist[key] 
				json.dump(client_prototype_dict, open(client_prototype_file, 'wb'))
				call_autopkg(key)

def call_autopkg(twitter_applist_pkg):
	logger = logging.getLogger('capd')
	logger.debug("autopkg")
	if os.path.exists("/Library/Autopkg"):
		try:
			check_call(["autopkg", "run", twitter_applist_pkg+".download"])
		except Exception:
			logger.error("[-] Package %s not found in autopkg", twitter_applist_pkg)
			sys.exit(1)
		f = plistlib.readPlist(autopkg_pkg_path_plist_file)
		autopkg_pkg_path = f[0][2]['Output']['pathname']
		call(['mv', autopkg_pkg_path, Software_Repo+'/apps/'])
	else:
		logger.error("[-] Autopkg does not appear to be installed")

def main():
	create_twitter_applist()
	compare_lists()
	call_autopkg()
	add_pkg_prefix()

if __name__ == '__main__':
	main()