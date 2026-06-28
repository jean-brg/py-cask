from flask import Flask, render_template
from cask.core import Cask

app = Cask(__name__, app_name="My Cask App")

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/about')
def about():
    return render_template('about.html')

if __name__ == '__main__':
    app.run_as_app(icon="./static/favicon.ico")