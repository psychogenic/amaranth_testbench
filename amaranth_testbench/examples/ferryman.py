'''
Created on May 23, 2023

@author: Pat Deegan
@copyright: Copyright (C) 2023 Pat Deegan, https://psychogenic.com
'''


from amaranth import Signal, Elaboratable, Module
from amaranth.build import Platform

class FerryManProblem(Elaboratable):
    '''
        Classic ferryman problem:
         The ferryman for some reason needs to transport 3 items
             wolf
             goat
             cabbage
         to the other shore, and can only transport 1 at a time.
         
         The complication is that neither
           the wolf and the goat, nor
           the goat and the cabbage
         may remain together a shore without being attended to by the 
         ferryman (i.e. present on the same shore without him) for... 
         culinary reasons.
         
        This module implements:
         * one signal for every character in our problem, including the ferryman
         * one signal to indicate a failure state -- when a rule has been broken
           or someone eaten.
        
        You may thus set the inputs to anything you wish, but the failure flag 
        may be raised.  That is all.
        
        The solution is found below, using a single cover statement
    
    '''
    
    def __init__(self):

        # players in our system, ferryman and co.
        self.ferryman = Signal()
        
        self.wolf = Signal()
        self.goat = Signal()
        self.cabbage = Signal()
        
        # failure state output signal
        self.failure = Signal()
    
    def elaborate(self, _platform:Platform):
        m = Module()
        
        # utility state n has changed condition, just used to clarify conditions below
        def changed(n):
            return (lastStates[n] != curStates[n])
        
        # utility func failure setting 
        def fail():
            m.d.sync += self.failure.eq(1)
            
            
        # named signals for last state, for clarity
        lastFerryman = Signal()
        lastWolf = Signal()
        lastGoat = Signal()
        lastCabbage = Signal()
        
        # utility arrays of signals
        curStates = [ self.wolf,    self.goat,      self.cabbage ]
        lastStates =[ lastWolf,     lastGoat,       lastCabbage  ]
        
        
        # always keep track of last state
        m.d.sync += lastFerryman.eq(self.ferryman)
        for i in range(len(lastStates)):
            m.d.sync += lastStates[i].eq(curStates[i])
            
        
        ### All the ways we can fail ###
        
        
        # if the wolf is on same side as goat, but ferryman isn't: deadly fail
        with m.If( (self.wolf == self.goat) & (self.ferryman != self.wolf)):
            fail()
            
            
        # if the goat is on the same side as the cabbage, but ferryman isn't: no coleslaw for you. fail
        with m.If( (self.goat == self.cabbage) & (self.ferryman != self.goat)):
            fail()
        
        
        # can't change more than one item at a time
        with m.If( 
                  (changed(0) & changed(1)) 
                 | 
                  (changed(0) & changed(2)) 
                 | 
                  (changed(1) & changed(2))
                ):
            fail()
        
        # items may only change ALONG WITH the ferryman, otherwise it's a fail
        for i in range(len(lastStates)):
            with m.If(changed(i)): # this item has changed shores
                # unless it followed the ferryman, we've failed
                with m.If( (lastStates[i] != lastFerryman) | (curStates[i] != self.ferryman)):
                    fail()
        
        
        # ok, our tree is ready to elaborate, return the module
        return m


    def ports(self):
        return [self.ferryman, self.wolf, self.goat, self.cabbage, self.failure]


if __name__ == "__main__":
    # allow us to run this directly
    from amaranth.cli import main
    
    m = Module() # top level
    m.submodules.ferryprob = dev = FerryManProblem()
    main(m, ports=dev.ports())

