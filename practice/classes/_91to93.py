# Resturant class 9.1
class Resturant():
    """"this class represent a resturant"""
    def __init__(self, resturant_name, crusine_type):
        """This is a constructor class"""
        self.resturant_name = resturant_name
        self.crusine_type = crusine_type
    
    def describe_resturant(self):
        """This method describes resturant"""
        print(f"{self.resturant_name} serves {self.crusine_type}")
    
    def open_resturant(self):
        """This method opens resturant"""
        print(f"{self.resturant_name} resturant is open now")


resturant = Resturant("Sai Krupa", "Italian")
print(f"Resturant {resturant.resturant_name} has best {resturant.crusine_type} crusine in the panvel city")
resturant.describe_resturant()
resturant.open_resturant()

# exercise 9.2
resturant_1 = Resturant("Sai deep", "Agri")
resturant_1.describe_resturant()
resturant_2 = Resturant("Malvan Tadaka", "Malavani")
resturant_2.describe_resturant()
resturant_3 = Resturant("Venkat Residency", "Chinese")
resturant_3.describe_resturant()

# Exercise 9.3
class User():
    """This class respresent users stores many attributes"""
    def __init__(self, first_name, last_name, **user_info):
        """this is constructor class"""
        self.user_info = {}
        self.user_info["user_first_name"] = first_name
        self.user_info["user_last_name"] = last_name
        for k, v in user_info.items():
            self.user_info[k]=v
    
    def describe_users(self):
        """This method describes user by printing attributes"""
        print(f"This is user information: {self.user_info}")
    
    def greet_user(self):
        """this method greets user"""
        print("Wecome "+self.user_info["user_first_name"]+" "+self.user_info["user_last_name"])

user_1 = User("Rajesh", "mhatre", age=38, sport="TT")
user_1.describe_users()
user_1.greet_user()

user_2 = User("Harshal", "Patil", age=58, sport="FUgadi")
user_2.describe_users()
user_2.greet_user()
