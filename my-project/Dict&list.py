#dictinary exploring
employees = {
    101: {"name": "Ravi", "salary": 50000},
    102: {"name": "Anita", "salary": 60000},
    103: {"name": "John", "salary": 55000}
}

print(employees[101])  # Output: {'name': 'Ravi', 'salary': 50000}

for emp_id, details in employees.items():
    print(f"Employee ID: {emp_id}, Name: {details['name']}, Salary: {details['salary']}")

#list exploring
#employees1 =["milk" ,"bread" ,"eggs" ,"cheese" ,"fruits" ,"vegetables" ,"meat" ,"fish" ,"cereal" ,"yogurt"]

numbers = [1, 2, 3, 4, 5]
squared_numbers = [num * 2 for num in numbers]  
print(squared_numbers)  # Output: [2, 4, 6, 8, 10]

marks = {101:85, 102:90, 103:78, 104:35, 105:88}
passed_students =  {roll : "ppass" if mark >= 40  else "Failed" for roll, mark in marks.items()}
print(passed_students(103)) 


  