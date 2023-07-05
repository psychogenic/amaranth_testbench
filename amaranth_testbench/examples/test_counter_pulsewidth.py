'''
Created on Jun 29, 2023

@author: Pat Deegan
@copyright: Copyright (C) 2023 Pat Deegan, https://psychogenic.com
'''
from amaranth_testbench.examples.counter import PulseWidthCounter

from amaranth import Signal, Module
from amaranth import ResetSignal # ClockDomain, ClockSignal, 

if __name__ == "__main__":
    # allow us to run this directly
    from amaranth.asserts import Assert, Cover, Assume
    from amaranth.sim import Delay, Tick
    from amaranth_testbench.cli import CLI, main
    from amaranth_testbench.simulator import Simulator
    from amaranth_testbench.verification import Verification
    from amaranth_testbench.history import History
    
    
    MaxCountValue = 60
    cli = CLI.get()
    m = Module() # top level
    m.submodules.counter = dut = PulseWidthCounter(MaxCountValue)
    
    rst = Signal()
    m.d.comb += ResetSignal().eq(rst)
    m.d.comb += [
        Assume(~rst), # don't play with reset
    ]
    
    # create a history instance and keep track 
    # off all the public signals (enable, resetcount and count)
    # NOTE: numCyclesToTrack MUST be > than the check depth for this to work.
    hist = History.new(m, numCyclesToTrack=MaxCountValue*2)
    hist.trackAll(dut.ports())
    
    
        
    @Simulator.simulate(m, 'count_pulses', traces=dut.ports(), clockFreq=1e6)
    def countPulses():
        yield Delay(5e-6)
        yield dut.input.eq(1)
        yield Tick()
        yield Tick()
        yield Tick()
        yield dut.input.eq(0)
        yield Delay(5e-6)
        yield dut.input.eq(1)
        yield Delay(25e-6)
        yield dut.input.eq(0)
        yield Delay(10e-6)
        
        
    @Verification.coverAndVerify(m, dut)
    def noOverflow(m:Module, counter:PulseWidthCounter, includeCovers:bool=False):
        # no matter what, counter never exceeds max
        m.d.comb += Assert(counter.count <= counter.max)
        
    @Verification.coverAndVerify(m, dut)
    def sequencesAndDepth(m:Module, counter:PulseWidthCounter, includeCovers:bool=False):

        with m.If(hist.cycle > 20):
            with m.If(hist.pastSequenceWas(counter.input, [1,0,1,1,1,1,0,0,0,1,1,1,1,1])):
                m.d.comb += Assert(counter.count == 5)
                @Verification.depthProbe
                def dp():
                    m.d.comb += Cover(counter.count == 5)
                            
        if includeCovers:
            
            # simply find some way to get to the max counter value
            m.d.comb += Cover(counter.count == counter.max)
            
            
                    
                    
            
    
    main(m, ports=dut.ports())