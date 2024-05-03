import dash

import os
import sys

import uuid

def add_subdirectories_to_sys_path(root_dir):
    """
    Adds all subdirectories under the specified root directory to sys.path
    to make them available for import.
    """
    for subdir, dirs, files in os.walk(root_dir):
        if subdir not in sys.path:
            sys.path.append(subdir)

add_subdirectories_to_sys_path('.')

from dash import Dash, dcc, html, Input, Output, State
import dash_bootstrap_components as dbc
import pandas as pd
from flask import session
from datetime import datetime
from src.Backend.src.SQLHandler.SQLHandler import SQLHandler

from src.Backend.src.HelperFunctions.ConfigLoader import ConfigLoader
#from src.FinTsHandler import FinTsHandler

class AddPaybackInfoAppWrapper:
    def __init__(self, server, url_base_pathname='/test/', app_title="Überweisungsmanager"):

        sqlTableDefinitionPath = ConfigLoader('config/config.yaml').data["SQL"]["tableDefinitionPath"]

        self.sqlHandlerReceipt = SQLHandler('receipt', sqlTableDefinitionPath)
        self.sqlHandlerUser = SQLHandler('user', sqlTableDefinitionPath)
        self.sqlHandlerAccounts = SQLHandler('accounts', sqlTableDefinitionPath)
        self.sqlHandlerProjects = SQLHandler('projects', sqlTableDefinitionPath)
        
        self.app = Dash(__name__, server=server, url_base_pathname=url_base_pathname, external_stylesheets=[dbc.themes.BOOTSTRAP])
        self.app.title = app_title
        self.setup_layout()
    
    def getUserDataForDisplay(self) -> dict:
        """pulls the entire user data from the respective SQL table and transforms them into a dict, having the nextcloudUserId as key and the nextcloudDisplayName as display name

        Returns:
            pd.DataFrame: a dictionary with nextcloudUserId as keys and nextcloudDisplayName as value
        """
        #get entire user data table
        userData = self.sqlHandlerUser.getColumnsFromTableWithCondition(None, None)
        #extract the dictionary from it
        return {key: value for key, value in zip(userData['nextcloudUserId'], userData['nextcloudDisplayName'])}
    
    def refineDataFrameForDisplay(self, df: pd.DataFrame) -> pd.DataFrame:
        
        userNameIDMapping = self.getUserDataForDisplay()
        df['nextcloudDisplayName_payedBy'] = df['nextcloudUserId_payedBy'].map(userNameIDMapping)
        df['nextcloudDisplayName_boughtBy'] = df['nextcloudUserId_boughtBy'].map(userNameIDMapping)
    
        dfRefined = df[['nextcloudDisplayName_payedBy', 'nextcloudDisplayName_boughtBy', 'amount', 'projectId', 'timestamp']].copy()
        dfRefined.rename(columns={'nextcloudDisplayName_payedBy': 'Bezahlt von', 'nextcloudDisplayName_boughtBy': 'getätigt von', 'amount': 'Betrag/€', 'projectId': 'Projekt', 'timestamp': 'Ausgabe registriert am'}, inplace=True)
        
        #map the project node ids to the names
        projectIdNameMapping = self.getProjectDataForDropdown()
        dfRefined['Projekt'] = dfRefined['Projekt'].map(projectIdNameMapping)
        
        return dfRefined
    
    def getProjectDataForDropdown(self) -> dict:
        """pulls the entire project data from the respective SQL table and transforms them into a dict, having the name of the project as key and the projectName as display name

        Returns:
            pd.DataFrame: a dictionary with nextcloudUserId as keys and nextcloudDisplayName as value
        """
        #get entire user data table
        userData = self.sqlHandlerProjects.getColumnsFromTableWithCondition(None, None)

        #extract the dictionary from it
        return {key: value for key, value in zip(userData['projectId'], userData['name'])}
    
    def setup_layout(self):
        self.app.layout = dbc.Container([
            html.H1(self.app.title),
            dbc.Form([
                html.H2('Ausgewählte Rechnung:'),
                dcc.Dropdown(id='receipt-selector', options=[], value=None, placeholder="Rechnung auswählen"),
                html.Br(),
                dbc.Button('Rückzahlung angewiesen', id='update-receipt-button', n_clicks=0, color='success'),
                ], className='mb-3'),
            dcc.Location(id='url', refresh=True),
            dbc.Button('Zurück zum Hauptmenü', id='redirect-button', n_clicks=0, color='primary'),
            html.Hr(),
            dbc.Label('aktueller kontostand:'),
            html.Div(id='balance-container'),
            html.H2('offene Rechnungen:'),
            html.Div(id='output-container'),
            html.Hr(),
        ])
        self.setup_callbacks()

    def setup_callbacks(self):

        @self.app.callback(
            Output('output-container', 'children'),
            Output('receipt-selector', 'options'),
            Output('balance-container', 'children'),
            [Input('update-receipt-button', 'n_clicks'),
             Input('url', 'pathname')],
            [State('receipt-selector', 'value')]
        )
        def update_entry(n_clicks, pathname, selected_entry):
            data = self.sqlHandlerReceipt.getColumnsFromTableWithCondition('paybackDate', '-')
    
            #determine from callback context which button was pressed
            clickedButtonID = [p['prop_id'] for p in dash.callback_context.triggered][0]

            if 'update-receipt-button' in clickedButtonID and selected_entry is not None:
                #update the respective entry in the sql library
                self.sqlHandlerReceipt.updateColumnCondition('receiptId', selected_entry, 'paybackDate', datetime.today().strftime('%d.%m.%Y') )

                #update the data displayed in the table
                data = self.sqlHandlerReceipt.getColumnsFromTableWithCondition('paybackDate', '-')
            
            # compute dropdown options
            data = self.sqlHandlerReceipt.getColumnsFromTableWithCondition('paybackDate', '-')
            
            userNameIDMapping = self.getUserDataForDisplay()
            data['nextcloudDisplayName_payedBy'] = data['nextcloudUserId_payedBy'].map(userNameIDMapping)
            data['nextcloudDisplayName_boughtBy'] = data['nextcloudUserId_boughtBy'].map(userNameIDMapping)
            
            #bring treehandler to the latest version of the table
            projectIdNameMapping = self.getProjectDataForDropdown()

            #convert the projectID into project Names
            data['projectId'] = data['projectId'].map(projectIdNameMapping)
            options = [{'label': f"{row['nextcloudDisplayName_boughtBy']} - {row['projectId']} - {row['amount']}€", 'value': row['receiptId']} for index, row in data.iterrows()]
            
            return dbc.Table.from_dataframe(self.refineDataFrameForDisplay(data), striped=True, bordered=True, hover=True), options, "default €"

        @self.app.callback(
        Output('url', 'pathname'),
        [Input('redirect-button', 'n_clicks')],
        )
        def redirect_to_flask(n_clicks):
            if n_clicks:
                return '/'