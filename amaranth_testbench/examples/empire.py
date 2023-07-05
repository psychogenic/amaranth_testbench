'''
Created on Jun 29, 2023

@author: Pat Deegan
@copyright: Copyright (C) 2023 Pat Deegan, https://psychogenic.com
'''

from amaranth import Signal, Elaboratable, Module
from amaranth.build import Platform

class Empire(Elaboratable):
    '''
        A simple counter that may be enabled/disabled and reset.
        
        While enabled, and not reset, it increments a counter on every cycle
        until a MAX value is reached at which point it starts back at 0.
        
        If reset the value will be zero, and not count forward.
        
        If not enabled, the value will be static.
    '''
    
    def __init__(self, maxStrain:int=20):
    
        # max possible count value
        self.maxstrain = maxStrain
        
        self.war = Signal()
        self.slaveryreliance = Signal(8)
        self.borderintegrety = Signal(reset=1)
        self.overspending = Signal()
        self.corruption = Signal()
        self.monotheism = Signal()
        self.eastern_ascendency = Signal()
        
        self.strain = Signal(10)
        self.rome = Signal(reset=1)
        
        #internal
        self.warcounter = Signal(8)
        
    def decrepitudeValue(self):
        # some random calculation of how bad things are going
        return (self.overspending * 5) \
                + (self.corruption * 10)  \
                + (self.monotheism * 3) \
                + (self.eastern_ascendency * 4) \
                + ((~self.borderintegrety)* 8) \
                + (self.slaveryreliance >> 3) \
                + (self.warcounter >> 2) 
        
    def elaborate(self, platform:Platform):
        m = Module()
        with m.If(self.war):
            m.d.sync += self.warcounter.eq(self.warcounter + 3)
        with m.Else():
            m.d.sync += self.warcounter.eq(0)
            
        m.d.sync += self.strain.eq(self.decrepitudeValue())
        
        with m.If( self.decrepitudeValue() > self.maxstrain):
            m.d.sync += self.rome.eq(0)
               
        return m
   
        
    def ports(self):
        return [self.war, self.slaveryreliance, self.overspending, 
                self.corruption, self.monotheism, 
                self.eastern_ascendency, self.borderintegrety, 
                self.rome, self.strain]
    
