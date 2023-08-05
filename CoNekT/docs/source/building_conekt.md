# Building CoNekt Grasses

## Using the admin panel to build CoNekt

Make sure *LOGIN_ENABLED=True* in *config.py* and the database was build with and admin account (check `install_linux.md` for instructions how to add an admin account). 

Make sure your server **doesn't time out requests**, some operations can take several minutes. If your server is live already running build steps can result in issues for active users. To avoid this consider running and extra CoNekT instance on the server using the built in web-server and connecting to it using an SSH tunnel.

To start building, go to the website, log in and (once logged in) click on the username (admin) in the top right corner. Select 'Admin Panel' from the drop-down menu.

`/images/admin_home.png`

The Admin Panel will welcome you with a large warning. Deleting data, overwriting or changing entries here can ruin a carefully set up 
database. Make sure to read instructions on pages and this documentation to avoid losing work. 

**When working with an existing database, make sure to back up the database before proceeding.**

Step-by-step instructions

  * Adding GO term and InterPro domain definitions
  * Adding a new species and functional data
  * Adding expression profiles and specificity
  * Adding co-expession networks and clusters
  * Adding comparative genomics data
  * Precomputing counts and more  
  
  * Controls
  * CRUD