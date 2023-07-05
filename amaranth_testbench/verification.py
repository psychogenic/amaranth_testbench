'''
Created on May 23, 2023

@author: Pat Deegan
@copyright: Copyright (C) 2023 Pat Deegan, https://psychogenic.com
'''

from amaranth_testbench.cli import CLI
from amaranth import Module, Signal

import logging 
log = logging.getLogger(__name__)


def signalTrue(s: Signal):
    return s.bool()

def signalFalse(s: Signal):
    return ~(s.bool())

def oneBitHot(sig:Signal, allowAllZero:bool=False):
    numBits = len(sig)
    
    if numBits == 1:
        if allowAllZero:
            raise ValueError('asking for oneBitHot for one-bit signal while allowing 0 state--always true')
        
        # this is a single bit signal
        return signalTrue(sig)
        
        
    sigBitsAsList = []
    for i in range(numBits):
        sigBitsAsList.append(sig[i])
        
    return oneHot(sigBitsAsList, allowAllZero)

def oneHot(signalsList:list, allowAllFalse:bool=False):
    '''
        compound statement that describes one-hot logic
        
        @param signalsList: [list, of, signals]
        @param allowAllFalse: whether to include all false as valid state [False]
        
         
    '''
    
    if type(signalsList) == type(Signal):
        return oneBitHot(signalsList)
    
    
    numSigs = len(signalsList)
    if not numSigs:
        raise ValueError('calling one hot with empty list')
    
    if numSigs == 1:
        return oneBitHot(signalsList[0])
    
    
    allZeroStatement = signalFalse(signalsList[0])
    oneHotStatementsList = []
    
    # for each signal, construct
    #  SIG is TRUE & ALLOTHER are FALSE
    for i in range(numSigs):
        oneH = signalTrue(signalsList[i])
        for j in range(numSigs):
            if i != j:
                oneH = oneH & signalFalse(signalsList[j])
        
        oneHotStatementsList.append(oneH)
        
    
    if allowAllFalse:
        for i in range(1, numSigs):
            allZeroStatement = (allZeroStatement | signalFalse(signalsList[i]))
        
    # allow any of the one-hot (sig is true, all other false, foreach sig)
    # to be active using OR
    oneHotPossibs = oneHotStatementsList[0]
    for i in range(1, numSigs):
        oneHotPossibs = oneHotPossibs | oneHotStatementsList[i]
        
    if allowAllFalse:
        return (allZeroStatement | oneHotPossibs)
    
    return oneHotPossibs


class Verification:
    Verbose = True
    DepthProbingEnable = False
    KnownGroups = dict()
    
    @classmethod 
    def groupKnown(cls, name:str):
        if name is None or not len(name):
            return False 
        
        if name in cls.KnownGroups:
            return True 
        
        return False
    
    @classmethod 
    def addKnownGroup(cls, name:str):
        if name is None or not len(name):
            return 
        
        cls.KnownGroups[name] = False
        
    
    @classmethod 
    def valueTrue(cls, s:Signal):
        return signalTrue(s)
    
    @classmethod 
    def valueFalse(cls, s:Signal):
        return signalFalse(s)
    
    
    @classmethod 
    def oneBitHot(cls, s:Signal, allowAllZero:bool=False):
        return oneBitHot(s, allowAllZero)
    
    @classmethod 
    def oneHot(cls, signalsList:list, allowAllFalse:bool=False):
        return oneHot(signalsList, allowAllFalse)
        
    @staticmethod
    def coverAndVerify(m:Module, dut, group=None):
        '''
            Functions decorated with coverAndVerify, e.g.
                @Verification.coverAndVerify(m, dut)
                def testme(m:Module, counter:BasicCounter, includeCovers:bool=False):
                    pass 
                    
            will only be called when the main runner is called with the 'verify' parameter, e.g.
            
                python tests/module.py verify --cover
                
            Thus you can decorate a number of these and they'll only have effect when you desire.
            
            The --cover switch sets the includeCovers parameter.  You don't have to care about this,
            but you may want to have some/all cover cases only happen when this is True.
        '''
        if group is not None and len(group):
            Verification.addKnownGroup(group)
            
        def wrapper(fn):
            if not CLI.get().verify:
                log.info("No verifications enabled")
            else:
                if group is None or CLI.get().groupEnabled(group):
                    
                    if group is not None:
                        log.info(f"Verif {group} enabled")
                        Verification.KnownGroups[group] = True 
                    else:
                        log.info(f"Verif (anon) enabled")
                        
                    # call the function
                    fn(m, dut, includeCovers=CLI.get().covers)
                else:
                    log.info("Verif disabled")
        return wrapper
    
    @staticmethod 
    def depthProbe(fn):
        '''
            This is a (somewhat funky) way to wrap Cover statements 
            such that they will only be included when plumbing the depths 
            required to reach asserts etc.
            
            For example doing
            condition X:
                condition Y:
                    condition Z:
                        Assert(whatever)
                        
            This test may pass just because we never get down into the weeds
            where the Assert lives, giving the false impression that all is 
            well when in fact the situation is simply never reached and tested.
            
            Adding
            condition X:
                condition Y:
                    condition Z:
                        Assert(whatever)
                        
                        @Verification.depthProbe
                        def dp():
                            m.d.comb += Cover(whatever)
            
            will have no impact, unless depth probing is enabled, i.e. setting
            DepthProbingEnable or using the --depthprobe switch to the main runner, e.g.
            
                python tests/module.py verify --depthprobe
            
            Assuming all asserts are actually reached, you'll wind up with a ton
            of these cover traces (which is why we don't want this normally).
            
            However, if e.g. the depth isn't large enough, you'll get
                Unreached cover statement at /path/to/file:110
            errors.
            
            The reason we're using this clunky decorator/function system is so that
            these messages can actually point to the Cover() file and line in question.
            
            
                        
        '''
        if Verification.DepthProbingEnable or CLI.get().depthProbe:
            fn()