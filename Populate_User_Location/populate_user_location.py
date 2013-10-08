#!/usr/bin/env python

#	Copyright 2013 Sar Haidar

#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

#	Possible future enhancements
# 	If cert username matches what's in generated xml file, no need to query or update, just exit.
#	Check JSS connection before running script
#	If username matches what's in JSS, don't upload xml
#	Replace os.popen with subprocess
#	Send email when a sys.ext error is encountered


import urllib2, re, os, sys
from subprocess import call

#Global variables
#Keep blank
UNAME = ""
name = ""
department = ""

#Replace with your own values
JSS_API = "https://localhost:8443/JSSResource/computers/name/"	#Change hostname
WP = "http://"		#URL for white pages username query
ldap_server = " "	#example ldap.example.com
ldap_searchbase = ""	#example ou=users,ou=people,dc=exmaple,dc=com
domain_name = "" #example google.com
casper_api_user = ""	#Casper API account that has 'update' computer privileges in JSS
casper_api_password = ""

def identify_uname():
	'''
	Get username or full name by searching through Mail.app or Tivoli Storage Manager nodename. 
	'''
	global UNAME
	UNAME = (os.popen('defaults read com.apple.mail MailSections |grep %s |grep -o "\w*@" |sed s/@//' % domain_name).read()).rstrip()
	if UNAME == "":
		UNAME = (os.popen("cat /Library/Preferences/Tivoli\ Storage\ Manager/dsm.sys |grep NODENAME |sed -n 's/^NODENAME //p'").read()).rstrip()
		if UNAME == "":
			sys.exit("Error - identify_uname - UNAME not available")
	print "identify_uname - get-identity-preference - UNAME: ", UNAME
	return UNAME

def ldap_query(uname):
	global name, department
	outfile = open("/tmp/casper_ldap.txt","w")
	if ' ' in UNAME:
		call(['ldapsearch','-LLL','-x','-h',ldap_server,'-b',ldap_searchbase,'displayName='+UNAME],stdout=outfile)
	else: 
		call(['ldapsearch','-LLL','-x','-h',ldap_server,'-b',ldap_searchbase,'uid='+UNAME],stdout=outfile) 
	outfile.close()	
	outfile = open("/tmp/casper_ldap.txt","r")
	if os.stat("/tmp/casper_ldap.txt").st_size == 0:
		print "ldapsearch did not work. Moving to wp_query"
		return wp_query(UNAME)
	ldap_file = outfile.read()
	username = re.findall(r'uid:(.*)',ldap_file)
	print "ldap_query - username: ", username
	name = re.findall(r'displayName:(.*)',ldap_file)
	print "ldap_query - name: ", name
	email = re.findall(r'mail:(.*)',ldap_file)
	print "ldap_query - email: ", email
	phone = re.findall(r'telephoneNumber:(.*)',ldap_file)
	print "ldap_query - phone: ", phone
	title = re.findall(r'title:(.*)',ldap_file)
	title = [t.replace('&','&amp;') for t in title]
	print "ldap_query - title: ", title
	department = re.findall(r'ou:(.*)',ldap_file)
	department = [d.replace('&','&amp;') for d in department]
	print "ldap_query - department: ", department
	room = re.findall(r'roomNumber:(.*)',ldap_file)
	print "ldap_query - room: ", room
	print "ldap_query - casper_ldap.txt closed"
	generate_xml(username,name,email,phone,title,department,room)

def wp_query(uname): 
	global name, department
	wp_url = urllib2.Request(WP + UNAME)
	try:
		wp_html = urllib2.urlopen(wp_url).read()
	except urllib2.URLError as e:
		sys.exit("Error - Can't access whitepages")
	name = re.findall(r'name:(.*)',wp_html)
	if not name:
		print "Could not find [", uname, "] in wp"
		sys.exit("Error - wp query failed") 
	else:
		print "wp_query - name: ", name
		username = [UNAME]
		print "wp_query - username: ", username
		email = [UNAME + "@mit.edu"]
		print "wp_query - email: ", email
		phone = re.findall(r'phone:(.*)',wp_html)
		print "wp_query - phone: ", phone
		title = re.findall(r'title:(.*)',wp_html)
		title = [t.replace('&','&amp;') for t in title]				#Check for ampersand and replace with &amp cause & is reserved char in xml
		print "wp_query - title: ", title
		department = re.findall(r'department:(.*)',wp_html)
		department = [d.replace('&','&amp;') for d in department]	#Check for ampersand and replace with &amp cause & is reserved char in xml
		print "wp_query - department: ", department
		room = re.findall(r'address:(.*)',wp_html)
		print "wp_query - room: ", room
		print "wp_query complete"
		generate_xml(username,name,email,phone,title,department,room)

def generate_xml(username,name,email,phone,title,department,room):
	casper_xml = open("/tmp/casper_xml.xml","w")
	casper_xml.write('<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n')
	casper_xml.write('<computer>\n<location>\n\t<username>')
	casper_xml.write(username[0])
	casper_xml.write('</username>\n')
	casper_xml.write('\t<real_name>')
	casper_xml.write(name[0])
	casper_xml.write('</real_name>\n\t<email_address>')
	casper_xml.write(email[0])
	casper_xml.write('</email_address>\n\t<phone>')
	casper_xml.write(phone[0])
	casper_xml.write('</phone>\n\t<position>')
	casper_xml.write(title[0])
	casper_xml.write('</position>\n\t<department>')
	casper_xml.write(department[0])
	casper_xml.write('</department>\n\t<room>')
	casper_xml.write(room[0])
	casper_xml.write('</room>\n</location>\n</computer>')
	casper_xml.close()
	print "generate_xml - casper_xml done"

def get_compname():
	computer_name = (os.popen("jamf getComputerName |grep -o '>.*<' |sed 's/>//g' | sed 's/<//g'")).read().rstrip()
	computer_name = computer_name.replace(" ", "%20")  # Space
	computer_name = computer_name.replace("(", "%28")  # Opening Parenthesis
	computer_name = computer_name.replace(")", "%29")  # Closing Parenthesis
	computer_name = computer_name.replace(".", "%2E")  # Stop
	print "get_compname - Computer Name: ",computer_name
	return computer_name

def update_record(computer_name,casper_xml):	#Using urllib2 instead of curl
	xml_file = open(casper_xml, "r").read()
	upload_url = JSS_API + str(computer_name)
	password_mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
	password_mgr.add_password(None, upload_url, casper_api_user, casper_api_password)
	handler = urllib2.HTTPBasicAuthHandler(password_mgr)
	opener = urllib2.build_opener(urllib2.HTTPHandler,handler)
	req = urllib2.Request(upload_url, xml_file)
	req.add_header ('Content-Type','text/xml')
	req.get_method = lambda: 'PUT'
	try:
		f = opener.open(req)
	except urllib2.HTTPError as e:
		if e.code == 409:
			print "Error - update_record - This department doesn't appear to be in JSS"
		else:
			pass

if __name__ == "__main__":
	UNAME = identify_uname()
	ldap_query(UNAME)
	computer_name = get_compname()
	update_record (computer_name, "/tmp/casper_xml.xml")
