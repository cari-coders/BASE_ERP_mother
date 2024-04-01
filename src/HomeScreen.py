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

from flask import Flask, redirect, url_for, request, render_template, session
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from authlib.integrations.flask_client import OAuth
import urllib.parse


import json
import logging
import yaml

from src.Backend.src.HelperFunctions.ConfigLoader import ConfigLoader
from src.Backend.src.HelperFunctions.Server import Server
from urllib.parse import urlencode


# read logging informaation
with open('config/config.yaml', 'r') as file:
    # Load the YAML content
    data = yaml.safe_load(file)
    # Configuration for logging to a file
    logging.basicConfig(filename=data['logging']['logFilePath'], filemode='w', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

#TODO diese Klasse koennte mehr enthalten als nur eine ID -- ist es eventuell sinnvoll user zu speichern?
#TODO macht es sinn diese klasse ins Backend zu legen oder in die HomeScreenServer-Klasse
class User(UserMixin):
    def __init__(self, id):
        self.id = id

class HomeScreen(Server):
    """
    Represents the HomeScreen server for providing access to the different IT tools, depending on the user access rights.
    It extends the basic generic Server class from the Backend module to include methods needed for the HomeScreenServer

    Methods:
    - __init__: Initializes the OAuth server with necessary configurations.
    - defineRoutes: Defines the Flask routes for OAuth authentication flow.
    """

    def __init__(self):
        """
        Initializes the HomeScreenServer instance.
        """
                
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
            return User(user_id)
        
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
            authServerPort = os.getenv("AUTHENTICATION_SERVER_PORT")
            homescreenServerPort = os.getenv('HOMESCREEN_SERVER_PORT')

            authenticationURL =f'{urlFormat}://{authServerIP}:{authServerPort}/authenticate?callback_port={homescreenServerPort}'
            return redirect(authenticationURL)

        @self.app.route('verified_callback')
        def verifiedCallback():

            # this function is called from the authentication server after successfull authentication

            #login user
            user = User(session.get('nextcloudUserID'))
            self.login_manager(user)

            #TODO implement acess logic (hier? oder vielleicht besser in der User-Klasse)

            return redirect(url_for('home'))

        # Logout route
        @self.app.route('/logout')
        def logout():
            logout_user()
            return redirect(url_for('home'))

if __name__ == '__main__':
    
    homeScreenServer = HomeScreen()
    
    # load global config, get debug level and port
    gcl = ConfigLoader(str(os.getenv('GLOBAL_CONFIG_PATH')))
    debugLevel = True if gcl.data['debugLevel'] == 'True' else False

    homeScreenServer.run(debug=debugLevel, port=gcl.data['ports']['NcOAuth'])
