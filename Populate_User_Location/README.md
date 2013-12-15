Aim of this program is to automatically populate the 'User Location' info in the computer records running the Casper client. 

#### How it works
Running as a Casper policy:
* Get username or full name by searching through Mail.app or Tivoli Storage Manager nodename (client backup).
* Based on username or full name, query ldap or white pages for detailed info such as position, department, title ...
* Generate an xml file containing the info received from ldap or white pages
* Get computer name and update the approriate computer record in JSS

#### Assumptions
* Ability to query ldap or white pages
* End-user is using Mail.app or Tivoli Storage Manager

#### Requirements
* JSS API account that has update computer record priviliges

#### Future Improvements
* GUI interface to enter values
* Other apps to get username from (I've written a couple of those, but are specific to my case and thus didn't include in here).
* Improve Error Reporting
* Check if computer record is already populated with correct info and exit if it is
