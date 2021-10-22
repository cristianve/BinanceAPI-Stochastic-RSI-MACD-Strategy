from threading import Thread

def func1():
    print('Working')

def func2():
    print("Working")

if __name__ == '__main__':
    Thread(target = func1).start()
    Thread(target = func2).start()