# import time 
    
# start = time .perf_counter()

# arr = [52,95,3,6,8,10,1,2,1]

# arr.sort()

# end = time .perf_counter()    

# print("hello tim sort" , start , end)




# def quicksort (arr):
#     if len(arr) <= 1:
#         return arr
    
#     pivot = arr[len(arr) // 2]
    
#     left  = [x for x in arr if x < pivot]
#     equal = [x for x in arr if x == pivot]
#     right = [x for x in arr if x > pivot]

#     return quicksort(left) + equal + quicksort(right)

# data = [52,95,3,6,8,10,1,2,1]
# print(quicksort(data))

# data.sort()
# print("hello tim sort" ,data)



def insertionSort(arr):
    for i in range(1, len(arr)):
        key = arr[i]
        j = i-1
        while j >= 0 and key < arr[j] :
                arr[j + 1] = arr[j]
                j -= 1
        arr[j + 1] = key


arr = [52,95,3,6,8,10,1,2,1]
insertionSort(arr)
print ("Sorted array is:", arr)







