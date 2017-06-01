from knn import *
import random


wordlist = getKeywords()

casebase = buildCasebase(wordlist)

'''count = 0
for case in casebase:
    count += 1
    pprint("case%d:" % count)
    pprint(vars(case))'''
fcount = 0
for i in range(1,299):
    newcase = casebase[1]
    casebase.remove(newcase)
    predo = computePrediction(newcase,casebase,4)
    actual = newcase.outcome
    if predo == actual:
        result = "success"
    else:
        result = "fail"
        fcount +=1
    print("predicted = " + predo + ", actual = " + actual + "      " + result)
    casebase.append(newcase)
print(fcount)