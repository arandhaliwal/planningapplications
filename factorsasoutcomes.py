import json
from pprint import pprint
import os
import sys
import re

def getKeywords():
    with open("keywords.txt","r") as keywords:
        wordlist = []
        for line in keywords:
            wordlist.append(line)
        wordlist = [i.strip() for i in wordlist]
    return wordlist

def getFactor():
    with open("factorinput.txt","r") as input:
        factor = input.read()  
    return factor
    
def extract(text,wordlist):
    """Gets the keywords from a text excerpt."""
    result = []
    for keyword in wordlist:
        if keyword in text:
            result.append(keyword)
    result = ["screen" if x == "screening" 
               else "glazed" if x == "glazing"
               else "roof slope" if x == "roofslope"
               else x for x in result]
    result = set(result)
    return result
    
class Case:

    def __init__(self, args, outcome,attacks,attackedby,origtext):
        self.args = args
        self.outcome = outcome
        self.attacks = attacks
        self.attackedby = attackedby
        self.origtext = origtext
              
        
def buildCasebase(wordlist):
    with open('app.json') as datafile:
        data = json.load(datafile) 
    casebase = []
    factor = getFactor()
    defaultcase = Case([],'not %s' % factor,[],[],'DEFAULT')
    casebase.append(defaultcase)
    for datum in data:
        outcome = datum["decision"][0].strip()
        origtext = datum["proposal"][0].strip()
        if (outcome == 'Application Approved'):
            args = []
            proposal = extract(datum["proposal"][0].strip(),wordlist)
            if factor in proposal:
                proposal.remove(factor)
                outcome = factor
            else:
                outcome = 'not %s' % factor
            constraints = [(x.replace(":","")).strip() for x in datum["constraints"]]
            args.append(proposal)
            args.append(constraints)
            args = [item for sublist in args for item in sublist]
            case = Case(args,outcome,[],[],origtext)
            casebase.append(case)
    return casebase
  
def getNewCase(wordlist):  
    with open("proposalinput.txt","r") as input:
        proposal = input.read()  
            
    args = extract(proposal,wordlist)
    constraints = []
    with open("constraintsinput.txt","r") as input2:
        for line in input2:
            constraints.append(line.strip())
        args.update(constraints)
        
    newcase = Case(args,"Outcome Unknown",[],[],'NEWCASE: ' + proposal)
    return newcase

'''count = 0
for case in casebase:
    count += 1
    pprint("case%d:" % count)
    pprint(vars(case))'''
    
def differentoutcomes(a,b):
    return a.outcome != b.outcome

#A is more specific than B
def specificity(a,b):
    return set(b.args).issubset(set(a.args))
    
# there does not exist another case in cases which is less specific than a and more specific than b with the same outcome as a
def concision(cases,a,b):
    return not any((specificity(a,case) and specificity(case,b) and not(differentoutcomes(a,case)) and (case != a) and (case!=b)) for case in cases)


def attacks(cases,a,b):
    return differentoutcomes(a,b) and specificity(a,b) and concision(cases,a,b)
    
def newcaseattacks(newcase,targetcase):
    return not specificity(newcase,targetcase)
    
'''def isnearest(case,newcase,casebase):
    return specificity(newcase,case) and (not any (specificity(newcase,othercase) and specificity(othercase,case) and case != othercase for othercase in casebase))
  
def printnearest(newcase,casebase):
    for case in casebase:
        if isnearest(case,newcase,casebase):
            pprint(vars(case))'''
            
#case1 is default case
def computePrediction(newcase,casebase):
    factor = getFactor()
    f = open("input.dl","w+")
    count = 0
    for case in casebase:
        count += 1
        f.write("arg(case%d).\n" % (count))
    f.write("arg(newcase).\n")
    count1 = 0
    for case in casebase:
        count1 += 1
        count2 = 0
        for othercase in casebase:
            count2 += 1
            if attacks(casebase,case,othercase):
                f.write("att(case%d,case%d).\n" % (count1,count2))
                case.attacks.append(othercase)
                othercase.attackedby.append(case)
        if newcaseattacks(newcase,case):
            f.write("att(newcase,case%d).\n" % (count1))
            newcase.attacks.append(case)
            case.attackedby.append(newcase)
    f.close()

    os.system("gringo --warn none ground.dl input.dl | clasp 0 >extension.txt")
            
    #print("Prediction:")
    if 'in(case1)' in open('extension.txt').read():  
        return('not %s' % factor)
    else:
        return(factor)
        
def getGroundedExtension(casebase,newcase):
    with(open("extension.txt")) as extension:
        for line in extension:
            if line.startswith("in"):
                groundedextension = line
            
    ge = re.findall(r'\d+', groundedextension)
    ge = [int(s) for s in ge]
    ge = [casebase[x-1] for x in ge]
    if "newcase" in groundedextension:
        ge.append(newcase)
    return ge
    
def recursivefunctiondisagree(tree,case,count,newcase,ge):
    treecopy = list(tree)
    nextcase = case.attackedby[count]
    treecopy.append(nextcase)
    if nextcase.attackedby == []:
        return treecopy
    else:
        return recursivefunctionagree(treecopy,nextcase,ge,newcase)

def recursivefunctionagree(tree,case,ge,newcase):
    biglist = []
    for nextcase in ge:
        if case in nextcase.attacks:
            treecopy = list(tree)
            treecopy.append(nextcase)
            if nextcase.attackedby == []:
                biglist.append(treecopy)
            else:
                count = 0
                for next2case in nextcase.attackedby:
                    biglist.append(recursivefunctiondisagree(treecopy,nextcase,count,newcase,ge))
                    count += 1
    return biglist
        
def flatten(mylist):
    for i in mylist:
        if isinstance(i, (list,tuple)):
            for j in flatten(i):
                yield j
        else:
            yield i  

def computeExplanation(agreement,ge,casebase,newcase):
    if agreement:        
       treeslist = []
       for case in casebase[0].attackedby:
           treebase = [casebase[0],case]
           treeslist.append(recursivefunctionagree(treebase,case,ge,newcase))
    else:
        treeslist = []
        for case in ge:
            if casebase[0] in case.attacks:
                treebase = [casebase[0],case]
                if case.attackedby == []:
                    treeslist.append(treebase)
                else:
                    count = 0
                    for nextcase in case.attackedby:
                        treeslist.append(recursivefunctiondisagree(treebase,case,count,newcase,ge))
                        count += 1
    treeslist = list(flatten(treeslist))  

    sublist = []
    trees = []
    for case in treeslist:
        if case == casebase[0]:
            if sublist: 
                trees.append(sublist)
            sublist = [case]
        else:
            sublist.append(case)
    trees.append(sublist)
    return trees

def printExplanation(trees):
    for tree in trees:     
        for case in tree:
            print(case.origtext)
            print("Outcome " + case.outcome)
            if tree[len(tree)-1] != case:
               print("\nis attacked by...\n")
            else:
                print("\nwhich is unattacked\n")
        if trees[len(trees)-1] != tree:
           print("OR\n")