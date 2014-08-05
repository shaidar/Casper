#!/usr/bin/env python

# Copyright 2013 Sar Haidar, Massachusetts Institute of Technology, All Rights Reserved.

import argparse
import ConfigParser
import logging
import json
import os
import plistlib
import re
import requests
import shutil
import sys
import time
import xml.etree.ElementTree as ET
from subprocess import call, check_output, check_call, CalledProcessError
from twython import Twython, TwythonError
from fabfile import *

'''
Improvements:
- Add function description
- Change static twitter_count value 
- Unmount CasperShare at the end
- upload_pkg_to_JSS: If you don't properly encode special characters in password, you will get a No route to host error
- Add email notification
'''

# Global Variables
Software_Repo = ""
headers = {'content-type':'application/json', 'accept':'application/json'}
twitter_applist = {}
client_prototype_applist = {}
updates_applist = {}
api_account_permissions = ['Read Accounts', 'Create Categories', 'Read Categories', 'Read Computers', 'Update Computers', 'Create Packages',
							'Read Packages', 'Update Packages', 'Delete Packages', 'Create Policies', 'Read Policies', 'Update Policies',
							'Delete Policies', 'Read Sites']
autopkg_pkg_path_plist_file = os.environ["HOME"]+"/Library/AutoPkg/Cache/autopkg_results.plist"
autopkg_git_repo = "http://github.com/autopkg/recipes.git"

class Package(object):		#object is there to make it a new-style class
	"All package attributes"
	def __init__(self, name=None, version=None, extension=None, prefix = None):
		config = ConfigParser.ConfigParser()
		config.read(Software_Repo+'/conf/JSS_Server.conf')
		self.name = name
		self.version = version
		self.extension = extension

	def full_name(self):
		return self.name + self.extension

	def path(self):
		return Software_Repo+"/apps/"+self.name+"/"

	def absolute_path(self):
		return Software_Repo+"/apps/"+self.name+self.extension

	def pkg_xml(self):
		return Software_Repo+"/apps/"+self.name+".xml"

	def pol_xml(self):
		return Software_Repo+"/apps/"+self.name+"_pol.xml"

class JSS(object):
	"All JSS attributes"
	def __init__(self):
		config = ConfigParser.ConfigParser()
		config.read(Software_Repo+'/conf/JSS_Server.conf')
		self.hostname = config.get('JSS_Server', 'jss_hostname', 0)
		self.url = config.get('JSS_Server', 'jss_url', 0)
		self.share = config.get('JSS_Server', 'jss_share', 0)
		self.share_username = config.get('JSS_Server', 'jss_share_username', 0)
		self.share_password = config.get('JSS_Server', 'jss_share_password', 0)
		self.api_url = config.get('JSS_Server', 'url_api', 0)
		self.api_user = config.get('JSS_Server', 'api_user', 0)
		self.api_pass = config.get('JSS_Server', 'api_pass', 0)
		self.category_name = config.get('JSS_Server', 'jss_category_name', 0)
		self.client_prototype_uuid = config.get('Client_Prototype', 'client_prototype_uuid', 0)

	def jss_pkg_id(self):
		'''Append existing JSS pkg_id's to a list and to find an unused value'''
		jss_pkg_id_list = []
		r = requests.get(self.api_url+"packages", auth = (self.api_user, self.api_pass), verify = False)
		tree = ET.fromstring(r.content)
		for elem in tree.findall("./package/id"):
			jss_pkg_id_list.append(elem.text)
		jss_pkg_id_list = map(int, jss_pkg_id_list)
		available_pkg_id = max(jss_pkg_id_list) + 1
		return available_pkg_id
		
	def jss_pkg_url(self):
		return self.api_url+"packages/id/"+str(self.jss_pkg_id())

	def jss_pol_id(self):
		'''Append existing JSS pol_id's to a list and to find an unused value'''
		jss_pol_id_list = []
		r = requests.get(self.api_url+"policies", auth = (self.api_user, self.api_pass), verify = False)
		tree = ET.fromstring(r.content)
		for elem in tree.findall("./policy/id"):
			jss_pol_id_list.append(elem.text)
		jss_pol_id_list = map(int, jss_pol_id_list)
		available_pol_id = max(jss_pol_id_list) + 1
		return available_pol_id
	
	def jss_pol_url(self):
		return self.api_url+"policies/id/"+str(self.jss_pol_id())

	def jss_computer_url(self):
		return self.api_url+"computers/udid/"+str(self.client_prototype_uuid)

	def jss_category_id(self):
		'''If category_name already in JSS, get category_id, otherwise append existing JSS category_id's to a list and find an unused value'''
		jss_category_id_list = []
		jss_category_name_dict = {}
		r = requests.get(self.api_url+"categories", auth = (self.api_user, self.api_pass), verify = False)
		tree = ET.fromstring(r.content)
		for number, name in tree.findall("./category"):
			jss_category_name_dict[name.text] = number.text
		if self.category_name in jss_category_name_dict:
			category_id = jss_category_name_dict[self.category_name]
		else:
			r = requests.get(self.api_url+"categories", auth = (self.api_user, self.api_pass), verify = False)
			tree = ET.fromstring(r.content)
			for elem in tree.findall("./category/id"):
				jss_category_id_list.append(elem.text)
			jss_category_id_list = map(int, jss_category_id_list)
			category_id = max(jss_category_id_list) + 1
			template = '''<?xml version="1.0" encoding="UTF-8" standalone="no"?>
			<category>
			<id>{category_id}</id>
			<name>{category_name}</name>
			</category>
			'''
			context = {
			"category_id": category_id,
			"category_name": self.category_name
			}
			with open(Software_Repo+"/conf/category.xml","w+") as category_xml:
				category_xml.write(template.format(**context))
				r = requests.post(self.api_url+"categories/id/"+str(category_id), auth = (self.api_user, self.api_pass), data = category_xml, verify = False)
		return category_id

def get_info():
	global Software_Repo
	parser = argparse.ArgumentParser()
	parser.add_argument("software_repository", help = "Full local path where the installers are located. example: /Users/joe/Documents/Apps/ ")
	args = parser.parse_args()
	Software_Repo = args.software_repository
	if os.path.exists(Software_Repo):
		if not os.path.exists(Software_Repo+"/logs"):
			os.mkdir(Software_Repo+"/logs")
		if not os.path.exists(Software_Repo+"/apps"):
			os.mkdir(Software_Repo+"/apps")
		if not os.path.exists(Software_Repo+"/conf"):
			os.mkdir(Software_Repo+"/conf")
		if not os.path.exists(Software_Repo+"/sequenced"):
			os.mkdir(Software_Repo+"/sequenced")
		init_logging(Software_Repo)
		logger = logging.getLogger('capd')
		check_conf = os.listdir(Software_Repo+"/conf")
		if "JSS_Server.conf" in check_conf:
			use_overwrite = raw_input("Config file already exists! Would you like to use it or overwrite it? U(se) O(verwrite): ")
			if use_overwrite == 'U':
				logger.info("Using existing config file")
			elif use_overwrite == 'O':
				logger.info("Overwriting config file")
				create_conf()
			else:
				logger.error("Wrong choice! Exiting!")
				print sys.exit("Wrong choice! Exiting!")
		else:
			create_conf()
	else:
		logger.error("Software Repository can't be found")
		sys.exit(1)

def init_logging(path_to_log):
	#set up logging to file
	logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p', filename=Software_Repo+'/logs/'+'capd.log', filemode='w')
	#define a Handler which writes DEBUG messages or higher to the sys.stderr
	console = logging.StreamHandler()
	console.setLevel(logging.INFO)
	#set a format which is simpler for console use
	formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
	# tell the handler to use this format
	console.setFormatter(formatter)
	#add the handler to the root logger
	logging.getLogger('').addHandler(console)
	logger = logging.getLogger('capd')

def create_conf():
	logger = logging.getLogger('capd')
	logger.debug("create_conf")
	jss_hostname = raw_input("JSS hostname: ")
	jss_url = raw_input("Full JSS URL and port number (ex. https://myjss.example.com:8443): ")
	jss_share = raw_input("Casper share name (ex. /Volumes/CasperShare/Packages/): ")
	jss_share_username = raw_input("Casper username with read/write access to share: ")
	jss_share_password = raw_input("Casper password for username with read/write access to share: ")
	api_user = raw_input("Account username with API priviliges: ")
	api_pass = raw_input("Password of API account: ")
	jss_category_name = raw_input("JSS Category name to use for packages and policy: ")
	twitter_app_key = raw_input("Twitter App Key: ")
	twitter_app_secret = raw_input("Twitter App Secret: ")
	twitter_oauth_token = raw_input("Twitter OAuth Token: ")
	twitter_oauth_token_secret = raw_input("Twitter OAuth Token Secret: ")
	client_prototype_uuid = raw_input("Hardware UUID of client prototype runnig casper client: ")
	client_prototype_ip = raw_input("IP address of client prototype running casper client: ")
	mac_host_ip = raw_input("IP address of Mac hosting client prototype VM: ")
	client_prototype_user = raw_input("Username for client prototype running casper client: ")
	client_prototype_pass = raw_input("Password for client prototype running casper client: ")
	client_prototype_vm_file = raw_input("Path to .vmx file (ex. /Users/joe/Documents/VMs/10.8.vmware.vm/10.8.vmx): ")
	client_prototype_clean_snapshot = raw_input("Name of clean VM snapshot: ")
	vmrun_command = raw_input("Path to vmrun command (ex. VMware Fusion path by default is /Applications/VMware\ Fusion.app/Contents/Libray/vmrun): ")
	config = ConfigParser.RawConfigParser()
	config.add_section('JSS_Server')
	config.add_section('local_config')
	config.add_section('Twitter_Auth')
	config.add_section('Client_Prototype')
	config.add_section('Fab_Config')
	config.set('JSS_Server', 'jss_hostname', jss_hostname)
	config.set('JSS_Server', 'jss_url', jss_url)
	config.set('JSS_Server', 'url_api', jss_url+'/JSSResource/')
	config.set('JSS_Server', 'jss_share', jss_share)
	config.set('JSS_Server', 'jss_share_username', jss_share_username)
	config.set('JSS_Server', 'jss_share_password', jss_share_password)
	config.set('JSS_Server', 'api_user', api_user)
	config.set('JSS_Server', 'api_pass', api_pass)
	config.set('JSS_Server', 'jss_category_name', jss_category_name)
	config.set('local_config', 'logs', Software_Repo+'/logs/')
	config.set('Twitter_Auth', 'twitter_app_key', twitter_app_key)
	config.set('Twitter_Auth', 'twitter_app_secret', twitter_app_secret)
	config.set('Twitter_Auth', 'twitter_oauth_token', twitter_oauth_token)
	config.set('Twitter_Auth', 'twitter_oauth_token_secret', twitter_oauth_token_secret)
	config.set('Client_Prototype', 'client_prototype_uuid', client_prototype_uuid)
	config.set('Fab_Config', 'client_prototype_ip', client_prototype_ip)
	config.set('Fab_Config', 'mac_host_ip', mac_host_ip)
	config.set('Fab_Config', 'client_prototype_user', client_prototype_user)
	config.set('Fab_Config', 'client_prototype_pass', client_prototype_pass)
	config.set('Fab_Config', 'client_prototype_vm_file', client_prototype_vm_file)
	config.set('Fab_Config', 'client_prototype_clean_snapshot', client_prototype_clean_snapshot)
	config.set('Fab_Config', 'vmrun_command', vmrun_command)
	with open(Software_Repo+'/conf/JSS_Server.conf', 'wb') as configfile:
		config.write(configfile)

def check_conf():
	''' Using info from conf file, check JSS connection, check API privileges, and check Twitter Auth'''
	logger = logging.getLogger('capd')
	logger.debug("check_conf")
	config = ConfigParser.ConfigParser()
	config.read(Software_Repo+'/conf/JSS_Server.conf')
	
	#### check JSS connection ####
	logger.info("Checking JSS Connection ...")
	try:
		r = requests.get(config.get('JSS_Server', 'jss_url', 0), verify = False)
		logger.info("JSS connection OK")
	except requests.exceptions.RequestException as e:
		logger.error("JSS Server problem with following error: %s", e)
		sys.exit(1)

	#### check API Privileges ####
	logger.info("Checking API Privileges ...")
	api_user_permissions = []
	try:
		url_api = config.get('JSS_Server', 'url_api', 0)
		api_user = config.get('JSS_Server', 'api_user',0)
		api_pass = config.get('JSS_Server', 'api_pass', 0)
		r = requests.get(url_api+'accounts/username/'+api_user, auth = (api_user, api_pass) ,verify = False)
	except requests.exceptions.RequestException as e:
		logger.error("JSS Server problem with following error: %s", e)
		sys.exit(1)
	tree = ET.fromstring(r.content)
	for elem in tree.iterfind('./privileges/jss_objects/'):
		api_user_permissions.append(elem.text)
	if not list(set(api_account_permissions) - set(api_user_permissions)):
		logger.info("API Privilegs OK")
	else:
		logger.error("You appear to be missing the following API privilege(s): %s", list(set(api_account_permissions) - set(api_user_permissions)))
		sys.exit(1)

	#### check Twitter Auth ####
	logger.info("Checking Twitter Auth ...")
	try:
		app_key = config.get('Twitter_Auth', 'twitter_app_key',0)
		if not app_key:
			logger.info("No Twitter App Key provided. Proceeding without the use of Twitter!")
			return
		app_secret = config.get('Twitter_Auth', 'twitter_app_secret', 0)
		oauth_token = config.get('Twitter_Auth', 'twitter_oauth_token',0)
		oauth_token_secret = config.get('Twitter_Auth', 'twitter_oauth_token_secret',0)
		twitter = Twython(app_key, app_secret, oauth_token, oauth_token_secret)
		twitter.get("https://api.twitter.com/1.1/account/verify_credentials.json")
		logger.info("Twitter Auth OK")
	except TwythonError as e:
		logger.error("Check twitter oauth credentials. %s", e)
		sys.exit(1)

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
	if not app_key:
		logger.info("No Twitter app_key. Will not create twitter applist!")
		return
	twitter = Twython(app_key, app_secret, oauth_token, oauth_token_secret)
	n = 0
	tweet_object = twitter.get_user_timeline(screen_name='current_version', count=12)
	for n in range(len(tweet_object)):
		pkg_info = tweet_object[n]['text']
		pkg_list = re.findall(r"\[(.*?)\]",pkg_info)
		if pkg_list[0] == "Mac":
			twitter_applist[pkg_list[1]] = pkg_list[2]
		n += 1

def get_client_prototype_applist(jss_computer_url, api_user, api_pass):
	global client_prototype_applist
	name = []
	version = []
	logger = logging.getLogger('capd')
	logger.debug("get_client_prototype_applist")
	r = requests.get(jss_computer_url, auth = (api_user, api_pass), verify = False)
	tree = ET.fromstring(r.content)
	for elem in tree.iterfind("./software/applications/application/name"):
		name.append(os.path.splitext(elem.text)[0])
	for elem in tree.iterfind("./software/applications/application/version"):
		version.append(elem.text)
	for n, v in zip(name, version):
		client_prototype_applist[n] = v

def compare_lists():
	global updates_applist
	logger = logging.getLogger('capd')
	logger.debug("compare_lists")
	if not twitter_applist:
		logger.info("No twitter credentials provided, so no lists to compare")
		return	
	logger.debug("Client Prototype AppList: %s", client_prototype_applist)
	logger.debug("Twitter AppList: %s", twitter_applist)
	dict_intersection = client_prototype_applist.viewkeys() & twitter_applist.viewkeys()
	if not dict_intersection:
		logger.error("No apps installed on client that match list from twitter")
		exit(0)
	for key in set(client_prototype_applist) & set(twitter_applist):
		if client_prototype_applist[key] == twitter_applist[key]:
			logger.info("App installed is up-to-date: %s %s", key, client_prototype_applist[key])
		elif client_prototype_applist[key] > twitter_applist[key]:
			logger.info ("App installed %s is a newer version %s", key, client_prototype_applist[key])
		else:
			updates_applist[key] = twitter_applist[key]
			logger.info("Installed app: %s %s -------- new version: %s", key, client_prototype_applist[key], twitter_applist[key])
			call_autopkg(key)

def call_autopkg(twitter_applist_pkg):
	logger = logging.getLogger('capd')
	logger.debug("autopkg")
	if os.path.exists("/Library/Autopkg"):
		try:
			check_call(["autopkg", "run", twitter_applist_pkg+".download"])
		except Exception:
			logger.error("Package %s not found in autopkg", twitter_applist_pkg)
			sys.exit(1)
		f = plistlib.readPlist(autopkg_pkg_path_plist_file)
		autopkg_pkg_path = f[0][2]['Output']['pathname']
		call(['mv', autopkg_pkg_path, Software_Repo+'/apps/'])
	else:
		logger.error("Autopkg does not appear to be installed")

def add_pkg_prefix():
	logger = logging.getLogger('capd')
	logger.debug("add_pkg_prefix")
	pkg_prefix = time.strftime("%y%m%d%H%M")+"_"
	pkgs = os.listdir(Software_Repo+"/apps/")
	for pkg in pkgs:
		pkg_name = pkg.split('.')[0]
		pkg_ext = pkg.split('.')[1]
		if not pkg.startswith('.') and not pkg.startswith(pkg_prefix):
			os.rename(Software_Repo+"/apps/"+pkg, Software_Repo+"/apps/"+pkg_prefix+pkg_name+'_'+updates_applist[pkg_name]+'.'+pkg_ext)
			logger.info("Package %s renamed", pkg)

def create_pkg_xml(jss_pkg_id, jss_category_name, pkg_xml, pkg_full_name):
	logger = logging.getLogger('capd')
	logger.debug("create_pkg_xml")
	template = '''<?xml version="1.0" encoding="UTF-8" standalone="no"?>
	<package>
	<id>{jss_pkg_id}</id>
	<name>{pkg_full_name}</name>
	<category>{jss_category_name}</category>
	<filename>{pkg_full_name}</filename>
	<info/>
	<notes/>
	<priority>10</priority>
	<reboot_required>false</reboot_required>
	<fill_user_template>false</fill_user_template>
	<fill_existing_users>false</fill_existing_users>
	<boot_volume_required>false</boot_volume_required>
	<allow_uninstalled>true</allow_uninstalled>
	<os_requirements/>
	<required_processor>None</required_processor>
	<switch_with_package>Do Not Install</switch_with_package>
	<install_if_reported_available>false</install_if_reported_available>
	<reinstall_option>Do Not Reinstall</reinstall_option>
	<triggering_files/>
	<send_notification>false</send_notification>
	</package>
	'''
	context = {
	"jss_pkg_id": jss_pkg_id,
	"pkg_full_name": pkg_full_name,
	"jss_category_name": jss_category_name
	}
	with open(pkg_xml,"w+") as package_xml:
		package_xml.write(template.format(**context))
	logger.info("%s file successfully created", pkg_xml)

def post_pkg(jss_url,jss_category_id, pkg_xml,jss_pkg_url, api_user, api_pass):
	logger = logging.getLogger('capd')
	logger.debug("post_pkg")
	try:
		r = requests.get(jss_url, verify = False)
		logging.debug("JSS status code: %s" ,r.status_code)
	except requests.exceptions.RequestException as e:
		logger.error('Problem connecting to JSS', exc_info=True)
		sys.exit(1)
	xml_file = open(pkg_xml)
	r = requests.post(jss_pkg_url, auth = (api_user, api_pass), data = xml_file, verify = False)
	if r.status_code == 201:
		logger.info("%s successfully posted to Casper Admin", pkg_xml)
	else:
		logger.error("Something wrong with post_package. Status Code: %s %s", r.status_code, r.content)
		sys.exit(1)

def upload_pkg_to_JSS(jss_share,jss_share_username, jss_share_password,jss_hostname,pkg_absolute_path):
	''' If Casper Share not mounted, mount it. Then copy packages to Distribution point'''
	logger = logging.getLogger('capd')
	logging.debug("upload_pkg_to_JSS")
	if not os.path.exists("/Volumes/"+jss_share):
		call(["mkdir", "/Volumes/"+jss_share])
		try:
			check_output(["mount_smbfs", "//"+jss_share_username+":"+jss_share_password+"@"+jss_hostname+"/"+jss_share,"/Volumes/"+jss_share]) #Have to properly encode pass
		except CalledProcessError as e:
			logger.error(e.message)			#Message not descriptive
			sys.exit(1)
		logger.info("%s successfully mounted", jss_share)
	logger.info("Copying %s to JSS distribution point", pkg_absolute_path)
	call(["cp",pkg_absolute_path,'/Volumes/'+jss_share+'/Packages/'])
	logger.info("%s successfully copied to JSS distribution point", pkg_absolute_path)

def create_pol_xml(jss_category_id, jss_category_name, jss_pol_id, jss_pkg_id, pkg_pol_xml, pkg_full_name):
	logger = logging.getLogger('capd')
	logger.debug("create_pol_xml")
	template = '''<?xml version="1.0" encoding="UTF-8" standalone="no"?>
	<policy>
	  <general>
	    <id>{jss_pol_id}</id>
	    <name>{pkg_full_name}</name>
	    <enabled>true</enabled>
	    <trigger>EVENT</trigger>
	    <trigger_checkin>true</trigger_checkin>
	    <trigger_enrollment_complete>false</trigger_enrollment_complete>
	    <trigger_login>false</trigger_login>
	    <trigger_logout>false</trigger_logout>
	    <trigger_network_state_changed>false</trigger_network_state_changed>
	    <trigger_startup>false</trigger_startup>
	    <trigger_other/>
	    <frequency>Once per computer</frequency>
	    <target_drive>default</target_drive>
	    <offline>false</offline>
	    <category>
	      <id>{jss_category_id}</id>
	      <name>{jss_category_name}</name>
	    </category>
	    <date_time_limitations>
	      <activation_date/>
	      <activation_date_epoch>0</activation_date_epoch>
	      <activation_date_utc/>
	      <expiration_date/>
	      <expiration_date_epoch>0</expiration_date_epoch>
	      <expiration_date_utc/>
	      <no_execute_on/>
	      <no_execute_start/>
	      <no_execute_end/>
	    </date_time_limitations>
	    <network_limitations>
	      <minimum_network_connection>No Minimum</minimum_network_connection>
	      <any_ip_address>true</any_ip_address>
	      <network_segments/>
	    </network_limitations>
	    <override_default_settings>
	      <target_drive>default</target_drive>
	      <distribution_point/>
	      <force_afp_smb>false</force_afp_smb>
	      <sus>default</sus>
	      <netboot_server>current</netboot_server>
	    </override_default_settings>
	    <network_requirements>Any</network_requirements>
	    <site>
	      <id>-1</id>
	      <name>None</name>
	    </site>
	  </general>
	  <scope>
	    <all_computers>true</all_computers>
	    <computers/>
	    <computer_groups/>
	    <buildings/>
	    <departments/>
	    <limit_to_users>
	      <user_groups/>
	    </limit_to_users>
	    <limitations>
	      <users/>
	      <user_groups/>
	      <network_segments/>
	    </limitations>
	    <exclusions>
	      <computers/>
	      <computer_groups/>
	      <buildings/>
	      <departments/>
	      <users/>
	      <user_groups/>
	      <network_segments/>
	    </exclusions>
	  </scope>
	  <self_service>
	    <use_for_self_service>false</use_for_self_service>
	    <install_button_text>Install</install_button_text>
	    <self_service_description/>
	    <force_users_to_view_description>false</force_users_to_view_description>
	    <self_service_icon/>
	  </self_service>
	  <package_configuration>
	    <packages>
	      <size>1</size>
	      <package>
	        <id>{jss_pkg_id}</id>
	        <name>{pkg_full_name}</name>
	        <action>Cache</action>
	        <fut>false</fut>
	        <feu>false</feu>
	        <update_autorun>false</update_autorun>
	      </package>
	    </packages>
	  </package_configuration>
	  <scripts>
	    <size>1</size>
	    <script>
      		<id>27</id>
      		<name>install_casper_cache_v5.py</name>
      		<priority>After</priority>
      		<parameter4/>
      		<parameter5/>
      		<parameter6/>
      		<parameter7/>
      		<parameter8/>
      		<parameter9/>
      		<parameter10/>
      		<parameter11/>
	  </script>
	  </scripts>
	  <printers>
	    <size>0</size>
	    <leave_existing_default/>
	  </printers>
	  <dock_items>
	    <size>0</size>
	  </dock_items>
	  <account_maintenance>
	    <accounts>
	      <size>0</size>
	    </accounts>
	    <directory_bindings>
	      <size>0</size>
	    </directory_bindings>
	    <management_account>
	      <action>doNotChange</action>
	    </management_account>
	    <open_firmware_efi_password>
	      <of_mode>none</of_mode>
	      <of_password/>
	    </open_firmware_efi_password>
	  </account_maintenance>
	  <reboot>
	    <message>This computer will restart in 5 minutes. Please save anything you are working on and log out by choosing Log Out from the bottom of the Apple menu.</message>
	    <startup_disk>Current Startup Disk</startup_disk>
	    <specify_startup/>
	    <no_user_logged_in>Restart if a package or update requires it</no_user_logged_in>
	    <user_logged_in>Restart if a package or update requires it</user_logged_in>
	    <minutes_until_reboot>5</minutes_until_reboot>
	  </reboot>
	  <maintenance>
	    <recon>true</recon>
	    <reset_name>false</reset_name>
	    <install_all_cached_packages>false</install_all_cached_packages>
	    <heal>false</heal>
	    <prebindings>false</prebindings>
	    <permissions>false</permissions>
	    <byhost>false</byhost>
	    <system_cache>false</system_cache>
	    <user_cache>false</user_cache>
	    <verify>false</verify>
	  </maintenance>
	  <files_processes>
	    <search_by_path/>
	    <delete_file>false</delete_file>
	    <locate_file/>
	    <update_locate_database>false</update_locate_database>
	    <spotlight_search/>
	    <search_for_process/>
	    <kill_process>false</kill_process>
	    <run_command/>
	  </files_processes>
	  <user_interaction>
	    <message_start/>
	    <allow_users_to_defer>false</allow_users_to_defer>
	    <allow_deferral_until_utc/>
	    <message_finish/>
	  </user_interaction>
	</policy>'''
	context = {
	"jss_pol_id": jss_pol_id,
	"jss_pkg_id": jss_pkg_id,
	"jss_category_id": jss_category_id,
	"jss_category_name": jss_category_name,
	"pkg_full_name": pkg_full_name
	}
	with open(pkg_pol_xml,"w+") as policy_xml:
		policy_xml.write(template.format(**context))
	logger.info("%s file successfully created", pkg_pol_xml)

def post_pol(jss_url,api_user, api_pass, jss_pol_url, pkg_pol_xml):
	logger = logging.getLogger('capd')
	logger.debug("post_pol")
	r = requests.post(jss_pol_url, auth = (api_user, api_pass), data = open(pkg_pol_xml), verify = False)
	if r.status_code == 201:
		logger.info("Policy using %s successfully created", pkg_pol_xml)
	else:
		logger.error("Something wrong with post_pol. Status Code: %s %s", r.status_code, r.content)
		sys.exit(1)

def mv_pkg_to_apps():
	logger = logging.getLogger('capd')
	logger.debug("mv_pkg_to_apps")
	pkgs = os.listdir(Software_Repo)
	for pkg in pkgs:
		if pkg.lower().endswith(('.zip','.pkg','.mpkg','.app','.dmg')):
			shutil.move(Software_Repo+"/"+pkg, Software_Repo+"/apps")
			logger.info("Moved %s to apps folder", pkg)

def mv_pkg_to_sequenced():
	logger = logging.getLogger('capd')
	logger.debug("mv_pkg_to_sequenced")
	pkgs = os.listdir(Software_Repo+"/apps/")
	for pkg in pkgs:
		if pkg.lower().endswith(('.zip','.pkg','.mpkg','.app','.dmg','.xml')):
			print pkg
			shutil.move(Software_Repo+"/apps/"+pkg, Software_Repo+"/sequenced")
			logger.info("Moved %s to sequenced folder", pkg)

def call_fabfile(pkg_name):
	#execute(revert_snapshot_vm)
	execute(start_vm)
	time.sleep(60)
	execute(check_policy)
	time.sleep(60)
	execute(run_app,pkg_name)
	time.sleep(10)
	execute(is_running, pkg_name)
	execute(screencapture,pkg_name)
	execute(send_screencapture,pkg_name)
	time.sleep(10)

def main():
	get_info()
	check_conf() 
	mv_pkg_to_apps()
	cs = JSS()
	create_twitter_applist()
	get_client_prototype_applist(cs.jss_computer_url(), cs.api_user, cs.api_pass)
	compare_lists()
	add_pkg_prefix()
	packages = os.listdir(Software_Repo+"/apps")
	for pkg in packages:
		if not pkg.startswith('.') or pkg.endswith('.xml'):
			p = Package()
			p.name = os.path.splitext(pkg)[0]
			p.extension = os.path.splitext(pkg)[1]
			create_pkg_xml(cs.jss_pkg_id(),cs.category_name, p.pkg_xml(),p.full_name())
			post_pkg(cs.url,cs.jss_category_id(),p.pkg_xml(),cs.jss_pkg_url(),cs.api_user,cs.api_pass)
			upload_pkg_to_JSS(cs.share,cs.share_username, cs.share_password,cs.hostname,p.absolute_path())
			create_pol_xml(cs.jss_category_id(), cs.category_name, cs.jss_pol_id(), cs.jss_pkg_id(), p.pol_xml(), p.full_name())
			post_pol(cs.url, cs.api_user, cs.api_pass, cs.jss_pol_url(), p.pol_xml(),)
			pkg_name = p.name.split("_")[1]
			call_fabfile(pkg_name)
	mv_pkg_to_sequenced()

if __name__ == "__main__":
	main()

