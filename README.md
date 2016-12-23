# Writing Reusable Code Feedback at Scale with Mixed-Initiative Program Synthesis 
by A Head, EL Glassman, G Soares, R Suzuki, L Figueredo, L D'Antoni and B Hartmann 
Presented at *ACM Learning at Scale 2017*

## Abstract

## Demo Video

# Refazer Grading Application

## Running the App Locally

First, install python3.

Clone this repository.
Create virtual environment in the cloned folder:

    virtualenv venv
    source venv/bin/activate  # initializes the virtual environment

Install Python dependencies:

    pip install -r requirements.txt

Initialize the local database:

    sqlite3 flaskr.db < db/init.sql

Add data from student submissions to the local database:

    PYTHONPATH=.:$PYTHONPATH python util/load_data.py file data/accumulate-mistakes.json 0 flaskr.db --prettify-code
    PYTHONPATH=.:$PYTHONPATH python util/load_data.py file data/Product-mistakes.json 1 flaskr.db --prettify-code
    PYTHONPATH=.:$PYTHONPATH python util/load_data.py file data/repeated-mistakes.json 2 flaskr.db --prettify-code

Run unit tests to group the submissions:

    PYTHONPATH=.:$PYTHONPATH python util/pretest_submissions.py flaskr.db

## Deploying the app to a server

See the `deploy` directory.
The `deploy` script in the `deploy` directory calls Ansible scripts to provision a machine to run the grader application.

## Running data processing scripts

The `data_processing` directory includes scripts to process some of the data from the local database into the measurements we reported in the paper.
Details about what commands to run are forthcoming.
