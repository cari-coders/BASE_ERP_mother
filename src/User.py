from flask_login import UserMixin
from typing import List

from flask_login import UserMixin

import uuid

import pickle
import base64
import pandas as pd

from typing import List

from src.Backend.src.SQLHandler.SQLHandler import SQLHandler

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
        """
        representation function: meant to return an unambiguous (eindeutige) string representation of an object 
        that can be used, for instance, to reproduce the same object when fed to the eval() function.

        Returns:
            str: a string containing unambigous information about the users id and roles.
        """
        return f"User(id={self.id}, roles={self.roles})"
    
class UserManagement:
    """
    A class for managing user operations, based on the User class defined above.

    Methods:
    - __init__(self):
        Initializes the UserManagement object with a SQLLiteHandler instance.

    - getNewUserWithRoles(self, roles: List[str]):
        Creates a new user instance with specified roles.
        Serializes the user instance and stores it in the database.

    - queryWithId(self, id: str):
        Queries the database for a user with the specified ID.
        Returns the user instance if found, otherwise returns None.
    """
    def __init__(self):
        """
        Initializes the UserManagement object with a SQLLiteHandler instance.
        """
        self.sqlLiteHandler = SQLHandler('flaskUser', '/home/matt/workspace/BASE/Finanztool/BASE_ERP_mother/config/TableDefinitions.yaml')


    def getNewUserWithRoles(self, roles: List[str]):
        """
        Creates a new user instance with specified roles.
        Serializes the user instance and stores it in the database.

        Args:
        - roles (List[str]): List of roles for the new user.

        Returns:
        - User: Newly created user instance.
        """

        # crate new user
        userInstance = User(roles)
        
        #serialize the class instance to store it
        serializedUserInstance = base64.b64encode(pickle.dumps(userInstance)).decode('utf-8')

        # store user in database
        self.sqlLiteHandler.appendDataToTable(pd.DataFrame([[userInstance.get_id(), serializedUserInstance]], columns = ['id', 'serializedInstance']))

        # store it in database
        return userInstance
    
    def queryWithId(self, id: str):
        """
        Queries the database for a user with the specified ID.
        Returns the user instance if found, otherwise returns None.

        Args:
        - id (str): ID of the user to query.

        Returns:
        - User or None: User instance if found, otherwise None.
        """
               
        df = self.sqlLiteHandler.getColumnsFromTableWithCondition('id', id)

        # if the user is not in the databas, return None
        if df.empty:
            return None
        
        # else, get the serialized instance from the DF and deserialize is
        serializedUserInstance = df.loc[df['id'] == id, 'serializedInstance'].values[0]
        userInstance = pickle.loads(base64.b64decode(serializedUserInstance.encode('utf-8')))

        return userInstance