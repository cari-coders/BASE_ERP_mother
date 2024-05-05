# Server 1: Authentication Server
import os
import sys

def add_subdirectories_to_sys_path(root_dir):
    """
    Adds all subdirectories under the specified root directory to sys.path
    to make them available for import.
    """
    for subdir, dirs, files in os.walk(root_dir):
        if subdir not in sys.path:
            sys.path.append(subdir)

add_subdirectories_to_sys_path('.')

from flask import Flask, redirect, url_for, request, render_template, session, flash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user

import logging
import yaml
from typing import List, Callable
import pandas as pd

from src.Backend.src.HelperFunctions.ConfigLoader import ConfigLoader
from src.Backend.src.HelperFunctions.Server import Server
from Backend.src.SQLHandler.UserEntitiesHelpers.FlaskUser import FlaskUser
from Backend.src.SQLHandler.UserEntitiesHelpers.NextcloudUser import NextcloudUser

from Backend.src.SQLHandler.DatabaseSessionSetup import SqlSession, init_db

from src.DashApps.AddUserInfoAppWrapper import AddUserInfoAppWrapper
from src.DashApps.AddSpendingsAppWrapper import AddSpendingsAppWrapper
# from src.DashApps.AddPaybackInfoAppWrapper import AddPaybackInfoAppWrapper

from urllib.parse import urlencode
from functools import wraps

# read logging informaation
with open('config/config.yaml', 'r') as file:
    # Load the YAML content
    data = yaml.safe_load(file)
    # Configuration for logging to a file

    if data['logging']['logLevel'] == 'debug':
        logLevel = logging.DEBUG
    elif data['logging']['logLevel'] == 'info':
        logLevel = logging.INFO

    logging.basicConfig(filename=data['logging']['logFilePath'], filemode='w', level=logLevel, format='%(asctime)s - %(levelname)s - %(message)s')


# initiate Flask internal data base
class HomeScreen(Server):
    """
    Represents the HomeScreen server for providing access to the different IT tools, depending on the user access rights.
    It extends the basic generic Server class from the Backend module to include methods needed for the HomeScreenServer

    Methods:
    - __init__: Initializes the OAuth server with necessary configurations.
    - defineRoutes: Defines the Flask routes for OAuth authentication flow.
    - accessRestriction: decorateor to protect routes of the server
    """

    # define access decorator
    @staticmethod
    def accessRestriction(requiredRoles: List[str]):
        """
        Decorator function to restrict access to routes based on user roles.

        Args:
            requiredRoles (List[str]): A list of role names required to access the route.

        Returns:
            decorator: A decorator function that restricts access based on the specified roles.

        Usage:
            @accessRestriction(['admin', 'manager'])
            def some_protected_route():
                # Code for the protected route
        """
        def decorator(f : Callable):
            @wraps(f)
            def wrappedFunction(*args, **kwargs):
                # check if the user is already authenticated (same as @login_required?) 
                if not current_user.is_authenticated:
                    return redirect(url_for('home'))
                
                # convert the user.role list and the requiredRoles list into sets and check for intersections -> if they intersect, the user has the required role
                usersRolesSet = set(current_user.getRoles())
                requiredRolesSet = set(requiredRoles)
                setsIntersect = bool(usersRolesSet & requiredRolesSet)

                if not setsIntersect:
                    # user does not have the required role: # TODO show an error or redirect ? Wie handeln wir das?
                    flash('You do not have permission to access this page.')
                    return redirect(url_for('home'))

                # if the sets intersect, return the wrapped function
                return f(*args, *kwargs)
            return wrappedFunction
        return decorator


    def __init__(self):
        """
        Initializes the HomeScreenServer instance.
        """
                
        init_db()
        #call parent __init__ to initialize the flask server instance
        super().__init__('HomeScreen', debugLevel = os.getenv('DEBUG_LEVEL'))

        # Flask-Login setup
        self.login_manager = LoginManager()
        self.login_manager.init_app(self.app)
        self.login_manager.login_view = 'login'

        self.defineRoutes()
    

    def defineRoutes(self):
        """
        Defines the Flask routes for the OAuth authentication flow, including
        the index, login, and authorization endpoints.
        """

        # User loader function for Flask-Login
        @self.login_manager.user_loader
        def load_user(user_id):
            """
            funcition provides a callback for the flask LoginManager to reload the user object from the user ID stored in the session (see https://flask-login.readthedocs.io/en/latest/). 

            It should return None (not raise an exception) if the ID is not valid. (In that case, the ID will manually be removed from the session and processing will continue.)
            """
            sqlSession = SqlSession()
            user = sqlSession.query(FlaskUser).get(user_id)
            sqlSession.close()
            return user

        # Home route
        @self.app.route('/')
        def home():
            # display the buttons that direct to the tools depending on the users access rights (# TODO)
            if current_user.is_authenticated:
                return render_template('home_auth.html', username=session.get("currentUserDisplayName"))
            else:
                return render_template('home.html')
            
        # Login route
        @self.app.route('/login')
        def login():

            # check wether https is active between containers
            if os.getenv('HTTPS_ACTIVE'): #TODO convert string to boolean
                urlFormat = "https"
            else:
                urlFormat = "http"

            authServerIP = os.getenv("BASE_URL")
            authServerPort = os.getenv("PORT_OAUTH")
            homescreenServerPort = os.getenv('PORT_HOMESCREEN')

            authenticationURL =f'{urlFormat}://{authServerIP}:{authServerPort}/authenticate?callback_port={homescreenServerPort}'
            return redirect(authenticationURL)

        @self.app.route('/verified_callback')
        def verifiedCallback():

            # this function is called from the authentication server after successfull authentication

            # create FlaskUser instance
            flaskUser = FlaskUser()
            flaskUser.setRoles(session["nextcloudUserGroups"])

            #create SQL session
            sqlSession = SqlSession()

            #add FlaskUser to SQL data base and commit
            sqlSession.add(flaskUser)
            sqlSession.commit()

            #login the FlaskUser
            login_user(flaskUser)

            #check if user is already in db and add user otherwise
            nextcloudUserId = session.get('nextcloudUserId')
            currentUserDisplayName = session.get('currentUserDisplayName')

            # check if user is already in sql table
            if sqlSession.query(NextcloudUser).filter(NextcloudUser.nextcloudUserId == nextcloudUserId).first() is None:
                newEntry = {
                    "nextcloudUserId": [nextcloudUserId],
                    "nextcloudDisplayName": [currentUserDisplayName],
                    "isGuest": [0],
                    "nextcloudGroups": [', '.join(session.get('nextcloudUserGroups'))],
                    "nextcloudEmail": [session.get('nextcloudUserEmail')],
                }
                nextcloudUser = NextcloudUser.fromDict(newEntry)
                sqlSession.add(nextcloudUser)
                sqlSession.commit()

            sqlSession.close()
            return redirect(url_for('home'))

        # Logout route
        @self.app.route('/logout')
        def logout():
            logout_user()
            return redirect(url_for('home'))


        addUserInfoPath = '/adduserinfo/'
        addUserInfoApp = AddUserInfoAppWrapper(self.app, url_base_pathname = addUserInfoPath)

        addSpendingPath = '/addspendings/'
        addUserInfoApp = AddSpendingsAppWrapper(self.app, url_base_pathname = addSpendingPath)

        # addPaybackinfoPath = '/addpaybackinfo/'
        # addUserInfoApp = AddPaybackInfoAppWrapper(self.app, url_base_pathname = addPaybackinfoPath)

if __name__ == '__main__':
    
    homeScreenServer = HomeScreen()
    
    debugLevel = True if os.getenv("DEBUG_LEVEL") == 'True' else False

    port = os.getenv("PORT_HOMESCREEN")
    address = os.getenv("BASE_URL")
    
    logtext = f'starting Homescreen Server at: http://{address}:{port}'

    logging.info(logtext)
    print(logtext)
    
    homeScreenServer.run(debug=debugLevel, port=port)
