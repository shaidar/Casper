#!/usr/bin/env python
'''
Copright 2013 Sar Haidar, Massachusetts Institute of Technology, All Rights Reserved.
Last Modified: 11/12/13

Description:
I wrote this to get out of the hassle of packaging some apps or mounting some dmg's and then uploading the pkg to Casper.
I wanted to upload to the Casper share what the vendor provides and then setup a policy to 'Cache' the app and then 
run this script to install the cached file(s).

Future improvements:
- Automatically get startup_disk
'''
import glob, os, shutil, subprocess

i = 0
startup_disk = "/Volumes/Macintosh HD"		# Make sure that this is correct on the client
pkg_path = "/Library/Application Support/JAMF/Waiting Room/"
mounted_pkg = ""
mnt_pkg_path = ""

def install_pkg(pkg_abspath, mnt_pkg_path):
	subprocess.call(['installer','-package', pkg_abspath, '-target', startup_disk])
	print "Successfully installed", pkg_abspath

def install_app(pkg_abspath, mnt_pkg_path):
	subprocess.call(['cp','-R',pkg_abspath,'/Applications'])
	print "Successfully installed", pkg_abspath

def mnt_dmg(pkg_name):
	global mounted_pkg, mnt_pkg_path
	if pkg_name.endswith(".dmg"):
		p1 = subprocess.Popen(['hdiutil', 'mount', pkg_name, '-nobrowse'], stdout=subprocess.PIPE)
		p2 = subprocess.Popen(['grep', '-o', '/Volumes/.*'], stdin=p1.stdout, stdout=subprocess.PIPE)
		p1.stdout.close()
		mnt_pkg_path = (p2.communicate()[0]).rstrip()
		p2.stdout.close()
		mounted_pkg = os.listdir(mnt_pkg_path)
	elif pkg_name.endswith(".zip"):
		subprocess.call(['unzip', '-u',pkg_name, '-d', pkg_path+'folder'])
		mnt_pkg_path = pkg_path+'folder'
		mounted_pkg = os.listdir(mnt_pkg_path)
		print mounted_pkg
	return mounted_pkg, mnt_pkg_path

def unmnt_dmg(mnt_pkg_path):
	subprocess.call(['hdiutil', 'unmount', mnt_pkg_path])

def del_pkg(pkg_path):
	shutil.rmtree(pkg_path)

while i < len(glob.glob(pkg_path+"*.*")):
	pkg_name = glob.glob(pkg_path+"*.*")[i]
	if pkg_name.endswith(".dmg") or pkg_name.endswith(".zip"):
		mnt_dmg(pkg_name)
		for item in mounted_pkg:
			if item.endswith(".app"):
				pkg_abspath = mnt_pkg_path+'/'+item
				install_app(pkg_abspath, mnt_pkg_path)
			elif item.endswith(".pkg") or item.endswith(".mpkg"):
				pkg_abspath = mnt_pkg_path+'/'+item
				print pkg_abspath
				install_pkg(pkg_abspath, mnt_pkg_path)
		if "/Volumes" in mnt_pkg_path:
			unmnt_dmg(mnt_pkg_path)
	elif pkg_name.endswith(".pkg"):
		install_pkg(pkg_abspath, mnt_pkg_path)
	i += 1
del_pkg(pkg_path)
