#! /usr/bin/env python

import logging
import ConfigParser
import requests
import os
import shutil
import sys
from twython import Twython, TwythonError
import xml.etree.ElementTree as ET

# Global Variables
Software_Repo = os.environ['HOME']+"/Documents/capd"
api_account_permissions = ['Read Accounts', 'Create Categories', 'Read Categories', 'Read Computers', 'Update Computers', 'Create Packages',
							'Read Packages', 'Update Packages', 'Delete Packages', 'Create Policies', 'Read Policies', 'Update Policies',
							'Delete Policies', 'Read Sites']

def check_conf(args):
	''' Using info from conf file, check JSS connection, check API privileges, and check Twitter Auth'''
	logger = logging.getLogger('capd')
	logger.debug("check_conf")
	config = ConfigParser.ConfigParser()
	config.read(Software_Repo+'/conf/JSS_Server.conf')
	
	#### check JSS connection ####
	## Add name of JSS server being checked!!!!!!!! ###
	logger.info("[+] Checking JSS Connection ...")
	try:
		r = requests.get(config.get('JSS_Server', 'jss_url', 0), timeout=10, verify=False)
		logger.info("[+] JSS connection OK")
	except requests.exceptions.RequestException as e:
		logger.error("[-] JSS Server problem with following error: %s", e)
		sys.exit(1)

	#### check API Privileges ####
	logger.info("[+] Checking API Privileges ...")
	api_user_permissions = []
	try:
		url_api = config.get('JSS_Server', 'url_api', 0)
		api_user = config.get('JSS_Server', 'api_user', 0)
		api_pass = config.get('JSS_Server', 'api_pass', 0)
		r = requests.get(url_api+'accounts/username/'+api_user, auth=(api_user, api_pass), verify=False)
	except requests.exceptions.RequestException as e:
		logger.error("[-] JSS Server problem with following error: %s", e)
		sys.exit(1)
	tree = ET.fromstring(r.content)
	for elem in tree.iterfind('./privileges/jss_objects/'):
		api_user_permissions.append(elem.text)
	if not list(set(api_account_permissions) - set(api_user_permissions)):
		logger.info("[+] API Privilegs OK")
	else:
		logger.error("[-] You appear to be missing the following API privilege(s): %s", list(set(api_account_permissions) - set(api_user_permissions)))
		sys.exit(1)

	#### check Twitter Auth ####
	logger.info("[+] Checking Twitter Auth ...")
	try:
		app_key = config.get('Twitter_Auth', 'twitter_app_key', 0)
		if not app_key:
			logger.info("[+] No Twitter App Key provided!")
			return
		app_secret = config.get('Twitter_Auth', 'twitter_app_secret', 0)
		oauth_token = config.get('Twitter_Auth', 'twitter_oauth_token', 0)
		oauth_token_secret = config.get('Twitter_Auth', 'twitter_oauth_token_secret', 0)
		twitter = Twython(app_key, app_secret, oauth_token, oauth_token_secret)
		twitter.get("https://api.twitter.com/1.1/account/verify_credentials.json")
		logger.info("[+] Twitter Auth OK")
	except TwythonError as e:
		logger.error("[-] Check twitter oauth credentials. %s", e)
		sys.exit(1)

	#### clear apps and screenshots folder ####
	logger.info("Cleaning out apps folder ...")
	shutil.rmtree(Software_Repo+'/apps/')
	shutil.rmtree(Software_Repo+'/logs/screenshots/')
	os.mkdir(Software_Repo+'/apps')
	os.mkdir(Software_Repo+'/logs/screenshots')


	#### check cert and local App Server ####

	#### check Mail Server ####

def main():
	check_conf()

if __name__ == '__main__':
	main()
