#! /usr/bin/env python

# Copyright 2014 Sar Haidar, Massachusetts Institute of Technology, All Rights Reserved.

import hashlib
import os

mit_software_repo = "/Users/sar/Desktop/sum/"

class AppChecksum:
	'Calculate and store downloaded app checksum'

	def __init__(self,app_repo, app_name=None, app_checksum=None, app_dict=None):
		self.app_repo = app_repo
		self.app_name = app_name
		self.app_checksum = app_checksum
		self.app_dict = app_dict

	def appChecksum(self):
		downloaded_apps = os.listdir(self.app_repo)
		app_dict = {}
		for self.app_name in downloaded_apps:
			if not self.app_name.startswith('.'):
				self.app_checksum = hashlib.sha256(file(self.app_repo+self.app_name, 'rb').read())
				app_dict[self.app_name] = self.app_checksum.hexdigest()
		return app_dict


def download_mit_apps():
	pass

def compare_checksums():
	pass

def main():
	a = AppChecksum(mit_software_repo)
	print a.appChecksum()
	print a.app_repo

if __name__=="__main__":
	main()