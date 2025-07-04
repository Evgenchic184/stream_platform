import os
import time
from flask import Flask, render_template, Response
from flask_socketio import SocketIO, emit
import subprocess

app = Flask(__name__)
socketio = SocketIO(app)

@app.route('/')
def index():
    try:    
        f = open('history', "r")
        title = os.path.basename(f.readline().strip())
        f.close()
    except:
        title = "history not found"

    return render_template('index_2.html', title=title)

if __name__ == '__main__':
    #socketio.run(app, host='192.168.0.108', port=5000)
    #socketio.run(app, host='10.0.0.12', port=5000)
    app.run(host="0.0.0.0", port=5000)

