from flask import Flask, jsonify, request
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)

@app.route('/')
def index():
    return '
    '


if __name__ == '__main__':
    app.run(debug=True)