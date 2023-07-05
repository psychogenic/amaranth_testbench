'''
Created on Jun 29, 2023

@author: Pat Deegan
@copyright: Copyright (C) 2023 Pat Deegan, https://psychogenic.com
'''

from amaranth import Signal, Elaboratable, Module
from amaranth.build import Platform
import math


class BasicCounter(Elaboratable):
    '''
        A simple counter that counts up to MAX and restarts at 0.
    '''
    
    def __init__(self, maxValue:int):
    
        # max possible count value
        self.max = maxValue
        
        # output
        self.count = Signal(math.ceil(math.log2(maxValue))+1)
        
    def elaborate(self, platform:Platform):
        m = Module()
        with m.If(self.count < self.max):
            # as long as we're currently below max, 
            # increment on each clock
            m.d.sync += self.count.eq(self.count + 1)
        with m.Else():
            # otherwise, back to 0
            m.d.sync += self.count.eq(0)
                    
        return m
    
    def ports(self):
        return [self.count]

class ControlledCounter(Elaboratable):
    '''
        A simple counter that may be enabled/disabled and resetcount.
        
        While enabled, and not resetcount, it increments a counter on every cycle
        until a MAX value is reached at which point it starts back at 0.
        
        If resetcount the value will be zero, and not count forward.
        
        If not enabled, the value will be static.
    '''
    def __init__(self, maxValue:int):
    
        # max possible count value
        self.max = maxValue
        
        # public interface
        # inputs
        self.enable = Signal()
        self.resetcount = Signal()
        
        # output
        self.count = Signal(math.ceil(math.log2(maxValue))+1)
        
        
        
        
    def elaborate(self, _platform:Platform):
        m = Module()
        
        with m.If(self.resetcount):
            # set to 0 on resetcount, no counting while resetcount asserted
            m.d.sync += self.count.eq(0)
            
        with m.Elif(self.enable):
            # only count while enable is true
            
            with m.If(self.count < self.max):
                # as long as we're currently below max, 
                # increment on each clock
                m.d.sync += self.count.eq(self.count + 1)
            with m.Else():
                # otherwise, back to 0
                m.d.sync += self.count.eq(0)
                    
        return m
    
    def ports(self):
        return [self.resetcount, self.enable, self.count ]
    

class PulseWidthCounter(Elaboratable):
    '''
        A pulse width counter that always outputs the width of the 
        last pulse encountered.
        
        Count is only reset on new pulse
    '''
    
    def __init__(self, maxValue:int):
    
        # max possible count value
        self.max = maxValue
        
        # public interface
        # inputs
        self.input = Signal()
        
        # output
        self.count = Signal(math.ceil(math.log2(maxValue))+1)
        
    def elaborate(self, platform:Platform):
        m = Module()
        
        lastInput = Signal()
        
        with m.If(self.input):
            with m.If(lastInput):
                # we're counting
                with m.If(self.count < self.max):
                    m.d.sync += self.count.eq(self.count + 1)
            with m.Else():
                # new pulse
                m.d.sync += self.count.eq(1)
        
        m.d.sync += lastInput.eq(self.input)
        
        return m
    
    def ports(self):
        return [self.input, self.count ]
    
    

if __name__ == "__main__":
    # allow us to run this directly
    from amaranth.cli import main
    
    MaxCountValue = 0xAC
    m = Module() # top level
    m.submodules.basic = BasicCounter(MaxCountValue)
    m.submodules.controlled = ccounter = ControlledCounter(MaxCountValue)
    m.submodules.pwm = PulseWidthCounter(MaxCountValue)
    
    main(m, ports=ccounter.ports())




    


    
