#function

# def get_high_score(marks):
#     result = {}
#     for student, mark in marks.items():
#         if mark >= 90:
#             result[student] = "A"
#         elif mark >= 80:
#             result[student] = "B"
#         elif mark >= 70:
#             result[student] = "C"
#         elif mark >= 60:
#             result[student] = "D"
#         else:
#             result[student] = "F"
#     return result

# marks = {"Alice": 95, "Bob": 82, "Charlie": 78, "David": 65, "Eve": 55}
# high_scores = get_high_score(marks)

# print (high_scores)  

# def get_high_score(marks):
#     return {roll: mark for roll, mark in marks.items() if mark >= 80}
# marks = {101: 95, 102: 82, 103: 78, 104: 65, 105: 55}
# high_scores = get_high_score(marks)
# print(high_scores)

# def get_high_score(marks):
#     return[
#         (studentid,
#             "A" if mark >= 90 else
#             "B" if mark >= 80 else
#             "C" if mark >= 70 else
#             "D" if mark >= 60 else
#             "F"
#         )
#         for studentid, mark in marks.items()
#     ]

# marks = {101: 95, 102: 82, 103: 78, 104: 65, 105: 55}
# print(get_high_score(marks))

#Calling a Function Inside Another Function#########################

# def ishighscorrer(mark):
#     return mark >= 95

# def get_high_score(marks):
#     result = {}
#     for studentid , mark in marks.items():
#         if ishighscorrer(mark):
#             result[studentid] = "ppass"
#         else:
#             result[studentid] = "Fail"
#     return result

# marks = {101: 95, 102: 82, 103: 78, 104: 65, 105: 55}
# print(get_high_score(marks))

# *args & **kwargs

# def totalmarks(*args):
#     return sum(args)
# print(totalmarks(85,  78, 65, 55))
# def process_data(* args):
#     return sum(args)

# def wrapper(*args):
#     print("Before function call")
#     result = process_data(*args)
#     print("After function call")
#     return result

# print(wrapper(10, 20 ,30))


## default parameter for function 

def greet(name, message="Hello"):
    return message + " " + name

print(greet("Ravi"))           # Hello Ravi
print(greet("Ravi", "Hi"))     # Hi Ravi
print(greet("Ravi", message="Welcome"))  # Welcome Ravi


