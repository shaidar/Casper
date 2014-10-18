#!/usr/bin/env python

'''
Copyright 2013 Sar Haidar, Massachusetts Institute of Technology, All Rights Reserved.
'''


import re
import requests
import time
from bs4 import BeautifulSoup
from twython import Twython

# twitter_oauth is a .py file that u need to specify values for twitter app_key, app_secret, oauth_token, and oauth_token_secret
from twitter_oauth import app_key, app_secret, oauth_token, oauth_token_secret

# Global Variables
twitter = Twython(app_key, app_secret, oauth_token, oauth_token_secret)
mac_user_agent = {'User-agent': 'Mozilla/5.0 (Macintosh)'}
win_user_agent = {'User-agent': 'Mozilla/5.0 (compatible; MSIE 10.0; Windows NT 6.1; WOW64; Trident/6.0)'}
exact_time = time.strftime("%m%d%y%H%M")
new_mac_user_agent = {'User-agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/28.0.1500.71 Safari/537.36'}

# Functions to get versions of different software

def get_Adium_ver():
	name = 'Adium'
	mac_link = requests.get("https://adium.im")
	mac_soup = BeautifulSoup(mac_link.text)
	mac_version = re.findall('Adium (.+)<',str(mac_soup.find('span', {'class':'downloadlink'})))
	update_mac_twitter_status(name, mac_version[0])

def get_Adober_Reader_ver():
 	name = 'Adobe_Reader'
	win_link = requests.get("http://get.adobe.com/reader/", headers = win_user_agent)
	win_soup = BeautifulSoup(win_link.text)
	win_version = re.findall('\((.+)\)',str(win_soup.find(id='AUTO_ID_columnleft_p_version')))
	update_win_twitter_status(name, win_version[0])

def get_Adobe_Flash_ver():
	name = 'Adobe Flash'
	win_link = requests.get("http://get.adobe.com/flashplayer/", headers = win_user_agent)
	win_soup = BeautifulSoup(win_link.text)
	win_version = re.findall('Version (.*?)<',str(win_soup.find(id='AUTO_ID_columnleft_p_version')))
	update_win_twitter_status(name, win_version[0])

def get_Casper_ver():
	name = 'Casper'
	mac_link = requests.get("https://jamfnation.jamfsoftware.com/viewProduct.html?id=1&view=info", headers = mac_user_agent)
	mac_soup = BeautifulSoup(mac_link.text)
	mac_version = re.findall('Current Version: </strong>(.*?)<',str(mac_soup.find(id='infoPane')))
	update_mac_twitter_status(name, mac_version[0])

def get_Dropbox_ver():
	name = 'Dropbox'
	mac_link = requests.get("https://www.dropbox.com/install2", headers = mac_user_agent)
	mac_soup = BeautifulSoup(mac_link.text)
	mac_version = re.findall('>(.+) for',str(mac_soup.find_all(id="version_str")))
	win_link = requests.get("https://www.dropbox.com/install2", headers = win_user_agent)
	win_soup = BeautifulSoup(win_link.text)
	win_version = re.findall('>(.+) for',str(win_soup.find_all(id="version_str")))
	update_mac_twitter_status(name, mac_version[0])
	update_win_twitter_status(name, win_version[0])

def get_Firefox_ESR_ver():
	name = 'Firefox'
	mac_link = requests.get("http://www.mozilla.org/en-US/firefox/organizations/all.html", headers = mac_user_agent)
	mac_soup = BeautifulSoup(mac_link.text)
	mac_version = re.findall('-(.*?)esr',str(mac_soup.select('a[href*="os=osx&lang=en-US"]')))
	win_version = re.findall('-(.*?)esr',str(mac_soup.select('a[href*="os=win&lang=en-US"]')))
	update_mac_twitter_status(name, mac_version[0])
	update_win_twitter_status(name, win_version[0])

def get_Java_ver():
	name = 'Java'
	mac_link = requests.get("http://www.java.com/en/download/mac_download.jsp?locale=en", headers = new_mac_user_agent)
	mac_soup = BeautifulSoup(mac_link.text)
	mac_version = re.findall('Recommended Version (.+) \(filesize:',str(mac_soup.findAll('b')))
	update_mac_twitter_status(name, mac_version[0])

def get_Office_2011_ver():
	name = 'Office_2011'
	mac_link = requests.get("http://www.microsoft.com/mac/downloads", headers = mac_user_agent)
	mac_soup = BeautifulSoup(mac_link.text)
	temp = re.findall('Mac 2011 (.*?)<',str(mac_soup.find('a', {'class': 'download_link'})))
	mac_version = temp[0].replace('\xc2\xa0','')
	update_mac_twitter_status(name, mac_version)

def get_TextWrangler_ver():
	name = 'TextWrangler'
	mac_link = requests.get("http://www.barebones.com/products/textwrangler/download.html", headers = mac_user_agent)
	mac_soup = BeautifulSoup(mac_link.text)
	mac_version = re.findall('r (.*?)<',str(mac_soup.find_all('h3')))
	update_mac_twitter_status(name, mac_version[0])

def get_VLC_ver():
	name = 'VLC'
	mac_link = requests.get("http://www.videolan.org/vlc/download-macosx.html", headers = mac_user_agent)
	mac_soup = BeautifulSoup(mac_link.text)
	mac_version = re.findall('X (.*?)<',str(mac_soup.find('span', {'class':'downloadText'})))
	win_link = requests.get("http://www.videolan.org/vlc/download-macosx.html", headers = win_user_agent)
	win_soup = BeautifulSoup(win_link.text)
	win_version = re.findall('X (.*?)<',str(win_soup.find('span', {'class':'downloadText'})))
	update_mac_twitter_status(name, mac_version[0])
	update_win_twitter_status(name, win_version[0])

# Two functions that post software version to twitter
def update_mac_twitter_status(name, version):
	twitter.update_status(status='%s [Mac], [%s], [%s]' %(exact_time,name, version))

def update_win_twitter_status(name, version):
	twitter.update_status(status='%s [Win], [%s], [%s]' %(exact_time,name, version))

##############

get_Adium_ver()
get_Adobe_Flash_ver()
get_Adober_Reader_ver()
get_Java_ver()
get_Casper_ver()
get_Dropbox_ver()
get_Firefox_ESR_ver()
get_Office_2011_ver()
get_TextWrangler_ver()
get_VLC_ver()
