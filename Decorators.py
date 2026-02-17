# What Is a Decorator? (Plain English)

# A decorator adds extra behavior to a function
# without changing the function’s code.

# Think:

# logging

# timing

# authentication

# validation

# All added from outside.

def add(a, b):
    return a + b

def log_decorator(func):
    def wrapper(*args, **kwargs):
        print(f"Calling function: {func.__name__}")
        result = func(*args, **kwargs)
        print(f"Function {func.__name__} returned: {result}")
        return result
    return wrapper

@log_decorator
def add(a, b, c):
    return a + b + c
add(5, 3,4) 

# **Decorator executes once at definition time, wrapper executes every time at call time**



