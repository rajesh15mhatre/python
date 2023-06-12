# Python based projects setup

## Set up keys for github
- first generate ssh keys using gitbash  in you local machine 
- ssh-keygen -t rsa -b 4096 -C "youremail@domain.com"
- store generated keys in .shh diretory 
- add public key in you git hosting service provider like github

then run bat file stored in `scripts/setup_github_keys.bat` to setup github, post setup c`lone your repo

## Git config`
in order to post your chnages add below config:

git config --global user.email "you@example.com"

git config --global user.name "Your Name"

## Run as module
- Create __init__.py file in each folder to run pipeline as a module
- Make sure you have updated your launch.json file and select default python ineterpreter in setting -> search select python -> select desired python setup
