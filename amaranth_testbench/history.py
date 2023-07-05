'''
Created on Apr 18, 2023

@author: Pat Deegan
@copyright: Copyright (C) 2023 Pat Deegan, https://psychogenic.com
'''
from amaranth import Elaboratable, Signal, Module, Array, Cat

from amaranth.asserts import Assert, Assume
from amaranth.build import Platform
import math

import logging 

log = logging.getLogger(__name__)

class SignalUniqueNames:
    
    NameIDsUsed = dict()
    
    @classmethod 
    def generateUniqueName(cls, baseName):
        
        i = 0
        n = baseName 
        while n in SignalUniqueNames.NameIDsUsed:
            i += 1
            n = f'{baseName}{i}'
            
        SignalUniqueNames.NameIDsUsed[n] = True
        
        return n

class RiseFallPast(SignalUniqueNames):
    
    def __init__(self, histIdx:int, s:Signal, numCyclesToTrack:int=50):
        
        npref = self.generateUniqueName(f'trk{histIdx}_rf_{s.name}')
        
        self.rose = Signal(name=f'{npref}_rose')
        self.fell = Signal(name=f'{npref}_fell')
        self.rose_trace = Signal(numCyclesToTrack, name=f'{npref}_rosetrace')
        self.fell_trace = Signal(numCyclesToTrack, name=f'{npref}_felltrace')
        self.rose_past = Signal(numCyclesToTrack, name=f'{npref}_rosepast')
        self.fell_past = Signal(numCyclesToTrack, name=f'{npref}_fellpast')

        
        
class SignalHistory(SignalUniqueNames):
    
    def __init__(self, histIdx:int, s:Signal, numCyclesToTrack:int=50):
        self.signal = s 
        self.name = s.name 
        self.width = len(s)
        self.numCyclesToTrack = numCyclesToTrack
        
        
        self.usingPast = False
        self.usingRiseFallPast = False
        
        
        npref = self.generateUniqueName(f'trk{histIdx}_s_{s.name}')
            
        
        self.riseFallPast = RiseFallPast(histIdx, s, numCyclesToTrack)
        sigHistArray = [None]*self.numCyclesToTrack
        for i in range(0, self.numCyclesToTrack):
            s = Signal(self.width, name=f'{npref}_st{i}')
            sigHistArray[i] = s
            
        self.history = sigHistArray
        self.past = Signal(self.width*numCyclesToTrack, name=f'{npref}_past')
            



class History(Elaboratable):
    '''
        Track the history of signals of interest.
        
        Past and all my old friends for testing seem to be deprecated and
        the only info received on best practice usage was "use registers", 
        thus this universal container for registers and handling the past.
        
        This utility class lets you preserve and observe the history of 
        signals of interest.
        
        @copyright: (C) 2023 Pat Deegan, https://psychogenic.com
        
        Basic attempt to replace Past() functions.  Rather than working backwards,
        you track() signals of interest and then can access their state at any point
        (up to numCyclesToTrack), e.g.
        
        
        # initialize a history object
        
        hist = History()
        
        # you may pass it a maximum number of states to preserve
        # with History(numCyclesToTrack=25)
        
        # tell it which signals are of interest
        hist.track(somesignal)
        hist.track(anothersignal)
        
        
        # ...  
        
        # when doing verification the
        #  valueAt(SIGNAL, STEPINDEX)
        # method is the value of SIGNAL at clock/step STEPINDEX
        
        # since we don't always know/care how many steps we've performed 
        # and often 
        
        
        # two cycles after somesignal rises, anothersig will be true
        with m.If( (hist.cycle == 3) & 
                    ~hist.valueAt(somesignal, 0) &
                    hist.valueAt(somesignal, 1)):
            m.d.comb += Assert(anothersig == 1)
    '''
    
    HistoryModuleCount = 0
    MinCapacity = 1e6 # arbitrarily huge
    MaxCapacity = 0
    
    @classmethod 
    def new(cls, m:Module, numCyclesToTrack:int=100, name:str=None):
        '''
            Classmethod to create a new History instance and ensure
            all setup (adding to module) is handled.
            
            myTracker = History.new(m, numCyclesToTrack
        
        '''
        
        hModCount = cls.HistoryModuleCount
        
        hist = cls(numCyclesToTrack, name)
        
        if hist.name is not None:
            name = hist.name
        elif hModCount:
            name = f'_history{hModCount}'
        else:
            name = '_history'
        setattr(m.submodules, name, hist)
        return hist 
    
    def __init__(self, numCyclesToTrack:int=100, name:str=None):
        '''
            History Constructor.
            @param numCyclesToTrack: Optional max history to hold for every signal tracked, defaults to 100
             
        '''
        self.name = name
        
        
        self._idx = History.HistoryModuleCount
        History.HistoryModuleCount += 1
        if numCyclesToTrack > History.MaxCapacity:
            History.MaxCapacity = numCyclesToTrack
        if numCyclesToTrack < History.MinCapacity:
            History.MinCapacity = numCyclesToTrack
        
        
        self.registers = Array() # cache for the signals we are tracking
        self.registerInfo = dict() # all the info on signals tracked
        # self.riseFallPast = Array()
        self.regmap = dict() # signal name to idx in reg/regInfo
        
        self.numCyclesToTrack = numCyclesToTrack
        
        
        
        self._cycle = Signal(range(numCyclesToTrack + 1), name=SignalHistory.generateUniqueName('cycle')) # clock ticks counter
        self.cyclespassed = Signal(numCyclesToTrack, name=SignalHistory.generateUniqueName('cyclespassed'))
        
        
        
    @property 
    def cycle(self) -> Signal:
        '''
            the cycle (tick) counter
        '''
        return self._cycle
    
    
    
    def cyclePassed(self, cycleNum:int):
        if cycleNum > self.numCyclesToTrack:
            raise ValueError(f'Checking cyclePassed for {cycleNum}: beyond history capacity')
        
        return self.cyclespassed[cycleNum]
    
    
    @property
    def started(self):
        return self.cyclePassed(0)
    
    
        
    def track(self, s:Signal):
        '''
            track -- add signal to list of those for which we take valueAts
            @param s: signal to keep track of
        '''
        
        
        sigHist = SignalHistory(self._idx, s, self.numCyclesToTrack)
        
        # extending the object to give it a UID
        s.__histname = SignalHistory.generateUniqueName(s.name)
        
        
        regIdx = len(self.registers)
        self.registerInfo[self.internalNameFor(s)] = sigHist
        self.registers.append(s)
        self.regmap[self.internalNameFor(s)] = regIdx


    def trackAll(self, signals:list):
        '''
            keep track of every signal in [list]
        '''
        for s in signals:
            self.track(s)
            
    def valueAt(self, s:Signal, cycleNum:int):
        '''
            valueAt -- get the value of the signal at tick cycleNum
            @param s: Signal of interest (must be track()ed)
            @param cycleNum: cycle index we are looking at
            
            @note: signal must be tracked and cycleNum must be passed already to 
            contain anything valid. 
        '''
        
        
        if cycleNum > self.numCyclesToTrack:
            raise ValueError('looking at past value > than total history capacity')
            
            
        return self.registerInfo[self.internalNameFor(s)].history[cycleNum]
    
    def valueTrue(self, s:Signal):
        '''
            safely use signal in multi-condition if/asserts
            
            m.If(sig1 & sig2)  will work as expected for single-bit signals
            but 
            m.If(hist.valueTrue(sig1) & hist.valueTrue(sig2)) 
            will always work, regardless of width.
        '''
        return s.bool()
    
    def valueFalse(self, s:Signal):
        '''
            safely use signal in multi-condition if/asserts
            
            m.If(~sig1 & ~sig2)  will work as expected for single-bit signals
            but 
            m.If(hist.valueFalse(sig1) & hist.valueFalse(sig2)) 
            will always work, regardless of width.
        '''
        return ~(s.bool())
    
    
    
    def past(self, s:Signal, stepsAgo:int=1):
        '''
            past -- the value of signal s stepsAgo cycles in the past.
            
            @param s: Signal of interest (must be track()ed)
            @param stepsAgo: optional number of cycles in the past, defaults to 1
            
            @note: signal must be tracked and stepsAgo must be less than 
            actual number of cycles passed to be valid
        '''
        
        if stepsAgo < 1:
            raise ValueError('past stepsAgo MUST be >= 1.  Remember: you\'re livin\' in the past, maaaan')
        
        if stepsAgo > self.numCyclesToTrack:
            raise ValueError('looking at past value > than total history capacity')
        
        regInfo = self.regInfoFor(s)
        regInfo.usingPast = True
        
        sstart = self.sliceStart(s, stepsAgo - 1)
        send = self.sliceEnd(s, stepsAgo - 1)
        #print(f"PAST: [{sstart}:{send}]")
        if sstart >= len(regInfo.past) or send > len(regInfo.past):
            raise ValueError('looking at past value > than total history capacity')
            
        return regInfo.past[sstart:send]
    
    def pastTrue(self, s:Signal, stepsAgo:int=1):
        '''
            pastTrue 
            Signal, stepsAgo cycles in the past, evaluated to True
            
            
            @param s: Signal of interest (must be track()ed)
            @param stepsAgo: optional number of cycles in the past, defaults to 1
            
            @note: signal must be tracked and stepsAgo must be less than 
            actual number of cycles passed to be valid
            
        '''
        return self.valueTrue(self.past(s, stepsAgo))
    
    def pastFalse(self, s:Signal, stepsAgo:int=1):
        '''
            pastFalse
            Signal, stepsAgo cycles in the past, evaluated to False
            
            
            @param s: Signal of interest (must be track()ed)
            @param stepsAgo: optional number of cycles in the past, defaults to 1
            
            @note: signal must be tracked and stepsAgo must be less than 
            actual number of cycles passed to be valid
            
        '''
        return self.valueFalse(self.past(s, stepsAgo))
    
    def pastSequence(self, s:Signal, numStepsBackWidth:int=2):
        '''
            get a signal (numStepsBackWidth - 1)*signal.width bits wide representing
            the past states for signal.
            
            For a 1-bit signal, hist.pastN(4) would return e.g.
            
            pastN => 0b1110
            where 
            pastN[0] is one cycle ago (0)
            pastN[1] is two cycles ago (1)
            ...
        
        '''
        if numStepsBackWidth < 2:
            return self.past(s, numStepsBackWidth)
        
        if numStepsBackWidth > self.numCyclesToTrack:
            raise ValueError('looking at past value > than total history capacity')
        
        regInfo = self.regInfoFor(s)
        regInfo.usingPast = True
        
        sstart = self.sliceStart(s, 0)
        send = self.sliceEnd(s, numStepsBackWidth - 1)
        log.debug(f"SLICE SIZE {sstart}:{send}")
        return regInfo.past[sstart:send]
    
    def pastSequenceWas(self, s:Signal, valuesFromEarliestToMostRecent:list):
        '''
            pastSequenceWas
            @param s: Signal in question (must be tracked)
            @param values: list of values, sorted as a human can grok (see note)
            
            @return: conditional
            
            Returns something you can use in an m.If() to say,
            whichever cycle we are at, 1,2,...n cycles ago the signal 
            matched these values.
            
            @note: The values list is ordered in a way that makes code easy (for me?)
            to understand, i.e. furthest in time first in the list
            For example:
                [5, 4, 3, 2, 1]
            says the signal should've been
                5 => 5 cycles ago
                4 => 4 cycles ago
                ...
                1 => 1 cycle ago
            
            @note: that this doesn't imply anything about the signal "now", 
            only what it was 1 (and more) cycles ago
            
        '''
        massagedSequenceAsValue = self.orderPastSignalStatesEarliestToLast(s, valuesFromEarliestToMostRecent)
        #log.debug(valuesFromEarliestToMostRecent)
        numValues = len(valuesFromEarliestToMostRecent)
        numStepsBack =  numValues + 1
        
        if numValues:
            # log.debug(str(((self.cycle >= numValues) & (self.pastSequence(s, numStepsBack) == massagedSequenceAsValue))))
            return ((self.cycle >= numValues) & (self.pastSequence(s, numStepsBack) == massagedSequenceAsValue))
    
    
    
    def pastWasConstant(self, s:Signal, value:int, numCycles:int=2):
        '''
            pastWasConstant
            
            @param s: Signal in question (must be tracked)
            @param value: the signal value we expect
            @param numCycles: how long it was constant for.
             
            @return: conditional
            
            Returns something you can stick in an m.If() to say
            if this signal had this value for this last numCycles cycles
            then ...
            
            @note: that this doesn't imply anything about the signal "now", 
            only what it was 1 (and more) cycles ago
            
        '''
        return self.pastSequenceWas(s, [value]*numCycles)
    
    def orderPastSignalStatesEarliestToLast(self, s:Signal, valuesFromEarliestToLast:list):
        # used internally for past* calls
        return self.orderPastSignalStatesLastToEarliest(s, list(reversed(valuesFromEarliestToLast)))
    
    def orderPastSignalStatesLastToEarliest(self, s:Signal, valuesFromLastToEarliest:list):
        # used internally for past* calls
        mask = 0
        sigWidth = s.shape().width
        for i in range(sigWidth):
            mask |= 1 << i 
            
        val = 0
        for i in range(len(valuesFromLastToEarliest)):
            pastState = valuesFromLastToEarliest[i]
            val |= (pastState & mask) << (sigWidth * i)
            
        return val
        
        
    
    
    
    def stable(self, s:Signal, stepsAgo:int=0):
        return ~(self.changed(s, stepsAgo))
    def changed(self, s:Signal, stepsAgo:int=0):
        return self.rose(s, stepsAgo) | self.fell(s, stepsAgo)
        
    def rose(self, s:Signal, stepsAgo:int=0):
        '''
            rose -- if the signal of interest just went from low to high
            @param s: Tracked signal to check 
        '''

        if stepsAgo:
            return self.pastRose(s, stepsAgo)
        
        regInfo = self.regInfoFor(s)
        regInfo.usingRiseFallPast = True
        regInfo.usingPast = True
        
        # return (self.started & self.pastFalse(s) & self.valueTrue(s))
        return (self.started & self.pastFalse(s) & self.valueTrue(s))
        
        # return regInfo.riseFallPast.rose
    
    def fell(self, s:Signal, stepsAgo:int=0):
        '''
            fell - if the signal of interest just went from high to low
            @param s: Tracked signal to check 
        '''
        
        if stepsAgo:
            return self.pastFell(s, stepsAgo)
        
        regInfo = self.regInfoFor(s)
        regInfo.usingRiseFallPast = True
        regInfo.usingPast = True
        
        # return (self.started & self.pastTrue(s) & self.valueFalse(s))
        return (self.pastTrue(s) & self.valueFalse(s))
        
        # return self.riseFallPast[self.regmap[s.name]].fell
        # return regInfo.riseFallPast.fell
    
    
    def pastRose(self, s:Signal, stepsAgo:int=1):
        '''
            roseInPast -- whether signal in question rose stepsAgo cycles ago.
            
        '''
        regInfo = self.regInfoFor(s)
        regInfo.usingRiseFallPast = True
        
        
        eventHistory = regInfo.riseFallPast.rose_past
        
        #return ((self.cycle >= stepsAgo) &  
        return   self._riseFallPastEvents(regInfo.riseFallPast.rose, eventHistory, stepsAgo)
    
    def roseWithin(self, s:Signal, numCycles:int=1):
        '''
            Rose at any point within the last numCycle cycles
        
        '''
        regInfo = self.regInfoFor(s)
        regInfo.usingRiseFallPast = True
        
        eventHistory = regInfo.riseFallPast.rose_past
        
        eventsValue = self._riseFallPastEvents(regInfo.riseFallPast.rose, eventHistory, stepsAgo=1, includeStepsBack=(numCycles-1))
        
        return (eventsValue.bool() | self.rose(s))
    
    def roseOnCycle(self, s:Signal, atCycle:int):
        '''
            observe rose status for cycle atCycle (not we are counting forward here, 
            from cycle 0.. use pastRose or roseWithin if thinking backward from arbitrary point.
            
            @param s: Signal (must be tracked)
            @param atCycle: cycle in question
            
            @return: returns a single bit value, which may be evaled true of false in m.If() and asserts  
        
        '''
        
        regInfo = self.regInfoFor(s)
        regInfo.usingRiseFallPast = True
        
        if atCycle >= self.numCyclesToTrack:
            raise ValueError(f'trying to observe rose beyond history capacity ({atCycle} cycle)')
        
        return regInfo.riseFallPast.rose_trace[atCycle]
        
    def fellOnCycle(self, s:Signal, atCycle:int):
        
        '''
            observe fell status for cycle atCycle (not we are counting forward here, 
            from cycle 0.. use pastFell or fellWithin if thinking backward from arbitrary point.
            
            @param s: Signal (must be tracked)
            @param atCycle: cycle in question
            
            @return: returns a single bit value, which may be evaled true of false in m.If() and asserts  
        
        '''
        
        regInfo = self.regInfoFor(s)
        regInfo.usingRiseFallPast = True
        
        if atCycle >= self.numCyclesToTrack:
            raise ValueError(f'trying to observe fell beyond history capacity ({atCycle} cycle)')
        
        return regInfo.riseFallPast.fell_trace[atCycle]
        
        
    
    def fellWithin(self, s:Signal, numCycles:int=1):
        '''
            Rose at any point within the last numCycle cycles
        
        '''
        regInfo = self.regInfoFor(s)
        regInfo.usingRiseFallPast = True
        
        eventHistory = regInfo.riseFallPast.fell_past
        
        eventsValue = self._riseFallPastEvents(regInfo.riseFallPast.fell, eventHistory, stepsAgo=1, includeStepsBack=(numCycles-1))
        
        # return ((self.cycle >= numCycles) &  (eventsValue.bool() | self.fell(s)))
        return (eventsValue.bool() | self.fell(s))
        
    
    def pastFell(self, s:Signal, stepsAgo:int=1):
        '''
            fellInPast -- whether signal in question rose stepsAgo cycles ago.
            
        '''
        
        regInfo = self.regInfoFor(s)
        regInfo.usingRiseFallPast = True
        
        eventHistory = regInfo.riseFallPast.fell_past
        
        return ((self.cycle >= stepsAgo) &  
                self._riseFallPastEvents(regInfo.riseFallPast.fell, eventHistory, stepsAgo))
        
        
        #return ((self.cycle >= stepsAgo) &  
        #        self._riseFallPastEvents(regInfo.riseFallPast.fell, eventHistory, stepsAgo))
        
        return (self._riseFallPastEvents(regInfo.riseFallPast.fell, eventHistory, stepsAgo))
    
    
    def _riseFallPastEvents(self, s:Signal, eventHistory:Signal, stepsAgo:int=1, includeStepsBack:int=0):
        
        if stepsAgo < 1:
            raise ValueError('past stepsAgo MUST be >= 1.  Remember: you\'re livin\' in the past, maaaan')
        
        finalStepBack = stepsAgo+includeStepsBack
        if finalStepBack > self.numCyclesToTrack:
            raise ValueError('looking at past value > than total history capacity')
        
        
        sstart = self.sliceStart(s, stepsAgo - 1)
        send = self.sliceEnd(s, finalStepBack - 1)
        
        
        if sstart >= len(eventHistory) or send > len(eventHistory):
            raise ValueError(f'looking at past rise/fall value > than total history capacity {len(eventHistory)} vs [{sstart}:{send}]')
            
        return eventHistory[sstart:send]
    
    
    
    def wasEver(self, s:Signal, value:int, numCyclesBack:int=None):
        '''
            @param s: signal in question (must be tracked)
            @param value: the value of interest 
            @param numCyclesBack: (optional) maximum # of cycles to look back  
            
            @return: returns a conditional, that can be put in a m.If or assert...
            
            The conditional will be true if the signal was ever == to this value
            (within the # of cycles back)
        '''
        if numCyclesBack is None:
            numCyclesBack = self.numCyclesToTrack
            
        if numCyclesBack > self.numCyclesToTrack:
            raise ValueError('looking at sequence > than total history capacity')
        
        v = None 
        for i in range(1, numCyclesBack):
            if v is None:
                v = (self.past(s, i) == value)
            else:
                v = v | (self.past(s, i) == value)
                
        return v
    
    def wasNever(self, s:Signal, value:int, numCyclesBack:int=None):
        '''
        
            @param s: signal in question (must be tracked)
            @param value: the value of interest 
            @param numCyclesBack: (optional) maximum # of cycles to look back  
            
            @return: returns a conditional, that can be put in a m.If or assert...
            
            The conditional will be true if the signal was NEVER == to this value
            (within the # of cycles back)
            
        '''
        return ~(self.wasEver(s, value, numCyclesBack))
    
    def wasConstant(self, s:Signal, value:int, numCyclesBack:int=2):
        '''
            wasConstant
            Returns something you can stick in an m.If() to say
            if this signal had value value for the last numCyclesBack many ticks
            then ...
        '''
        vList = [value] * numCyclesBack
        return self.pastSequenceWas(s, vList)
    
    
    @property
    def now(self):
        '''
            now - current timestep/tick count
        '''
        return self.cycle
    
    def sequence(self, s:Signal, startCycle:int, numCycles:int):
        '''
            sequence -- get the value(s) of a signal over multiple ticks, all as one long blob
            
            example
            m.If(history.sequence(inputpulses, 0, 6) == 0b100111):
                # ...
        '''
        if (startCycle + numCycles) > self.numCyclesToTrack:
            raise ValueError('want sequence > than total history capacity')
        
        
        return Cat(self.regInfoFor(s).history[startCycle:startCycle+numCycles])
    
    
    def isEver(self, s:Signal, value:int, startCycle:int=0, numCycles:int=None):
        '''
            Returns a testable compound statement concerning the value of 
            signal from startCycle, for numCycles
        
        '''
        if numCycles is None or (startCycle + numCycles) > self.numCyclesToTrack:
            numCycles = self.numCyclesToTrack - startCycle
            
        
        if (startCycle + numCycles) > self.numCyclesToTrack:
            raise ValueError('looking at sequence > than total history capacity')
        
        v = None 
        for i in range(startCycle, numCycles):
            if v is None:
                v = (self.valueAt(s, i) == value)
            else:
                v = v | (self.valueAt(s, i) == value)
                
        return v
    
    def isNever(self, s:Signal, value:int, startCycle:int=0, numCycles:int=None):
        return ~(self.isEver(s, value, startCycle, numCycles))
    
    def isConstant(self, s:Signal, value:int, startCycle, numCycles:int=2):
        '''
            isConstant
            Returns something you can stick in an m.If() to say
            if this signal had value value for this many ticks, starting at tick x
            then ...
        '''
        vList = [value] * numCycles
        return self.followsSequence(s, vList, startCycle, numCycles)
    
    def followsSequence(self, s:Signal, values:list, startCycle:int=0, numCycles:int=None):
        '''
            followsSequence
            Similar to isConstant(), but rather than being constant, the value is expected 
            to have followed the pattern is the values list.
            
            with m.If(history.followedSequenc(mysignal, [1,2,3,4], startCycle=10)):
                # ... various asserts etc
                
            
        '''
        if numCycles is None or not numCycles:
            numCycles = len(values)
        v = None
        vIdx = 0
        
        endTick = startCycle+numCycles
        if startCycle >= endTick:
            raise ValueError('Must have at least 1 tick in sequence')
            return 1
        
        
        if (startCycle + numCycles) > self.numCyclesToTrack:
            raise ValueError('looking to gen sequence > than total history capacity')
        
        for i in range(startCycle, startCycle+numCycles):
            if v is None:
                v = (self.valueAt(s, i) == values[vIdx])
            else:
                v = v & (self.valueAt(s, i) == values[vIdx])
                
            vIdx += 1
        # print(v)
        if v is None:
            raise ValueError('History got nothing from valueAt sequence?')
        return v
    
    
    def internalNameFor(self, s:Signal) -> str:
        return s.__histname
    
    def regInfoFor(self, s:Signal) -> SignalHistory:
        # shorthand utility method
        return self.registerInfo[self.internalNameFor(s)]
            
    def elaborate(self, _plat:Platform):
        m = Module()
        
        
        # unclear on the possible detrimental impacts of this
        # because it's hard to sync with externally created
        # sby file depth settings and because of unknowns 
        # (on my part) related to the solvers, but prove mode
        # messes with things a lot and fails for reasons 
        # outside of the tested module and in here unless 
        # we assume we never go beyond the actual space we 
        # have for recording the past
        if History.MaxCapacity:
            m.d.comb += [
                    Assume(self.cycle < History.MinCapacity)
            ]
    
        
        
        # this convoluted tick counter setup isn't needed for
        # BMC but anything involving the past get's pretty 
        # broken in prove mode.  
        # combined with the conditional block below, seems
        # to solve the issue
        with m.If(self.started):
            m.d.sync += self.cycle.eq(self.cycle + 1)
        with m.Else():
            m.d.sync += [
                self.cycle.eq(1),
                self.cyclespassed[0].eq(1)
            ]
            
        
        
        # generate logic for every tracked register
        for sigHname, regInfo in self.registerInfo.items(): #  in range(len(self.registers)):
            
            sig = self.registers[self.regmap[sigHname]]
            #regInfo = self.registerInfo[ridx]
            
            # prove-mode sanity, see note above on
            # If(self.started) for tick counts
            with m.If(~self.started):
                m.d.sync += [
                    regInfo.past.eq(0),
                    regInfo.riseFallPast.rose.eq(0),
                    regInfo.riseFallPast.rose_trace.eq(0),
                    regInfo.riseFallPast.rose_past.eq(0),
                    regInfo.riseFallPast.fell.eq(0),
                    regInfo.riseFallPast.fell_trace.eq(0),
                    regInfo.riseFallPast.fell_past.eq(0),
                ]
                
            
            for t in range(self.numCyclesToTrack):
                with m.If(self.cycle == t):
                    
                    # keep an eye on how far along we are
                    m.d.sync += self.cyclespassed[t].eq(1)
                    
                    # track history as signal size blocks
                    m.d.sync += regInfo.history[t].eq(sig)
                    
                    if False:
                        with m.If(self.cycle.bool()):
                            m.d.comb += Assert(self.cyclespassed[t-1])
                        
                        
                    
                    if regInfo.usingPast:
                        m.d.sync += regInfo.past.eq((regInfo.past << regInfo.width) | sig) 
                        
                            
                    if regInfo.usingRiseFallPast and t:
                        prevStep = t - 1
                        riseFallPast = regInfo.riseFallPast
                        
                        prevStepWasTrue = (regInfo.history[prevStep]).bool()
                        with m.If(sig.bool()):
                            # now "high" 
                            # surely did not fall
                            m.d.sync += [
                                riseFallPast.fell_past.eq(riseFallPast.fell_past << 1),
                                riseFallPast.fell.eq(0)
                            ]
                            with m.If(~prevStepWasTrue):
                                # and was low: rose
                                m.d.sync += [
                                    riseFallPast.rose_trace[t].eq(1),
                                    riseFallPast.rose.eq(1),
                                    riseFallPast.rose_past.eq((riseFallPast.rose_past << 1) | 1)
                                    
                                ]
                            with m.Else():
                                m.d.sync += [
                                    
                                    riseFallPast.rose.eq(0),
                                    riseFallPast.rose_past.eq( (riseFallPast.rose_past << 1))
                                ]
                                
                                
                        with m.Else():
                            # low 
                            # surely did not rise
                            m.d.sync += [
                                riseFallPast.rose_past.eq(riseFallPast.rose_past << 1),
                                riseFallPast.rose.eq(0)
                            ]
                                
                            
                            
                            with m.If(prevStepWasTrue):
                                # and was high: fell
                                m.d.sync += [
                                    riseFallPast.fell_trace[t].eq(1),
                                    riseFallPast.fell.eq(1),
                                    riseFallPast.fell_past.eq((riseFallPast.fell_past << 1) | 1)
                                ]
                            with m.Else():
                                m.d.sync += [
                                    riseFallPast.fell_past.eq(riseFallPast.fell_past << 1),
                                    riseFallPast.fell.eq(0)
                                    ]
                                
                                    
                            
                    
        
        return m
    
    
        
    def sizeFor(self, s:Signal):
        return len(s)
    
    def sliceStart(self, s:Signal, cycleNum:int):
        ssize = self.sizeFor(s)
        return cycleNum*ssize
        
    def sliceEnd(self, s:Signal, cycleNum:int):
        return self.sliceStart(s, cycleNum) + self.sizeFor(s)


