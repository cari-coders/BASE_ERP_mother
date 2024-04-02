# Server 2: Application Server

from flask import Flask, request, redirect, url_for, session
import os




app = Flask(__name__)
app.secret_key = 'debug'#os.getenv('SECRET_KEY', 'another_secret_key')  # Should also be a random secret!

@app.route('/')
def home():
    user_email = session.get('email')
    user_groups = session.get('groups')
    if user_email:
        return f'Welcome, {user_email}! Groups: {user_groups}'
    else:
        return 'Welcome! Please <a href="http://127.0.0.1:5000/login">log in</a>.'

@app.route('/verify')
def verify():
    # Server 1 redirects here after authentication
    email = request.args.get('email')
    groups = request.args.get('groups', '').split(',')
    
    # Store the user information
    session['email'] = email
    session['groups'] = groups
    
    return redirect(url_for('home'))

@app.route('/logout')
def logout():
    session.pop('email', None)
    session.pop('groups', None)
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True, port=5001)
