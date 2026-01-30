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
        info_string = f.readline().strip().split(":")
        title = os.path.basename(info_string[0])
        f.close()
    except:
        title = "history not found"
        
    time_to_reload = 20 * 60
    time_start = float(info_string[1])
    time_duration = float(info_string[2])
    if time_start != 0 and time_duration != 0:
        time_to_reload = time_start + time_duration - time.time()
    return render_template('index_2.html', title=title, time_to_reload=int(time_to_reload * 1000))

if __name__ == '__main__':
    #socketio.run(app, host='192.168.0.108', port=5000)
    #socketio.run(app, host='10.0.0.12', port=5000)
    app.run(host="0.0.0.0", port=5000)

