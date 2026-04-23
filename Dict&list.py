# #dictinary exploring
# employees = {
#     101: {"name": "Ravi", "salary": 50000},
#     102: {"name": "Anita", "salary": 60000},
#     103: {"name": "John", "salary": 55000}
# }

# print(employees[101])  # Output: {'name': 'Ravi', 'salary': 50000}

# for emp_id, details in employees.items():
#     print(f"Employee ID: {emp_id}, Name: {details['name']}, Salary: {details['salary']}")

# #list exploring
# #employees1 =["milk" ,"bread" ,"eggs" ,"cheese" ,"fruits" ,"vegetables" ,"meat" ,"fish" ,"cereal" ,"yogurt"]

# numbers = [1, 2, 3, 4, 5]
# squared_numbers = [num * 2 for num in numbers]  
# print(squared_numbers)  # Output: [2, 4, 6, 8, 10]

# marks = {101:85, 102:90, 103:78, 104:35, 105:88}
# passed_students =  {roll : "ppass" if mark >= 40  else "Failed" for roll, mark in marks.items()}
# print(passed_students(103)) 

# 3. Data Structures
# Lists (indexing, slicing)
# Tuples
# Sets
# Dictionaries
# Nested data structures
# List comprehensions


# 1. Lists (Most Used)

# 👉 Ordered, mutable (changeable), allows duplicates

  
num = [10,20,30,40,50,10 ]
print(num[-1])

# num1 = [10,20,30,40,50 ]
# print(num1[::2])

# list1 = [10,20,30,40,50 ]
# print(list1[0:3])


# for i in num:
#     print(i)

# num[1]= 30
# print('hi', num[1])

# num.append(60)
# print(num)

# num.insert(1 , 25)
# print(num)

# num.remove(10)
# print(num)


# remove all ocurunce 

# num = [i for i in num if i != 10 ]
# print(num)

# 2---nd method using while loop 

# while 10 in num:
#     num.remove(10)
#     print('while', num)



# 2. Tuples

# # 👉 Ordered, immutable (cannot change))  

# tup = ( 10,20 ,20 ,30,40,50)

# print('tupple1' , tup[0:2])

# print('tupple' ,tup.count(20))


# tup1 = (10,[20,30],40)

# tup1[1].append(50)
# print(tup1)
#####################################################################

# 3. Sets
# 👉 Unordered, unique elements only  {  }

sets = { 10,20,30,40,50,10}
print(sets.add(60))

print(sets)

a= {1,2,3,4,5}
b = {4,5,6,7,8}

print(a.intersection(b))

print(a.difference(b))




