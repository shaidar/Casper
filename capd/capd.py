#!/usr/bin/env python

import argparse
import ConfigParser
import logging
import os
import requests
import shutil
import sys
import time
import xml.etree.ElementTree as ET
from fabfile import *
import external_apps, internal_apps, check_conf, jss_upload


# Global Variables
Software_Repo = os.environ['HOME']+"/Documents/capd"
headers = {'content-type':'application/xml', 'accept':'application/xml'}

class Package(object):
	"All package attributes"
	def __init__(self, name=None, version=None, extension=None, prefix=None):
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

	def prefix(self):
		return time.strftime("%y%m%d%H%M")+"_"

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
		'''Append existing JSS pkg_id's to a list and find an unused value'''
		jss_pkg_id_list = []
		r = requests.get(self.api_url+"packages", auth=(self.api_user, self.api_pass), verify=False, headers=headers)
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
		r = requests.get(self.api_url+"policies", auth=(self.api_user, self.api_pass), verify=False, headers=headers)
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
		r = requests.get(self.api_url+"categories", auth=(self.api_user, self.api_pass), verify=False, headers=headers)
		tree = ET.fromstring(r.content)
		for number, name in tree.findall("./category"):
			jss_category_name_dict[name.text] = number.text
		if self.category_name in jss_category_name_dict:
			category_id = jss_category_name_dict[self.category_name]
		else:
			r = requests.get(self.api_url+"categories", auth=(self.api_user, self.api_pass), verify=False, headers=headers)
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
			with open(Software_Repo+"/conf/category.xml", "w+") as category_xml:
				category_xml.write(template.format(**context))
				r = requests.post(self.api_url+"categories/id/"+str(category_id), auth=(self.api_user, self.api_pass), data=category_xml, verify=False)
		return category_id

def create_capd_folders():
	if not os.path.exists(Software_Repo):
		os.mkdir(Software_Repo)
	if os.path.exists(Software_Repo):
		if not os.path.exists(Software_Repo+"/logs"):
			os.mkdir(Software_Repo+"/logs")
		if not os.path.exists(Software_Repo+"/logs/screenshots"):
			os.mkdir(Software_Repo+"/logs/screenshots")
		if not os.path.exists(Software_Repo+"/apps"):
			os.mkdir(Software_Repo+"/apps")
		if not os.path.exists(Software_Repo+"/internal_apps"):
			os.mkdir(Software_Repo+"/internal_apps")
		if not os.path.exists(Software_Repo+"/cert"):
			os.mkdir(Software_Repo+"/cert")
		if not os.path.exists(Software_Repo+"/conf"):
			os.mkdir(Software_Repo+"/conf")
		if not os.path.exists(Software_Repo+"/sequenced"):
			os.mkdir(Software_Repo+"/sequenced")

def init_logging():
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

def create_conf(args):
	logger = logging.getLogger('capd')
	logger.debug("create_conf")
	cfg_file = os.listdir(Software_Repo+"/conf")
	if "JSS_Server.conf" in cfg_file:
		use_overwrite = raw_input("Config file already exists! Would you like to use it or overwrite it? U(se) O(verwrite): ")
		if use_overwrite == 'U':
			logger.info("[+] Using existing config file")
			sys.exit("Done")
		elif use_overwrite == 'O':
			logger.info("[+] Overwriting config file")
			generate_conf_file()
		else:
			logger.error("[-] Wrong choice! Exiting!")
			sys.exit("[-] Wrong choice! Exiting!")
	else:
		generate_conf_file()

def generate_conf_file():
	logger = logging.getLogger('capd')
	logger.debug("generate_conf_file")
	jss_hostname = raw_input("JSS hostname: ")
	jss_url = raw_input("Full JSS URL and port number (ex. https://myjss.example.com:8443): ")
	jss_share = raw_input("Casper share name (ex. /Volumes/CasperShare/Packages/): ")
	jss_share_username = raw_input("Casper username with read/write access to share: ")
	jss_share_password = raw_input("Casper password for username with read/write access to share: ")
	api_user = raw_input("Account username with API priviliges: ")
	api_pass = raw_input("Password of API account: ")
	jss_category_name = raw_input("JSS Category name to use for packages and policy: ")
	internal_apps_cert = raw_input("Full name including path of cert to download internal apps: ")
	internal_apps_cert_key = raw_input("Full name including path of cert key to download internal apps: ")
	internal_apps_repo = raw_input("Path for internal app repo: ")
	external_apps_list = raw_input("List names of external/freeware apps that you'd like to keep up to date (ex. Firefox: ")
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
	vmrun_command = raw_input("Path to vmrun command (ex. VMware Fusion path by default is /Applications/VMware Fusion.app/Contents/Libray/vmrun): ")
	mailserver = raw_input("Enter mailserver fqdn for email notification: ")
	sender = raw_input("Enter the sender's email address: ")
	receiver = raw_input("Enter the receiver's email address: ")
	config = ConfigParser.RawConfigParser()
	config.add_section('JSS_Server')
	config.add_section('local_config')
	config.add_section('Internal_Apps')
	config.add_section('External_Apps')
	config.add_section('Twitter_Auth')
	config.add_section('Client_Prototype')
	config.add_section('Fab_Config')
	config.add_section('Mail')
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
	config.set('local_config', 'screenshots', Software_Repo+'/logs/screenshots/')
	config.set('Internal_Apps', 'internal_apps_cert', Software_Repo+'/cert/'+internal_apps_cert)
	config.set('Internal_Apps', 'internal_apps_cert_key', Software_Repo+'/cert/'+internal_apps_cert_key)
	config.set('Internal_Apps', 'internal_apps_repo', Software_Repo+'/internal_apps/')
	config.set('External_Apps', 'external_apps_list', external_apps_list)
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
	config.set('Mail', 'mailserver', mailserver)
	config.set('Mail', 'sender', sender)
	config.set('Mail', 'receiver', receiver)
	with open(Software_Repo+'/conf/JSS_Server.conf', 'wb') as configfile:
		config.write(configfile)

def mv_pkg_to_apps():
	logger = logging.getLogger('capd')
	logger.debug("mv_pkg_to_apps")
	pkgs = os.listdir(Software_Repo)
	for pkg in pkgs:
		if pkg.lower().endswith(('.zip', '.pkg', '.mpkg', '.app', '.dmg')):
			shutil.move(Software_Repo+"/"+pkg, Software_Repo+"/apps")
			logger.info("[+] Moved %s to apps folder", pkg)

def call_fabfile(pkg_name):
	execute(revert_snapshot_vm)
	execute(start_vm)
	time.sleep(60)
	execute(check_policy)
	time.sleep(60)
	execute(run_app)
	time.sleep(10)
	execute(is_running)
	execute(screencapture, pkg_name)
	execute(send_screencapture, pkg_name)
	time.sleep(10)

def banner():
	print "\n#####################################################"
	print "\tcapd - cASPER aUTOMATED pACKAGE dEPLOYMENT"
	print "#####################################################\n"
	print "\t    \t    \t    \t   #"
	print "\t   \t    \t    \t   #"
	print "\t####\t####\t####\t####"
	print "\t#   \t#  #\t#  #\t#  #"
	print "\t#   \t#  #\t#  #\t#  #"
	print "\t####\t######\t####\t####"
	print "\t    \t     \t#"
	print "\t    \t     \t#\n"
	print "#####################################################\n"

def update_external_apps(args):
	check_conf.check_conf(True)
	cs = JSS()
	external_apps.create_twitter_applist()
	external_apps.compare_lists()
	external_apps.add_pkg_prefix()
	jss_upload.run_all()

def update_internal_apps(args):
	''' Download internal apps and run checksum. If checksum match, exit, otherwise upload to JSS '''
	check_conf.check_conf(True)
	internal_apps.download_internal_apps()
	internal_apps.compare_app_checksum()
	pkgs = os.listdir(Software_Repo+'/internal_apps/')
	for pkg in pkgs:
		if pkg.lower().endswith(('.zip', '.pkg', '.mpkg', '.app', '.dmg')):
			shutil.move(Software_Repo+"/internal_apps/"+pkg, Software_Repo+"/apps")
	internal_apps.add_pkg_prefix()
	jss_upload.run_all()

def update_all_apps(args):
	check_conf.check_conf(True)
	cs = JSS()
	external_apps.create_twitter_applist()
	external_apps.compare_lists()
	internal_apps.download_internal_apps()
	internal_apps.compare_app_checksum()
	pkgs = os.listdir(Software_Repo+'/internal_apps/')
	for pkg in pkgs:
		if pkg.lower().endswith(('.zip', '.pkg', '.mpkg', '.app', '.dmg')):
			shutil.move(Software_Repo+"/internal_apps/"+pkg, Software_Repo+"/apps")
	internal_apps.add_pkg_prefix()
	jss_upload.run_all()


def main():
	banner()
	create_capd_folders()
	init_logging()
	if "JSS_Server.conf" not in os.listdir(Software_Repo+"/conf"):
		print "Config File not found!"
		print "Running 'capd.py create_conf' to create config file and all required folders\n"
		create_conf(True)
	
	# create the top-level parser
	parser = argparse.ArgumentParser()
	subparsers = parser.add_subparsers(title='subcommands', description='valid commands', help='additional help')

	# parser for create_conf
	parser_create_conf = subparsers.add_parser('create_conf', help='create config file')
	parser_create_conf.set_defaults(func=create_conf)

	#parser for check_conf 
	parser_check_conf = subparsers.add_parser('check_conf', help='test config file values')
	parser_check_conf.set_defaults(func=check_conf.check_conf)

	#parser for update_external_apps
	parser_check_conf = subparsers.add_parser('update_external_apps', help='update all external apps (ie freeware')
	parser_check_conf.set_defaults(func=update_external_apps)

	#parser for update_internal_apps
	parser_check_conf = subparsers.add_parser('update_internal_apps', help='update all internal apps')
	parser_check_conf.set_defaults(func=update_internal_apps)

	#parser for update_all_apps
	parser_check_conf = subparsers.add_parser('update_all_apps', help='update all apps')
	parser_check_conf.set_defaults(func=update_all_apps)

	args = parser.parse_args()
	args.func(args)


if __name__ == "__main__":
	main()

