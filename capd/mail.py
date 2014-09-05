#! /usr/bin/env python

import ConfigParser
import logging
import os
import shutil
import smtplib
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart

# Global Variables
Software_Repo = os.environ['HOME']+"/Documents/capd"

def notify(pkg_name):
	logger = logging.getLogger('capd')
	logger.debug("notify")
	config = ConfigParser.ConfigParser()
	config.read(Software_Repo+'/conf/JSS_Server.conf')
	mailserver = config.get('Mail', 'mailserver', 0)
	screenshot_dir = (config.get('local_config', 'screenshots', 0))
	sender = config.get('Mail', 'sender', 0)
	receiver = config.get('Mail', 'receiver', 0)
	text = "The following app has been uploaded to Casper Test: " + pkg_name + "\n\n\n"
	msg = MIMEMultipart()
	msg['Subject'] = 'capd - New app has been tested'
	msg['From'] = sender
	msg['To'] = receiver
	msg.attach(MIMEText(text))
	screenshot_files = os.listdir(screenshot_dir)
	try:
		for sc_file in screenshot_files:
			fp = open(screenshot_dir+sc_file, 'rb')
			img = MIMEImage(fp.read())
			fp.close()
			msg.attach(img)
			logger.info("[+] Screenshot attached")
			if sc_file.endswith('.jpg'):
				shutil.move(screenshot_dir+sc_file, Software_Repo+"/sequenced"+sc_file)
				logger.info("[+] Screenshot moved to sequenced folder")
	except:
		logger.info("[+] No screenshot found to be attached")
	s = smtplib.SMTP(mailserver)
	s.sendmail(sender, receiver, msg.as_string())
	s.quit()

def main():
	notify(pkg_name)

if __name__ == "__main__":
	main()
