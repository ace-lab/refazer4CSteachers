# Refazer Grading Application

## Running the App Locally

First, install python3.

Then clone this repository.
Create virtual environment in the cloned folder:

    virtualenv venv
    source venv/bin/activate  # initializes the virtual environment

Install the Python dependencies:

    pip install -r requirements.txt

Initialize the local database:

    sqlite3 flaskr.db < db/init.sql

Then load student submission data into the database.
This should be in the form of a `json` file.
Contact the project maintainer if you need access to this data.

Once you have downloaded the data as `json` files, you can load it into the database with the `load_data.py` script:

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
