#!/usr/bin/env python

import sys
import time

if __name__ == '__main__':
    print("Hellooo from python main")
    print("This is the name of the script: ", sys.argv[0])
    print("Number of arguments: ", len(sys.argv))
    print("The arguments are: ", str(sys.argv))
    sys.stdout.flush()
 # Add these lines in to keep the pod up so you can /bin/ash, YES ash into it
    for i in range(10000):
       print(i)
       sys.stdout.flush()
       time.sleep(20)
