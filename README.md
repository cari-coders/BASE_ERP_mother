# BASE_ERP_mother
This repo contains the General Documentation of the ERP Project as well as the 'HomeScreen' Server. This server displays the buttons to access the different tools, depending on the access rights of the user. 

## Associated Repositorys
The reposetory 'Backend' is included in this reposetory as submodule.

## Functionalities/Workflow

The authentication process works as followed:

1. a
2. b
3. c


## Required Environment Variables
following environment variables are loaded by the server:

variable name | variable description
---|---
DEBUG_LEVEL | boolean, wether debug is On or Off.
HTTPS_ACTIVE | boolean, True if the communication between the containers is via 'https', False otherwise
AUTHENTICATION_SERVER_PORT | Port of the server in the network (defined by 'BASE_URL') that manages the authentication (nextcloud in our case)
HOMESCREEN_SERVER_PORT | port of the HomeScreenServer (the server defined by this reposetory)
BASE_URL | The URL of the Network of the NcOAuthServer; the server redirects responses to defined ports in that network
GLOBAL_CONFIG_PATH | path to the global config file (located in backend)



## Route Protection

The Homescreen Server manages the access to the different routes (the subsites of the server). The access to the routes must be user specific, depending on the access rights of the user. This can be applied in the code by using decorator functions.

Decorators allow you to modify or enhance the behavior of functions or methods without changing their actual code. Decorators wrap a function, allowing you to execute code before and after the wrapped function runs, effectively enabling aspect-oriented programming.

Within the decorator, we can check if the user has sufficient rights to enter the route. An example can be found in the following lines:

```python
from functools import wraps
from flask import flash, redirect, url_for
from flask_login import current_user

def role_required(*roles):  # name of the decorator
    def decorator(f):       # start definition of the decorator for the wrapped functin 'f'
        @wraps(f)           # this line preserve the wrapped function's metadata, such as its name, docstring, and module information
        def decorated_function(*args, **kwargs):    #call 'decorated_function' using the arguments with wich 'f' is called
            # check if the user is actually logged in (# TODO koennte man eventuell auch mit dem @login_requiered decorator machen (?))
            if not current_user.is_authenticated:
                # if not logged in, redirect to login page
                return redirect(url_for('login'))
            if not current_user.role in roles:
                # user does not have the required role: show an error or redirect ? Wie handeln wir das?
                flash('You do not have permission to access this page.')
                return redirect(url_for('index'))
            # if the user has the required role/the required access rights, run the wrapped function 'f'
            return f(*args, **kwargs)

        return decorated_function
    
    return decorator
```

This decorator can be applied to wrap functions as one can see in the following example:

```python
@app.route('/protected-route')
@role_required('admin')  # only allow access for admins (whatever an admin is in our case)
def special_area():
    return 'This is a protected route for admins.'
```
