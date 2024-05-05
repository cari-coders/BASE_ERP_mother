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
from Backend.src.SQLHandler.DatabaseSessionSetup import SqlSession

from Backend.src.SQLHandler.FinancialEntitiesHelpers.Project import Project
from Backend.src.SQLHandler.FinancialEntitiesHelpers.FiannceEntities import FinanceReceipt
from Backend.src.SQLHandler.UserEntitiesHelpers.NextcloudUser import NextcloudUser

from src.Backend.src.HelperFunctions.ConfigLoader import ConfigLoader
#from src.FinTsHandler import FinTsHandler

class AddPaybackInfoAppWrapper:
    def __init__(self, server, url_base_pathname='/test/', app_title="Überweisungsmanager"):

        self.app = Dash(__name__, server=server, url_base_pathname=url_base_pathname, external_stylesheets=[dbc.themes.BOOTSTRAP])
        self.app.title = app_title
        self.setup_layout()
    
    def getUserIdNameMapping(self, reverse = False) -> dict:
        sqlSession = SqlSession()
        
        userData = sqlSession.query(NextcloudUser.nextcloudDisplayName, NextcloudUser.nextcloudUserId).all()
        # Convert list of tuples into a dictionary
        nameIdMapping = {id: name for name, id in userData}

        return {value: key for key, value in nameIdMapping.items()} if reverse else nameIdMapping
    
    def getProjectDataForDropdown(self) -> dict:
        """pulls the entire project data from the respective SQL table and transforms them into a dict, having the name of the project as key and the projectName as display name

        Returns:
            pd.DataFrame: a dictionary with nextcloudUserId as keys and nextcloudDisplayName as value
        """

        #instanciate sql session
        sqlSession = SqlSession()

        # fetch all projects from table
        projectData = sqlSession.query(Project).all()

        sqlSession.close()

        #extract the dictionary from it
        return [{'label': project.name, 'value': project.id} for project in projectData]
    
    def refineReceiptDataForDisplay(self, receipts: list) -> pd.DataFrame:
        #transform list into dataframe

        userNameIDMapping = self.getUserIdNameMapping()
        df = pd.DataFrame([{
                'nextcloudUserDisplayName_sender': userNameIDMapping[receipt.nextcloudUserId_sender],
                'nextcloudUserDisplayName_reciever': userNameIDMapping[receipt.nextcloudUserId_reciever],
                'amount': receipt.amount,
                'projectName': receipt.project.name,
                'paybackDate': receipt.paybackDate,
                'timestamp': receipt.timestamp,
                'receiptDate': receipt.receiptDate,
                'description': receipt.description,
        } for receipt in receipts])

        df.rename(columns={'nextcloudUserDisplayName_sender': 'Bezahlt von', 'nextcloudUserDisplayName_reciever': 'Bezahlt an', 'amount': 'Betrag / €', 'projectName': 'Projekt', 'description': 'Beschreibung', 'receiptDate': 'Rechnungsdatum', 'paybackDate': 'Datum Rücküberweisung', 'timestamp': 'Zeitstempel'}, inplace=True)
        return df

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

            sqlSession = SqlSession()
            
            #determine from callback context which button was pressed
            clickedButtonID = [p['prop_id'] for p in dash.callback_context.triggered][0]

            if 'update-receipt-button' in clickedButtonID and selected_entry is not None:
                #update the respective entry in the sql library
                chosenReceipt = sqlSession.query(FinanceReceipt).filter(FinanceReceipt.id == selected_entry).first()
                chosenReceipt.paybackDate = datetime.now()

                sqlSession.commit()

            receiptHistory = sqlSession.query(FinanceReceipt).filter(FinanceReceipt.paybackDate == None).all()
            
            options = [{'label': f"{receipt.nextcloudUserId_sender} - {receipt.project.name} - {receipt.amount}€", 'value': str(receipt.id)} for receipt in receiptHistory]
            
            return dbc.Table.from_dataframe(self.refineReceiptDataForDisplay(receiptHistory), striped=True, bordered=True, hover=True), options, "default €"

        @self.app.callback(
        Output('url', 'pathname'),
        [Input('redirect-button', 'n_clicks')],
        )
        def redirect_to_flask(n_clicks):
            if n_clicks:
                return '/'