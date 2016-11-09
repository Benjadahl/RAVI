#!/usr/bin/env python3
from flask import *
import sqlite3
import re
import atexit

#BOM stuff
import os
from werkzeug.utils import secure_filename
from BOM.bom import conveter
import shutil

#for tempfiles
UPLOAD_FOLDER = './upload/'
if not os.path.isdir(UPLOAD_FOLDER):
	print(" * Could not find " + UPLOAD_FOLDER + ". Making new")
	os.makedirs(UPLOAD_FOLDER)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

db_name = "RAVI.db"

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

#TODO: Database versioning
def dbInit():
    db = sqlite3.connect(db_name)
    db.execute("""CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY NOT NULL,
                position INTEGER NOT NULL,
                name TEXT,
                data TEXT,
                stencil TEXT,
                program TEXT,
                montage TEXT,
                delivery TEXT,
                comments TEXT,
                components TEXT,
                PCB TEXT,
                visible INTEGER
                )
               """)
    db.execute("""CREATE TABLE IF NOT EXISTS colours (
                id INTEGER PRIMARY KEY NOT NULL,
                position INTEGER NOT NULL,
                name TEXT,
                data TEXT,
                stencil TEXT,
                program TEXT,
                montage TEXT,
                delivery TEXT,
                comments TEXT,
                components TEXT,
                PCB TEXT,
                visible INTEGER
                )
               """)
    db.close()

#Add entry with the name, comments, components and PCB as values
def addEntry(name, data, stencil, program, montage, delivery, comments, components, PCB):
    db = sqlite3.connect(db_name)
    c = db.cursor()
    #Hold on to your butts, this is a long one.
    c.execute("INSERT INTO tasks (position, name, data, stencil, program, montage, delivery, comments, components, PCB, visible) VALUES((SELECT IFNULL(MAX(position), 0) + 1 FROM tasks), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", [name, data, stencil, program, montage, delivery, comments, components, PCB, 1])
    c.execute("INSERT INTO colours (position, name, comments, components, PCB, visible) VALUES((SELECT IFNULL(MAX(position), 0) + 1 FROM colours), ' ', ' ', ' ', ' ', 1)")
    db.commit()
    db.close()

#Update the cell with the ID row. Then the column "column" is set to newValue.
def updateCell(row, column, newValue):
    db = sqlite3.connect(db_name)
    c = db.cursor()
    #Remove anything that isn't a character from a-Z from the column value with a regex. This should help against SQL injection.
    column = re.sub("[^a-zA-Z]","", column)
    c.execute("UPDATE tasks SET " + column + " = ? WHERE id=?", [newValue, row])
    db.commit()
    db.close()

@app.route('/updateRow/', methods=['POST'])
def updateRow():
    row = request.json['id']
    column = request.json['column']
    newValue = request.json['newValue']
    column = headers[int(column)]
    updateCell(row, column, newValue)
    # retrnes a sringe ingore
    return "lol"

@app.route('/hideRow/', methods=['POST'])
def hideRow():
    row = request.json['id']
    updateCell(row, "visible", request.json['visible'])
    #Updates the colour database
    db = sqlite3.connect(db_name)
    c = db.cursor()
    c.execute("UPDATE colours SET " + "visible" + " = ? WHERE id=?", [request.json['visible'], row])
    db.commit()
    db.close()
    return "Row number" + str(row) + " hidden"

def getTasks():
    db = sqlite3.connect(db_name)
    cursor = db.cursor()
    body = []
    for row in cursor.execute("SELECT * FROM tasks WHERE visible=1 ORDER BY position"):
        body.append([row[0], row[2], row[3], row[4], row[5], row[6], row[7], row[10], row[9], row[8]])
        print (row)
    return body

def getColours():
    db = sqlite3.connect(db_name)
    cursor = db.cursor()
    colours = []
    for row in cursor.execute("SELECT * FROM colours WHERE visible=1 ORDER BY position"):
        colours.append([row[0], row[2], row[3], row[4], row[5], row[6], row[7], row[10], row[9], row[8]])
    return colours

def getHiddenTasks():
	db = sqlite3.connect(db_name)
	cursor = db.cursor()
	body = []
	hiddenStates = []
	for row in cursor.execute("SELECT * FROM tasks ORDER BY position"):
		try:
			body.append([row[0], row[2], row[3], row[4], row[5], row[6], row[7], row[10], row[9], row[8]])
			hiddenStates.append(row[11])
			print (row)
		except:
			print("error")
	return [body, hiddenStates]


def getHiddenColours():
    db = sqlite3.connect(db_name)
    cursor = db.cursor()
    colours = []
    for row in cursor.execute("SELECT * FROM colours ORDER BY position"):
        colours.append([row[0], row[2], row[3], row[4], row[5], row[6], row[7], row[10], row[9], row[8]])
    return colours

@app.route("/")
def main():
    headers = ["ID", "Navn", "Data", "Dato", "Deadline", "Lokation", "Ansvarlig", "Opgave", "Prioritet", "Kommentarer", "Komplet"]
    return render_template('index.html', headers=headers, body=getTasks(), colours=getColours(), hiddenStates=[], link="/hidden/")

@app.route("/hidden/")
def hidden():
	tasks = getHiddenTasks()
	headers = ["ID", "Navn", "Data", "Dato", "Deadline", "Lokation", "Ansvarlig", "Opgave", "Prioritet", "Kommentarer", "Komplet"]
	return render_template('index.html', headers=headers, body=tasks[0], colours=getHiddenColours(), hiddenStates=tasks[1],  link="/")

@app.route('/addRow/', methods=['POST'])
def addRow():
    text = request.json['text']
    addEntry(text, "", "", "", "", "", "", "", "")
    return "true"

@app.route('/updateColour/', methods=['POST'])
def updateColour():
    column = headers[int(request.json['column'])]
    db = sqlite3.connect(db_name)
    c = db.cursor()
    c.execute("UPDATE colours SET " + column + " = ? WHERE id=?", [request.json['colour'], str(request.json['row'])])
    db.commit()
    db.close()
    return "true"




@app.route('/bom/', methods=['GET', 'POST'])
def upload_file():
    #Check if there is a request
    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        # if user does not select file, browser also
        # submit a empty part without filename
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file:
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], file.filename))
            #Run the converter
            conveter(UPLOAD_FOLDER + file.filename);
            #Send converted file back to user
            return send_file(UPLOAD_FOLDER + file.filename + ".csv", as_attachment=True)
    #If no file is uploaded send bom html upload site
    return render_template('bom.html')


#Remove tempfiles on exit
@atexit.register
def exit():
    print("Removing temp files")
    shutil.rmtree(UPLOAD_FOLDER)
    os.makedirs(UPLOAD_FOLDER)



if __name__ == "__main__":
    headers = ["id", "name", "data", "stencil", "program", "montage", "delivery", "PCB", "components", "comments"]
    dbInit()
    app.run(debug=True, host="0.0.0.0")
