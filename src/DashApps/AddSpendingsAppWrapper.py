
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
add_subdirectories_to_sys_path('./src/Backend/FinancialEntitiesHelper')


# dash_app.py
import dash
from dash import Dash, dcc, html, Input, Output, State
import dash_bootstrap_components as dbc
import pandas as pd
from flask import session

import img2pdf
from pathlib import Path
import dash_uploader as du
from datetime import datetime, date
import uuid

from Backend.src.SQLHandler.DatabaseSessionSetup import SqlSession
from sqlalchemy.sql import or_

from Backend.src.SQLHandler.FinancialEntitiesHelpers.Project import Project
from Backend.src.SQLHandler.FinancialEntitiesHelpers.FiannceEntities import FinanceReceipt
from Backend.src.SQLHandler.UserEntitiesHelpers.NextcloudUser import NextcloudUser

from src.Backend.src.HelperFunctions.ConfigLoader import ConfigLoader
class AddSpendingsAppWrapper:
    def __init__(self, server = None, url_base_pathname = '/test/', app_title="AddSpendingsInterface"):

#        self.financialEntitieshandler = FinancialEntitiesHandler()

        self.app = Dash(__name__, server = server, url_base_pathname = url_base_pathname, external_stylesheets=[dbc.themes.BOOTSTRAP])
        self.app.title = app_title
        
        self.imageUploadPath = ConfigLoader('config/config.yaml').data["receiptUpload"]["uploadPath"]

        du.configure_upload(self.app, self.imageUploadPath)

        self.setup_layout()

    def getUserIdNameMapping(self, reverse = False) -> dict:
        sqlSession = SqlSession()
        
        userData = sqlSession.query(NextcloudUser.nextcloudDisplayName, NextcloudUser.nextcloudUserId).all()
        # Convert list of tuples into a dictionary
        nameIdMapping = {id: name for name, id in userData}

        return {value: key for key, value in nameIdMapping.items()} if reverse else nameIdMapping

    def getUserDataForDropdown(self, onlyCompleteAccounts:bool = False, excludeNextcloudUserDisplayNameList: list = []) -> dict:
        """pulls the entire user data from the respective SQL table and transforms them into a dict, having the nextcloudUserId as key and the nextcloudDisplayName as display name

        Returns:
            pd.DataFrame: a dictionary with nextcloudUserId as keys and nextcloudDisplayName as value
        """
        # query the dict keys and values from the sql data base
        sqlSession = SqlSession()

        if onlyCompleteAccounts:
            #query the user IDs and dispaly names and filter for complete Banking Data and excludeList
            filteredUserData = sqlSession.query(NextcloudUser.nextcloudUserId, NextcloudUser.nextcloudDisplayName, NextcloudUser.nextcloudDisplayName).filter(NextcloudUser.nextcloudDisplayName.notin_(excludeNextcloudUserDisplayNameList)).all()
            filteredUserData = ((id, name) for (id, name, isComplete) in filteredUserData if isComplete)
        else:
            filteredUserData = sqlSession.query(NextcloudUser.nextcloudUserId, NextcloudUser.nextcloudDisplayName).filter(NextcloudUser.nextcloudDisplayName.notin_(excludeNextcloudUserDisplayNameList)).all()
        
        sqlSession.close()
        
        #extract the dictionary from the dataframe
        return [{'label':name, 'value': id} for id, name in filteredUserData]

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
        df = pd.DataFrame([{
                'nextcloudUserId_sender': [receipt.nextcloudUserId_sender],
                'nextcloudUserId_reciever': [receipt.nextcloudUserId_reciever],
                'amount': [receipt.amount],
                'projectId': [receipt.projectId],
                'paybackDate': [receipt.paybackDate],
                'timestamp': [receipt.timestamp],
                'receiptDate': [receipt.receiptDate],
                'description': [receipt.description],
        } for receipt in receipts])

        if not df.empty:
            #map nextcloud IDs to nextcloud Names
            userNameIDMapping = self.getUserIdNameMapping()
            df['nextcloudUserIDisplayName_sender'] = df['nextcloudUserId_sender'].map(userNameIDMapping)
            df['nextcloudUserDisplayName_reciever'] = df['nextcloudUserId_reciever'].map(userNameIDMapping)

            projectIdNameMapping = self.getProjectDataForDropdown()
            df['projectId'] = df['projectId'].map(projectIdNameMapping)

        df.rename(columns={'nextcloudUserIDisplayName_sender': 'Bezahlt von', 'nextcloudUserDisplayName_reciever': 'bezahlt an', 'amount': 'Betrag / €', 'projectId': 'Projekt', 'description': 'Beschreibung', 'receiptDate': 'Rechnungsdatum', 'paybackDate': 'Datum Rücküberweisung', 'timestamp': 'Zeitstempel'}, inplace=True)

        return df

    def manageUploadedImages(self, description, fileNames, uploadID):
        # transform the images into a single pdf if not already; provide a unique filename for the image
        
        #assume that fileNames has at least one element

        uniquePdfPath = os.path.join(self.imageUploadPath, description + str(uuid.uuid4()) + '.pdf')

        # Filter for supported image types (PNG, JPEG)
        supported_extensions = ['.png', '.jpg', '.jpeg']
        imageFiles = [os.path.join(self.imageUploadPath, uploadID, file) for file in fileNames if os.path.splitext(file)[1].lower() in supported_extensions]

        with open(uniquePdfPath, "wb") as f:
            imgData = [open(imagePath, "rb").read() for imagePath in imageFiles]
            f.write(img2pdf.convert(imgData))

        return uniquePdfPath

    def setup_layout(self):

        self.app.layout = dbc.Container([
            html.H1('Ausgaben zufügen'),
            dbc.Label("Um eine Ausgabe hinzuzufügen, gib die erforderlichen Daten an und drücke auf senden. Es können nur Ausgaben für Menschen zugefügt werden, die ihre KOntodaten im Menupunkt 'Userinfos zufügen' vollständig hinterlegt haben"),
            dbc.Form([
                dbc.Label('Die Ausgabe wurde bezahlt von:'),
                    dcc.Dropdown(
                    id='bezahlt-dd',
                    #options=self.getUserDataForDisplay(), optioen werden in callback function berechnet -> somit werden die optionen neu geladen jedes mal wenn die seite gerendert wird
                    searchable=True,  # Make the dropdown searchable
                    placeholder="gib einen Namen ein",
                ),
                html.Br(),
                dbc.Label('Die Ausgabe wurde getätigt von:'),
                dcc.Dropdown(
                    id='getaetigt-dd',
                    #options=self.getUserDataForDisplay(),
                    searchable=True,  # Make the dropdown searchable
                    placeholder="gib einen Namen ein",
                ),
                html.Br(),
                dbc.Label('Aktion oder Projekt:'),
                dcc.Dropdown(
                    id='project-dd',
                    #options=self.getUserDataForDisplay(),
                    searchable=True,  # Make the dropdown searchable
                    placeholder="gib einen Namen ein",
                ),
                html.Br(),
                dbc.Label('Betrag / € (mit Punkt statt Komma):'),
                dbc.Input(id='betrag', type='number', placeholder='gib den Betrag in € ein'),
                html.Br(),
                dbc.Label('Beschreibung der Ausgabe:'),
                dbc.Input(id='description', placeholder='gib eine Beschreibung der gekauften Ariekl ein'),
                html.Br(),
                dbc.Label('Datum der Ausgabe:  '),
                dcc.DatePickerSingle(id='date-receipt',
                                     min_date_allowed=date(2024,1,1),
                                     max_date_allowed=datetime.today(),
                                     initial_visible_month=datetime.today()
                                     ),
                html.Br(),
                html.Br(),
                html.Div([du.Upload(
                    id='receipt-upload',
                    filetypes=['png', 'jpg', 'jpeg', 'pdf'],
                    text='Drag and Drop (maximal 10) Bilder von der Rechnung',
                    max_file_size=1024, # TODO ändern
                    max_files = 10
                )
                        ]),
                html.Div(id='output-file-upload'),
                html.Br(),
                dbc.Button('Senden', id='submit-button', n_clicks=0, color='primary'),
                html.Hr(),
            ], className='mb-3'),
            html.Div(id='feedback-container'),
            html.Hr(),
            dcc.Location(id='url', refresh=True),
            dbc.Button('Zurück zum Hauptmenü', id='redirect-button', n_clicks=0, color='primary'),
            html.Hr(),
            html.H2('Verlauf:'),
            #TODO integrate dash_table.DataTable (hat sorting und sowas)
            html.Div(id='receipt-table'),
        ])
        self.setup_callbacks()
        

    def setup_callbacks(self):
        
        # callback to update dropdown menu options when the page is loaded
        @self.app.callback(
            [Output('bezahlt-dd', 'options'),
             Output('getaetigt-dd', 'options'),
             Output('project-dd', 'options')],
            [Input('url', 'pathname')]  # Triggered every time the page is loaded
        )
        def updateDropdownOptions(pathname):
            
            optionsUserNamesComplete = self.getUserDataForDropdown(onlyCompleteAccounts = True)
            optionsUserNamesInComplete =self.getUserDataForDropdown(onlyCompleteAccounts = False, excludeNextcloudUserDisplayNameList=['CaRi Konto', 'CaRi Bargeld'])
            optionsProjects = self.getProjectDataForDropdown()
            return optionsUserNamesComplete, optionsUserNamesInComplete, optionsProjects

        # callback to save the information and update the table when 'submit' is clicked
        @self.app.callback(
            Output('feedback-container', 'children'),
            Output('receipt-table', 'children'),
            Output('bezahlt-dd', 'value'),
            Output('getaetigt-dd', 'value'),
            Output('project-dd', 'value'),
            Output('betrag', 'value'),
            Output('description', 'value'),
            [Input('submit-button', 'n_clicks')],
            [State('bezahlt-dd', 'value'),
            State('getaetigt-dd', 'value'),
            State('project-dd', 'value'),
            State('betrag', 'value'),
            State('description', 'value'),
            State('date-receipt', 'date'),
            State('receipt-upload', 'fileNames'),
            State('receipt-upload', 'upload_id'),
            State('receipt-upload', 'isCompleted')]
        )
        def update_output(n_clicks, bezahlt, getaetigt, project, betrag, description, date, fileNames, uploadID, isCompleted):

            #determin from callback context which button was pressed
            clickedButtonID = [p['prop_id'] for p in dash.callback_context.triggered][0]
            
            #instanciate sqlSession
            sqlSession = SqlSession()

            #get userid from session
            nextcloudUserId = session.get('nextcloudUserId')

            #get the receipt of the current user (both, the ones that have currentUser as payed by and as bought by)
            receiptHistory = sqlSession.query(FinanceReceipt).filter(or_(FinanceReceipt.nextcloudUserId_sender == nextcloudUserId,
                                                                  FinanceReceipt.nextcloudUserId_reciever == nextcloudUserId,
                                                                  FinanceReceipt.nextcloudUserId_enteredBy == nextcloudUserId))
            
            if fileNames:
                if not isCompleted:
                    return "Warte bis der Upload abgeschlossen ist und klicke erneut. . ." , dbc.Table.from_dataframe(self.refineDataFrameForDisplay(receiptHistory), striped=True, bordered=True, hover=True), bezahlt, getaetigt, project, betrag, description

            if 'submit' in clickedButtonID:
                if bezahlt and getaetigt and project and betrag and description and date and fileNames and isCompleted:
                
                    imageUploadPathUnique = self.manageUploadedImages(description, fileNames, uploadID)

                    datetimeNow = datetime.now()

                    newEntry = {
                        'receiptId': [str(uuid.uuid4())], #get random Universal Unique Identifier
                        'nextcloudUserId_sender': [bezahlt],
                        'nextcloudUserId_reciever': [getaetigt],
                        'nextcloudUserId_enteredBy': [getaetigt],
                        #'projectId': [project],
                        'description': [description],
                        'amount': [betrag],
                        'imagePath': imageUploadPathUnique,
                        'receiptDate': [date],
                        'paybackDate': ["-"],
                        'timestamp': [datetimeNow.strftime('%d.%m.%Y - %H:%M:%S')]}
                    
                    sqlSession.add(FinanceReceipt.fromDict(newEntry))

                    receiptHistory = pd.concat([receiptHistory, pd.DataFrame(newEntry)], ignore_index=True)

                    return 'Die Ausgabe wurde erfolgreich hinzugefügt', dbc.Table.from_dataframe(self.refineReceiptDataForDisplay(receiptHistory), striped=True, bordered=True, hover=True), "", "", "", "", ""
            
                else:
                    return 'Die Informationen sind nicht vollständig.', dbc.Table.from_dataframe(self.refineReceiptDataForDisplay(receiptHistory), striped=True, bordered=True, hover=True), bezahlt, getaetigt, project, betrag, description

            return '', dbc.Table.from_dataframe(self.refineReceiptDataForDisplay(receiptHistory), striped=True, bordered=True, hover=True), bezahlt, getaetigt, project, betrag, description


        # define a callback that informas the user about which files have been uploaded yet
        @self.app.callback(
            Output('output-file-upload', 'children'),
            [Input('receipt-upload', 'isCompleted')],
            [State('receipt-upload', 'fileNames'),
            State('receipt-upload', 'upload_id')]
        )
        def update_output(isCompleted, fileNames, uploadID):
            
            if not fileNames:
                return "Keine Bilder ausgewählt."
            if not isCompleted:
                return "Bilder werden hochgeladen . . ."
            
            uploadDir = os.path.join(self.imageUploadPath, uploadID)
            if not os.path.exists(uploadDir):
                return "Fehler beim hochladen."

            fileNames = [f.name for f in Path(uploadDir).iterdir() if f.is_file()]
            # Simply join the file names into a string for testing
            fileNamesStr = ', '.join(fileNames)
            return f"Uploaded files: {fileNamesStr}"

            
        @self.app.callback(
        Output('url', 'pathname'),
        [Input('redirect-button', 'n_clicks')],
        )
        def redirect_to_flask(n_clicks):
            if n_clicks:
                return '/'

if __name__ == '__main__':
    my_dash_app = AddSpendingsAppWrapper()
    my_dash_app.app.run_server(debug=True)