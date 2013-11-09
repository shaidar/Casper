Computer_Site_Assignment is to be used with JAMF Casper 9 or above and its new sites feature. 
This progam will assign a computer to a site based on the department that the user of the computer record belongs to.

#### Use Case:
If it's not very feasible for you to create a seperate Casper installer for every site that you've created, this program comes in handy. You can schedule it to run on your JSS or another server during certain intervals and it'll contact the JSS and assign the computer object to the approriate site based on the department info under 'User & Location' in a computer record. 

If you're looking for an automated way to populate the 'User & Location' fields, you might be interested in my [other program] (https://github.com/shaidar/Casper/blob/master/Computer_Site_Assignment/assign_computer_site.py)

#### Requirements:
* JAMF Casper 9 or above
* JSS API account with Read and Update privileges on computer object
* Python Requests package
