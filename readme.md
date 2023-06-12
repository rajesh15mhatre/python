#Python based projects

## Set up keys for github
- first generate ssh keys using gitbash  in you local machine 
ssh-keygen -t rsa -b 4096 -C "rajesh15mhatre@gmail.com"
store generated keys in .shh diretory 
add public key in you git hosting service proviser like github

then run bat file to setup github, post setup clone your repo

## Git config
in order to post your chnages add below config
git config --global user.email "you@example.com"
git config --global user.name "Your Name"

## run as module
Create __init__.py file in each folder to run pipeline as a module

