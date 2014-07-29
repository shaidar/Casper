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
import argparse
import ConfigParser
import logging
from fabric.api import *
from fabric.tasks import execute
from fabric.network import disconnect_all
from fabric.context_managers import settings

'''
Requirements
For run_app method, the user needs to be logged in to the GUI otherwise it would fail
'''
parser = argparse.ArgumentParser()
parser.add_argument("software_repository", help = "Full local path where the installers are located. example: /Users/joe/Documents/Apps/ ")
args = parser.parse_args()
Software_Repo = args.software_repository
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
def run_app(pkg_name):
	run("open -a '%s'" % pkg_name)

@roles('client_prototype')
def is_running(pkg_name):
	run ("ps x |grep '%s' |grep -v grep" % pkg_name)

@roles('client_prototype')
def screencapture(pkg_name):
	run ("screencapture '%s.jpg'" % pkg_name)

@roles('client_prototype')
def send_screencapture(pkg_name):
	get('%s.jpg' % pkg_name, logs)
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
