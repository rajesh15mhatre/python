# Python based projects setup

## Set up keys for github
- first generate ssh keys using gitbash  in you local machine 
- $ ssh-keygen -t rsa -b 4096 -C "youremail@domain.com"
- store generated keys in .shh diretory 
- add public key in you git hosting service provider like github

then run bat file stored in `scripts/setup_github_keys.bat` to setup github, post setup clone your repo

## Git config
in order to post your chanages to github add below config:

git config --global user.email "you@example.com"

git config --global user.name "Your Name"

## Run as module
- Create __init__.py file in each folder to run pipeline as a module
- Make sure you have updated your launch.json file and select default python interpreter in setting -> search select python -> select desired python setup

# Creating virtual env - Windows
## Find your python setup and add that directory path to environment variable also for pip to work; add /Scripts folder path  to 'Path' env variable in user setting 
## Then install pipenv env manager
pip install pipenv
## Create  virtual env in the desired project directory 
pipenv install --python 3.8
## if pipenv is not recognised then either make below setting or use below alternate command
python -m pipenv install --python 3.x
  # settings - Add path to env variable C:\Users\user\AppData\Roaming\Python\Python310\Scripts

