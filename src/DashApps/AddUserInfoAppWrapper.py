# dash_app.py
import dash
from dash import Dash, dcc, html, Input, Output, State
import dash_bootstrap_components as dbc
import pandas as pd
from flask import session

import uuid
import logging

from typing import Tuple
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

from datetime import datetime

from src.Backend.src.SQLHandler.SQLHandler import SQLHandler
from src.Backend.src.FinTsHandler.IbanCheckHelper import IbanCheckHelper


class AddUserInfoAppWrapper:
    def __init__(self, server = False, url_base_pathname = '/test/', app_title="AddSpendingsInterface"):

        self.sqlLiteHandlerUser = SQLHandler('user', '/home/matt/workspace/BASE/Finanztool/BASE_ERP_mother/config/TableDefinitions.yaml')
        
        self.app = Dash(__name__, server = server, url_base_pathname = url_base_pathname, external_stylesheets=[dbc.themes.BOOTSTRAP])
        self.app.title = app_title
        self.setup_layout()

    def refineDataFrameForDisplay(self, df: pd.DataFrame) -> pd.DataFrame:
        dfRefined = df[['nextcloudDisplayName',
                        'nextcloudGroups',
                        'banking_iban',
                        'banking_account_name',
                        'banking_bic',
                        'nextcloudEmail']].copy()
        
        dfRefined.rename(columns={'nextcloudDisplayName': 'Name', 
                                  'banking_iban': 'IBAN',
                                  'banking_bic': 'BIC',
                                  'banking_account_name': 'Name Kontoinhaber:in',
                                  'nextcloudGroups': 'Mitgliedschaft Gruppen',
                                  'nextcloudEmail': 'Email'}, inplace=True)
        return dfRefined
    
    def setup_layout(self):
        self.app.layout = dbc.Container([
            html.H1('Userinfos zufügen und aktualisieren'),
            dbc.Form([
                html.Br(),
                html.Div(id='input-field-div-0'),
                html.Br(),
                dbc.Label('Wähle aus, welche Information du zufügen oder aktualisiern möchtest.'),
                dcc.Dropdown(
                    id='dropdown_information',
                    options=[
                        {'label': 'IBAN', 'value': 'banking_iban'},
                        {'label': 'Name Kontoinhaber:in', 'value': 'banking_account_name'},
                        {'label': 'BIC', 'value': 'banking_bic'}
                    ],
                    value='iban'
                ),
                html.Br(),
                dbc.Label('Gib einen Wert ein:'),
                html.Br(),
                dcc.Input(id='input-field', type='text', value=''),
                html.Br(),
                dbc.Button('Aktualisieren', id='submit-button', n_clicks=0, color='primary'),
            ], className='mb-3'),

            html.Div(id='feedback-container'),
            html.Hr(),
            dcc.Location(id='url', refresh=True),
            dbc.Button('Zurück zum Hauptmenü', id='redirect-button', n_clicks=0, color='primary'),
            html.Hr(),
            html.H2('Folgende Daten werden für deine Rücküberweisung verwendet:'),
            #TODO integrate dash_table.DataTable (hat sorting und sowas)
            html.Div(id='userData-table'),
            html.Hr(),
            html.Hr(),
        ])
        self.setup_callbacks()
    

    def setup_callbacks(self):
        #set callback to automatically update the text of the input-field-div depending on the dropdown selection
        @self.app.callback(
            Output('input-field-div', 'children'),
            [Input('dropdown', 'value')]
        )
        def update_input_field(dropdownValue):
            text = f'Gebe einen neuen Wert ein für: {dropdownValue}'
            return dcc.Input(id='input-field', type='text', value='', placeholder=text)

        #set callback to 
        @self.app.callback(
            Output('feedback-container', 'children'),
            Output('userData-table', 'children'),
            Output('input-field', 'value'),
            Output('input-field-div-0', 'children'),
            [Input('submit-button', 'n_clicks')],
            [State('dropdown_information', 'value'),
             State('input-field', 'value')]
        )
        def update_output(n_clicks, informationName, informationValue):

            #determin from callback context which button was pressed
            clickedButtonID = [p['prop_id'] for p in dash.callback_context.triggered][0]

            # get users nextcloud ID from session
            nextcloudUserId = session.get('nextcloudUserId')

            feedback = None

            #if clicked, check iban and update iban if valid
            if 'submit-button' in clickedButtonID and informationValue and informationName :
                
                readableDict = {"banking_iban": "IBAN",
                                "banking_bic": "BIC",
                                "banking_account_name": "Name Kontoinhaber:in"}
                feedback = f'Wert aktualisiert: {readableDict[informationName]}'
                preventUpdate = False

                # if the entered value is an iban, make checks
                if informationName == "banking_iban":
                    if IbanCheckHelper.checkIban(informationValue):
                        #iban is valid
                        informationValue = IbanCheckHelper.formatIban(informationValue)
                    else:
                        #iban is invalid
                        feedback = 'Die eingegebene IBAN scheint ungültig zu sein. Die Iban wurde nicht aktualisiert.'
                        preventUpdate = True
                
                if not preventUpdate:
                    #update the database with the new value
                    self.sqlLiteHandlerUser.updateColumnCondition('nextcloudUserId', nextcloudUserId, informationName, informationValue)

            userData = self.sqlLiteHandlerUser.getColumnsFromTableWithCondition('nextcloudUserId', nextcloudUserId)

            #check if all banking data is provided
            bankingDataIsComplete = 1 if userData["banking_iban"][0] != "" and userData["banking_account_name"][0] != "" and userData["banking_bic"][0] != "" else 0
            self.sqlLiteHandlerUser.updateColumnCondition('nextcloudUserId', nextcloudUserId, "informationComplete", bankingDataIsComplete)

            feedback1Text = "Deine Überweisungsdaten sind noch nicht vollständig. Um Rechnungen auf deinen Namen anzugeben speichere eine Iban, den Namen der:s Kontoinhabers:in und die BIC." if not bankingDataIsComplete else "Deine Überweisungsdaten sind vollständig."
            feedback = feedback if feedback is not None else ''
            return feedback, dbc.Table.from_dataframe(self.refineDataFrameForDisplay(userData), striped=True, bordered=True, hover=True), informationValue, feedback1Text
            
        @self.app.callback(
        Output('url', 'pathname'),
        [Input('redirect-button', 'n_clicks')],
        )
        def redirect_to_flask(n_clicks):
            if n_clicks:
                return '/'