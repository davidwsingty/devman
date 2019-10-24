#!/usr/bin/python
# Name: ASR Validation utility
# Author: David Ingty <david.ingty@oracle.com>
# Language: Python 2.7.10
# Last Edited: 2019-10-24 01:35 IST (GMT +5:30)


from flask import Flask, render_template, session, redirect, url_for, request
import os, re

app = Flask(__name__)
app.secret_key = "my_secret_key"
script_path = "/opt/asrvalidationscript/asrvalidator.py"
flask_templates_path = "/opt/asrvalidationscript/templates/"
file_contents = ""
myserials = []
out_file_name = ""



def writer(filename, listname):
    with open(filename, 'w') as f:
        for eachline in listname:
            f.write(eachline)



def get_serials():
    with open(out_file_name, 'r') as file:
        global file_contents
        file_contents = file.readlines()
        for line in file_contents:
            if ":->" in line:
                line = line.split(':')
                myserial = line[0]
                if myserial not in myserials:
                    myserials.append(myserial)



@app.route("/", methods=['GET', 'POST'])
def home():
    if request.method == "POST":    # checks if the user clicked the submit button
        srnum = request.values.get('srnum')     # get the srnumber value of field from the form
        list_asset = request.form['list_asset'] # get the list_asset value of field from the form
        ib = request.form['ib']  # get the ib value of field from the form
        
        if os.path.exists(srnum + 'list_asset.txt'):
            os.remove(srnum + 'list_asset.txt')

        if os.path.exists(srnum + 'ib.txt'):
            os.remove(srnum + 'ib.txt')

        writer(srnum + 'list_asset.txt', list_asset)  # write list_asset file in flask app dir
        writer(srnum + 'ib.txt', ib)   # write ib file in flask app dir
        os.system('/usr/bin/python /opt/asrvalidationscript/asrvalidator.py ' + srnum)    # execute the validation script
        #os.system('python /opt/asrvalidationscript/asrvalidator.py ' + srnum)
        # path where result outputs are stored under templates dir
        in_file_name = flask_templates_path + srnum + "-out.html"
        global out_file_name
        out_file_name = flask_templates_path + srnum + "-out.html"

        # creating jinj2 template format for "out_file_name" file.
        with open(in_file_name, 'r') as f:
            global file_contents
            file_contents = f.read()

        with open(out_file_name, 'w') as r:
            r.write("{% extends \"layout.html\" %}")
            r.write("{% block content %}")
            r.write("<pre>")

        with open(out_file_name, 'a') as r:
            for line in file_contents:
                r.write(line)
            r.write("</pre>")
            r.write("{% endblock content %}")

        get_serials()

        for serial in myserials:
            os.system("sed -i 's/{}/<a href=https:\/\/fems.us.oracle.com\/FEMSService\/resources\/femsservice\/femsview\/{} target=\"_blank\">{}<\/a>/g' {}"\
                .format(serial, serial, serial, out_file_name))

        return render_template(srnum + "-out.html")


    # Default page to be rendered!
    return render_template('home.html')



if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=8000)


