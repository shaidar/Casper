#! /usr/bin/env python

import ConfigParser
import logging
import requests
import os
import shutil
import sys
import time
from subprocess import call, check_output, check_call, CalledProcessError
import capd
import mail
from fabfile import *

# Global Variables
Software_Repo = os.environ['HOME']+"/Documents/capd"

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
	with open(pkg_xml, "w+") as package_xml:
		package_xml.write(template.format(**context))
	logger.info("[+] %s file successfully created", pkg_xml)

def post_pkg(jss_url, jss_category_id, pkg_xml, jss_pkg_url, api_user, api_pass):
	logger = logging.getLogger('capd')
	logger.debug("post_pkg")
	try:
		r = requests.get(jss_url, verify=False)
		logging.debug("JSS status code: %s", r.status_code)
	except requests.exceptions.RequestException as e:
		logger.error('[-] Problem connecting to JSS', exc_info=True)
		sys.exit(1)
	xml_file = open(pkg_xml)
	r = requests.post(jss_pkg_url, auth=(api_user, api_pass), data=xml_file, verify=False)
	if r.status_code == 201:
		logger.info("[+] %s successfully posted to Casper Admin", pkg_xml)
	else:
		logger.error("[-] Something wrong with post_package. Status Code: %s %s", r.status_code, r.content)
		sys.exit(1)

def upload_pkg_to_JSS(jss_share, jss_share_username, jss_share_password, jss_hostname, pkg_absolute_path):
	''' If Casper Share not mounted, mount it. Then copy packages to Distribution point'''
	logger = logging.getLogger('capd')
	logging.debug("upload_pkg_to_JSS")
	if not os.path.exists("/Volumes/"+jss_share):
		call(["mkdir", "/Volumes/"+jss_share])
		try:
			# Change this to os.system because of win test account - this works for Casper Dev
			#check_output(["mount_smbfs", "//"+jss_share_username+":"+jss_share_password+"@"+jss_hostname+"/"+jss_share, "/Volumes/"+jss_share]) #Have to properly encode pass
			# For Casper Test
			os.system("mount_smbfs //'"+jss_share_username+":"+jss_share_password+"'@"+jss_hostname+"/"+jss_share+" /Volumes/"+jss_share)
		except CalledProcessError as e:
			logger.error(e.message)			#Message not descriptive
			sys.exit(1)
		logger.info("[+] %s successfully mounted", jss_share)
	logger.info("[+] Copying %s to JSS distribution point", pkg_absolute_path)
	try:
		call(["cp", pkg_absolute_path, '/Volumes/'+jss_share+'/Packages/'])
	except CalledProcessError as e:
		logger.error(e.message)
		sys.exit(1)
	logger.info("[+] %s successfully copied to JSS distribution point", pkg_absolute_path)

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
      		<id>37</id>
      		<name>install_casper_cache.py</name>
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
	with open(pkg_pol_xml, "w+") as policy_xml:
		policy_xml.write(template.format(**context))
	logger.info("[+] %s file successfully created", pkg_pol_xml)

def post_pol(jss_url, api_user, api_pass, jss_pol_url, pkg_pol_xml):
	logger = logging.getLogger('capd')
	logger.debug("post_pol")
	r = requests.post(jss_pol_url, auth=(api_user, api_pass), data=open(pkg_pol_xml), verify=False)
	if r.status_code == 201:
		logger.info("[+] Policy using %s successfully created", pkg_pol_xml)
	else:
		logger.error("[-] Something wrong with post_pol. Status Code: %s %s", r.status_code, r.content)
		sys.exit(1)

def mv_pkg_to_sequenced():
	logger = logging.getLogger('capd')
	logger.debug("mv_pkg_to_sequenced")
	pkgs = os.listdir(Software_Repo+"/apps/")
	for pkg in pkgs:
		if pkg.lower().endswith(('.zip', '.pkg', '.mpkg', '.app', '.dmg', '.xml')):
			shutil.move(Software_Repo+"/apps/"+pkg, Software_Repo+"/sequenced")
			logger.info("[+] Moved %s to sequenced folder", pkg)

def run_all():
	packages = os.listdir(Software_Repo+"/apps")
	cs = capd.JSS()
	for pkg in packages:
		if not pkg.startswith('.') or pkg.endswith('.xml'):
			p = capd.Package()
			p.name = os.path.splitext(pkg)[0]
			p.extension = os.path.splitext(pkg)[1]
			create_pkg_xml(cs.jss_pkg_id(), cs.category_name, p.pkg_xml(), p.full_name())
			post_pkg(cs.url, cs.jss_category_id(), p.pkg_xml(), cs.jss_pkg_url(), cs.api_user, cs.api_pass)
			upload_pkg_to_JSS(cs.share, cs.share_username, cs.share_password, cs.hostname, p.absolute_path())
			create_pol_xml(cs.jss_category_id(), cs.category_name, cs.jss_pol_id(), cs.jss_pkg_id(), p.pol_xml(), p.full_name())
			post_pol(cs.url, cs.api_user, cs.api_pass, cs.jss_pol_url(), p.pol_xml(),)
			pkg_name = p.name.split("_")[1]
			capd.call_fabfile(pkg_name)
			mail.notify(p.full_name())
	mv_pkg_to_sequenced()

def main():
	run_all()

if __name__ == '__main__':
	main()