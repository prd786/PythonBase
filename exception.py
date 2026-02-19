# #Exceptions & Error Handling

# try:
#     a= int(input("enter a number"))
#     b = int(input("enter a seconf number "))
#     print(a/b)
# except ZeroDivisionError:
#     print("Error: Division by zero is not allowed.")
# except ValueError:
#     print("Error: Please enter valid integers.")
# finally:
#     print("This block will always execute, regardless of exceptions.")   


#user defined exceptions

# built in exceptions:
# 1) ValueError
# 2) TypeError
# 3) IndexError
# 4) KeyError

class invalidagexception(Exception):
    def __init__(self , message):
        self.message = message
        super().__init__(self.message)



def checkage(age):
    if age < 18:
        raise invalidagexception("Age must be at least 18.")
    else:
        print("Age is valid.")

try:
    print(checkage(15))
except ValueError as e:
   raise invalidagexception("Invalid age: " + str(e)) from e








