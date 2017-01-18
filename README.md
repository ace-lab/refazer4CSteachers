# OverHint

##Running the App Locally
1. Install python3
2. Clone https://github.com/lucasmf/HerokuUI
3. Create virtualenvironment in cloned folder and run 
  - ```pip3 install -r requirements.txt```
  - ```python3 flaskr.py```

##Running the App on Heroku
1. Create heroku login
2. Create an app on the heroku site
3. Install heroku toolbelt from https://toolbelt.heroku.com/
4. Login at your own terminal by running heroku login
5. Establish heroku as a new remote by running ```heroku git:remote -a [name of your app]```
6. Push the app to heroku: ```git push heroku master```
