#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# C++ Insights Web, copyright (c) by Andreas Fertig
# Distributed under an MIT license. See /LICENSE

import datetime
from urllib import quote, unquote, unquote_plus

from flask import Flask, make_response, render_template, request, send_from_directory

import subprocess
import base64
import os
import tempfile
#------------------------------------------------------------------------------

app = Flask(__name__, static_folder='static', static_url_path='')
#------------------------------------------------------------------------------

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')
#------------------------------------------------------------------------------

def robust_encode(data):
    try:
        return data.encode()
    except UnicodeDecodeError:
        return data
#------------------------------------------------------------------------------

def robust_decode(data):
    try:
        return data.decode('utf8')
    except UnicodeDecodeError:
        return data.decode('latin1')
#------------------------------------------------------------------------------

def runDocker(code):
    fd, fileName = tempfile.mkstemp(suffix='.cpp')
    try:
        with os.fdopen(fd, 'w') as tmp:
            # write the data into the file
            tmp.write(code)

        # FIXME (jim 2018-04-28): workaround as docker pfes user cannot read file without this
        os.chmod(fileName, 436)

        # on mac for docker file must be under /private where we also find var
        # For Mac: '/private%s:/home/insights/insights.cpp' %(fileName)
        cmd = ['sudo', '-u', 'pfes', 'docker', 'run', '--net=none', '-v', '%s:/home/insights/insights.cpp' %(fileName), '--rm', '-i', 'insights-test']
        #cmd = [ 'docker', 'run', '--net=none', '-v', '/private%s:/home/insights/insights.cpp' %(fileName), '--rm', '-i', 'insights-test']
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = p.communicate()
        returncode     = p.returncode
    finally:
        os.remove(fileName)

    return stdout, stderr, returncode
#------------------------------------------------------------------------------

@app.route("/", methods=['GET', 'POST'])
def index():
        code = request.form.get('code', request.cookies.get('code', """#include <cstdio>
#include <vector>

int main()
{
    const char arr[10]{2,4,6,8};

    for(const char& c : arr)
    {
      printf("c=%c\\n", c);
    }
}"""))
        code = robust_encode(code)
        stdout, stderr, returncode = runDocker(code)

        if (None == stderr) or ('' == stderr):
            stderr = 'Insights exited with result code: %d' %(returncode)

#        repr(stdout)

        stderr = robust_decode(stderr)
        html   = robust_decode(stdout)

        if returncode:
            html = "Compilation failed!"

        next_year = datetime.datetime.now() + datetime.timedelta(days=365)

        response = make_response(render_template('index.html', **locals()))
        # store the last example in a cookie
        response.set_cookie('code', code, expires=next_year)

        return response
#------------------------------------------------------------------------------

@app.route("/lnk", methods=['GET', 'POST'])
def api():
    code = request.args['code']
    rev  = request.args['rev']

    if not code or not rev or '1.0' != rev:
        response = make_response(render_template('error.html'))
        return response

    try:
        # keep this in mind if, we get a incorrect length base64 string
        #code = code + '=' * (-len(code) % 4)
        # XXX: somehow we get a curropt base64 string
        code = code.replace(' ', '+')

        # base 64 decode
        code = code.decode('base64')

        next_year = datetime.datetime.now() + datetime.timedelta(days=365)
        response  = make_response(render_template('index.html', **locals()))

        # store the last example in a cookie
        response.set_cookie('code', code, expires=next_year)

    except:
        print repr(code)

    return response
#------------------------------------------------------------------------------


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

# for debugging/testing disable caching
@app.after_request
def add_header(r):
    """
    Add headers to both force latest IE rendering engine or Chrome Frame,
    and also to cache the rendered page for 10 minutes.
    """
    r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    r.headers["Pragma"] = "no-cache"
    r.headers["Expires"] = "0"
    r.headers['Cache-Control'] = 'public, max-age=0'
    return r
#------------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(host='0.0.0.0')
#------------------------------------------------------------------------------

