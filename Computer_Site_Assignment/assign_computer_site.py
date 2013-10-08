#!/usr/bin/env python
'''
Copyright 2013 Sar Haidar

Licensed under the Apache License, Version 2.0 (the "License");
You may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
'''			

import requests

#API account needs to have Read and Update on Computer Object
api_user = ""  
api_pass = ""

#Plugin your servername and port here
url_computers = "https://servername:port/JSSResource/computers"
url_id = "https://servername:port/JSSResource/computers/id/"
url_sites = "https://servername:port/JSSResource/sites"
subset_id = "/subset/General&Location"

headers = {'content-type':'application/json', 'accept':'application/json'}
sites_list = requests.get(url_sites,auth=(api_user,api_pass), verify=False, headers=headers)
computers_list = requests.get(url_computers, auth=(api_user,api_pass), verify=False, headers = headers)

i = 0
while i < len(computers_list.json()['computers']['computer']):
	computer_id = computers_list.json()['computers']['computer'][i]['id']
	computer_info = requests.get(url_id+str(computer_id)+subset_id, auth=(api_user,api_pass), verify=False, headers = headers) 
	if not computer_info.json()['computer']['location']['department']:
		print "No department"
	else:
		if computer_info.json()['computer']['location']['department'] == computer_info.json()['computer']['general']['site']['name']:
			print "Site name is the same as Dept name"
		else:
			site_xml = open('/pathtofile/site.xml','w+') #Change PathToFile
			site_name = computer_info.json()['computer']['location']['department']
			if '&' in site_name:
				site_name = site_name.replace('&','&amp;')
			site_xml.write('<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n')
			site_xml.write('<computer>\n<general>\n<site>\n\t<name>')
			site_xml.write(site_name+'</name>\n</site>\n</general>\n</computer>')
			site_xml.close()
			site_xml = open('/pathtofile/site.xml','r') #Change PathToFile
			requests.put(url_id+str(computer_id),data=site_xml,auth=(api_user,api_pass), verify=False)
	i += 1