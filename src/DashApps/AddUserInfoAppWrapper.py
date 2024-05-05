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

from Backend.src.FinTsHandler.BankingCheckHelper import BankingCheckHelper
from Backend.src.SQLHandler.DatabaseSessionSetup import SqlSession
from Backend.src.SQLHandler.UserEntitiesHelpers.NextcloudUser import NextcloudUser


class AddUserInfoAppWrapper:
    def __init__(self, server = False, url_base_pathname = '/test/', app_title="AddSpendingsInterface"):

        self.app = Dash(__name__, server = server, url_base_pathname = url_base_pathname, external_stylesheets=[dbc.themes.BOOTSTRAP])
        self.app.title = app_title
        self.setup_layout()

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
                        {'label': 'IBAN', 'value': 'bankingIban'},
                        {'label': 'Name Kontoinhaber:in', 'value': 'bankingAccountName'},
                        {'label': 'BIC', 'value': 'bankingBic'}
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

            sqlSession = SqlSession()

            # get users nextcloud ID from session
            nextcloudUserId = session.get('nextcloudUserId')

            # get nextcloud user instance from data base
            nextcloudUser = sqlSession.query(NextcloudUser).filter(NextcloudUser.nextcloudUserId == nextcloudUserId).first()
            
            #determin from callback context which button was pressed
            clickedButtonID = [p['prop_id'] for p in dash.callback_context.triggered][0]

            feedback = ""

            #if clicked, check iban and update iban if valid
            if 'submit-button' in clickedButtonID and informationValue and informationName :
                
                readableDict = {"bankingIban": "IBAN",
                                "bankingBic": "BIC",
                                "bankingAccountName": "Name Kontoinhaber:in"}
                feedback = f'Wert aktualisiert: {readableDict[informationName]}'
                preventUpdate = False

                # if the entered value is an iban, make checks
                if informationName == "bankingIban":
                    if BankingCheckHelper.checkIban(informationValue):
                        #iban is valid
                        informationValue = BankingCheckHelper.formatIban(informationValue)
                    else:
                        #iban is invalid
                        feedback = 'Die eingegebene IBAN scheint ungültig zu sein. Die Iban wurde nicht aktualisiert.'
                        preventUpdate = True
                elif informationName == "bankingBic":
                    if not BankingCheckHelper.checkBic(informationValue):
                        #biv is invalid
                        feedback = 'Die eingegebene BIC scheint ungültig zu sein. Die BIC wurde nicht aktualisiert.'
                        preventUpdate = True

                if not preventUpdate: #update the database with the new value
                    # get the sql session and query the nextcloud user instance
                    setattr(nextcloudUser, informationName, informationValue)
                    sqlSession.commit()

            feedback1Text = "Deine Überweisungsdaten sind vollständig." if nextcloudUser.bankingDataIsComplete() else "Deine Überweisungsdaten sind noch nicht vollständig. Um Rechnungen auf deinen Namen anzugeben speichere eine Iban, den Namen der:s Kontoinhabers:in und die BIC."

            return feedback, dbc.Table.from_dataframe(nextcloudUser.getUserInformationAsDataFrame(forDisplay=True), striped=True, bordered=True, hover=True), informationValue, feedback1Text
            
        @self.app.callback(
        Output('url', 'pathname'),
        [Input('redirect-button', 'n_clicks')],
        )
        def redirect_to_flask(n_clicks):
            if n_clicks:
                return '/'