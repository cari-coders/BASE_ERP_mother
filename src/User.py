from flask_login import UserMixin
from typing import List

from flask_login import UserMixin

import uuid

import pickle
import base64
import pandas as pd

from typing import List

from src.Backend.src.SQLHandler.SQLLiteHandler import SQLLiteHandler

class User(UserMixin):
    """
    Represents a user with an identifier and a list of roles.

    Attributes:
        id (str or int): The unique identifier of the user.
        roles (List[str]): A list of roles associated with the user.

    Methods:
        __init__: Initializes a new User instance with the specified identifier and roles.
        getRoles: Returns the list of roles associated with the user.
    """

    def __init__(self, roles: List[str]):
        """
        Initializes a new User instance.

        Args:
            id (str or int): The unique identifier of the user.
            roles (List[str]): A list of roles associated with the user.
        """

        self.id = str(uuid.uuid4())

        self.roles = roles

    def getRoles(self) -> List[str]:
        """
        Returns the list of roles associated with the user.

        Returns:
            List[str]: A list of roles.
        """
        return self.roles

    def __repr__(self): 
        return f"User(id={self.id}, roles={self.roles})"
    
class UserManagement:
    
    def __init__(self):
        self.sqlLiteHandler = SQLLiteHandler('flaskUser')


    def getNewUserWithRoles(self, roles: List[str]):
    
        # crate new user
        userInstance = User(roles)
        
        #serialize the class instance to store it
        serializedUserInstance = base64.b64encode(pickle.dumps(userInstance)).decode('utf-8')

        # store user in database
        self.sqlLiteHandler.appendDataToTable(pd.DataFrame([[userInstance.get_id(), serializedUserInstance]], columns = ['id', 'serializedInstance']))

        # store it in database
        return userInstance
    
    def queryWithId(self, id: str):
        
        df = self.sqlLiteHandler.getColumnsFromTableWithCondition('id', id)

        # if the user is not in the databas, return None
        if df.empty:
            return None
        
        # else, get the serialized instance from the DF and deserialize is
        serializedUserInstance = df.loc[df['id'] == id, 'serializedInstance'].values[0]
        userInstance = pickle.loads(base64.b64decode(serializedUserInstance.encode('utf-8')))

        return userInstance