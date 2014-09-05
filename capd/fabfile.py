# Copyright 2013 Sar Haidar, Massachusetts Institute of Technology, All Rights Reserved.

'''
Workflow:
Using mac_host, revert client_prototype to snapshot.
Using mac_host, start client_prototype.
Using client_prototype, list_pre_apps
Using client_prototype, check_policy
Using client_prototype, list_post_apps
Using client_prototype, diff_pre_post
Using client_prototype, run_app
Using client_prototype, is_running
Using client_prototype, screencapture
Using client_prototype, send_screencapture
'''
import ConfigParser
import logging
import os
from fabric.api import *
from fabric.tasks import execute
from fabric.network import disconnect_all
from fabric.context_managers import settings

'''
Requirements
- For run_app method, the user needs to be logged in to the GUI otherwise it would fail
- mac_host and client_prototype have to have the same account name and password
- mac_host and client_prototype have to have ssh enabled so that fabric can connect
- client_prototype needs to be configured to auto-login
'''

Software_Repo = os.environ['HOME']+"/Documents/capd"
config = ConfigParser.ConfigParser()
config.read(Software_Repo+'/conf/JSS_Server.conf')

env.roledefs = {
	'mac_host': [config.get('Fab_Config','mac_host_ip',0)],
	'client_prototype': [config.get('Fab_Config','client_prototype_ip',0)]
}

env.user = config.get('Fab_Config','client_prototype_user',0)
env.password = config.get('Fab_Config','client_prototype_pass',0)
logs = config.get('local_config', 'logs',0)
vm_file = config.get('Fab_Config','client_prototype_vm_file',0)
vmrun = config.get('Fab_Config','vmrun_command',0)
client_prototype_clean_snapshot = config.get('Fab_Config', 'client_prototype_clean_snapshot', 0)

@roles('client_prototype')
def check_policy():
	sudo("jamf policy")

@roles('client_prototype')
def run_app():
	# Don't want program to terminate in case it couldn't launch app. Cisco VPN when installed is a folder
	# instead of a .app, so this would've failed eventhough it was deployed by Casper.
	with settings(warn_only=True):
		pkg_name = run('cat /Users/adm/Documents/new_app.txt')
		run("open -a '%s'" % pkg_name)

@roles('client_prototype')
def is_running():
	# Don't want program to terminate in case it couldn't launch app. Cisco VPN when installed is a folder
	# instead of a .app, so this would've failed eventhough it was deployed by Casper.
	with settings(warn_only=True):	
		pkg_name = run('cat /Users/adm/Documents/new_app.txt')
		run ("ps x |grep '%s' |grep -v grep" % pkg_name)

@roles('client_prototype')
def screencapture(pkg_name):
	run ("screencapture '%s.jpg'" % pkg_name)

@roles('client_prototype')
def send_screencapture(pkg_name):
	get('%s.jpg' % pkg_name, logs+'/screenshots/')
	disconnect_all()

@roles('mac_host')
def start_vm():
	run("%s -T fusion start %s" % (vmrun, vm_file))

@roles('mac_host')
def stop_vm():
	run("%s -T fusion stop %s" % (vmrun, vm_file))

@roles('mac_host')
def revert_snapshot_vm():
	run("%s -T fusion revertToSnapshot %s %s" % (vmrun, vm_file, client_prototype_clean_snapshot))
