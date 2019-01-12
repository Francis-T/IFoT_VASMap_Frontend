from flask import Flask

app = Flask(__name__)

from ifot_vasmap import routes

