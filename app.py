# class CarInputError(Exception):
#     pass

# class Car:
#     def engine(self, power):
#         if not isinstance(power, str) or not power.strip():
#             raise CarInputError("Engine power must be a non-empty string.")
#         self.power = power

#     def chasis(self, size):
#         if not isinstance(size, str) or not size.strip():
#             raise CarInputError("Chasis size must be a non-empty string.")
#         self.size = size

# try:
#     car = Car()
#     car.engine(150)
#     car.chasis("hello")

#     print("Engine power:", car.power)
#     print("Chasis size:", car.size)
# except CarInputError as e:
#     print("Input Error:", e)




